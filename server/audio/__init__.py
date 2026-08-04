from __future__ import annotations

from .play import play_audio, stop_audio
from .notify import notify_audio, list_notification_audios
from .alarm import play_alarm, list_alarm_audios
from .speaker import mute, unmute, get_volume, set_volume

__all__ = [
    "play_audio",
    "stop_audio",
    "notify_audio",
    "list_notification_audios",
    "play_alarm",
    "list_alarm_audios",
    "mute",
    "unmute",
    "get_volume",
    "set_volume",
]
