from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Post",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("content", models.TextField(blank=True)),
                ("video", models.FileField(blank=True, null=True, upload_to="videos/")),
                ("ascii_gif", models.FileField(blank=True, null=True, upload_to="ascii_gifs/")),
                ("ascii_width", models.IntegerField(default=100)),
                ("max_frames", models.IntegerField(default=10)),
                ("frame_interval", models.IntegerField(default=30)),
                ("gif_duration", models.IntegerField(default=100)),
                ("char_style", models.CharField(choices=[("standard", "기본"), ("bold", "진한 문자"), ("dots", "점묘 스타일")], default="standard", max_length=20)),
                ("status", models.CharField(choices=[("PENDING", "변환 대기"), ("PROCESSING", "변환 중"), ("DONE", "변환 완료"), ("FAILED", "변환 실패")], default="PENDING", max_length=20)),
                ("error_message", models.TextField(blank=True)),
                ("view_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="posts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AsciiFrame",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("frame_index", models.IntegerField()),
                ("ascii_text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ascii_frames", to="board.post")),
            ],
            options={
                "ordering": ["frame_index"],
                "unique_together": {("post", "frame_index")},
            },
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to=settings.AUTH_USER_MODEL)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="board.post")),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="Like",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="board.post")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("post", "user")},
            },
        ),
    ]
