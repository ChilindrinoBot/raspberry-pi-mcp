from __future__ import annotations

import subprocess
import threading
import random
from pathlib import Path
from typing import Final

from ..audio.play import _is_ffplay_running, stop_audio
from .. import mcp

# Absolute paths based on workspace structure
MEDIA_ROOT: Path = Path(__file__).resolve().parents[2] / "media"
ALARMS_DIR: Path = MEDIA_ROOT / "audio" / "alarms"

DEFAULT_ALARM_STOP_TIME: Final[int] = 60


@mcp.resource("alarms://list")
def list_alarm_audios() -> str:
    """
    Returns a list of available alarm audio files.
    """
    if not ALARMS_DIR.exists() or not ALARMS_DIR.is_dir():
        return "No alarms directory found."

    alarm_files = list(ALARMS_DIR.glob("*.mp3"))
    if not alarm_files:
        return "No alarm audio files found."

    alarms = [f.name for f in alarm_files]
    return "Available alarms:\n" + "\n".join(alarms)


@mcp.tool()
def play_alarm(stop_time: int = DEFAULT_ALARM_STOP_TIME, random_alarm: bool = False) -> dict[str, str]:
    """
    Play an alarm sound in a loop for a given duration.
    If random_alarm is True, picks a random alarm from the alarms directory.
    If random_alarm is False, plays the default alarm.

    Args:
        stop_time: Seconds before auto-stopping. Defaults to 60.
        random_alarm: If True, picks a random alarm from the directory.
    """
    if _is_ffplay_running():
        return {
            "status": "busy",
            "message": "The system is busy. Audio is currently playing on the Raspberry Pi."
        }

    if random_alarm:
        alarm_files = list(ALARMS_DIR.glob("*.mp3"))
        if not alarm_files:
            return {
                "status": "error",
                "message": "No alarms found in the directory to pick from."
            }
        alarm_path = random.choice(alarm_files)
    else:
        alarm_path = MEDIA_ROOT / "default" / "alarm.mp3"

    if not alarm_path.exists():
        return {
            "status": "error",
            "message": f"Audio file not found: {alarm_path.name}"
        }

    try:
        process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loop", "0", str(alarm_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        from ..audio.play import register_process
        register_process(process.pid)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Failed to start alarm: {exc}"
        }


    timer = threading.Timer(stop_time, stop_audio)
    timer.daemon = True
    timer.start()

    return {
        "status": "playing",
        "message": f"Playing '{alarm_path.name}' for {stop_time}s."
    }
