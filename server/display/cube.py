from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

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
