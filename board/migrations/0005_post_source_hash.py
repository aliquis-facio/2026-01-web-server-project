import hashlib
from pathlib import Path

from django.conf import settings
from django.db import migrations, models


def populate_source_hash(apps, schema_editor):
    Post = apps.get_model("board", "Post")
    media_root = Path(settings.MEDIA_ROOT)

    for post in Post.objects.all():
        media_name = post.image.name if post.image else post.video.name if post.video else ""
        if not media_name:
            continue

        media_path = media_root / media_name
        if not media_path.exists():
            continue

        hasher = hashlib.sha256()
        with media_path.open("rb") as media_file:
            for chunk in iter(lambda: media_file.read(1024 * 1024), b""):
                hasher.update(chunk)

        post.source_hash = hasher.hexdigest()
        post.save(update_fields=["source_hash"])


class Migration(migrations.Migration):

    dependencies = [
        ("board", "0004_post_ascii_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="source_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.RunPython(populate_source_hash, migrations.RunPython.noop),
    ]
