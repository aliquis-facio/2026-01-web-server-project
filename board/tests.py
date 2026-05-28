from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .forms import PostForm
from .models import Post


class PostFormMediaDetectionTests(SimpleTestCase):
    def _form(self, uploaded_file):
        return PostForm(
            data={
                "title": "test upload",
                "content": "",
                "ascii_width": "",
                "max_frames": 3,
                "frame_interval": 1,
                "gif_duration": 120,
                "char_style": Post.CharStyle.STANDARD,
            },
            files={"media_file": uploaded_file},
        )

    def _gif_file(self, name, *, animated):
        from PIL import Image

        buffer = BytesIO()
        first_frame = Image.new("RGB", (4, 4), "white")
        if animated:
            second_frame = Image.new("RGB", (4, 4), "black")
            first_frame.save(
                buffer,
                format="GIF",
                save_all=True,
                append_images=[second_frame],
                duration=100,
                loop=0,
            )
        else:
            first_frame.save(buffer, format="GIF")
        buffer.seek(0)
        return SimpleUploadedFile(name, buffer.read(), content_type="image/gif")

    def test_regular_image_upload_is_detected_as_image(self):
        uploaded_file = SimpleUploadedFile(
            "sample.png",
            b"not inspected for non-gif image types",
            content_type="image/png",
        )

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors.as_data())
        self.assertEqual(form.detected_media_type, Post.MediaType.IMAGE)

    def test_video_upload_is_detected_as_video(self):
        uploaded_file = SimpleUploadedFile(
            "sample.mp4",
            b"fake video content",
            content_type="video/mp4",
        )

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors.as_data())
        self.assertEqual(form.detected_media_type, Post.MediaType.VIDEO)

    def test_static_gif_upload_is_detected_as_image(self):
        form = self._form(self._gif_file("static.gif", animated=False))

        self.assertTrue(form.is_valid(), form.errors.as_data())
        self.assertEqual(form.detected_media_type, Post.MediaType.IMAGE)

    def test_animated_gif_upload_is_detected_as_video(self):
        form = self._form(self._gif_file("animated.gif", animated=True))

        self.assertTrue(form.is_valid(), form.errors.as_data())
        self.assertEqual(form.detected_media_type, Post.MediaType.VIDEO)
