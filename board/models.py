from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


class Post(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "변환 대기"
        PROCESSING = "PROCESSING", "변환 중"
        DONE = "DONE", "변환 완료"
        FAILED = "FAILED", "변환 실패"

    class CharStyle(models.TextChoices):
        STANDARD = "standard", "기본"
        BOLD = "bold", "진한 문자"
        DOTS = "dots", "점묘 스타일"

    class MediaType(models.TextChoices):
        IMAGE = "IMAGE", "이미지"
        VIDEO = "VIDEO", "영상"

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices,
        default=MediaType.VIDEO,
    )
    image = models.FileField(upload_to="images/", blank=True, null=True)
    video = models.FileField(upload_to="videos/", blank=True, null=True)
    source_hash = models.CharField(max_length=64, blank=True, db_index=True)
    ascii_image = models.FileField(upload_to="ascii_images/", blank=True, null=True)
    ascii_gif = models.FileField(upload_to="ascii_gifs/", blank=True, null=True)

    ascii_width = models.PositiveIntegerField(blank=True, null=True)
    max_frames = models.IntegerField(default=settings.DEFAULT_MAX_FRAMES)
    frame_interval = models.IntegerField(default=settings.DEFAULT_FRAME_INTERVAL)
    gif_duration = models.IntegerField(default=settings.DEFAULT_GIF_DURATION)
    char_style = models.CharField(
        max_length=20,
        choices=CharStyle.choices,
        default=CharStyle.STANDARD,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    view_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("post_detail", args=[self.pk])

    @property
    def is_image(self):
        return self.media_type == self.MediaType.IMAGE

    @property
    def is_video(self):
        return self.media_type == self.MediaType.VIDEO

    @property
    def is_gif_upload(self):
        source_name = ""
        if self.image:
            source_name = self.image.name
        elif self.video:
            source_name = self.video.name
        return Path(source_name).suffix.lower() == ".gif"


class AsciiFrame(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="ascii_frames")
    frame_index = models.IntegerField()
    ascii_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["frame_index"]
        unique_together = ("post", "frame_index")

    def __str__(self):
        return f"{self.post_id} - frame {self.frame_index}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} on {self.post_id}"


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user} likes {self.post_id}"
