# 🖥️ MCP Audio Server

The **Audio Server** is an MCP-compliant server that provides low-level access to the host machine's audio hardware. It is designed to be deployed on resource-constrained devices like a Raspberry Pi.

## 🛠️ Key Features

- **Remote Playback**: Stream audio bytes via Base64 encoding.
- **Hardware Control**: Mute/Unmute and volume adjustments.
- **System Awareness**: Detects if `ffplay` is already running to prevent overlapping audio.
- **Async Execution**: Audio is played in the background to keep the server responsive.

## 🔌 Toolset

The server exposes the following MCP tools:

| Tool | Description | Parameters |
| :--- | :--- | :--- |
| `play_audio` | Plays a Base64 encoded audio string | `encoded_audio` (str) |
| `stop_audio` | Stops all current system playback | None |

## ⚙️ Installation

### Dependencies
The server relies on `ffplay` for decoding multiple audio formats:
```bash
sudo apt install ffmpeg
```

### Running the Server
Assuming you are using the `mcp` package:
```bash
python -m server.main
```

## 📝 Implementation Details

- **Audio Pipeline**: The server receives Base64 data $\rightarrow$ decodes to bytes $\rightarrow$ pipes into `ffplay` via `stdin`.
- **Process Management**: Uses `pgrep` and `pkill` to ensure only one audio source is active at a time.
- **Memory Safety**: Implements a `MAX_AUDIO_BYTES` limit (10MB) to prevent memory exhaustion.
