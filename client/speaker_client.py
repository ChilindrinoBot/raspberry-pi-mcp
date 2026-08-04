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


async def set_volume(level: int) -> dict[str, str | int]:
    """Requests the server to set the volume to a level between 0 and 100."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("set_volume", {"level": level})
        return result.structured_content


async def get_volume() -> str:
    """Fetches the current volume level from the server resource."""
    async with Client(SERVER_URL) as client:
        result = await client.read_resource("speaker://volume")

        if not result.contents:
            return "No volume information available."

        return result.contents[0].text