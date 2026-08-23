from __future__ import annotations

import base64
from pathlib import Path

from mcp import Client

from .auth import AuthTransport
from .config import SERVER_URL


async def get_cube_current_gif() -> str:
    """Fetches the gif currently displayed on the Cube from the server resource."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://current-gif")

        if not result.contents:
            return "No current gif information available for the Cube."

        return result.contents[0].text


async def list_cube_gifs() -> str:
    """Fetches the list of gifs available on the Cube from the server resource."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://gifs")

        if not result.contents:
            return "No gifs found on the Cube."

        return result.contents[0].text


async def get_cube_free_space() -> str:
    """Fetches the free storage space available on the Cube from the server resource."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://free-space")

        if not result.contents:
            return "No space information available for the Cube."

        return result.contents[0].text


async def get_cube_brightness() -> str:
    """Fetches the current brightness level of the Cube from the server resource."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://brightness")

        if not result.contents:
            return "No brightness information available for the Cube."

        return result.contents[0].text


async def set_cube_gif(gif: str) -> dict[str, str]:
    """Requests the server to display a gif on the Cube (validated against the file list)."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool("set_cube_gif", {"gif": gif})
        return result.structured_content


async def set_cube_brightness(level: int = 50) -> dict[str, str]:
    """Requests the server to set the Cube display brightness (0-100, default 50)."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool("set_cube_brightness", {"level": level})
        return result.structured_content


async def turn_cube_display_off() -> dict[str, str]:
    """Requests the server to turn off the Cube display (brightness 0, remembering the previous level)."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool("turn_cube_display_off", {})
        return result.structured_content


async def turn_cube_display_on() -> dict[str, str]:
    """Requests the server to turn on the Cube display (restores the remembered brightness, default 50)."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool("turn_cube_display_on", {})
        return result.structured_content


def _encode_image(data: bytes) -> str:
    """Encode raw image bytes in Base64 for the server."""
    return base64.b64encode(data).decode()


async def upload_cube_image(file_path: str) -> dict[str, str]:
    """Uploads a local image to the Cube display.

    Gif/jpg images must be exactly 240x240; any other format (png, webp...)
    is converted server-side to an exact 240x240 JPEG and stored as
    <name>.jpg. The file is read locally, Base64-encoded and sent to the
    server without any filesystem path.
    """
    path = Path(file_path.strip())
    data = path.read_bytes()
    encoded = _encode_image(data)

    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool(
            "upload_cube_image",
            {"data": encoded, "filename": path.name},
        )
        return result.structured_content


async def show_temporary_gif(file_path: str, seconds: int = 5) -> dict[str, str]:
    """Shows a local image temporarily on the Cube display.

    Gif/jpg images must be exactly 240x240; any other format is converted
    server-side to a 240x240 JPEG. The file is uploaded as tmp.gif/tmp.jpg,
    displayed for the given seconds (default 5, max 30) and afterwards the
    previous gif is restored.
    """
    path = Path(file_path.strip())
    data = path.read_bytes()
    encoded = _encode_image(data)

    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool(
            "show_temporary_gif",
            {"data": encoded, "filename": path.name, "seconds": seconds},
        )
        return result.structured_content


async def save_image_in_gallery(file_path: str, name: str) -> dict[str, str]:
    """Saves a local image into the server's media/images pool for the Cube.

    The file is read locally, Base64-encoded and sent to the server together
    with `name`, the desired save name (usually without suffix; a trailing
    image suffix like .jpg/.png is stripped and ".jpg" is always appended,
    max 25 characters). The server resizes/pads the image to exactly 240x240
    and converts it to JPEG.
    """
    path = Path(file_path.strip())
    data = path.read_bytes()
    encoded = _encode_image(data)

    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool(
            "save_image_in_gallery",
            {"data": encoded, "name": name},
        )
        return result.structured_content


async def get_random_gif_status() -> str:
    """Fetches the random gif mode status (running, current gif) from the server resource."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://random-gif")

        if not result.contents:
            return "No random gif information available for the Cube."

        return result.contents[0].text


async def start_random_cube_gifs(seconds: int = 60) -> dict[str, str]:
    """Requests the server to start cycling random gifs as random.gif on the Cube.

    A new random gif from media/video/gifs is uploaded and displayed every
    `seconds` (default 60 = 1 minute) until stop is requested.
    """
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool("start_random_gifs", {"seconds": seconds})
        return result.structured_content


async def stop_random_cube_gifs() -> dict[str, str]:
    """Requests the server to stop cycling random gifs on the Cube."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool("stop_random_gifs", {})
        return result.structured_content


async def get_random_image_status() -> str:
    """Fetches the random image mode status (running, current image) from the server resource."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.read_resource("cube://random-image")

        if not result.contents:
            return "No random image information available for the Cube."

        return result.contents[0].text


async def start_random_cube_images(seconds: int = 60) -> dict[str, str]:
    """Requests the server to start cycling random images as random.jpg on the Cube.

    A new random image from media/images is uploaded and displayed every
    `seconds` (default 60 = 1 minute) until stop is requested.
    """
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool("start_random_images", {"seconds": seconds})
        return result.structured_content


async def stop_random_cube_images() -> dict[str, str]:
    """Requests the server to stop cycling random images on the Cube."""
    async with Client(AuthTransport(SERVER_URL)) as client:
        result = await client.call_tool("stop_random_images", {})
        return result.structured_content
