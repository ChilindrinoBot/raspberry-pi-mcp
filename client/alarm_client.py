import asyncio
from mcp import Client
from server import mcp

async def list_alarms():
    """Fetches the list of available alarms from the server resource."""
    async with Client(mcp) as client:
        result = await client.read_resource("alarms://list")
        
        if not result.contents:
            return "No alarms found."
            
        return result.contents[0].text
