from __future__ import annotations

from pathlib import Path
from .. import mcp

# Absolute paths based on workspace structure
MEDIA_ROOT: Path = Path(__file__).resolve().parents[2] / "media"
ALARMS_DIR: Path = MEDIA_ROOT / "audio" / "alarms"

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
