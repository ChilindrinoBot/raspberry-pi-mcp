from __future__ import annotations

import random
from io import BytesIO
from pathlib import Path

from PIL import Image

from ... import mcp
from . import config
from . import http
from . import images
from . import state


def _format_size_kb(size_bytes: int) -> str:
    """Format a byte count as a human readable KB string, e.g. '12.3 KB'."""
    return f"{size_bytes / 1024:.1f} KB"


def _list_local_gifs() -> list[Path]:
    """List the .gif files available in RANDOM_GIF_DIR (empty when missing)."""
    if not config.RANDOM_GIF_DIR.is_dir():
        return []
    return sorted(
        path
        for path in config.RANDOM_GIF_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".gif"
    )


def _pick_random_gif(exclude: str | None = None) -> Path | None:
    """Pick a random gif from the local folder, avoiding `exclude` if possible."""
    gifs = _list_local_gifs()
    if not gifs:
        return None

    excluded = (exclude or "").lower()
    candidates = [gif for gif in gifs if gif.name.lower() != excluded]
    return random.choice(candidates if candidates else gifs)


def _list_local_images() -> list[Path]:
    """List the .jpg/.jpeg files available in RANDOM_IMAGE_DIR (empty when missing)."""
    if not config.RANDOM_IMAGE_DIR.is_dir():
        return []
    return sorted(
        path
        for path in config.RANDOM_IMAGE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in config.LOCAL_IMAGE_SUFFIXES
    )


def _pick_random_image(exclude: str | None = None) -> Path | None:
    """Pick a random image from the local folder, avoiding `exclude` if possible."""
    image_list = _list_local_images()
    if not image_list:
        return None

    excluded = (exclude or "").lower()
    candidates = [image for image in image_list if image.name.lower() != excluded]
    return random.choice(candidates if candidates else image_list)


@mcp.tool()
def save_image_in_gallery(data: str, name: str) -> dict[str, str]:
    """
    Saves an image into media/images ready for the Cube display.

    The image bytes must be Base64-encoded by the client. After decoding, the
    image is scaled down preserving its aspect ratio until it fits 240x240,
    padded with black (on the sides or top/bottom as needed) up to exactly
    240x240 and re-encoded as JPEG. The result is verified to be a valid
    240x240 jpg before being stored in the local images pool used by
    start_random_images; any source format (png, gif, webp, jpg...) is accepted.
    The final .jpg name (save name plus ".jpg") must be at most 25 characters.

    Args:
        data: Image bytes encoded in Base64 (client-side).
        name: Desired save name, usually without suffix; a trailing image
            suffix (.jpg, .png...) is stripped and ".jpg" is always appended.
    """
    requested = name.strip()
    if not requested:
        return {"status": "error", "message": "Image name is required."}

    candidate = Path(requested)
    stem = (
        candidate.stem
        if candidate.suffix.lower() in config.STRIPPABLE_IMAGE_SUFFIXES
        else candidate.name
    ).strip().rstrip(".")
    if not stem or requested.startswith("."):
        return {"status": "error", "message": "Image name is required."}

    target_name = f"{stem}.jpg"
    if len(target_name) > config.IMAGE_NAME_MAX_LENGTH:
        return {
            "status": "error",
            "message": (
                f"Image name is too long: {target_name} ({len(target_name)} characters). "
                f"Max is {config.IMAGE_NAME_MAX_LENGTH} characters."
            ),
        }

    try:
        payload = images._decode_image(data)
    except Exception as e:
        return {"status": "error", "message": f"Failed to decode image {name}: {e}"}

    if not payload:
        return {"status": "error", "message": f"Image is empty: {name}."}

    try:
        processed = images._fit_image_to_jpg(payload)
    except Exception as e:
        return {"status": "error", "message": f"Failed to process image {name}: {e}"}

    try:
        with Image.open(BytesIO(processed)) as check:
            if check.format != "JPEG":
                return {
                    "status": "error",
                    "message": f"Processed image is not a valid JPEG: {name}.",
                }
            if check.size != config.IMAGE_REQUIRED_DIMENSIONS:
                width, height = check.size
                return {
                    "status": "error",
                    "message": (
                        f"Processed image must be {config.IMAGE_REQUIRED_DIMENSIONS[0]}x{config.IMAGE_REQUIRED_DIMENSIONS[1]} "
                        f"(got {width}x{height}): {name}."
                    ),
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Processed image is not a valid JPEG: {name} ({e}).",
        }

    target = config.RANDOM_IMAGE_DIR / target_name
    try:
        config.RANDOM_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        target.write_bytes(processed)
    except Exception as e:
        return {"status": "error", "message": f"Failed to save image {target.name}: {e}"}

    return {
        "status": "success",
        "message": f"Image saved to {config.RANDOM_IMAGE_DIR}: {target.name} (240x240 JPEG).",
    }


@mcp.tool()
def show_gallery_image(filename: str) -> dict[str, str]:
    """
    Shows an image from the media/images gallery on the Cube display.

    Looks up `filename` in the local gallery (with or without the .jpg/.jpeg
    suffix), uploads it to the Cube under its own name and displays it.
    Unlike show_temporary_gif there is no timer: the image stays on screen
    until another gif or image is set. Images that are not 240x240 JPEGs
    yet are converted first (scaled down and padded with black). If a random
    mode (gifs or images) is running it is stopped first so the requested
    image stays on screen.

    Args:
        filename: Name of the image file in the gallery, usually without
            suffix.
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    requested = filename.strip().lstrip("/")
    if not requested:
        return {"status": "error", "message": "Image name is required."}

    candidate = Path(requested)
    names = [candidate.name]
    if candidate.suffix.lower() in config.LOCAL_IMAGE_SUFFIXES:
        names.extend([f"{candidate.stem}.jpg", f"{candidate.stem}.jpeg"])
    else:
        names.extend([f"{candidate.name}.jpg", f"{candidate.name}.jpeg"])
    path = next(
        (
            config.RANDOM_IMAGE_DIR / candidate_name
            for candidate_name in dict.fromkeys(names)
            if (config.RANDOM_IMAGE_DIR / candidate_name).is_file()
        ),
        None,
    )
    if path is None:
        available = ", ".join(image.name for image in _list_local_images()) or "none"
        return {
            "status": "error",
            "message": f"Image not found in {config.RANDOM_IMAGE_DIR}: {requested}. Available: {available}.",
        }

    payload = path.read_bytes()
    upload_name = path.name
    try:
        with Image.open(BytesIO(payload)) as img:
            ready = img.format == "JPEG" and img.size == config.IMAGE_REQUIRED_DIMENSIONS
    except Exception:
        ready = False

    if not ready:
        upload_name = f"{path.stem}.jpg"
        try:
            payload = images._fit_image_to_jpg(payload)
        except Exception as e:
            return {"status": "error", "message": f"Failed to convert image {path.name}: {e}"}

    rejection = images._cube_free_space_rejection(len(payload))
    if rejection:
        return {"status": "error", "message": rejection}

    try:
        http._upload_cube_image(upload_name, payload)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to upload image {upload_name} ({len(payload)} bytes) to Cube: {e}",
        }

    try:
        available = http._fetch_cube_gifs()
    except Exception as e:
        return {"status": "error", "message": f"Failed to verify upload of {upload_name} on Cube: {e}"}

    if not images._is_in_cube_filelist(upload_name, available):
        return {
            "status": "error",
            "message": f"Upload could not be confirmed: {upload_name} is not in the Cube file list.",
        }

    was_running_gif, _previous_random = state._stop_random_mode()
    was_running_image, _previous_random_image = state._stop_image_mode()
    was_running_special, _previous_special = state._stop_special_mode()

    try:
        response = http._set_cube_gif(upload_name)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set image on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set image {upload_name}. Response: {response}",
        }

    parts = [f"Cube image set to: {upload_name} (no timer; it stays until changed)"]
    if was_running_gif:
        parts.append("Random gif mode stopped.")
    if was_running_image:
        parts.append("Random image mode stopped.")
    if was_running_special:
        parts.append("Special routine stopped.")
    if response:
        parts.append(f"Device response: {response}")

    return {"status": "success", "message": ". ".join(parts)}


@mcp.tool()
def show_gallery_gif(filename: str) -> dict[str, str]:
    """
    Shows a gif from the media/gifs gallery on the Cube display.

    Looks up `filename` in the local gifs gallery (with or without the .gif
    suffix), uploads it to the Cube as tmp.gif and displays it. Unlike
    show_temporary_gif there is no timer: the gif stays on screen until
    another gif or image is set, so nothing is remembered or restored.
    While a temporary gif is being shown this call is rejected. If a random
    mode (gifs or images) is running it is stopped first so the requested
    gif stays on screen.

    Args:
        filename: Name of the gif file in the gallery, usually without
            suffix.
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    requested = filename.strip().lstrip("/")
    if not requested:
        return {"status": "error", "message": "Gif name is required."}

    candidate = Path(requested)
    names = [candidate.name] if candidate.suffix.lower() == ".gif" else [f"{candidate.name}.gif"]
    path = next(
        (
            config.RANDOM_GIF_DIR / candidate_name
            for candidate_name in dict.fromkeys(names)
            if (config.RANDOM_GIF_DIR / candidate_name).is_file()
        ),
        None,
    )
    if path is None:
        available = ", ".join(gif.name for gif in _list_local_gifs()) or "none"
        return {
            "status": "error",
            "message": f"Gif not found in {config.RANDOM_GIF_DIR}: {requested}. Available: {available}.",
        }

    with state._TEMP_GIF_LOCK:
        busy = state._TEMP_GIF_RUNNING
    if busy:
        return {
            "status": "error",
            "message": "A temporary gif is already being shown. Wait for it to finish before starting another.",
        }

    payload = path.read_bytes()

    try:
        with Image.open(BytesIO(payload)) as img:
            fmt, size = img.format, img.size
    except Exception as e:
        return {"status": "error", "message": f"Not a valid GIF: {path.name} ({e})."}

    if fmt != "GIF":
        return {"status": "error", "message": f"Not a valid GIF: {path.name}."}

    if size != config.IMAGE_REQUIRED_DIMENSIONS:
        return {
            "status": "error",
            "message": (
                f"Gif must be {config.IMAGE_REQUIRED_DIMENSIONS[0]}x{config.IMAGE_REQUIRED_DIMENSIONS[1]} "
                f"(got {size[0]}x{size[1]}): {path.name}."
            ),
        }

    rejection = images._cube_free_space_rejection(len(payload))
    if rejection:
        return {"status": "error", "message": rejection}

    try:
        http._upload_cube_image(f"{config.TEMP_GIF_NAME}.gif", payload)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to upload gif {path.name} ({len(payload)} bytes) to Cube: {e}",
        }

    try:
        available = http._fetch_cube_gifs()
    except Exception as e:
        return {"status": "error", "message": f"Failed to verify upload of {config.TEMP_GIF_NAME}.gif on Cube: {e}"}

    if not images._is_in_cube_filelist(f"{config.TEMP_GIF_NAME}.gif", available):
        return {
            "status": "error",
            "message": f"Upload could not be confirmed: {config.TEMP_GIF_NAME}.gif is not in the Cube file list.",
        }

    was_running_gif, _previous_random = state._stop_random_mode()
    was_running_image, _previous_random_image = state._stop_image_mode()
    was_running_special, _previous_special = state._stop_special_mode()

    try:
        response = http._set_cube_gif(f"{config.TEMP_GIF_NAME}.gif")
    except Exception as e:
        return {"status": "error", "message": f"Failed to set gif on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set gif {config.TEMP_GIF_NAME}.gif. Response: {response}",
        }

    parts = [f"Cube gif set to: {config.TEMP_GIF_NAME}.gif (from {path.name}; no timer; it stays until changed)"]
    if was_running_gif:
        parts.append("Random gif mode stopped.")
    if was_running_image:
        parts.append("Random image mode stopped.")
    if was_running_special:
        parts.append("Special routine stopped.")
    if response:
        parts.append(f"Device response: {response}")

    return {"status": "success", "message": ". ".join(parts)}


@mcp.resource("gallery://images")
def list_gallery_images() -> str:
    """
    Returns a list of images available in the local media/images gallery,
    with each file's size in KB.
    """
    found = _list_local_images()

    if not found:
        return f"No images found in {config.RANDOM_IMAGE_DIR}."

    lines = [
        f"{path.name} ({images._format_size_kb(path.stat().st_size)})" for path in found
    ]
    return "Available gallery images:\n" + "\n".join(lines)


@mcp.resource("gallery://gifs")
def list_gallery_gifs() -> str:
    """
    Returns a list of gifs available in the local media/gifs gallery,
    with each file's size in KB.
    """
    found = _list_local_gifs()

    if not found:
        return f"No gifs found in {config.RANDOM_GIF_DIR}."

    lines = [f"{path.name} ({images._format_size_kb(path.stat().st_size)})" for path in found]
    return "Available gallery gifs:\n" + "\n".join(lines)
