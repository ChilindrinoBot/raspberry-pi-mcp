# 🔊 Raspberry Pi MCP Audio Control System

A distributed audio management system based on the **Model Context Protocol (MCP)**. This project allows you to remotely control audio playback and system volume on a target machine (e.g., a Raspberry Pi) via a standardized MCP interface.

## 🏗️ Architecture

The system is split into two main components:

- **`server/`**: The MCP Server. It runs on the machine connected to the speakers. It exposes tools to play audio bytes, stop playback, and manage volume.
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
```

## 🧪 Testing

You can run the integration tests to verify the audio processing and server logic:

```bash
# Run all tests in the tests/ directory
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
├── server/             # MCP Server implementation
│   ├── audio/          # Audio playback and volume logic
│   ├── image/          # Placeholder for image tools
│   └── video/          # Placeholder for video tools
└── tests/              # Integration tests
```
