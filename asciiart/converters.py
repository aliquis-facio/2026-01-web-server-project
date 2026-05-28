from pathlib import Path


class ConversionError(Exception):
    pass


ASCII_CHARSETS = {
    "standard": "@%#*+=-:. ",
    "bold": "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
    "dots": "@#*+=-:. ",
}

ASCII_RENDER_FONT_SIZE = 10


def _load_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise ConversionError(
            "OpenCV가 설치되어 있지 않습니다. `pip install -r requirements.txt`를 실행하세요."
        ) from exc
    return cv2


def _load_pillow():
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise ConversionError(
            "Pillow가 설치되어 있지 않습니다. `pip install -r requirements.txt`를 실행하세요."
        ) from exc
    return Image, ImageOps


def _load_pillow_sequence():
    try:
        from PIL import Image, ImageSequence
    except ImportError as exc:
        raise ConversionError(
            "Pillow가 설치되어 있지 않습니다. `pip install -r requirements.txt`를 실행하세요."
        ) from exc
    return Image, ImageSequence


def _is_gif_path(path):
    return Path(path).suffix.lower() == ".gif"


def _gray_pixels_to_ascii(pixels, image_width, image_height, charset):
    chars = ASCII_CHARSETS.get(charset, ASCII_CHARSETS["standard"])

    scale = (len(chars) - 1) / 255
    lines = []
    for y in range(image_height):
        row = pixels[y * image_width : (y + 1) * image_width]
        line = "".join(chars[int((255 - pixel) * scale)] for pixel in row)
        lines.append(line)

    return "\n".join(lines)


def _resolve_width(width, source_width):
    if width in (None, ""):
        return max(1, int(source_width))
    return max(1, int(width))


def _resolve_ascii_height(width, source_width, source_height):
    from .gif import get_ascii_cell_aspect

    source_ratio = source_height / source_width
    cell_aspect = get_ascii_cell_aspect(font_size=ASCII_RENDER_FONT_SIZE)
    return max(1, round(width * source_ratio * cell_aspect))


def get_image_dimensions(image_path):
    Image, _ = _load_pillow()
    try:
        with Image.open(image_path) as image:
            return image.size
    except OSError as exc:
        raise ConversionError("이미지 파일을 열 수 없습니다. 파일 형식을 확인하세요.") from exc


def get_video_dimensions(video_path):
    if _is_gif_path(video_path):
        return get_image_dimensions(video_path)

    cv2 = _load_cv2()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ConversionError("영상을 열 수 없습니다. 파일 형식 또는 경로를 확인하세요.")

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        cap.release()

    if width <= 0 or height <= 0:
        raise ConversionError("영상 크기를 읽을 수 없습니다.")

    return width, height


def extract_frames(video_path, frame_interval=30, max_frames=10):
    cv2 = _load_cv2()
    video_path = Path(video_path)
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise ConversionError("영상을 열 수 없습니다. 파일 형식 또는 경로를 확인하세요.")

    frames = []
    frame_index = 0
    frame_interval = max(1, int(frame_interval))
    max_frames = max(1, int(max_frames))

    try:
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_index % frame_interval == 0:
                frames.append(frame)

            frame_index += 1
    finally:
        cap.release()

    if not frames:
        raise ConversionError("영상에서 추출된 프레임이 없습니다.")

    return frames


def extract_gif_frames(gif_path, frame_interval=1, max_frames=10):
    Image, ImageSequence = _load_pillow_sequence()
    gif_path = Path(gif_path)
    frame_interval = max(1, int(frame_interval))
    max_frames = max(1, int(max_frames))
    frames = []

    try:
        with Image.open(gif_path) as image:
            for frame_index, frame in enumerate(ImageSequence.Iterator(image)):
                if frame_index % frame_interval == 0:
                    frames.append(frame.copy().convert("RGB"))
                    if len(frames) >= max_frames:
                        break
    except OSError as exc:
        raise ConversionError("GIF 파일을 열 수 없습니다. 파일 형식을 확인하세요.") from exc

    if not frames:
        raise ConversionError("GIF에서 추출된 프레임이 없습니다.")

    return frames


def frame_to_ascii(frame, width=None, charset="standard"):
    cv2 = _load_cv2()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    original_height, original_width = gray.shape
    width = _resolve_width(width, original_width)
    target_height = _resolve_ascii_height(width, original_width, original_height)
    resized = cv2.resize(gray, (width, target_height))

    pixels = [int(pixel) for row in resized for pixel in row]
    return _gray_pixels_to_ascii(pixels, width, target_height, charset)


def pil_frame_to_ascii(frame, width=None, charset="standard"):
    _, ImageOps = _load_pillow()

    gray = ImageOps.grayscale(frame)
    original_width, original_height = gray.size
    width = _resolve_width(width, original_width)
    target_height = _resolve_ascii_height(width, original_width, original_height)
    resized = gray.resize((width, target_height))
    pixels = list(resized.getdata())

    return _gray_pixels_to_ascii(pixels, width, target_height, charset)


def image_to_ascii(image_path, width=None, charset="standard"):
    Image, _ = _load_pillow()

    try:
        with Image.open(image_path) as image:
            return pil_frame_to_ascii(image, width=width, charset=charset)
    except OSError as exc:
        raise ConversionError("이미지 파일을 열 수 없습니다. 파일 형식을 확인하세요.") from exc


def convert_image_to_ascii_frame(image_path, width=None, charset="standard"):
    return image_to_ascii(image_path, width=width, charset=charset)


def convert_video_to_ascii_frames(
    video_path,
    width=None,
    frame_interval=30,
    max_frames=10,
    charset="standard",
):
    if _is_gif_path(video_path):
        frames = extract_gif_frames(
            video_path,
            frame_interval=frame_interval,
            max_frames=max_frames,
        )
        return [
            pil_frame_to_ascii(frame, width=width, charset=charset)
            for frame in frames
        ]

    frames = extract_frames(video_path, frame_interval=frame_interval, max_frames=max_frames)
    return [frame_to_ascii(frame, width=width, charset=charset) for frame in frames]
