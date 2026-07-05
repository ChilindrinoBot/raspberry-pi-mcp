import base64
from pathlib import Path
from mcp import Client
from server import mcp

async def play_audio_file(file_path: str):
    """Reads an audio file, encodes it to base64 and sends it to the MCP server."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    # Read and encode the audio file
    encoded_audio = base64.b64encode(path.read_bytes()).decode("ascii")

    async with Client(mcp) as client:
        result = await client.call_tool(
            "play_audio",
            {"encoded_audio": encoded_audio},
        )
        return result.structured_content

async def stop_audio():
    """Sends a command to the MCP server to stop any current audio playback."""
    async with Client(mcp) as client:
        result = await client.call_tool("stop_audio", {})
        return result.structured_content