from __future__ import annotations

import base64
from pathlib import Path

from mcp import Client

from .auth import HMACTransport
from .config import SERVER_URL


async def get_cube_current_gif() -> str:
    """Fetches the gif currently displayed on the Cube from the server resource."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://current-gif")

        if not result.contents:
            return "No current gif information available for the Cube."

        return result.contents[0].text


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


async def get_cube_brightness() -> str:
    """Fetches the current brightness level of the Cube from the server resource."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://brightness")

        if not result.contents:
            return "No brightness information available for the Cube."

        return result.contents[0].text


async def set_cube_gif(gif: str) -> dict[str, str]:
    """Requests the server to display a gif on the Cube (validated against the file list)."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.call_tool("set_cube_gif", {"gif": gif})
        return result.structured_content


async def set_cube_brightness(level: int = 50) -> dict[str, str]:
    """Requests the server to set the Cube display brightness (0-100, default 50)."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.call_tool("set_cube_brightness", {"level": level})
        return result.structured_content


async def turn_cube_display_off() -> dict[str, str]:
    """Requests the server to turn off the Cube display (brightness 0, remembering the previous level)."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.call_tool("turn_cube_display_off", {})
        return result.structured_content


async def turn_cube_display_on() -> dict[str, str]:
    """Requests the server to turn on the Cube display (restores the remembered brightness, default 50)."""
    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.call_tool("turn_cube_display_on", {})
        return result.structured_content


def _encode_image(data: bytes) -> str:
    """Encode raw image bytes in Base64 for the server."""
    return base64.b64encode(data).decode()


async def upload_cube_image(file_path: str) -> dict[str, str]:
    """Uploads a local gif/jpg image (240x240) to the Cube display.

    The file is read locally, Base64-encoded and sent to the server without
    any filesystem path.
    """
    path = Path(file_path.strip())
    data = path.read_bytes()
    encoded = _encode_image(data)

    async with Client(HMACTransport(SERVER_URL)) as client:
        result = await client.call_tool(
            "upload_cube_image",
            {"data": encoded, "filename": path.name},
        )
        return result.structured_content
