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


def _fetch_cube_images() -> list[str]:
    """Fetch the /filelist page from the Cube and extract the available image paths."""
    url = f"{CUBE_BASE_URL}/filelist"
    html = urllib.request.urlopen(url).read().decode()
    images = _HREF_PATTERN.findall(html)
    return [image.lstrip("/") for image in images]


@mcp.resource("cube://images")
def list_cube_images() -> str:
    """
    Returns a list of images available on the Cube display.
    """
    if not CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        images = _fetch_cube_images()
    except Exception as e:
        return f"Failed to fetch images from Cube: {e}"

    if not images:
        return "No images found on the Cube."

    return "Available Cube images:\n" + "\n".join(images)


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


def _set_cube_image(image: str) -> str:
    """Send a /set request to the Cube to display the given image, returning the response body.

    The Cube stores its display assets under the /image directory, so the image name is
    sent as /image/<name> to match how the device resolves them. Slashes are kept
    verbatim (e.g. /set?img=/image/Bomb.gif) while the rest is percent-encoded.
    """
    encoded = urllib.parse.quote(f"/image/{image}")
    url = f"{CUBE_BASE_URL}/set?img={encoded}"
    return urllib.request.urlopen(url).read().decode().strip()


@mcp.tool()
def set_cube_image(image: str) -> dict[str, str]:
    """
    Displays an image on the Cube display.

    Validates that the image exists in the Cube's file list before sending the /set request.

    Args:
        image: Name (or relative path) of the image to display on the Cube.
    """
    if not CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    image = image.strip().lstrip("/")
    if not image:
        return {"status": "error", "message": "Image name is required."}

    try:
        available = _fetch_cube_images()
    except Exception as e:
        return {"status": "error", "message": f"Failed to verify image availability: {e}"}

    if image not in available:
        return {
            "status": "error",
            "message": f"Image not found on Cube: {image}. Available: {', '.join(available) or 'none'}.",
        }

    try:
        response = _set_cube_image(image)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set image on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set image {image}. Response: {response}",
        }

    if not response:
        return {"status": "success", "message": f"Cube image set to: {image}"}

    return {
        "status": "success",
        "message": f"Cube image set to: {image}. Device response: {response}",
    }
