from __future__ import annotations

import base64
import json
import os
import random
import re
import threading
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Final

import httpx
from dotenv import load_dotenv
from PIL import Image, ImageOps

from .. import mcp

# Absolute paths based on workspace structure
ENV_PATH: Final[Path] = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ENV_PATH)

CUBE_BASE_URL: Final[str] = os.environ.get("CUBE_BASE_URL", "").rstrip("/")

_HREF_PATTERN: Final[re.Pattern[str]] = re.compile(r"href='([^']+)'")

BRIGHTNESS_DEFAULT: Final[int] = 50
BRIGHTNESS_MIN: Final[int] = 0
BRIGHTNESS_MAX: Final[int] = 100

# Brightness level remembered when the display is turned off, so it can be
# restored on the next power on. None means nothing has been remembered yet.
_REMEMBERED_BRIGHTNESS: int | None = None

CUBE_IMAGE_DIR: Final[str] = "/image"
ALLOWED_UPLOAD_SUFFIXES: Final[frozenset[str]] = frozenset({".gif", ".jpg", ".jpeg"})
IMAGE_REQUIRED_DIMENSIONS: Final[tuple[int, int]] = (240, 240)

JPEG_SAVE_QUALITY: Final[int] = 90

# Maximum length of the .jpg name stored in media/images by save_image_in_gallery.
IMAGE_NAME_MAX_LENGTH: Final[int] = 25

# Trailing suffixes stripped from the save name sent to save_image_in_gallery, which
# usually arrives without any suffix; anything else is kept as part of the name.
STRIPPABLE_IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
)

TEMP_GIF_NAME: Final[str] = "tmp"
TEMP_GIF_DEFAULT_SECONDS: Final[int] = 5
TEMP_GIF_MIN_SECONDS: Final[int] = 1
TEMP_GIF_MAX_SECONDS: Final[int] = 30

# Temporary gif flow state. While _TEMP_GIF_RUNNING is True a tmp gif is being
# shown and its previous gif has not been restored yet; new temporary shows are
# rejected until it finishes.
_TEMP_GIF_RUNNING: bool = False
_TEMP_GIF_LOCK: Final[threading.Lock] = threading.Lock()

# Local folder holding the gif pool used by the random gif mode.
RANDOM_GIF_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "media" / "gifs"

# Name under which every picked gif is temporarily uploaded to the Cube, so a
# new random gif simply overwrites the previous one.
RANDOM_GIF_NAME: Final[str] = "random.gif"

RANDOM_GIF_DEFAULT_SECONDS: Final[int] = 60
RANDOM_GIF_MIN_SECONDS: Final[int] = 5
RANDOM_GIF_MAX_SECONDS: Final[int] = 3600

# Random gif mode state. _RANDOM_MODE_RUNNING is True while the background
# loop keeps swapping gifs; _RANDOM_CURRENT_GIF remembers which local gif is
# currently uploaded and displayed as random.gif; _RANDOM_MODE_SUSPENDED is
# True while a temporary gif borrowed the screen, so the loop waits without
# cycling until the previous gif is restored. While the Cube display is off
# (brightness 0 or unreachable) the loop also pauses by itself.
_RANDOM_MODE_RUNNING: bool = False
_RANDOM_MODE_SUSPENDED: bool = False
_RANDOM_CURRENT_GIF: str | None = None
_RANDOM_MODE_LOCK: Final[threading.Lock] = threading.Lock()

# Local folder holding the image pool used by the random image mode.
RANDOM_IMAGE_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "media" / "images"

# Suffixes accepted in the random image pool. Every picked image is uploaded
# to the Cube under RANDOM_IMAGE_NAME, so only jpg/jpeg sources make sense.
LOCAL_IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset({".jpg", ".jpeg"})

# Name under which every picked image is temporarily uploaded to the Cube, so a
# new random image simply overwrites the previous one.
RANDOM_IMAGE_NAME: Final[str] = "random.jpg"

RANDOM_IMAGE_DEFAULT_SECONDS: Final[int] = 60
RANDOM_IMAGE_MIN_SECONDS: Final[int] = 5
RANDOM_IMAGE_MAX_SECONDS: Final[int] = 3600

# Random image mode state; mirrors the random gif mode state. Both modes share
# one screen, so starting one stops the other and a temporary gif suspends
# whichever mode is active until the previous gif is restored.
_RANDOM_IMAGE_MODE_RUNNING: bool = False
_RANDOM_IMAGE_MODE_SUSPENDED: bool = False
_RANDOM_CURRENT_IMAGE: str | None = None
_RANDOM_IMAGE_MODE_LOCK: Final[threading.Lock] = threading.Lock()


def _fetch_cube_gifs() -> list[str]:
    """Fetch the /filelist page from the Cube and extract the available gif paths."""
    url = f"{CUBE_BASE_URL}/filelist"
    html = urllib.request.urlopen(url).read().decode()
    gifs = _HREF_PATTERN.findall(html)
    return [gif.lstrip("/") for gif in gifs]


@mcp.resource("cube://gifs")
def list_cube_gifs() -> str:
    """
    Returns a list of gifs available on the Cube display.
    """
    if not CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        gifs = _fetch_cube_gifs()
    except Exception as e:
        return f"Failed to fetch gifs from Cube: {e}"

    if not gifs:
        return "No gifs found on the Cube."

    return "Available Cube gifs:\n" + "\n".join(gifs)


def _fetch_cube_space() -> tuple[int, int]:
    """Fetch the /space.json endpoint from the Cube and return (free, total) bytes."""
    url = f"{CUBE_BASE_URL}/space.json"
    data = json.loads(urllib.request.urlopen(url).read().decode())
    return int(data["free"]), int(data["total"])


@mcp.resource("cube://free-space")
def get_cube_free_space() -> str:
    """
    Returns the free storage space available on the Cube display.
    """
    if not CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        free, total = _fetch_cube_space()
    except Exception as e:
        return f"Failed to fetch free space from Cube: {e}"

    return f"Free space on Cube: {free // 1024} KB (total: {total // 1024} KB)"


def _set_cube_brightness(level: int) -> str:
    """Send a /set?brt=<level> request to the Cube, returning the response body."""
    url = f"{CUBE_BASE_URL}/set?brt={level}"
    return urllib.request.urlopen(url).read().decode().strip()


@mcp.tool()
def set_cube_brightness(level: int = BRIGHTNESS_DEFAULT) -> dict[str, str]:
    """
    Sets the brightness of the Cube display.

    The level is clamped to the valid range [0, 100] before being sent to the
    Cube via its /set?brt= endpoint.

    Args:
        level: Brightness level between 0 and 100 (default: 50).
    """
    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    clamped = max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, level))

    try:
        response = _set_cube_brightness(clamped)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set brightness on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set brightness {clamped}. Response: {response}",
        }

    if not response:
        return {"status": "success", "message": f"Cube brightness set to: {clamped}"}

    return {
        "status": "success",
        "message": f"Cube brightness set to: {clamped}. Device response: {response}",
    }


def _fetch_cube_brightness() -> int:
    """Fetch the /brt.json endpoint from the Cube and return the current brightness level."""
    url = f"{CUBE_BASE_URL}/brt.json"
    data = json.loads(urllib.request.urlopen(url).read().decode())
    return int(data["brt"])


@mcp.resource("cube://brightness")
def get_cube_brightness() -> str:
    """
    Returns the current brightness level of the Cube display.
    """
    if not CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        brightness = _fetch_cube_brightness()
    except Exception as e:
        return f"Failed to fetch brightness from Cube: {e}"

    return f"Current Cube brightness: {brightness}"


def _fetch_cube_current_gif() -> str:
    """Fetch the /img.json endpoint from the Cube and return the currently displayed gif path."""
    url = f"{CUBE_BASE_URL}/img.json"
    data = json.loads(urllib.request.urlopen(url).read().decode())
    return str(data["img"]).strip()


@mcp.resource("cube://current-gif")
def get_cube_current_gif() -> str:
    """
    Returns the gif currently set on the Cube display.
    """
    if not CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        gif = _fetch_cube_current_gif()
    except Exception as e:
        return f"Failed to fetch current gif from Cube: {e}"

    if not gif:
        return "No gif is currently set on the Cube."

    name = gif.removeprefix(f"{CUBE_IMAGE_DIR}/").lstrip("/")
    return f"Current Cube gif: {name}"


@mcp.tool()
def turn_cube_display_off() -> dict[str, str]:
    """
    Turns off the Cube display by setting its brightness to 0.

    The brightness level active before turning off is remembered in memory so it
    can be restored later with turn_cube_display_on. The level is queried from
    the device; if unavailable, the last remembered value or the default (50)
    is used instead.
    """
    global _REMEMBERED_BRIGHTNESS

    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    try:
        previous = _fetch_cube_brightness()
    except Exception:
        previous = _REMEMBERED_BRIGHTNESS if _REMEMBERED_BRIGHTNESS is not None else BRIGHTNESS_DEFAULT

    if previous > BRIGHTNESS_MIN:
        _REMEMBERED_BRIGHTNESS = max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, previous))

    try:
        response = _set_cube_brightness(BRIGHTNESS_MIN)
    except Exception as e:
        return {"status": "error", "message": f"Failed to turn off Cube display: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to turn off display. Response: {response}",
        }

    remembered = _REMEMBERED_BRIGHTNESS if _REMEMBERED_BRIGHTNESS is not None else BRIGHTNESS_DEFAULT
    message = f"Cube display turned off. Brightness will be restored to {remembered} on next power on."
    if response:
        message += f" Device response: {response}"

    return {"status": "success", "message": message}


@mcp.tool()
def turn_cube_display_on() -> dict[str, str]:
    """
    Turns on the Cube display by restoring the remembered brightness level.

    Uses the brightness saved before the display was turned off; if nothing is
    remembered (or the remembered value is 0), defaults to 50. The level is
    clamped to the valid range [0, 100].
    """
    global _REMEMBERED_BRIGHTNESS

    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    if _REMEMBERED_BRIGHTNESS is not None and _REMEMBERED_BRIGHTNESS > BRIGHTNESS_MIN:
        level = _REMEMBERED_BRIGHTNESS
    else:
        level = BRIGHTNESS_DEFAULT
    clamped = max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, level))

    try:
        response = _set_cube_brightness(clamped)
    except Exception as e:
        return {"status": "error", "message": f"Failed to turn on Cube display: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to turn on display. Response: {response}",
        }

    message = f"Cube display turned on at brightness {clamped}."
    if response:
        message += f" Device response: {response}"

    return {"status": "success", "message": message}


def _set_cube_gif(gif: str) -> str:
    """Send a /set request to the Cube to display the given gif, returning the response body.

    The Cube stores its display assets under the /image directory, so the gif name is
    sent as /image/<name> to match how the device resolves them. Slashes are kept
    verbatim (e.g. /set?img=/image/Bomb.gif) while the rest is percent-encoded.
    """
    encoded = urllib.parse.quote(f"/image/{gif}")
    url = f"{CUBE_BASE_URL}/set?img={encoded}"
    return urllib.request.urlopen(url).read().decode().strip()


@mcp.tool()
def set_cube_gif(gif: str) -> dict[str, str]:
    """
    Displays a gif on the Cube display.

    Validates that the gif exists in the Cube's file list before sending the /set request.
    If the random gif or random image mode is running it is stopped first, so
    the requested gif stays on screen.

    Args:
        gif: Name (or relative path) of the gif to display on the Cube.
    """
    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    gif = gif.strip().lstrip("/")
    if not gif:
        return {"status": "error", "message": "Gif name is required."}

    try:
        available = _fetch_cube_gifs()
    except Exception as e:
        return {"status": "error", "message": f"Failed to verify gif availability: {e}"}

    if gif not in available:
        return {
            "status": "error",
            "message": f"Gif not found on Cube: {gif}. Available: {', '.join(available) or 'none'}.",
        }

    was_running_gif, _previous_random = _stop_random_mode()
    was_running_image, _previous_random_image = _stop_image_mode()

    try:
        response = _set_cube_gif(gif)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set gif on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set gif {gif}. Response: {response}",
        }

    parts = [f"Cube gif set to: {gif}"]
    if was_running_gif:
        parts.append("Random gif mode stopped.")
    if was_running_image:
        parts.append("Random image mode stopped.")
    if response:
        parts.append(f"Device response: {response}")

    return {"status": "success", "message": ". ".join(parts)}


def _image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Return the (width, height) of an image, or None if it cannot be determined."""
    try:
        with Image.open(BytesIO(data)) as img:
            return img.size
    except Exception:
        return None


def _upload_cube_image(name: str, data: bytes) -> None:
    """POST an image to the Cube's /doUpload endpoint as multipart/form-data.

    Mirrors the device's web uploader: gifs are sent in the "image" field while
    jpg/jpeg files are sent in the "file" field, always targeting the /image dir.
    """
    field = "image" if name.lower().endswith(".gif") else "file"
    url = f"{CUBE_BASE_URL}/doUpload?dir={CUBE_IMAGE_DIR}"
    response = httpx.post(url, files={field: (name, data)}, timeout=60)
    response.raise_for_status()


def _is_in_cube_filelist(name: str, entries: list[str]) -> bool:
    """Check whether an uploaded file shows up in the Cube file list."""
    lowered = name.lower()
    return any(
        entry.lower() == lowered or entry.lower().endswith(f"/{lowered}")
        for entry in entries
    )


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
    if suffix in ALLOWED_UPLOAD_SUFFIXES:
        return name, payload, None

    try:
        return f"{Path(name).stem}.jpg", _fit_image_to_jpg(payload), None
    except Exception as e:
        return name, b"", f"Failed to convert image {name} to JPEG: {e}"


@mcp.tool()
def upload_cube_image(data: str, filename: str) -> dict[str, str]:
    """
    Uploads a gif or jpg/jpeg image to the Cube display.

    The image bytes must be Base64-encoded by the client. After decoding, the
    file is validated: allowed extension (.gif, .jpg, .jpeg), dimensions
    exactly 240x240, and enough free space on the Cube before uploading it to
    the /image directory via /doUpload. Other formats (png, webp, bmp...) are
    not rejected: they are automatically converted to an exact 240x240 JPEG
    and their name gets a .jpg suffix.

    Args:
        data: Image bytes encoded in Base64 (client-side).
        filename: Name of the image, used to determine its type.
    """
    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    name = Path(filename.strip()).name
    if not name:
        return {"status": "error", "message": "Filename is required."}

    try:
        payload = _decode_image(data)
    except Exception as e:
        return {"status": "error", "message": f"Failed to decode image {name}: {e}"}

    if not payload:
        return {"status": "error", "message": f"Image is empty: {name}."}

    name, payload, conversion_error = _to_cube_compatible_image(name, payload)
    if conversion_error:
        return {"status": "error", "message": conversion_error}

    dimensions = _image_dimensions(payload)
    if dimensions is None:
        return {"status": "error", "message": f"Could not read image dimensions of {name}."}

    if dimensions != IMAGE_REQUIRED_DIMENSIONS:
        width, height = dimensions
        return {
            "status": "error",
            "message": (
                f"Image must be {IMAGE_REQUIRED_DIMENSIONS[0]}x{IMAGE_REQUIRED_DIMENSIONS[1]} "
                f"(got {width}x{height}): {name}."
            ),
        }

    try:
        free, _total = _fetch_cube_space()
    except Exception as e:
        return {"status": "error", "message": f"Failed to check free space on Cube: {e}"}

    if len(payload) > free:
        return {
            "status": "error",
            "message": (
                f"Not enough space on Cube: file needs {len(payload)} bytes "
                f"but only {free} bytes are free."
            ),
        }

    try:
        _upload_cube_image(name, payload)
    except Exception as e:
        return {"status": "error", "message": f"Failed to upload image to Cube: {e}"}

    try:
        available = _fetch_cube_gifs()
    except Exception as e:
        return {"status": "error", "message": f"Failed to verify upload of {name} on Cube: {e}"}

    if not _is_in_cube_filelist(name, available):
        return {
            "status": "error",
            "message": f"Upload could not be confirmed: {name} is not in the Cube file list.",
        }

    return {"status": "success", "message": f"Image uploaded to Cube: {name}"}


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

    target_w, target_h = IMAGE_REQUIRED_DIMENSIONS
    width, height = flattened.size
    scale = min(1.0, target_w / width, target_h / height)
    fitted_size = (
        min(target_w, max(1, round(width * scale))),
        min(target_h, max(1, round(height * scale))),
    )

    canvas = Image.new("RGB", IMAGE_REQUIRED_DIMENSIONS, (0, 0, 0))
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
    canvas.save(buffer, format="JPEG", quality=JPEG_SAVE_QUALITY)
    return buffer.getvalue()


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
        if candidate.suffix.lower() in STRIPPABLE_IMAGE_SUFFIXES
        else candidate.name
    ).strip().rstrip(".")
    if not stem or requested.startswith("."):
        return {"status": "error", "message": "Image name is required."}

    target_name = f"{stem}.jpg"
    if len(target_name) > IMAGE_NAME_MAX_LENGTH:
        return {
            "status": "error",
            "message": (
                f"Image name is too long: {target_name} ({len(target_name)} characters). "
                f"Max is {IMAGE_NAME_MAX_LENGTH} characters."
            ),
        }

    try:
        payload = _decode_image(data)
    except Exception as e:
        return {"status": "error", "message": f"Failed to decode image {name}: {e}"}

    if not payload:
        return {"status": "error", "message": f"Image is empty: {name}."}

    try:
        processed = _fit_image_to_jpg(payload)
    except Exception as e:
        return {"status": "error", "message": f"Failed to process image {name}: {e}"}

    try:
        with Image.open(BytesIO(processed)) as check:
            if check.format != "JPEG":
                return {
                    "status": "error",
                    "message": f"Processed image is not a valid JPEG: {name}.",
                }
            if check.size != IMAGE_REQUIRED_DIMENSIONS:
                width, height = check.size
                return {
                    "status": "error",
                    "message": (
                        f"Processed image must be {IMAGE_REQUIRED_DIMENSIONS[0]}x{IMAGE_REQUIRED_DIMENSIONS[1]} "
                        f"(got {width}x{height}): {name}."
                    ),
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Processed image is not a valid JPEG: {name} ({e}).",
        }

    target = RANDOM_IMAGE_DIR / target_name
    try:
        RANDOM_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        target.write_bytes(processed)
    except Exception as e:
        return {"status": "error", "message": f"Failed to save image {target.name}: {e}"}

    return {
        "status": "success",
        "message": f"Image saved to {RANDOM_IMAGE_DIR}: {target.name} (240x240 JPEG).",
    }


def _restore_previous_gif(
    previous: str, seconds: int, resume_random: bool = False, resume_image: bool = False
) -> None:
    """Sleep for `seconds` and then restore the previous gif on the Cube.

    Runs in a background thread after show_temporary_gif has already replied,
    so any error here cannot be reported back to the client. When
    `resume_random`/`resume_image` is True the suspended random gif/image mode
    is resumed after the restore.
    """
    global _TEMP_GIF_RUNNING

    try:
        time.sleep(seconds)
        if previous:
            _set_cube_gif(previous)
    except Exception:
        pass
    finally:
        with _TEMP_GIF_LOCK:
            _TEMP_GIF_RUNNING = False
        if resume_random:
            _resume_random_mode()
        if resume_image:
            _resume_image_mode()


@mcp.tool()
def show_temporary_gif(data: str, filename: str, seconds: int = TEMP_GIF_DEFAULT_SECONDS) -> dict[str, str]:
    """
    Shows a gif or jpg/jpeg image temporarily on the Cube display.

    The flow is: read the gif currently displayed (to restore it later), upload
    the new image as tmp.gif/tmp.jpg with the same validations as
    upload_cube_image (Base64 decode, allowed extension, 240x240 dimensions,
    free space, upload confirmation) and display it. Other formats (png, webp,
    bmp...) are not rejected: they are converted to an exact 240x240 JPEG and
    shown as tmp.jpg. The call returns
    immediately; after the configured seconds a background job restores the
    previous gif. Only one temporary gif can run at a time: while one is being
    shown, new requests are rejected until it finishes. If the random gif mode
    is running it is suspended while the temporary gif is on screen and
    resumed automatically after the previous gif is restored. The same applies
    to the random image mode.

    Args:
        data: Image bytes encoded in Base64 (client-side).
        filename: Name of the image, used to determine its type (.gif -> tmp.gif,
            anything else -> tmp.jpg).
        seconds: Seconds to show the image (default 5, clamped to [1, 30]).
    """
    global _TEMP_GIF_RUNNING

    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    with _TEMP_GIF_LOCK:
        busy = _TEMP_GIF_RUNNING
    if busy:
        return {
            "status": "error",
            "message": "A temporary gif is already being shown. Wait for it to finish before starting another.",
        }

    clamped = max(TEMP_GIF_MIN_SECONDS, min(TEMP_GIF_MAX_SECONDS, seconds))

    name = Path(filename.strip()).name

    try:
        payload = _decode_image(data)
    except Exception as e:
        return {"status": "error", "message": f"Failed to decode image {name}: {e}"}

    if not payload:
        return {"status": "error", "message": f"Image is empty: {name}."}

    name, payload, conversion_error = _to_cube_compatible_image(name, payload)
    if conversion_error:
        return {"status": "error", "message": conversion_error}

    tmp_name = f"{TEMP_GIF_NAME}.gif" if name.lower().endswith(".gif") else f"{TEMP_GIF_NAME}.jpg"

    was_running_random = _suspend_random_mode()
    was_running_image = _suspend_image_mode()

    try:
        current = _fetch_cube_current_gif()
    except Exception as e:
        if was_running_random:
            _resume_random_mode()
        if was_running_image:
            _resume_image_mode()
        return {"status": "error", "message": f"Failed to read current gif from Cube: {e}"}

    result = upload_cube_image(base64.b64encode(payload).decode("ascii"), tmp_name)
    if result["status"] != "success":
        if was_running_random:
            _resume_random_mode()
        if was_running_image:
            _resume_image_mode()
        return result

    with _TEMP_GIF_LOCK:
        if _TEMP_GIF_RUNNING:
            if was_running_random:
                _resume_random_mode()
            if was_running_image:
                _resume_image_mode()
            return {
                "status": "error",
                "message": "A temporary gif is already being shown. Wait for it to finish before starting another.",
            }
        _TEMP_GIF_RUNNING = True

    try:
        response = _set_cube_gif(tmp_name)
    except Exception as e:
        with _TEMP_GIF_LOCK:
            _TEMP_GIF_RUNNING = False
        if was_running_random:
            _resume_random_mode()
        if was_running_image:
            _resume_image_mode()
        return {"status": "error", "message": f"Failed to display temporary gif {tmp_name}: {e}"}

    if "FAIL" in response.upper():
        with _TEMP_GIF_LOCK:
            _TEMP_GIF_RUNNING = False
        if was_running_random:
            _resume_random_mode()
        if was_running_image:
            _resume_image_mode()
        return {
            "status": "error",
            "message": f"Cube refused to display temporary gif {tmp_name}. Response: {response}",
        }

    previous = current.removeprefix(f"{CUBE_IMAGE_DIR}/").lstrip("/")
    threading.Thread(
        target=_restore_previous_gif,
        args=(previous, clamped, was_running_random, was_running_image),
        daemon=True,
    ).start()

    paused_note = ""
    if was_running_random:
        paused_note = " Random gif mode paused (it will resume automatically)."
    elif was_running_image:
        paused_note = " Random image mode paused (it will resume automatically)."

    if not previous:
        return {
            "status": "success",
            "message": (
                f"Temporary gif {tmp_name} is now displayed for {clamped} seconds. "
                f"No previous gif to restore.{paused_note}"
            ),
        }

    return {
        "status": "success",
        "message": (
            f"Temporary gif {tmp_name} is now displayed for {clamped} seconds. "
            f"{previous} will be restored automatically.{paused_note}"
        ),
    }


def _list_local_gifs() -> list[Path]:
    """List the .gif files available in RANDOM_GIF_DIR (empty when missing)."""
    if not RANDOM_GIF_DIR.is_dir():
        return []
    return sorted(
        path
        for path in RANDOM_GIF_DIR.iterdir()
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
    if not RANDOM_IMAGE_DIR.is_dir():
        return []
    return sorted(
        path
        for path in RANDOM_IMAGE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in LOCAL_IMAGE_SUFFIXES
    )


def _pick_random_image(exclude: str | None = None) -> Path | None:
    """Pick a random image from the local folder, avoiding `exclude` if possible."""
    images = _list_local_images()
    if not images:
        return None

    excluded = (exclude or "").lower()
    candidates = [image for image in images if image.name.lower() != excluded]
    return random.choice(candidates if candidates else images)


def _is_random_mode_running() -> bool:
    with _RANDOM_MODE_LOCK:
        return _RANDOM_MODE_RUNNING


def _is_random_mode_suspended() -> bool:
    with _RANDOM_MODE_LOCK:
        return _RANDOM_MODE_SUSPENDED


def _stop_random_mode() -> tuple[bool, str | None]:
    """Stop the random gif mode entirely. Returns (was_running, current_gif)."""
    global _RANDOM_MODE_RUNNING, _RANDOM_MODE_SUSPENDED

    with _RANDOM_MODE_LOCK:
        was_running = _RANDOM_MODE_RUNNING
        _RANDOM_MODE_RUNNING = False
        _RANDOM_MODE_SUSPENDED = False
        return was_running, _RANDOM_CURRENT_GIF


def _suspend_random_mode() -> bool:
    """Pause the random gif loop while a temporary gif borrows the screen.

    Returns True when a running mode was suspended; the loop stays alive but
    does not cycle until _resume_random_mode is called.
    """
    global _RANDOM_MODE_SUSPENDED

    with _RANDOM_MODE_LOCK:
        if not _RANDOM_MODE_RUNNING:
            return False
        _RANDOM_MODE_SUSPENDED = True
        return True


def _resume_random_mode() -> None:
    """Lift a suspension made by _suspend_random_mode."""
    global _RANDOM_MODE_SUSPENDED

    with _RANDOM_MODE_LOCK:
        _RANDOM_MODE_SUSPENDED = False


def _is_image_mode_running() -> bool:
    with _RANDOM_IMAGE_MODE_LOCK:
        return _RANDOM_IMAGE_MODE_RUNNING


def _is_image_mode_suspended() -> bool:
    with _RANDOM_IMAGE_MODE_LOCK:
        return _RANDOM_IMAGE_MODE_SUSPENDED


def _stop_image_mode() -> tuple[bool, str | None]:
    """Stop the random image mode entirely. Returns (was_running, current_image)."""
    global _RANDOM_IMAGE_MODE_RUNNING, _RANDOM_IMAGE_MODE_SUSPENDED

    with _RANDOM_IMAGE_MODE_LOCK:
        was_running = _RANDOM_IMAGE_MODE_RUNNING
        _RANDOM_IMAGE_MODE_RUNNING = False
        _RANDOM_IMAGE_MODE_SUSPENDED = False
        return was_running, _RANDOM_CURRENT_IMAGE


def _suspend_image_mode() -> bool:
    """Pause the random image loop while a temporary gif borrows the screen.

    Returns True when a running mode was suspended; the loop stays alive but
    does not cycle until _resume_image_mode is called.
    """
    global _RANDOM_IMAGE_MODE_SUSPENDED

    with _RANDOM_IMAGE_MODE_LOCK:
        if not _RANDOM_IMAGE_MODE_RUNNING:
            return False
        _RANDOM_IMAGE_MODE_SUSPENDED = True
        return True


def _resume_image_mode() -> None:
    """Lift a suspension made by _suspend_image_mode."""
    global _RANDOM_IMAGE_MODE_SUSPENDED

    with _RANDOM_IMAGE_MODE_LOCK:
        _RANDOM_IMAGE_MODE_SUSPENDED = False


def _is_cube_display_on() -> bool:
    """Return True when the Cube display is on (brightness above zero).

    An unreachable device counts as off, so the random gif loop pauses
    instead of hammering a dead endpoint with uploads.
    """
    try:
        return _fetch_cube_brightness() > BRIGHTNESS_MIN
    except Exception:
        return False


def _wait_between_cycles(total_seconds: int, is_running, is_suspended) -> None:
    """Count total_seconds down in 1s steps, pausing whenever needed.

    The countdown only advances while the mode keeps running, it is not
    suspended and the Cube display is on; otherwise the wait keeps polling
    every second without counting down, resuming the cycle afterwards.
    """
    remaining = total_seconds
    while remaining > 0 and is_running():
        time.sleep(1)
        if not is_running():
            break
        if is_suspended():
            continue
        if _is_cube_display_on():
            remaining -= 1


def _sleep_interruptible(total_seconds: int) -> None:
    """Sleep for total_seconds in 1s steps so stop_random_gifs reacts fast.

    The countdown only advances while the Cube display is on and the mode is
    not suspended: when the display is off (or unreachable) or a temporary
    gif is being shown, the wait keeps polling every second without counting
    down, resuming the cycle afterwards.
    """
    _wait_between_cycles(total_seconds, _is_random_mode_running, _is_random_mode_suspended)


def _sleep_interruptible_for_images(total_seconds: int) -> None:
    """Sleep for total_seconds in 1s steps so stop_random_images reacts fast."""
    _wait_between_cycles(total_seconds, _is_image_mode_running, _is_image_mode_suspended)


def _run_random_cycle(exclude: str | None = None) -> tuple[bool, str]:
    """Upload and display one random local gif as random.gif on the Cube.

    Returns (True, gif_name) on success or (False, error_message) on failure.
    """
    try:
        gif_path = _pick_random_gif(exclude)
        if gif_path is None:
            return False, f"No .gif files found in {RANDOM_GIF_DIR}."

        encoded = base64.b64encode(gif_path.read_bytes()).decode("ascii")
        result = upload_cube_image(encoded, RANDOM_GIF_NAME)
        if result["status"] != "success":
            return False, result["message"]

        response = _set_cube_gif(RANDOM_GIF_NAME)
        if "FAIL" in response.upper():
            return False, f"Cube refused to display {RANDOM_GIF_NAME}. Response: {response}"

        return True, gif_path.name
    except Exception as exc:
        return False, str(exc)


def _run_random_image_cycle(exclude: str | None = None) -> tuple[bool, str]:
    """Upload and display one random local image as random.jpg on the Cube.

    Returns (True, image_name) on success or (False, error_message) on failure.
    """
    try:
        image_path = _pick_random_image(exclude)
        if image_path is None:
            return False, f"No .jpg files found in {RANDOM_IMAGE_DIR}."

        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        result = upload_cube_image(encoded, RANDOM_IMAGE_NAME)
        if result["status"] != "success":
            return False, result["message"]

        response = _set_cube_gif(RANDOM_IMAGE_NAME)
        if "FAIL" in response.upper():
            return False, f"Cube refused to display {RANDOM_IMAGE_NAME}. Response: {response}"

        return True, image_path.name
    except Exception as exc:
        return False, str(exc)


def _random_gif_loop(seconds: int, first_gif: str) -> None:
    """Keep uploading a new random gif every `seconds` until the mode stops.

    Runs in a background thread after start_random_gifs displayed the first
    gif. While the Cube display is off the loop stays paused, and any failed
    cycle is simply retried after the next wait.
    """
    global _RANDOM_MODE_RUNNING, _RANDOM_CURRENT_GIF

    previous = first_gif
    try:
        while _is_random_mode_running():
            _sleep_interruptible(seconds)
            if not _is_random_mode_running():
                break

            ok, value = _run_random_cycle(previous)
            if ok:
                with _RANDOM_MODE_LOCK:
                    _RANDOM_CURRENT_GIF = value
                previous = value
    finally:
        with _RANDOM_MODE_LOCK:
            _RANDOM_MODE_RUNNING = False


def _random_image_loop(seconds: int, first_image: str) -> None:
    """Keep uploading a new random image every `seconds` until the mode stops.

    Runs in a background thread after start_random_images displayed the first
    image. While the Cube display is off the loop stays paused, and any failed
    cycle is simply retried after the next wait.
    """
    global _RANDOM_IMAGE_MODE_RUNNING, _RANDOM_CURRENT_IMAGE

    previous = first_image
    try:
        while _is_image_mode_running():
            _sleep_interruptible_for_images(seconds)
            if not _is_image_mode_running():
                break

            ok, value = _run_random_image_cycle(previous)
            if ok:
                with _RANDOM_IMAGE_MODE_LOCK:
                    _RANDOM_CURRENT_IMAGE = value
                previous = value
    finally:
        with _RANDOM_IMAGE_MODE_LOCK:
            _RANDOM_IMAGE_MODE_RUNNING = False


@mcp.resource("cube://random-gif")
def get_random_gif_status() -> str:
    """
    Returns the state of the random gif mode.

    Reports whether the mode is running (or paused because the Cube display
    is off, or suspended while a temporary gif is shown) and which temporary
    gif (random.gif) is currently being used.
    """
    with _RANDOM_MODE_LOCK:
        running = _RANDOM_MODE_RUNNING
        suspended = _RANDOM_MODE_SUSPENDED
        current = _RANDOM_CURRENT_GIF

    if not running:
        state = "stopped"
    elif suspended:
        state = "running (suspended: temporary gif being shown)"
    elif _is_cube_display_on():
        state = "running"
    else:
        state = "running (paused: Cube display is off)"

    lines = [f"Random gif mode: {state}"]
    if current:
        lines.append(f"Current temporary gif: {current} (uploaded as {RANDOM_GIF_NAME})")
    else:
        lines.append("No temporary gif has been shown yet.")

    return "\n".join(lines)


@mcp.resource("cube://random-image")
def get_random_image_status() -> str:
    """
    Returns the state of the random image mode.

    Reports whether the mode is running (or paused because the Cube display
    is off, or suspended while a temporary gif is shown) and which temporary
    image (random.jpg) is currently being used.
    """
    with _RANDOM_IMAGE_MODE_LOCK:
        running = _RANDOM_IMAGE_MODE_RUNNING
        suspended = _RANDOM_IMAGE_MODE_SUSPENDED
        current = _RANDOM_CURRENT_IMAGE

    if not running:
        state = "stopped"
    elif suspended:
        state = "running (suspended: temporary gif being shown)"
    elif _is_cube_display_on():
        state = "running"
    else:
        state = "running (paused: Cube display is off)"

    lines = [f"Random image mode: {state}"]
    if current:
        lines.append(f"Current temporary image: {current} (uploaded as {RANDOM_IMAGE_NAME})")
    else:
        lines.append("No temporary image has been shown yet.")

    return "\n".join(lines)


@mcp.resource("gallery://images")
def list_gallery_images() -> str:
    """
    Returns a list of images available in the local media/images gallery.
    """
    images = _list_local_images()

    if not images:
        return f"No images found in {RANDOM_IMAGE_DIR}."

    return "Available gallery images:\n" + "\n".join(path.name for path in images)


@mcp.resource("gallery://gifs")
def list_gallery_gifs() -> str:
    """
    Returns a list of gifs available in the local media/gifs gallery.
    """
    gifs = _list_local_gifs()

    if not gifs:
        return f"No gifs found in {RANDOM_GIF_DIR}."

    return "Available gallery gifs:\n" + "\n".join(path.name for path in gifs)


@mcp.tool()
def start_random_gifs(seconds: int = RANDOM_GIF_DEFAULT_SECONDS) -> dict[str, str]:
    """
    Starts cycling random gifs from media/gifs on the Cube display.

    Picks a random gif from the local gifs folder, uploads it to the Cube as
    random.gif (overwriting the previous one) and displays it. Every `seconds`
    another random gif replaces it, forever, until stop_random_gifs is called;
    consecutive repeats are avoided when possible. The first gif is shown
    before this call returns. Read the cube://random-gif resource to know
    which gif is currently being used. If the random image mode is running it
    is stopped first, so both random modes never fight over the screen.

    Args:
        seconds: Seconds each gif stays on screen before switching to the next
            random gif (default 60 = 1 minute, clamped to [5, 3600]).
    """
    global _RANDOM_MODE_RUNNING, _RANDOM_MODE_SUSPENDED, _RANDOM_CURRENT_GIF

    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    with _RANDOM_MODE_LOCK:
        busy = _RANDOM_MODE_RUNNING
    if busy:
        return {
            "status": "error",
            "message": "Random gif mode is already running. Call stop_random_gifs first.",
        }

    clamped = max(RANDOM_GIF_MIN_SECONDS, min(RANDOM_GIF_MAX_SECONDS, seconds))

    if not _list_local_gifs():
        return {"status": "error", "message": f"No .gif files found in {RANDOM_GIF_DIR}."}

    with _RANDOM_MODE_LOCK:
        if _RANDOM_MODE_RUNNING:
            return {
                "status": "error",
                "message": "Random gif mode is already running. Call stop_random_gifs first.",
            }
        _RANDOM_MODE_RUNNING = True
        _RANDOM_MODE_SUSPENDED = False

    image_was_running, _previous_image = _stop_image_mode()

    current = _RANDOM_CURRENT_GIF
    ok, value = _run_random_cycle(current)

    if not ok:
        with _RANDOM_MODE_LOCK:
            _RANDOM_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to display the first random gif: {value}"}

    with _RANDOM_MODE_LOCK:
        _RANDOM_CURRENT_GIF = value

    threading.Thread(target=_random_gif_loop, args=(clamped, value), daemon=True).start()

    message = (
        f"Random gif mode started: {value} is displayed as {RANDOM_GIF_NAME}; "
        f"a new random gif will be shown every {clamped} seconds."
    )
    if image_was_running:
        message += " Random image mode stopped."

    return {"status": "success", "message": message}


@mcp.tool()
def stop_random_gifs() -> dict[str, str]:
    """
    Stops the random gif cycling started by start_random_gifs.

    The loop stops picking new gifs; whatever was uploaded as random.gif
    remains displayed on the Cube.
    """
    was_running, current = _stop_random_mode()

    if not was_running:
        return {"status": "success", "message": "Random gif mode is not running."}

    message = "Random gif mode stopped."
    if current:
        message += f" {current} ({RANDOM_GIF_NAME}) remains displayed."

    return {"status": "success", "message": message}


@mcp.tool()
def start_random_images(seconds: int = RANDOM_IMAGE_DEFAULT_SECONDS) -> dict[str, str]:
    """
    Starts cycling random images from media/images on the Cube display.

    Picks a random image from the local images folder, uploads it to the Cube
    as random.jpg (overwriting the previous one) and displays it. Every
    `seconds` another random image replaces it, forever, until
    stop_random_images is called; consecutive repeats are avoided when
    possible. Images must be exactly 240x240. The first image is shown before
    this call returns. Read the cube://random-image resource to know which
    image is currently being used. If the random gif mode is running it is
    stopped first, so both random modes never fight over the screen.

    Args:
        seconds: Seconds each image stays on screen before switching to the
            next random image (default 60 = 1 minute, clamped to [5, 3600]).
    """
    global _RANDOM_IMAGE_MODE_RUNNING, _RANDOM_IMAGE_MODE_SUSPENDED, _RANDOM_CURRENT_IMAGE

    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    with _RANDOM_IMAGE_MODE_LOCK:
        busy = _RANDOM_IMAGE_MODE_RUNNING
    if busy:
        return {
            "status": "error",
            "message": "Random image mode is already running. Call stop_random_images first.",
        }

    clamped = max(RANDOM_IMAGE_MIN_SECONDS, min(RANDOM_IMAGE_MAX_SECONDS, seconds))

    if not _list_local_images():
        return {"status": "error", "message": f"No .jpg files found in {RANDOM_IMAGE_DIR}."}

    with _RANDOM_IMAGE_MODE_LOCK:
        if _RANDOM_IMAGE_MODE_RUNNING:
            return {
                "status": "error",
                "message": "Random image mode is already running. Call stop_random_images first.",
            }
        _RANDOM_IMAGE_MODE_RUNNING = True
        _RANDOM_IMAGE_MODE_SUSPENDED = False

    gif_was_running, _previous_gif = _stop_random_mode()

    current = _RANDOM_CURRENT_IMAGE
    ok, value = _run_random_image_cycle(current)

    if not ok:
        with _RANDOM_IMAGE_MODE_LOCK:
            _RANDOM_IMAGE_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to display the first random image: {value}"}

    with _RANDOM_IMAGE_MODE_LOCK:
        _RANDOM_CURRENT_IMAGE = value

    threading.Thread(target=_random_image_loop, args=(clamped, value), daemon=True).start()

    message = (
        f"Random image mode started: {value} is displayed as {RANDOM_IMAGE_NAME}; "
        f"a new random image will be shown every {clamped} seconds."
    )
    if gif_was_running:
        message += " Random gif mode stopped."

    return {"status": "success", "message": message}


@mcp.tool()
def stop_random_images() -> dict[str, str]:
    """
    Stops the random image cycling started by start_random_images.

    The loop stops picking new images; whatever was uploaded as random.jpg
    remains displayed on the Cube.
    """
    was_running, current = _stop_image_mode()

    if not was_running:
        return {"status": "success", "message": "Random image mode is not running."}

    message = "Random image mode stopped."
    if current:
        message += f" {current} ({RANDOM_IMAGE_NAME}) remains displayed."

    return {"status": "success", "message": message}
