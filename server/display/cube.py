from __future__ import annotations

import os
import re
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
