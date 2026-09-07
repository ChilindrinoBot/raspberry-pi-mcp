from __future__ import annotations

import re
import shutil
import subprocess
from typing import Final

from .. import mcp

_VOLUME_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+)%")


def _get_pactl_path() -> str:
    """Return the path to pactl, raising RuntimeError if it is not installed."""
    pactl = shutil.which("pactl")
    if pactl:
        return pactl
    raise RuntimeError("pactl is not installed. Please run: sudo apt install pulseaudio-utils")


def _run_pactl(*args: str) -> subprocess.CompletedProcess[str]:
    """Run pactl with the given arguments and return the completed process."""
    pactl = _get_pactl_path()
    return subprocess.run(
        [pactl, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _get_default_sink() -> str:
    """Return the default PulseAudio/PipeWire sink name. Raises RuntimeError if unavailable."""
    result = _run_pactl("get-default-sink")
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("No default audio sink found. Check PulseAudio/PipeWire is running.")
    return result.stdout.strip()


def _get_volume_level() -> int | None:
    """Query the real volume level (0-100) via pactl. Returns None if it cannot be determined."""
    try:
        sink = _get_default_sink()
        result = _run_pactl("get-sink-volume", sink)
    except RuntimeError:
        return None

    if result.returncode != 0:
        return None

    match = _VOLUME_PATTERN.search(result.stdout)
    if match is None:
        return None

    return int(match.group(1))


@mcp.tool()
def mute() -> dict[str, str]:
    """Mute the audio output on the Raspberry Pi."""
    try:
        sink = _get_default_sink()
        result = _run_pactl("set-sink-mute", sink, "1")
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    if result.returncode != 0:
        return {
            "status": "error",
            "message": f"Failed to mute audio: {result.stderr.strip() or result.stdout.strip()}",
        }

    return {"status": "muted", "message": "Audio output has been muted."}


@mcp.tool()
def unmute() -> dict[str, str]:
    """Unmute the audio output on the Raspberry Pi."""
    try:
        sink = _get_default_sink()
        result = _run_pactl("set-sink-mute", sink, "0")
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    if result.returncode != 0:
        return {
            "status": "error",
            "message": f"Failed to unmute audio: {result.stderr.strip() or result.stdout.strip()}",
        }

    return {"status": "unmuted", "message": "Audio output has been unmuted."}


@mcp.tool()
def set_volume(level: int) -> dict[str, str | int]:
    """Set the audio output volume to a level between 0 and 100 on the Raspberry Pi."""
    if not 0 <= level <= 100:
        return {
            "status": "error",
            "message": "Volume level must be between 0 and 100.",
        }

    try:
        sink = _get_default_sink()
        result = _run_pactl("set-sink-volume", sink, f"{level}%")
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    if result.returncode != 0:
        return {
            "status": "error",
            "message": f"Failed to set volume: {result.stderr.strip() or result.stdout.strip()}",
        }

    return {"status": "volume-set", "level": level, "message": f"Volume set to {level}%."}


@mcp.resource("speaker://volume")
def get_volume() -> str:
    """Returns the current audio output volume level on the Raspberry Pi."""
    level = _get_volume_level()

    if level is None:
        return "Could not determine the current volume level."

    return f"Current volume: {level}%"

