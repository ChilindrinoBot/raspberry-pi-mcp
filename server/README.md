# 🖥️ MCP Audio & Camera Server

The **Audio & Camera Server** is an MCP-compliant server that provides low-level access to the host machine's audio hardware and camera. It is designed to be deployed on resource-constrained devices like a Raspberry Pi.

## 🛠️ Key Features

- **Remote Playback**: Stream audio bytes via Base64 encoding.
- **Local File Playback**: Trigger playback of files already present on the server's filesystem.
- **Notification System**: Play pre-defined system notification sounds with random selection.
- **Hardware Control**: Mute/Unmute and volume adjustments for both speakers and microphone.
- **Photo Capture**: Capture photos from the Raspberry Pi camera and return them Base64-encoded.
- **System Awareness**: Detects if `ffplay` is already running to prevent overlapping audio.
- **Async Execution**: Audio is played in the background to keep the server responsive.

## 🔌 Toolset

The server exposes the following MCP tools:

| Tool | Description | Parameters |
| :--- | :--- | :--- |
| `play_audio` | Plays a Base64 encoded audio string | `encoded_audio` (str) |
| `play_audio_file` | Plays a local file from the server's disk | `file_path` (str) |
| `notify_audio` | Plays a notification sound | `random_sound` (bool) |
| `stop_audio` | Stops all current system playback | None |
| `play_alarm` | Plays an alarm sound in a loop | `alarm_name` (str), `stop_time` (int) |
| `mute` | Mutes the audio output | None |
| `unmute` | Unmutes the audio output | None |
| `set_volume` | Sets the audio output volume to a level between 0 and 100 | `level` (int) |
| `mute_mic` | Mutes the microphone | None |
| `unmute_mic` | Unmutes the microphone | None |
| `set_mic_volume` | Sets the microphone volume to a level between 0 and 100 | `level` (int) |
| `take_photo` | Captures a photo from the Raspberry Pi camera and returns it Base64-encoded | None |

## 📚 Resources

The server exposes the following MCP resources:

- `notifications://list`: Returns a text list of all available notification audio files on the server.
- `alarms://list`: Returns a text list of all available alarm audio files on the server.
- `speaker://volume`: Returns the current audio output volume level (0-100) as text, e.g. `Current volume: 75%`.
- `micphone://mute-state`: Returns the current microphone mute state as text, e.g. `Microphone is muted.` or `Microphone is unmuted.`.
- `micphone://volume`: Returns the current microphone volume level (0-100) as text, e.g. `Current microphone volume: 75%`.

## ⚙️ Installation

### Dependencies
The server relies on `ffplay` for decoding multiple audio formats:
```bash
sudo apt install ffmpeg
```

For camera capture, the server needs one of:
- `rpicam-still` (newest Raspberry Pi OS with libcamera, Bookworm+)
- `libcamera-still` (modern Raspberry Pi OS)
- `raspistill` (legacy Raspberry Pi OS)

Install with:
```bash
sudo apt install rpicam-apps   # Bookworm+ (rpicam-still)
# or
sudo apt install libcamera-apps   # older Pi OS (libcamera-still)
# or
sudo apt install raspberrypi-userland  # legacy Pi OS (raspistill)
```

### Running the Server
Assuming you are using the `mcp` package:
```bash
python -m server.main
```

## 📝 Implementation Details

- **Audio Pipeline**: The server receives Base64 data $\rightarrow$ decodes to bytes $\rightarrow$ pipes into `ffplay` via `stdin`.
- **Photo Pipeline**: The server captures a photo via `rpicam-still`, `libcamera-still` or `raspistill` $\rightarrow$ reads the JPEG bytes $\rightarrow$ returns them Base64-encoded to the client.
- **Photo Performance**: Captures at 1280x720 @ JPEG quality 85 (≈150 KB) with a 100 ms timeout override (default is ~5 s), making capture, Base64 encoding, and HTTP transfer fast.
- **Process Management**: Uses `pgrep` and `pkill` to ensure only one audio source is active at a time.
- **Memory Safety**: Implements a `MAX_AUDIO_BYTES` limit (10MB) to prevent memory exhaustion.
