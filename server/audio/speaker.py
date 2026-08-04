from __future__ import annotations

import re
import shutil
import subprocess
from typing import Final

from .. import mcp

# Default ALSA control name for the master volume on Raspberry Pi.
MASTER_CONTROL: Final[str] = "Master"

_VOLUME_PATTERN: Final[re.Pattern[str]] = re.compile(r"\[(\d+)%\]")


def _get_amixer_path() -> str:
    """Return the path to amixer, raising RuntimeError if it is not installed."""
    amixer = shutil.which("amixer")
    if amixer:
        return amixer
    raise RuntimeError("amixer is not installed. Please run: sudo apt install alsa-utils")


def _run_amixer(*args: str) -> subprocess.CompletedProcess[str]:
    """Run amixer with the given arguments and return the completed process."""
    amixer = _get_amixer_path()
    return subprocess.run(
        [amixer, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _get_volume_level() -> int | None:
    """Query the real volume level (0-100) via amixer. Returns None if it cannot be determined."""
    try:
        result = _run_amixer("get", MASTER_CONTROL)
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
        result = _run_amixer("set", MASTER_CONTROL, "mute")
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
        result = _run_amixer("set", MASTER_CONTROL, "unmute")
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
        result = _run_amixer("set", MASTER_CONTROL, f"{level}%")
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


def increase_volume(step: int = 5) -> dict[str, str | int]:
    """Placeholder for increasing the volume level."""
    return {"status": "volume-increased", "level": step}


def decrease_volume(step: int = 5) -> dict[str, str | int]:
    """Placeholder for decreasing the volume level."""
    return {"status": "volume-decreased", "level": step}