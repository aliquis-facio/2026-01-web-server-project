from pathlib import Path


class GifRenderError(Exception):
    pass


RENDER_SAMPLE_TEXT = "Ag@#WMgjpqy"


def _load_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise GifRenderError(
            "Pillow가 설치되어 있지 않습니다. `pip install -r requirements.txt`를 실행하세요."
        ) from exc
    return Image, ImageDraw, ImageFont


def _load_monospace_font(ImageFont, font_size):
    candidates = [
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\cour.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, font_size)
    return ImageFont.load_default()


def get_ascii_cell_metrics(font_size=10):
    Image, ImageDraw, ImageFont = _load_pillow()
    font = _load_monospace_font(ImageFont, font_size)
    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)

    char_bbox = draw.textbbox((0, 0), "M", font=font)
    sample_bbox = draw.textbbox((0, 0), RENDER_SAMPLE_TEXT, font=font)
    char_width = max(1, char_bbox[2] - char_bbox[0])
    glyph_height = max(1, sample_bbox[3] - sample_bbox[1])
    line_gap = max(1, int(font_size * 0.25))
    return char_width, glyph_height, line_gap


def get_ascii_cell_aspect(font_size=10):
    char_width, glyph_height, line_gap = get_ascii_cell_metrics(font_size=font_size)
    return char_width / (glyph_height + line_gap)


def ascii_text_to_image(
    ascii_text,
    font_size=10,
    padding=16,
    background=(17, 17, 17),
    foreground=(238, 238, 238),
):
    Image, ImageDraw, ImageFont = _load_pillow()
    font = _load_monospace_font(ImageFont, font_size)
    lines = ascii_text.splitlines() or [""]
    _, glyph_height, line_gap = get_ascii_cell_metrics(font_size=font_size)

    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)

    max_width = 1
    for line in lines:
        bbox = draw.textbbox((0, 0), line or " ", font=font)
        width = max(1, bbox[2] - bbox[0])
        max_width = max(max_width, width)

    line_pitch = glyph_height + line_gap
    total_height = glyph_height * len(lines) + line_gap * max(0, len(lines) - 1)

    image = Image.new(
        "RGB",
        (max_width + padding * 2, total_height + padding * 2),
        background,
    )
    draw = ImageDraw.Draw(image)

    y = padding
    for line in lines:
        draw.text((padding, y), line, font=font, fill=foreground)
        y += line_pitch

    return image


def _normalize_frame_sizes(images):
    Image, _, _ = _load_pillow()
    max_width = max(image.width for image in images)
    max_height = max(image.height for image in images)
    normalized = []

    for image in images:
        canvas = Image.new("RGB", (max_width, max_height), (17, 17, 17))
        canvas.paste(image, (0, 0))
        normalized.append(canvas)

    return normalized


def ascii_frames_to_gif(ascii_frames, output_path, duration=100, font_size=10):
    if not ascii_frames:
        raise GifRenderError("GIF로 만들 ASCII 프레임이 없습니다.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    images = [
        ascii_text_to_image(frame, font_size=font_size)
        for frame in ascii_frames
    ]
    images = _normalize_frame_sizes(images)

    first, rest = images[0], images[1:]
    first.save(
        output_path,
        save_all=True,
        append_images=rest,
        duration=max(20, int(duration)),
        loop=0,
        optimize=False,
    )
    return output_path
