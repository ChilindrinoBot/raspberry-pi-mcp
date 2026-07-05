# 🎮 MCP Audio Client

The **Audio Client** is a reference implementation of a client that communicates with the MCP Audio Server. It provides both a programmatic API and a Command Line Interface (CLI).

## 🚀 Usage

### Using the CLI
The simplest way to interact with the server is via the provided CLI:

```bash
# 🎵 Play a local audio file
python -m client.main play --file "my_song.mp3"

# 🛑 Stop the server from playing audio
python -m client.main stop
```

### Using the API
You can integrate the client into your own Python scripts:

```python
import asyncio
from client.audio_client import play_audio_file, stop_audio

async def main():
    # Start playing a file
    result = await play_audio_file("alert.wav")
    print(f"Server said: {result}")

    # Later, stop the playback
    await stop_audio()

asyncio.run(main())
```

## 🛠️ How it Works

1. **File Processing**: The client reads a local file from disk.
2. **Encoding**: Converts the binary audio data into a **Base64 string** to be compatible with the MCP JSON-RPC transport.
3. **MCP Call**: Dispatches a `call_tool` request to the server's `play_audio` tool.
4. **Remote Execution**: The server decodes the string and pipes the bytes directly to the system audio player.

## 📋 Requirements
- Python 3.11+
- `mcp` client library
- Access to a running MCP Audio Server
