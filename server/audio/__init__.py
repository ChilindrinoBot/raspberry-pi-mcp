from __future__ import annotations

from .play import play_audio, stop_audio
from .notify import notify_audio, list_notification_audios
from .alarm import play_alarm, list_alarm_audios
# from .speaker import decrease_volume, get_volume, increase_volume, mute, set_volume, unmute

__all__ = [
    "play_audio",
    "stop_audio",
    "notify_audio",
    "list_notification_audios",
    "play_alarm",
    "list_alarm_audios",
]
