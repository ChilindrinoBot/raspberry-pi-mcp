import argparse
import asyncio
import base64
from pathlib import Path

from mcp import Client

from server import mcp


async def main() -> None:
    parser = argparse.ArgumentParser(description="Send audio to the Raspberry Pi MCP server")
    parser.add_argument("--stop", action="store_true", help="Stop the currently playing audio")
    args = parser.parse_args()

    async with Client(mcp) as client:
        if args.stop:
            result = await client.call_tool("stop_audio", {})
            print(result.structured_content)
            return

        workspace_root = Path(__file__).resolve().parents[1]
        audio_path = workspace_root / "tia paola.mp3"
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        encoded_audio = base64.b64encode(audio_path.read_bytes()).decode("ascii")

        result = await client.call_tool(
            "play_audio",
            {"encoded_audio": encoded_audio, "filename": audio_path.name},
        )
        print(result.structured_content)


asyncio.run(main())