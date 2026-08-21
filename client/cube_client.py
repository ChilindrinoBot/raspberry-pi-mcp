from __future__ import annotations

from mcp import Client

from .auth import HMACTransport
from .config import SERVER_URL


async def list_cube_images() -> str:
    """Fetches the list of images available on the Cube from the server resource."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://images")

        if not result.contents:
            return "No images found on the Cube."

        return result.contents[0].text


async def get_cube_free_space() -> str:
    """Fetches the free storage space available on the Cube from the server resource."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://free-space")

        if not result.contents:
            return "No space information available for the Cube."

        return result.contents[0].text


async def set_cube_image(image: str) -> dict[str, str]:
    """Requests the server to display an image on the Cube (validated against the file list)."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.call_tool("set_cube_image", {"image": image})
        return result.structured_content
