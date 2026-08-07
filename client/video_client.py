from __future__ import annotations

import base64
import binascii
from typing import Final

from mcp import Client

from .config import SERVER_URL

MAX_VIDEO_BYTES: Final[int] = 50 * 1024 * 1024


def _decode_video_payload(encoded_video: str, max_bytes: int = MAX_VIDEO_BYTES) -> bytes:
    """Decode a base64-encoded video payload and enforce a size limit."""
    try:
        decoded = base64.b64decode(encoded_video, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64 video payload.") from exc

    if len(decoded) > max_bytes:
        raise ValueError(f"Video payload exceeds the {max_bytes} byte limit.")

    return decoded


async def record_video(
    duration_seconds: int = 5, fps: int = 10
) -> dict:
    """Requests the server to record a video and returns the decoded video bytes.

    Args:
        duration_seconds: Desired recording length in seconds (1-30).
        fps: Desired framerate in frames per second (1-30). Low values keep the
            payload small.
    """
    async with Client(SERVER_URL) as client:
        result = await client.call_tool(
            "record_video",
            {"duration_seconds": int(duration_seconds), "fps": int(fps)},
        )
        content = result.structured_content

        if content.get("status") != "success":
            return content

        try:
            video_bytes = _decode_video_payload(content["data"])
        except (ValueError, KeyError) as exc:
            return {"status": "error", "message": str(exc)}

        return {
            "status": "success",
            "format": content.get("format", "mp4"),
            "data": video_bytes,
            "message": content.get("message", "Video recorded successfully."),
        }


async def save_video(output_path: str, duration_seconds: int = 5, fps: int = 10) -> dict:
    """Records a video and saves it to the given output file path."""
    result = await record_video(duration_seconds=duration_seconds, fps=fps)

    if result.get("status") != "success":
        return result

    with open(output_path, "wb") as f:
        f.write(result["data"])

    return {
        "status": "success",
        "path": output_path,
        "message": f"Video saved to {output_path}.",
    }