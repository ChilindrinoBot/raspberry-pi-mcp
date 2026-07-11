# 🎮 MCP Audio Client

The **Audio Client** is a reference implementation of a client that communicates with the MCP Audio Server. It provides both a programmatic API and a Command Line Interface (CLI).

## 🚀 Usage

### Using the CLI
The simplest way to interact with the server is via the provided CLI:

```bash
# 🎵 Play a local audio file on the server
python -m client.main play --file "my_song.mp3"

# 🔔 Play a notification sound
python -m client.main notify --random

# 📋 List available notification sounds
python -m client.main list

# 🛑 Stop the server from playing audio
python -m client.main stop
```

### Using the API
You can integrate the client into your own Python scripts:

```python
import asyncio
from client.audio_client import play_audio_file, stop_audio
from client.notification_client import send_notification, list_notifications

async def main():
    # 📋 List available notifications
    sounds = await list_notifications()
    print(f"Available sounds:\n{sounds}")

    # 🔔 Trigger a notification
    await send_notification(random_sound=True)

    # 🎵 Start playing a file
    result = await play_audio_file("alert.wav")
    print(f"Server said: {result}")

    # Later, stop the playback
    await stop_audio()

asyncio.run(main())
```

## 🛠️ How it Works

1. **Direct Path Trigger**: The client sends the path of a file to the server.
2. **Resource Discovery**: Uses MCP resources to discover available notification sounds.
3. **MCP Call**: Dispatches a `call_tool` request to the server's `play_audio_file` or `notify_audio` tools.
4. **Remote Execution**: The server decodes the string and pipes the bytes directly to the system audio player.

## 📋 Requirements
- Python 3.11+
- `mcp` client library
- Access to a running MCP Audio Server
