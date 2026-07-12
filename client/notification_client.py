import asyncio
from mcp import Client
from server import mcp

async def send_notification(random_sound: bool = False):
    """Sends a request to the server to play a notification sound."""
    async with Client(mcp) as client:
        result = await client.call_tool("notify_audio", {"random_sound": random_sound})
        return result.structured_content

async def list_notifications():
    """Fetches the list of available notification sounds from the server resource."""
    async with Client(mcp) as client:
        result = await client.read_resource("notifications://list")
        
        if not result.contents:
            return "No notification sounds found."
            
        return result.contents[0].text

async def notify_audio(random_sound: bool = False):
    """Wrapper for sending notification request."""
    return await send_notification(random_sound)