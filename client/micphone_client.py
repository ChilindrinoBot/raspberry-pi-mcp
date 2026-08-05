from mcp import Client
from .config import SERVER_URL


async def mute_mic() -> dict[str, str]:
    """Requests the server to mute the microphone."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("mute_mic", {})
        return result.structured_content


async def unmute_mic() -> dict[str, str]:
    """Requests the server to unmute the microphone."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("unmute_mic", {})
        return result.structured_content


async def set_mic_volume(level: int) -> dict[str, str | int]:
    """Requests the server to set the microphone volume to a level between 0 and 100."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("set_mic_volume", {"level": level})
        return result.structured_content


async def get_mic_volume() -> str:
    """Fetches the current microphone volume level from the server resource."""
    async with Client(SERVER_URL) as client:
        result = await client.read_resource("micphone://volume")

        if not result.contents:
            return "No microphone volume information available."

        return result.contents[0].text


async def get_mic_mute_state() -> str:
    """Fetches the current microphone mute state from the server resource."""
    async with Client(SERVER_URL) as client:
        result = await client.read_resource("micphone://mute-state")

        if not result.contents:
            return "No microphone mute state information available."

        return result.contents[0].text