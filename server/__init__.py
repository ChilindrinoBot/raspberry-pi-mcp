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
)

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
    "set_volume"
]
