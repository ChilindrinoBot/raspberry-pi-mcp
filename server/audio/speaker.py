from __future__ import annotations

import shutil
import subprocess
from typing import Final

from .. import mcp

# Default ALSA control name for the master volume on Raspberry Pi.
MASTER_CONTROL: Final[str] = "Master"


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


def set_volume(level: int) -> dict[str, str | int]:
    """Placeholder for setting the volume level."""
    return {"status": "volume-set", "level": level}


def get_volume() -> dict[str, str | int]:
    """Placeholder for getting the current volume level."""
    return {"status": "volume-read", "level": 50}


def increase_volume(step: int = 5) -> dict[str, str | int]:
    """Placeholder for increasing the volume level."""
    return {"status": "volume-increased", "level": step}


def decrease_volume(step: int = 5) -> dict[str, str | int]:
    """Placeholder for decreasing the volume level."""
    return {"status": "volume-decreased", "level": step}