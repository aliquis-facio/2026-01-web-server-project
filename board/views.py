import hashlib

from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from asciiart.converters import ConversionError
from asciiart.gif import GifRenderError
from asciiart.services import process_post

from .forms import CommentForm, PostForm
from .models import Like, Post


def _hash_uploaded_file(uploaded_file):
    hasher = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        hasher.update(chunk)

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    return hasher.hexdigest()


def _find_duplicate_upload(user, form, media_type, source_hash):
    cleaned_data = form.cleaned_data
    posts = Post.objects.filter(
        author=user,
        media_type=media_type,
        source_hash=source_hash,
        title=cleaned_data.get("title", ""),
        content=cleaned_data.get("content", ""),
        char_style=cleaned_data.get("char_style"),
        max_frames=cleaned_data.get("max_frames"),
        frame_interval=cleaned_data.get("frame_interval"),
        gif_duration=cleaned_data.get("gif_duration"),
    )

    ascii_width = cleaned_data.get("ascii_width")
    if ascii_width:
        posts = posts.filter(ascii_width=ascii_width)

    return posts.order_by("-created_at").first()


def post_list(request):
    if not request.user.is_authenticated:
        return render(
            request,
            "registration/login.html",
            {
                "form": AuthenticationForm(request),
                "next": request.get_full_path(),
                "is_index_login": True,
            },
        )

    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "latest")
    scope = request.GET.get("scope", "all")

    posts = Post.objects.select_related("author")

    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(content__icontains=query))

    if scope == "saved":
        posts = posts.filter(likes__user=request.user)
    elif scope == "mine":
        posts = posts.filter(author=request.user)
    else:
        scope = "all"

    posts = posts.annotate(like_count=Count("likes", distinct=True))

    if sort == "views":
        posts = posts.order_by("-view_count", "-created_at")
    elif sort == "likes":
        posts = posts.order_by("-like_count", "-created_at")
    else:
        posts = posts.order_by("-created_at")

    return render(
        request,
        "board/post_list.html",
        {
            "posts": posts,
            "query": query,
            "sort": sort,
            "scope": scope,
            "saved_post_ids": set(
                Like.objects.filter(user=request.user).values_list("post_id", flat=True)
            ),
        },
    )


@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_image = request.FILES.get("image")
            uploaded_video = request.FILES.get("video")
            media_type = Post.MediaType.IMAGE if uploaded_image else Post.MediaType.VIDEO
            source_hash = _hash_uploaded_file(uploaded_image or uploaded_video)
            duplicate_post = _find_duplicate_upload(
                request.user,
                form,
                media_type,
                source_hash,
            )
            if duplicate_post:
                messages.info(request, "이미 같은 업로드가 있어 기존 게시글로 이동했습니다.")
                return redirect("post_detail", post_id=duplicate_post.pk)

            post = form.save(commit=False)
            post.author = request.user
            post.status = Post.Status.PENDING
            post.source_hash = source_hash
            if uploaded_image:
                post.media_type = Post.MediaType.IMAGE
                post.video = None
            else:
                post.media_type = Post.MediaType.VIDEO
                post.image = None
            post.save()
            try:
                process_post(post)
                messages.success(request, "ASCII 변환이 완료되었습니다.")
            except (ConversionError, GifRenderError, OSError, ValueError) as exc:
                messages.error(request, f"변환에 실패했습니다: {exc}")
            return redirect("post_detail", post_id=post.pk)
    else:
        form = PostForm()

    return render(request, "board/post_form.html", {"form": form, "mode": "create"})


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related("author").prefetch_related(
            "ascii_frames",
            "comments__author",
            "likes",
        ),
        pk=post_id,
    )
    Post.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
    post.refresh_from_db(fields=["view_count"])

    frames = list(post.ascii_frames.values_list("ascii_text", flat=True))
    liked = request.user.is_authenticated and post.likes.filter(user=request.user).exists()

    return render(
        request,
        "board/post_detail.html",
        {
            "post": post,
            "ascii_frames": frames,
            "comment_form": CommentForm(),
            "liked": liked,
        },
    )


@login_required
def post_update(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return HttpResponseForbidden("작성자만 수정할 수 있습니다.")

    tracked_fields = ("ascii_width", "max_frames", "frame_interval", "gif_duration", "char_style")
    previous_options = {field: getattr(post, field) for field in tracked_fields}
    previous_image_name = post.image.name if post.image else ""
    previous_video_name = post.video.name if post.video else ""

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)
            image_changed = bool(request.FILES.get("image"))
            video_changed = bool(request.FILES.get("video"))
            media_changed = image_changed or video_changed

            if image_changed:
                updated_post.source_hash = _hash_uploaded_file(request.FILES["image"])
                if previous_video_name:
                    post.video.storage.delete(previous_video_name)
                updated_post.video = None
                updated_post.media_type = Post.MediaType.IMAGE
            elif video_changed:
                updated_post.source_hash = _hash_uploaded_file(request.FILES["video"])
                if previous_image_name:
                    post.image.storage.delete(previous_image_name)
                updated_post.image = None
                updated_post.media_type = Post.MediaType.VIDEO

            options_changed = any(
                previous_options[field] != getattr(updated_post, field)
                for field in tracked_fields
            )
            if media_changed or options_changed:
                updated_post.status = Post.Status.PENDING
            updated_post.save()

            if (updated_post.image or updated_post.video) and (media_changed or options_changed):
                try:
                    process_post(updated_post)
                    messages.success(request, "게시글과 ASCII 변환 결과를 갱신했습니다.")
                except (ConversionError, GifRenderError, OSError, ValueError) as exc:
                    messages.error(request, f"변환에 실패했습니다: {exc}")
            else:
                messages.success(request, "게시글을 수정했습니다.")

            return redirect("post_detail", post_id=updated_post.pk)
    else:
        form = PostForm(instance=post)

    return render(request, "board/post_form.html", {"form": form, "mode": "update", "post": post})


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return HttpResponseForbidden("작성자만 삭제할 수 있습니다.")

    if request.method == "POST":
        if post.image:
            post.image.delete(save=False)
        if post.video:
            post.video.delete(save=False)
        if post.ascii_image:
            post.ascii_image.delete(save=False)
        if post.ascii_gif:
            post.ascii_gif.delete(save=False)
        post.delete()
        messages.success(request, "게시글을 삭제했습니다.")
        return redirect("post_list")

    return render(request, "board/post_confirm_delete.html", {"post": post})


def download_ascii_txt(request, post_id):
    post = get_object_or_404(Post.objects.prefetch_related("ascii_frames"), pk=post_id)
    if not post.ascii_frames.exists():
        raise Http404("다운로드할 ASCII 프레임이 없습니다.")

    blocks = []
    for frame in post.ascii_frames.all():
        label = "ASCII ART" if post.is_image else f"FRAME {frame.frame_index}"
        blocks.append(f"[{label}]\n\n{frame.ascii_text}")

    response = HttpResponse("\n\n".join(blocks), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="post_{post.pk}_ascii.txt"'
    return response


def download_ascii_gif(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not post.ascii_gif:
        raise Http404("다운로드할 ASCII GIF 파일이 없습니다. 영상 게시글만 GIF를 제공합니다.")

    return FileResponse(
        post.ascii_gif.open("rb"),
        as_attachment=True,
        filename=f"post_{post.pk}_ascii.gif",
    )


@login_required
@require_POST
def toggle_like(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("post_detail", post_id=post.pk)


@login_required
@require_POST
def comment_create(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect("post_detail", post_id=post.pk)
