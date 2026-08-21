from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Final

from .. import mcp

MAX_PHOTO_BYTES: Final[int] = 10 * 1024 * 1024


def _get_camera_command() -> list[str]:
    """Return the camera capture command, preferring rpicam-still (newest Pi OS) over libcamera-still and raspistill.

    Speed optimisations:
    - Resolution 1280x720 @ JPEG quality 85 keeps the payload small (±150 KB)
      while remaining visually sharp, so encoding and HTTP transfer are fast.
    - ``--timeout 100`` / ``-t 100`` overrides the default ~5 second viewfinder
      warm-up delay, so the photo is captured almost immediately.
    """
    rpicam = shutil.which("rpicam-still")
    if rpicam:
        return [
            rpicam,
            "--output", "{output}",
            "--width", "1280",
            "--height", "720",
            "--quality", "85",
            "--nopreview",
            "--timeout", "100",
        ]

    libcamera = shutil.which("libcamera-still")
    if libcamera:
        return [
            libcamera,
            "--output", "{output}",
            "--width", "1280",
            "--height", "720",
            "--quality", "85",
            "--nopreview",
            "--timeout", "100",
        ]

    raspistill = shutil.which("raspistill")
    if raspistill:
        return [
            raspistill,
            "-o", "{output}",
            "-w", "1280",
            "-h", "720",
            "-q", "85",
            "-n",
            "-t", "100",
        ]

    raise RuntimeError(
        "No camera capture tool found. Please install rpicam-apps (rpicam-still), "
        "libcamera-apps (libcamera-still), or raspistill (raspberrypi-userland)."
    )


def _capture_photo_bytes() -> bytes:
    """Capture a photo from the Raspberry Pi camera and return the raw JPEG bytes."""
    command_template = _get_camera_command()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "photo.jpg"
        command = [part.format(output=str(output_path)) for part in command_template]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Camera capture failed: {result.stderr.strip() or result.stdout.strip()}"
            )

        if not output_path.exists():
            raise RuntimeError("Camera capture completed but no photo file was produced.")

        photo_bytes = output_path.read_bytes()

    if len(photo_bytes) > MAX_PHOTO_BYTES:
        raise RuntimeError(f"Captured photo exceeds the {MAX_PHOTO_BYTES} byte limit.")

    return photo_bytes


@mcp.tool()
def take_photo() -> dict[str, str]:
    """Capture a photo from the Raspberry Pi camera and return it base64-encoded."""
    try:
        photo_bytes = _capture_photo_bytes()
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    encoded_photo = base64.b64encode(photo_bytes).decode("ascii")

    return {
        "status": "success",
        "format": "jpeg",
        "encoding": "base64",
        "data": encoded_photo,
        "message": "Photo captured successfully.",
    }