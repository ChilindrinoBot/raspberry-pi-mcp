from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from . import config
from . import http


def _image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Return the (width, height) of an image, or None if it cannot be determined."""
    try:
        with Image.open(BytesIO(data)) as img:
            return img.size
    except Exception:
        return None


def _decode_image(data: str) -> bytes:
    """Decode a Base64-encoded image payload into raw bytes."""
    return base64.b64decode(data, validate=True)


def _to_cube_compatible_image(name: str, payload: bytes) -> tuple[str, bytes, str | None]:
    """Convert unsupported image formats to an exact 240x240 JPEG.

    Gifs and jpegs are returned untouched (their exact 240x240 dimensions are
    validated afterwards); any other format (png, webp, bmp...) is converted
    with _fit_image_to_jpg and its name gets a .jpg suffix. On failure the
    error message is returned and the payload is left empty.
    """
    suffix = Path(name).suffix.lower()
    if suffix in config.ALLOWED_UPLOAD_SUFFIXES:
        return name, payload, None

    try:
        return f"{Path(name).stem}.jpg", _fit_image_to_jpg(payload), None
    except Exception as e:
        return name, b"", f"Failed to convert image {name} to JPEG: {e}"


def _fit_image_to_jpg(data: bytes) -> bytes:
    """Scale an image to fit inside 240x240 and pad it with black up to exactly 240x240.

    The aspect ratio is preserved: the image is only scaled down when larger
    than the target, then centered on a black 240x240 canvas (black bars on
    the sides or top/bottom as needed) and encoded as JPEG. Transparent areas
    are composited over black so the JPEG output has no alpha channel.
    """
    with Image.open(BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)

        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            flattened = Image.new("RGB", rgba.size, (0, 0, 0))
            flattened.paste(rgba, mask=rgba.split()[-1])
        else:
            flattened = img.convert("RGB")

    target_w, target_h = config.IMAGE_REQUIRED_DIMENSIONS
    width, height = flattened.size
    scale = min(1.0, target_w / width, target_h / height)
    fitted_size = (
        min(target_w, max(1, round(width * scale))),
        min(target_h, max(1, round(height * scale))),
    )

    canvas = Image.new("RGB", config.IMAGE_REQUIRED_DIMENSIONS, (0, 0, 0))
    fitted = (
        flattened.resize(fitted_size, Image.Resampling.LANCZOS)
        if fitted_size != flattened.size
        else flattened
    )
    canvas.paste(
        fitted,
        ((target_w - fitted_size[0]) // 2, (target_h - fitted_size[1]) // 2),
    )

    buffer = BytesIO()
    canvas.save(buffer, format="JPEG", quality=config.JPEG_SAVE_QUALITY)
    return buffer.getvalue()


def _is_in_cube_filelist(name: str, entries: list[str]) -> bool:
    """Check whether an uploaded file shows up in the Cube file list."""
    lowered = name.lower()
    return any(
        entry.lower() == lowered or entry.lower().endswith(f"/{lowered}")
        for entry in entries
    )


def _cube_free_space_rejection(size: int) -> str | None:
    """Return an error message when the Cube cannot hold `size` bytes.

    The upload must fit in the free space reported by /space.json while
    keeping the UPLOAD_FREE_SPACE_BUFFER reserve untouched. Returns None
    when the upload can proceed.
    """
    try:
        free, _total = http._fetch_cube_space()
    except Exception as e:
        return f"Failed to check free space on Cube: {e}"

    if size + config.UPLOAD_FREE_SPACE_BUFFER > free:
        return (
            f"Not enough space on Cube: file needs {size} bytes plus a "
            f"{config.UPLOAD_FREE_SPACE_BUFFER // 1024} KB free reserve, but only "
            f"{free} bytes ({free / 1024:.1f} KB) are free."
        )

    return None


def _format_size_kb(size_bytes: int) -> str:
    """Format a byte count as a human readable KB string, e.g. '12.3 KB'."""
    return f"{size_bytes / 1024:.1f} KB"
