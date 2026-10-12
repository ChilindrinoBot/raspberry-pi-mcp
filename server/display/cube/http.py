from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from typing import Final

import httpx

from . import config

_HREF_PATTERN: Final[re.Pattern[str]] = re.compile(r"href='([^']+)'")
# /filelist renders one <tr> per stored file as
# <td><a href='/name.ext'>name.ext</a></td><td>SIZE_IN_KB</td>...
_FILELIST_ROW_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"<a href='([^']+)'>[^<]*</a>\s*</td>\s*<td>(\d+)\s*</td>", re.IGNORECASE
)


def _fetch_cube_files() -> list[tuple[str, int]]:
    """Fetch the /filelist page from the Cube and return (path, size_kb) pairs."""
    url = f"{config.CUBE_BASE_URL}/filelist"
    html = urllib.request.urlopen(url).read().decode()
    return [
        (href.lstrip("/"), int(size_kb))
        for href, size_kb in _FILELIST_ROW_PATTERN.findall(html)
    ]


def _fetch_cube_gifs() -> list[str]:
    """Fetch the /filelist page from the Cube and extract the stored file paths."""
    return [name for name, _size_kb in _fetch_cube_files()]


def _delete_cube_file(name: str) -> None:
    """Request the Cube's /delete endpoint to remove a file from its memory.

    Files live under /image on the device, so the canonical /image/<name> path
    is always used regardless of how the file list renders the name. Only the
    HTTP transport status raises; the response body is ignored because the
    firmware replies inconsistently (e.g. "OK" for no-ops, "Fail" on success).
    """
    clean = name.strip().lstrip("/")
    if not clean.startswith("image/"):
        clean = f"image/{clean}"
    url = f"{config.CUBE_BASE_URL}/delete?file={urllib.parse.quote('/' + clean, safe='')}"
    urllib.request.urlopen(url).read()


def _clear_cube_contents_request() -> str:
    """Send the Cube's clear request (GET /set?clear=image)."""
    url = f"{config.CUBE_BASE_URL}/set?clear=image"
    return urllib.request.urlopen(url).read().decode().strip()


def _fetch_cube_space() -> tuple[int, int]:
    """Fetch the /space.json endpoint from the Cube and return (free, total) bytes."""
    url = f"{config.CUBE_BASE_URL}/space.json"
    data = json.loads(urllib.request.urlopen(url).read().decode())
    return int(data["free"]), int(data["total"])


def _set_cube_brightness(level: int) -> str:
    """Send a /set?brt=<level> request to the Cube, returning the response body."""
    url = f"{config.CUBE_BASE_URL}/set?brt={level}"
    return urllib.request.urlopen(url).read().decode().strip()


def _fetch_cube_brightness() -> int:
    """Fetch the /brt.json endpoint from the Cube and return the current brightness level."""
    url = f"{config.CUBE_BASE_URL}/brt.json"
    data = json.loads(urllib.request.urlopen(url).read().decode())
    return int(data["brt"])


def _fetch_cube_current_gif() -> str:
    """Fetch the /img.json endpoint from the Cube and return the currently displayed gif path."""
    url = f"{config.CUBE_BASE_URL}/img.json"
    data = json.loads(urllib.request.urlopen(url).read().decode())
    return str(data["img"]).strip()


def _set_cube_gif(gif: str) -> str:
    """Send a /set request to the Cube to display the given gif, returning the response body.

    The Cube stores its display assets under the /image directory, so the gif name is
    sent as /image/<name> to match how the device resolves them. Slashes are kept
    verbatim (e.g. /set?img=/image/Bomb.gif) while the rest is percent-encoded.
    """
    encoded = urllib.parse.quote(f"/image/{gif}")
    url = f"{config.CUBE_BASE_URL}/set?img={encoded}"
    return urllib.request.urlopen(url).read().decode().strip()


def _upload_cube_image(name: str, data: bytes) -> None:
    """POST an image to the Cube's /doUpload endpoint as multipart/form-data.

    Mirrors the device's web uploader: gifs are sent in the "image" field while
    jpg/jpeg files are sent in the "file" field, always targeting the /image dir.
    The part content type is sent explicitly (image/gif or image/jpeg, like a
    browser would) instead of httpx's application/octet-stream default.
    Transport-level failures (read timeouts, dropped connections) are retried
    once after a short pause, because the device can stall while writing the
    previous upload to flash; HTTP error responses are not retried.
    """
    is_gif = name.lower().endswith(".gif")
    field = "image" if is_gif else "file"
    content_type = "image/gif" if is_gif else "image/jpeg"
    url = f"{config.CUBE_BASE_URL}/doUpload?dir={config.CUBE_IMAGE_DIR}"
    timeout = httpx.Timeout(config.UPLOAD_TIMEOUT_SECONDS, connect=config.UPLOAD_CONNECT_TIMEOUT_SECONDS)

    for attempt in range(1, config.UPLOAD_ATTEMPTS + 1):
        try:
            response = httpx.post(url, files={field: (name, data, content_type)}, timeout=timeout)
            response.raise_for_status()
            return
        except httpx.HTTPStatusError:
            raise
        except httpx.TransportError:
            if attempt >= config.UPLOAD_ATTEMPTS:
                raise
            time.sleep(2)
