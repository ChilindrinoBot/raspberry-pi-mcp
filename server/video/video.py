from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Final

from .. import mcp

MAX_VIDEO_DURATION_SECONDS: Final[int] = 30
DEFAULT_VIDEO_DURATION_SECONDS: Final[int] = 5
MIN_FRAMERATE: Final[int] = 1
MAX_FRAMERATE: Final[int] = 30
DEFAULT_FRAMERATE: Final[int] = 10
MAX_VIDEO_BYTES: Final[int] = 50 * 1024 * 1024

VIDEO_WIDTH: Final[str] = "1280"
VIDEO_HEIGHT: Final[str] = "720"
VIDEO_BITRATE: Final[str] = "2500000"


def _get_video_capture_command(output: Path, duration_ms: int, fps: int) -> list[str]:
    """Return the video recording command, preferring rpicam-vid (newest Pi OS)
    over libcamera-vid and raspivid.

    The camera tool always writes a raw H.264 stream; an MP4 container is produced
    afterwards with ffmpeg so the client gets a widely playable file. A low
    framerate keeps the encoded payload small, as requested.
    """
    rpicam = shutil.which("rpicam-vid")
    if rpicam:
        return [
            rpicam,
            "--output", str(output),
            "--width", VIDEO_WIDTH,
            "--height", VIDEO_HEIGHT,
            "--codec", "h264",
            "--framerate", str(fps),
            "--inline",
            "--bitrate", VIDEO_BITRATE,
            "--nopreview",
            "--timeout", str(duration_ms),
        ]

    libcamera = shutil.which("libcamera-vid")
    if libcamera:
        return [
            libcamera,
            "--output", str(output),
            "--width", VIDEO_WIDTH,
            "--height", VIDEO_HEIGHT,
            "--codec", "h264",
            "--framerate", str(fps),
            "--inline",
            "--bitrate", VIDEO_BITRATE,
            "--nopreview",
            "--timeout", str(duration_ms),
        ]

    raspivid = shutil.which("raspivid")
    if raspivid:
        return [
            raspivid,
            "-o", str(output),
            "-w", VIDEO_WIDTH,
            "-h", VIDEO_HEIGHT,
            "-b", VIDEO_BITRATE,
            "-fps", str(fps),
            "-n",
            "-t", str(duration_ms),
        ]

    raise RuntimeError(
        "No video camera available. Please install rpic-app (rpicam-vid), "
        "libcamera-apps (libcamera-vid), or raspivid (raspberrypi-userland)."
    )


def _remux_to_mp4(raw_path: Path, mp4_path: Path, fps: int = DEFAULT_FRAMERATE) -> None:
    """Remux a raw H.264 stream into an MP4 container using ffmpeg.

    The raw stream from rpicam-vid/libcamera-vid carries no reliable timing
    (its SPS VUI declares a broken rate), so ``-r <fps>`` is passed as an input
    option to stamp the frames with correct timestamps; otherwise the resulting
    MP4 is reported as ~0 seconds long and players only show a single frame.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not installed. Please run: sudo apt install ffmpeg")

    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-r", str(fps),
            "-i", str(raw_path),
            "-c", "copy",
            "-movflags", "+faststart",
            str(mp4_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg remux failed: {result.stderr.strip() or result.stdout.strip()}"
        )


def _record_video_bytes(duration_seconds: int, fps: int) -> tuple[bytes, str]:
    """Record a video clip from the Raspberry Pi camera and return its bytes
    along with the container format ("mp4", or "h264" as a fallback)."""
    duration_ms = duration_seconds * 1000

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / "video.h264"
        command = _get_video_capture_command(raw_path, duration_ms, fps)

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=duration_seconds + 15,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Video capture failed: {result.stderr.strip() or result.stdout.strip()}"
            )

        if not raw_path.exists():
            raise RuntimeError("Video capture completed but no video file was produced.")

        mp4_path = Path(tmpdir) / "video.mp4"
        try:
            _remux_to_mp4(raw_path, mp4_path, fps)
        except RuntimeError:
            # Graceful degradation: send the raw H.264 stream when ffmpeg is missing.
            video_bytes = raw_path.read_bytes()
            video_format = "h264"
        else:
            video_bytes = mp4_path.read_bytes()
            video_format = "mp4"

    if len(video_bytes) > MAX_VIDEO_BYTES:
        raise RuntimeError(f"Recorded video exceeds the {MAX_VIDEO_BYTES} byte limit.")

    return video_bytes, video_format


@mcp.tool()
def record_video(
    duration_seconds: int = DEFAULT_VIDEO_DURATION_SECONDS,
    fps: int = DEFAULT_FRAMERATE,
) -> dict[str, str]:
    """Record a video clip from the Raspberry Pi camera and return it base64-encoded.

    Args:
        duration_seconds: Desired recording length in seconds. It is clamped to the
            range [1, 30] so a recording can never exceed 30 seconds.
        fps: Desired framerate in frames per second. A low value (e.g. 1-10) keeps
            the encoded payload small. It is clamped to the range [1, 30].
    """
    duration_seconds = max(1, min(int(duration_seconds), MAX_VIDEO_DURATION_SECONDS))
    fps = max(MIN_FRAMERATE, min(int(fps), MAX_FRAMERATE))

    try:
        video_bytes, video_format = _record_video_bytes(duration_seconds, fps)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        return {"status": "error", "message": str(exc)}

    encoded_video = base64.b64encode(video_bytes).decode("ascii")

    return {
        "status": "success",
        "format": video_format,
        "encoding": "base64",
        "data": encoded_video,
        "message": f"Video recorded successfully ({duration_seconds}s @{fps}fps).",
    }
