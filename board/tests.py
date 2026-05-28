from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .forms import PostForm
from .models import AsciiFrame, Post


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


class DownloadAsciiFrameTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="test")
        self.post = Post.objects.create(
            author=self.author,
            title="ascii video",
            media_type=Post.MediaType.VIDEO,
        )
        AsciiFrame.objects.create(
            post=self.post,
            frame_index=1,
            ascii_text="first frame",
        )
        AsciiFrame.objects.create(
            post=self.post,
            frame_index=2,
            ascii_text="second frame",
        )

    def test_download_ascii_txt_defaults_to_first_frame(self):
        response = self.client.get(
            reverse("download_ascii_txt", kwargs={"post_id": self.post.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"first frame", response.content)
        self.assertNotIn(b"second frame", response.content)
        self.assertIn(
            f'post_{self.post.pk}_ascii_frame_1.txt',
            response.headers["Content-Disposition"],
        )

    def test_download_ascii_txt_can_select_current_frame(self):
        response = self.client.get(
            reverse("download_ascii_txt", kwargs={"post_id": self.post.pk}),
            {"frame": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"first frame", response.content)
        self.assertIn(b"second frame", response.content)
        self.assertIn(
            f'post_{self.post.pk}_ascii_frame_2.txt',
            response.headers["Content-Disposition"],
        )

    def test_detail_page_uses_unified_ascii_panel(self):
        response = self.client.get(
            reverse("post_detail", kwargs={"post_id": self.post.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ASCII 이미지/영상")
        self.assertNotContains(response, "ASCII 텍스트 프레임")
        self.assertContains(response, 'id="download-current-frame"')
