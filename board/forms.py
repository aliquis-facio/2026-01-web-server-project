from pathlib import Path

from django import forms
from django.conf import settings

from .models import Comment, Post


class PostForm(forms.ModelForm):
    media_file = forms.FileField(
        label="파일",
        required=False,
    )

    class Meta:
        model = Post
        fields = (
            "title",
            "content",
            "media_file",
            "ascii_width",
            "max_frames",
            "frame_interval",
            "gif_duration",
            "char_style",
        )
        widgets = {
            "content": forms.Textarea(attrs={"rows": 5}),
            "ascii_width": forms.NumberInput(
                attrs={
                    "min": 20,
                    "step": 10,
                    "placeholder": "비우면 원본 너비",
                }
            ),
            "max_frames": forms.NumberInput(attrs={"min": 1, "max": 20}),
            "frame_interval": forms.NumberInput(attrs={"min": 1, "max": 300}),
            "gif_duration": forms.NumberInput(attrs={"min": 20, "max": 1000, "step": 20}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detected_media_type = None
        self.fields["ascii_width"].required = False
        for field in self.fields.values():
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing_class} form-control".strip()

    def _is_animated_gif(self, uploaded_file):
        position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
        try:
            from PIL import Image

            with Image.open(uploaded_file) as image:
                return bool(getattr(image, "is_animated", False)) and image.n_frames > 1
        except OSError as exc:
            raise forms.ValidationError("GIF 파일을 열 수 없습니다. 파일 형식을 확인하세요.") from exc
        finally:
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(position)

    def clean_media_file(self):
        media_file = self.cleaned_data.get("media_file")
        uploaded_file = self.files.get(self.add_prefix("media_file"))
        if not uploaded_file:
            return media_file

        extension = Path(uploaded_file.name).suffix.lower()
        allowed_extensions = settings.SUPPORTED_IMAGE_EXTENSIONS | settings.SUPPORTED_VIDEO_EXTENSIONS
        if extension not in allowed_extensions:
            allowed = ", ".join(sorted(allowed_extensions))
            raise forms.ValidationError(f"지원하지 않는 파일 형식입니다. 허용 확장자: {allowed}")

        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            limit_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise forms.ValidationError(f"파일은 {limit_mb}MB 이하만 업로드할 수 있습니다.")

        if extension == ".gif":
            self.detected_media_type = (
                Post.MediaType.VIDEO
                if self._is_animated_gif(uploaded_file)
                else Post.MediaType.IMAGE
            )
        elif extension in settings.SUPPORTED_VIDEO_EXTENSIONS:
            self.detected_media_type = Post.MediaType.VIDEO
        else:
            self.detected_media_type = Post.MediaType.IMAGE

        return media_file

    def clean(self):
        cleaned_data = super().clean()
        uploaded_file = self.files.get(self.add_prefix("media_file"))

        has_existing_media = bool(
            self.instance.pk and (self.instance.image or self.instance.video)
        )
        if not has_existing_media and not uploaded_file:
            raise forms.ValidationError("파일을 업로드하세요.")

        return cleaned_data

    def clean_ascii_width(self):
        value = self.cleaned_data.get("ascii_width")
        if value in (None, ""):
            return None
        if value < 20:
            raise forms.ValidationError("ASCII 너비는 20 이상이어야 합니다.")
        return value

    def clean_max_frames(self):
        value = self.cleaned_data["max_frames"]
        if not 1 <= value <= 20:
            raise forms.ValidationError("추출 프레임 수는 1부터 20 사이여야 합니다.")
        return value

    def clean_gif_duration(self):
        value = self.cleaned_data["gif_duration"]
        if not 20 <= value <= 1000:
            raise forms.ValidationError("GIF 재생 속도는 20ms부터 1000ms 사이여야 합니다.")
        return value


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("content",)
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "댓글을 입력하세요.",
                    "class": "form-control",
                }
            )
        }
