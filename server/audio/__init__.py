from __future__ import annotations

from .play import play_audio, stop_audio
from .speaker import decrease_volume, get_volume, increase_volume, mute, set_volume, unmute

__all__ = [
    "play_audio",
    "stop_audio",
    "mute",
    "unmute",
    "set_volume",
    "get_volume",
    "increase_volume",
    "decrease_volume",
]
