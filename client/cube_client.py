from __future__ import annotations

from mcp import Client

from .auth import HMACTransport
from .config import SERVER_URL


async def list_cube_gifs() -> str:
    """Fetches the list of gifs available on the Cube from the server resource."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://gifs")

        if not result.contents:
            return "No gifs found on the Cube."

        return result.contents[0].text


async def get_cube_free_space() -> str:
    """Fetches the free storage space available on the Cube from the server resource."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://free-space")

        if not result.contents:
            return "No space information available for the Cube."

        return result.contents[0].text


async def set_cube_gif(gif: str) -> dict[str, str]:
    """Requests the server to display a gif on the Cube (validated against the file list)."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.call_tool("set_cube_gif", {"gif": gif})
        return result.structured_content
