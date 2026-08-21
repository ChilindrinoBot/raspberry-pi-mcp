from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Final

import httpx
from dotenv import load_dotenv
from PIL import Image

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

    try:
        response = _set_cube_gif(gif)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set gif on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set gif {gif}. Response: {response}",
        }

    if not response:
        return {"status": "success", "message": f"Cube gif set to: {gif}"}

    return {
        "status": "success",
        "message": f"Cube gif set to: {gif}. Device response: {response}",
    }


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


@mcp.tool()
def upload_cube_image(data: str, filename: str) -> dict[str, str]:
    """
    Uploads a gif or jpg/jpeg image to the Cube display.

    The image bytes must be Base64-encoded by the client. After decoding, the
    file is validated: allowed extension (.gif, .jpg, .jpeg), dimensions
    exactly 240x240, and enough free space on the Cube before uploading it to
    the /image directory via /doUpload.

    Args:
        data: Image bytes encoded in Base64 (client-side).
        filename: Name of the image, used to determine its type.
    """
    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    name = Path(filename.strip()).name
    if not name:
        return {"status": "error", "message": "Filename is required."}

    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        return {
            "status": "error",
            "message": f"Unsupported file type: {suffix or 'none'}. Allowed: .gif, .jpg, .jpeg.",
        }

    try:
        payload = _decode_image(data)
    except Exception as e:
        return {"status": "error", "message": f"Failed to decode image {name}: {e}"}

    if not payload:
        return {"status": "error", "message": f"Image is empty: {name}."}

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
