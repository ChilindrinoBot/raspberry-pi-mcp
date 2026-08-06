# 🎮 MCP Audio & Camera Client

The **Audio & Camera Client** is a reference implementation of a client that communicates with the MCP Audio & Camera Server. It provides both a programmatic API and a Command Line Interface (CLI).

## 🚀 Usage

### Using the CLI
The simplest way to interact with the server is via the provided CLI:

```bash
# 🎵 Play a local audio file on the server
python -m client.main play --file "my_song.mp3"

# 🔔 Play a notification sound
python -m client.main notify --random

# 📋 List available notification sounds
python -m client.main list-notifications

# ⏰ Play an alarm sound
python -m client.main play-alarm --random --stop-time 10

# 🔇 Mute the audio output
python -m client.main mute

# 🔊 Unmute the audio output
python -m client.main unmute

# 🔉 Set the volume to a specific level (0-100)
python -m client.main set-volume --level 75

# 📊 Get the current volume level
python -m client.main get-volume

# 🎤 Mute the microphone
python -m client.main mute-mic

# 🎤 Unmute the microphone
python -m client.main unmute-mic

# 🎚️ Set the microphone volume to a specific level (0-100)
python -m client.main set-mic-volume --level 75

# 📊 Get the current microphone volume level
python -m client.main get-mic-volume

# 🎤 Get the current microphone mute state
python -m client.main get-mic-mute-state

# 📷 Capture a photo from the Raspberry Pi camera
python -m client.main take-photo --output photo.jpg

# 🛑 Stop the server from playing audio
python -m client.main stop
```

### Using the API
You can integrate the client into your own Python scripts:

```python
import asyncio
from client.audio_client import play_audio_file, stop_audio
from client.notification_client import send_notification, list_notifications
from client.alarm_client import list_alarms
from client.speaker_client import mute, unmute, set_volume, get_volume
from client.micphone_client import mute_mic, unmute_mic, set_mic_volume, get_mic_volume, get_mic_mute_state
from client.image_client import take_photo, save_photo

async def main():
    # 📋 List available notifications
    sounds = await list_notifications()
    print(f"Available sounds:\n{sounds}")

    # ⏰ List available alarms
    alarms = await list_alarms()
    print(f"Available alarms:\n{alarms}")

    # 🔔 Trigger a notification
    await send_notification(random_sound=True)

    # 🎵 Start playing a file
    result = await play_audio_file("alert.wav")
    print(f"Server said: {result}")

    # 🔇 Mute the audio output
    await mute()

    # 🔊 Unmute the audio output
    await unmute()

    # 🔉 Set the volume to 75%
    await set_volume(75)

    # 📊 Get the current volume level
    volume = await get_volume()
    print(f"Current volume: {volume}")

    # 🎤 Mute the microphone
    await mute_mic()

    # 🎤 Unmute the microphone
    await unmute_mic()

    # 🎚️ Set the microphone volume to 75%
    await set_mic_volume(75)

    # 📊 Get the current microphone volume level
    mic_volume = await get_mic_volume()
    print(f"Current microphone volume: {mic_volume}")

    # 🎤 Get the current microphone mute state
    mic_mute_state = await get_mic_mute_state()
    print(f"Microphone mute state: {mic_mute_state}")

    # 📷 Capture a photo and save it to a file
    result = await save_photo("photo.jpg")
    print(f"Photo saved: {result}")

    # 📷 Or capture a photo and get the raw bytes
    photo = await take_photo()
    print(f"Photo format: {photo['format']}, {len(photo['data'])} bytes")

    # Later, stop the playback
    await stop_audio()


asyncio.run(main())
```

## 🛠️ How it Works

1. **Direct Path Trigger**: The client sends the path of a file to the server.
2. **Resource Discovery**: Uses MCP resources to discover available notification sounds.
3. **MCP Call**: Dispatches a `call_tool` request to the server's `play_audio_file` or `notify_audio` tools.
4. **Remote Execution**: The server decodes the string and pipes the bytes directly to the system audio player.
5. **Photo Capture**: The client calls the `take_photo` tool, receives a Base64-encoded JPEG, decodes it, and saves it locally.

## 📋 Requirements
- Python 3.11+
- `mcp` client library
- Access to a running MCP Audio & Camera Server