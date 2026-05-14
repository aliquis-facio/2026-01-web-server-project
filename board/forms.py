from pathlib import Path

from django import forms
from django.conf import settings

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = (
            "title",
            "content",
            "image",
            "video",
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
        self.fields["image"].required = False
        self.fields["video"].required = False
        self.fields["ascii_width"].required = False
        for field in self.fields.values():
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing_class} form-control".strip()

    def clean_image(self):
        image = self.cleaned_data.get("image")
        uploaded_image = self.files.get(self.add_prefix("image"))
        if not uploaded_image:
            return image

        extension = Path(uploaded_image.name).suffix.lower()
        if extension not in settings.SUPPORTED_IMAGE_EXTENSIONS:
            allowed = ", ".join(sorted(settings.SUPPORTED_IMAGE_EXTENSIONS))
            raise forms.ValidationError(f"지원하지 않는 이미지 형식입니다. 허용 확장자: {allowed}")

        if uploaded_image.size > settings.MAX_UPLOAD_SIZE:
            limit_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise forms.ValidationError(f"이미지 파일은 {limit_mb}MB 이하만 업로드할 수 있습니다.")

        return image

    def clean_video(self):
        video = self.cleaned_data.get("video")
        uploaded_video = self.files.get(self.add_prefix("video"))
        if not uploaded_video:
            return video

        extension = Path(uploaded_video.name).suffix.lower()
        if extension not in settings.SUPPORTED_VIDEO_EXTENSIONS:
            allowed = ", ".join(sorted(settings.SUPPORTED_VIDEO_EXTENSIONS))
            raise forms.ValidationError(f"지원하지 않는 영상 형식입니다. 허용 확장자: {allowed}")

        if uploaded_video.size > settings.MAX_UPLOAD_SIZE:
            limit_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise forms.ValidationError(f"영상 파일은 {limit_mb}MB 이하만 업로드할 수 있습니다.")

        return video

    def clean(self):
        cleaned_data = super().clean()
        uploaded_image = self.files.get(self.add_prefix("image"))
        uploaded_video = self.files.get(self.add_prefix("video"))

        if uploaded_image and uploaded_video:
            raise forms.ValidationError("이미지 또는 영상 중 하나만 업로드하세요.")

        has_existing_media = bool(
            self.instance.pk and (self.instance.image or self.instance.video)
        )
        if not has_existing_media and not uploaded_image and not uploaded_video:
            raise forms.ValidationError("이미지 또는 영상 파일을 업로드하세요.")

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
