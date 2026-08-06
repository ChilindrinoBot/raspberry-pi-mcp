from __future__ import annotations

import base64
import binascii
from typing import Final

from mcp import Client

from .config import SERVER_URL

MAX_PHOTO_BYTES: Final[int] = 10 * 1024 * 1024


def _decode_photo_payload(encoded_photo: str, max_bytes: int = MAX_PHOTO_BYTES) -> bytes:
    """Decode a base64-encoded photo payload and enforce a size limit."""
    try:
        decoded = base64.b64decode(encoded_photo, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64 photo payload.") from exc

    if len(decoded) > max_bytes:
        raise ValueError(f"Photo payload exceeds the {max_bytes} byte limit.")

    return decoded


async def take_photo() -> dict:
    """Requests the server to capture a photo and returns the decoded photo bytes."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool("take_photo", {})
        content = result.structured_content

        if content.get("status") != "success":
            return content

        try:
            photo_bytes = _decode_photo_payload(content["data"])
        except (ValueError, KeyError) as exc:
            return {"status": "error", "message": str(exc)}

        return {
            "status": "success",
            "format": content.get("format", "jpeg"),
            "data": photo_bytes,
            "message": content.get("message", "Photo captured successfully."),
        }


async def save_photo(output_path: str) -> dict:
    """Captures a photo and saves it to the given output file path."""
    result = await take_photo()

    if result.get("status") != "success":
        return result

    with open(output_path, "wb") as f:
        f.write(result["data"])

    return {
        "status": "success",
        "path": output_path,
        "message": f"Photo saved to {output_path}.",
    }