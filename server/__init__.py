from __future__ import annotations

from mcp.server import MCPServer

mcp = MCPServer("Raspberry Pi")

from .audio.play import play_audio, stop_audio  # noqa: E402,F401

__all__ = ["mcp", "play_audio", "stop_audio"]
