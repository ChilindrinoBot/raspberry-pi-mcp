from __future__ import annotations

import os
import random
import subprocess
from pathlib import Path
from typing import Final

from .. import mcp

# Absolute paths based on workspace structure
MEDIA_ROOT: Final[Path] = Path(__file__).resolve().parents[2] / "media"
NOTIFICATIONS_DIR: Final[Path] = MEDIA_ROOT / "audio" / "notifications"
DEFAULT_AUDIO: Final[Path] = MEDIA_ROOT / "default" / "notification.mp3"

def _play_file(file_path: Path) -> None:
    """
    Plays an audio file using a non-blocking system call.
    Using 'aplay' or 'mpg123' is common on Raspberry Pi, 
    but since ffplay is already confirmed installed, we use it 
    with -nodisp and -autoexit for a simple one-shot notification.
    """
    try:
        subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", str(file_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        raise RuntimeError(f"Failed to play notification sound: {e}")

@mcp.tool()
def notify_audio(random_sound: bool = False) -> dict[str, str]:
    """
    Plays a notification sound on the Raspberry Pi.
    
    Args:
        random_sound: If True, picks a random mp3 from /media/audio/notifications.
                     If False or no random files found, plays the default 'eureka.mp3'.
    """
    target_file = DEFAULT_AUDIO

    if random_sound:
        if NOTIFICATIONS_DIR.exists() and NOTIFICATIONS_DIR.is_dir():
            # Filter for mp3 files only
            audio_files = list(NOTIFICATIONS_DIR.glob("*.mp3"))
            if audio_files:
                target_file = random.choice(audio_files)
    
    if not target_file.exists():
        # Final fallback to default if for some reason default is also missing
        # although logically we should check this early
        return {
            "status": "error",
            "message": f"Notification audio file not found: {target_file}"
        }

    try:
        _play_file(target_file)
        return {
            "status": "success",
            "message": f"Playing notification: {target_file.name}"
        }
    except RuntimeError as e:
        return {
            "status": "error",
            "message": str(e)
        }
