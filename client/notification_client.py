import asyncio
from mcp import Client
from server import mcp

async def send_notification(random_sound: bool = False):
    """Sends a request to the server to play a notification sound."""
    async with Client(mcp) as client:
        result = await client.call_tool("notify_audio", {"random_sound": random_sound})
        return result.structured_content

async def notify_audio(random_sound: bool = False):
    """Wrapper for sending notification request."""
    return await send_notification(random_sound)
