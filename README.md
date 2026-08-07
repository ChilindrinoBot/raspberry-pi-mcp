# 🔊 Raspberry Pi MCP Audio Control System
Cualquier modificación en el nombre del proyecto debe ser consultada.

A distributed audio management system based on the **Model Context Protocol (MCP)**. This project allows you to remotely control audio playback and system volume on a target machine (e.g., a Raspberry Pi) via a standardized MCP interface.

## 🏗️ Architecture
The system is split into two main components:
- **`server/`**: The MCP Server. It runs on the machine connected to the speakers. It exposes tools to play audio bytes, stop playback, manage volume, control the microphone, play notification sounds, and capture photos/videos from the camera.
- **`client/`**: A reference Python client that demonstrates how to send audio files and control commands to the server.

## 🚀 Quick Start
### 1. Server Setup
The server requires `ffmpeg` (for `ffplay`) to be installed on the host machine:
```bash
sudo apt install ffmpeg
```

### 2. Running the Server
For production:
```bash
python -m server.main
```
For development:
```bash
uv run mcp dev server/main.py
```

### 3. Client Usage
Once the server is running, you can use the client CLI:
```bash
# Play an audio file
python -m client.main play --file path/to/audio.mp3

# Stop playback
python -m client.main stop

# Play a notification sound (default)
python -m client.main notify --random

# List available notification sounds
python -m client.main list-notifications

# Play an alarm sound
python -m client.main play-alarm --random --stop-time 10

# List available alarms
python -m client.main list-alarms

# 🔇 Mute the microphone
python -m client.main mute-mic

# 🔊 Unmute the microphone
python -m client.main unmute-mic

# 🔉 Set the microphone volume to a specific level (0-100)
python -m client.main set-mic-volume --level 75

# 📊 Get the current microphone volume level
python -m client.main get-mic-volume

# 📷 Capture a photo from the Raspberry Pi camera
python -m client.main take-photo --output photo.jpg

# 🎥 Record a 15 second video from the Raspberry Pi camera at a low framerate
python -m client.main record-video --output video.mp4 --duration 15 --fps 10
```

## 🧪 Testing

It is highly recommended to run the integration tests to verify the audio processing and server logic.

```bash
# Set PYTHONPATH to include the current directory and run tests
export PYTHONPATH=$PYTHONPATH:.
python -m unittest discover tests
```

## 🛠️ Tech Stack
- **Language:** Python 3.11+
- **Protocol:** Model Context Protocol (MCP)
- **Audio Backend:** `ffplay` (FFmpeg)
- **Package Management:** `uv` / `pyproject.toml`

## 📁 Project Structure
```text
.
├── client/             # Reference MCP Client
│   ├── main.py         # Client CLI entry point
│   ├── audio_client.py # Audio control logic
│   ├── image_client.py # Photo capture logic
│   ├── video_client.py # Video recording logic
│   └── notification_client.py # Notification logic
├── server/             # MCP Server implementation
│   ├── audio/          # Audio playback, volume and microphone logic
│   │   ├── play.py     # Base audio control
│   │   ├── notify.py   # Notification sounds logic
│   │   ├── speaker.py  # Speaker mute/unmute and volume control
│   │   └── micphone.py # Microphone mute/unmute and volume control
│   ├── image/          # Photo capture tools
│   └── video/          # Video recording tools
└── tests/              # Integration tests
```
