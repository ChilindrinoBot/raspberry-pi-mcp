from __future__ import annotations

from mcp.server import MCPServer

mcp = MCPServer("Raspberry Pi")

from .audio import (
    play_audio,
    stop_audio,
    notify_audio,
    list_notification_audios,
    play_alarm,
    list_alarm_audios,
    mute,
    unmute,
    get_volume,
    set_volume,
    mute_mic,
    unmute_mic,
    set_mic_volume,
    get_mic_mute_state_resource,
    get_mic_volume,
)
from .image import take_photo
from .video.video import record_video

__all__ = [
    "mcp", 
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
    "mute_mic",
    "unmute_mic",
    "set_mic_volume",
    "get_mic_mute_state_resource",
    "get_mic_volume",
    "take_photo",
    "record_video",
]
