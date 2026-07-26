from mcp import Client
from .config import SERVER_URL


async def play_audio_file(file_path: str):
    """Requests the server to play a local file from its filesystem."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("play_audio_file", {"file_path": file_path})
        return result.structured_content


async def stop_audio():
    """Sends a command to the MCP server to stop any current audio playback."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("stop_audio", {})
        return result.structured_content