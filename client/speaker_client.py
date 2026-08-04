from mcp import Client
from .config import SERVER_URL


async def mute() -> dict[str, str]:
    """Requests the server to mute the audio output."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("mute", {})
        return result.structured_content


async def unmute() -> dict[str, str]:
    """Requests the server to unmute the audio output."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("unmute", {})
        return result.structured_content