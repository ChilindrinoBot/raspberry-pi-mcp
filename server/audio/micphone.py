from __future__ import annotations

import re
import shutil
import subprocess
from typing import Final

from .. import mcp

# Default ALSA control name for the microphone capture on Raspberry Pi.
CAPTURE_CONTROL: Final[str] = "Capture"

_VOLUME_PATTERN: Final[re.Pattern[str]] = re.compile(r"\[(\d+)%\]")
_MUTE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\[(on|off)\]")


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


def _get_mic_mute_state() -> bool | None:
    """Query the real microphone mute state via amixer. Returns True if muted, False if unmuted, None if unknown."""
    try:
        result = _run_amixer("get", CAPTURE_CONTROL)
    except RuntimeError:
        return None

    if result.returncode != 0:
        return None

    match = _MUTE_PATTERN.search(result.stdout)
    if match is None:
        return None

    return match.group(1) == "off"


def _get_mic_volume_level() -> int | None:
    """Query the real microphone volume level (0-100) via amixer. Returns None if it cannot be determined."""
    try:
        result = _run_amixer("get", CAPTURE_CONTROL)
    except RuntimeError:
        return None

    if result.returncode != 0:
        return None

    match = _VOLUME_PATTERN.search(result.stdout)
    if match is None:
        return None

    return int(match.group(1))


@mcp.tool()
def mute_mic() -> dict[str, str]:
    """Mute the microphone on the Raspberry Pi."""
    try:
        result = _run_amixer("set", CAPTURE_CONTROL, "nocap")
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    if result.returncode != 0:
        return {
            "status": "error",
            "message": f"Failed to mute microphone: {result.stderr.strip() or result.stdout.strip()}",
        }

    return {"status": "muted", "message": "Microphone has been muted."}


@mcp.tool()
def unmute_mic() -> dict[str, str]:
    """Unmute the microphone on the Raspberry Pi."""
    try:
        result = _run_amixer("set", CAPTURE_CONTROL, "cap")
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    if result.returncode != 0:
        return {
            "status": "error",
            "message": f"Failed to unmute microphone: {result.stderr.strip() or result.stdout.strip()}",
        }

    return {"status": "unmuted", "message": "Microphone has been unmuted."}


@mcp.tool()
def set_mic_volume(level: int) -> dict[str, str | int]:
    """Set the microphone volume to a level between 0 and 100 on the Raspberry Pi."""
    if not 0 <= level <= 100:
        return {
            "status": "error",
            "message": "Volume level must be between 0 and 100.",
        }

    try:
        result = _run_amixer("set", CAPTURE_CONTROL, f"{level}%")
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    if result.returncode != 0:
        return {
            "status": "error",
            "message": f"Failed to set microphone volume: {result.stderr.strip() or result.stdout.strip()}",
        }

    return {"status": "volume-set", "level": level, "message": f"Microphone volume set to {level}%."}


@mcp.resource("micphone://mute-state")
def get_mic_mute_state_resource() -> str:
    """Returns the current microphone mute state on the Raspberry Pi."""
    state = _get_mic_mute_state()

    if state is None:
        return "Could not determine the current microphone mute state."

    return "Microphone is muted." if state else "Microphone is unmuted."


@mcp.resource("micphone://volume")
def get_mic_volume() -> str:
    """Returns the current microphone volume level on the Raspberry Pi."""
    level = _get_mic_volume_level()

    if level is None:
        return "Could not determine the current microphone volume level."

    return f"Current microphone volume: {level}%"