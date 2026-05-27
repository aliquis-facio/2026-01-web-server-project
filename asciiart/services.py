from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.db import transaction

from .converters import (
    ConversionError,
    convert_image_to_ascii_frame,
    convert_video_to_ascii_frames,
    get_image_dimensions,
    get_video_dimensions,
)
from .gif import GifRenderError, ascii_frames_to_gif, ascii_text_to_image


def process_post(post):
    from board.models import AsciiFrame, Post

    if not post.image and not post.video:
        raise ConversionError("업로드된 이미지 또는 영상 파일이 없습니다.")

    Post.objects.filter(pk=post.pk).update(status=Post.Status.PROCESSING, error_message="")
    post.refresh_from_db()

    try:
        if post.image:
            source_width, _ = get_image_dimensions(post.image.path)
            ascii_width = post.ascii_width or source_width
            post.ascii_width = ascii_width
            ascii_frames = [
                convert_image_to_ascii_frame(
                    post.image.path,
                    width=ascii_width,
                    charset=post.char_style,
                )
            ]
        else:
            source_width, _ = get_video_dimensions(post.video.path)
            ascii_width = post.ascii_width or source_width
            post.ascii_width = ascii_width
            ascii_frames = convert_video_to_ascii_frames(
                post.video.path,
                width=ascii_width,
                frame_interval=post.frame_interval,
                max_frames=post.max_frames,
                charset=post.char_style,
            )

        temp_dir = Path(settings.MEDIA_ROOT) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_gif = None
        temp_image = None
        if post.image:
            temp_image = temp_dir / f"post_{post.pk}_ascii.png"
            ascii_text_to_image(
                ascii_frames[0],
                font_size=10,
                padding=18,
            ).save(temp_image)
        elif post.video:
            temp_gif = temp_dir / f"post_{post.pk}_ascii.gif"
            ascii_frames_to_gif(
                ascii_frames,
                temp_gif,
                duration=post.gif_duration,
                font_size=10,
            )

        with transaction.atomic():
            post.ascii_frames.all().delete()
            AsciiFrame.objects.bulk_create(
                [
                    AsciiFrame(
                        post=post,
                        frame_index=index,
                        ascii_text=ascii_text,
                    )
                    for index, ascii_text in enumerate(ascii_frames, start=1)
                ]
            )

            if post.ascii_gif:
                post.ascii_gif.delete(save=False)
            if post.ascii_image:
                post.ascii_image.delete(save=False)

            if temp_image:
                with temp_image.open("rb") as image_file:
                    post.ascii_image.save(
                        f"post_{post.pk}_ascii.png",
                        File(image_file),
                        save=False,
                    )
                post.ascii_gif = None
            elif temp_gif:
                with temp_gif.open("rb") as gif_file:
                    post.ascii_gif.save(
                        f"post_{post.pk}_ascii.gif",
                        File(gif_file),
                        save=False,
                    )
                post.ascii_image = None
            else:
                post.ascii_image = None
                post.ascii_gif = None

            post.status = Post.Status.DONE
            post.error_message = ""
            post.save(
                update_fields=[
                    "ascii_width",
                    "ascii_image",
                    "ascii_gif",
                    "status",
                    "error_message",
                    "updated_at",
                ]
            )

        if temp_image:
            temp_image.unlink(missing_ok=True)
        if temp_gif:
            temp_gif.unlink(missing_ok=True)
        return ascii_frames

    except (ConversionError, GifRenderError, OSError, ValueError) as exc:
        Post.objects.filter(pk=post.pk).update(
            status=Post.Status.FAILED,
            error_message=str(exc),
        )
        raise
