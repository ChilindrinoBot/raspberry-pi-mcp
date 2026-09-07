# 🔊 Raspberry Pi MCP Audio Control System
Cualquier modificación en el nombre del proyecto debe ser consultada.

A distributed audio management system based on the **Model Context Protocol (MCP)**. This project allows you to remotely control audio playback and system volume on a target machine (e.g., a Raspberry Pi) via a standardized MCP interface.

## 🏗️ Architecture
The system is split into two main components:
- **`server/`**: The MCP Server. It runs on the machine connected to the speakers. It exposes tools to play audio bytes, stop playback, manage volume, control the microphone, play notification sounds, capture photos/videos from the camera, list the images available on the Cube display, save images into the local media/images pool (resized/padded to 240x240 JPEG), show gallery images and gifs on the Cube permanently, list the contents of the local galleries (images and gifs), cycle random images and random gifs on the Cube display, and run special routines (e.g. `pato-gira` – clears Cube, uploads `media/special/gifs/pato-gira/pato-gira.gif` + `pato-gira-rev.gif` and alternates every 60s via simple timer).
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

# 🧊 Get the gif currently displayed on the Cube
python -m client.main get-cube-gif

# 📂 List the files (gifs and images) stored on the Cube, with sizes in KB
python -m client.main list-cube-contents

# 🗑️ Delete a file from the Cube's memory
python -m client.main delete-cube-file --file tmp.gif

# 🧹 Clear all files from the Cube's memory
python -m client.main clear-cube-contents

# 💾 Get the free storage space on the Cube display
python -m client.main get-cube-free-space

# 🖼️ Display a gif on the Cube (validated against the Cube file list, sent as /image/<name>)
python -m client.main set-cube-gif --gif gif1.gif

# 💡 Set the Cube display brightness to a specific level (0-100, default 50)
python -m client.main set-cube-brightness --level 10

# ✨ Get the current brightness level of the Cube display
python -m client.main get-cube-brightness

# 🌙 Turn off the Cube display (brightness 0, remembers the previous level)
python -m client.main turn-cube-off

# ☀️ Turn on the Cube display (restores the remembered brightness, default 50)
python -m client.main turn-cube-on

# 📤 Upload a gif/jpg image (must be 240x240) to the Cube display (sent Base64-encoded)
python -m client.main upload-cube-gif --file path/to/image.gif

# 💾 Save any image in the server's media/images pool, resized/padded to exactly 240x240 JPEG (--name usually has no suffix;  max 25 chars)
python -m client.main save-image-in-gallery --file path/to/photo.png --name test

# 📺 Show an image already stored in the server's gallery on the Cube (no timer, it stays until changed)
python -m client.main show-gallery-image --file test.jpg

# 📺 Show a gif from the server's media/gifs gallery on the Cube as tmp.gif (no timer, it stays until changed)
python -m client.main show-gallery-gif --file test.gif

# 🖼️ List the images stored in the server's local gallery (media/images)
python -m client.main list-gallery-images

# 🎞️ List the gifs stored in the server's local gallery (media/gifs)
python -m client.main list-gallery-gifs

# ⏱️ Show an image temporarily on the Cube (default 5 s, max 30 s, non-blocking; other formats are converted)
python -m client.main show-cube-gif --file path/to/image.gif --seconds 10

# 🎲 Start cycling random images from media/images as random.jpg (must be 240x240, default 300 s / 5 min, max 3600 s)
python -m client.main start-random-images --seconds 300

# 🔍 Get which temporary image (random.jpg) is currently being used on the Cube
python -m client.main get-current-random-image

# 🛑 Stop cycling random images on the Cube (the last random.jpg stays displayed)
python -m client.main stop-random-images

# 🎲 Start cycling random gifs from media/gifs as random.gif (default 300 s / 5 min, max 3600 s)
python -m client.main start-random-gifs --seconds 300

# 🔍 Get which temporary gif (random.gif) is currently being used on the Cube
python -m client.main get-current-random-gif

# 🛑 Stop cycling random gifs on the Cube (the last random.gif stays displayed)
python -m client.main stop-random-gifs

# 🦆 Special routine `pato-gira` — clears Cube, uploads 2 gifs from media/special/gifs/pato-gira and loops every 60s (1 min) simple timer
python -m client.main special --routine pato-gira
python -m client.main special --routine pato-gira --seconds 60
python -m client.main special --status   # show special routine status
python -m client.main special --stop     # stop special routine
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
- **Audio Backend:** `pactl` (PipeWire/PulseAudio)
- **Image Validation:** Pillow
- **Package Management:** `uv` / `pyproject.toml`

## 🐚 Systemd Service Setup (Raspberry Pi)

To run the MCP server automatically on boot, create a systemd service.

### 1. Create the service file

```bash
sudo nano /etc/systemd/system/mcpserver.service
```

Paste the following template:

```ini
[Unit]
Description=Raspberry Pi MCP Server
After=network-online.target
Wants=network-online.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/Workspace/server
ExecStart=/home/YOUR_USERNAME/.local/bin/uv run python -m server.main
Restart=always
RestartSec=5

# Environment
Environment="PATH=/home/YOUR_USERNAME/.local/bin:/home/YOUR_USERNAME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native"

[Install]
WantedBy=multi-user.target
```

> Replace `YOUR_USERNAME` with your actual username.

### 2. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcpserver
sudo systemctl start mcpserver
```

### 3. Useful commands

```bash
# Check status
sudo systemctl status mcpserver

# View logs
sudo journalctl -u mcpserver -f

# Restart after code changes
sudo systemctl restart mcpserver

# Stop the service
sudo systemctl stop mcpserver
```

### 4. Troubleshooting

**Volume control fails with "Connection refused"**

The `PULSE_SERVER` env var is missing or wrong. Verify the socket path:
```bash
pactl info | grep "Server String"
```
Then update the service file with the correct path and restart.

**Audio not playing**

Ensure `ffplay` is installed:
```bash
sudo apt install ffmpeg
```

**Permission denied on PulseAudio**

Make sure your user has access to PulseAudio:
```bash
pactl info
```
If this fails, add your user to the `audio` group:
```bash
sudo usermod -aG audio YOUR_USERNAME
```

## 📁 Project Structure
```text
.
├── client/             # Reference MCP Client
│   ├── main.py         # Client CLI entry point
│   ├── audio_client.py # Audio control logic
│   ├── image_client.py # Photo capture logic
│   ├── video_client.py # Video recording logic
│   ├── notification_client.py # Notification logic
│   └── cube_client.py # Cube display image listing
├── server/             # MCP Server implementation
│   ├── audio/          # Audio playback, volume and microphone logic
│   │   ├── play.py     # Base audio control
│   │   ├── notify.py   # Notification sounds logic
│   │   ├── speaker.py  # Speaker mute/unmute and volume control
│   │   └── micphone.py # Microphone mute/unmute and volume control
│   ├── image/          # Photo capture tools
│   ├── video/          # Video recording tools
│   └── display/        # Cube display image and storage info
│       └── cube.py     # Cube current gif (/img.json), file listing with sizes (cube://contents), file deletion (/delete?file=), clear all (/set?clear=image), free space, gif-set (/image/<name>), brightness (/set?brt=, /brt.json), display on/off, image upload (/doUpload), temporary gif, local image saving (media/images, 240x240 JPEG with black padding), permanent gallery image/gif show, gallery listing (gallery://images, gallery://gifs), random image cycling (media/images -> random.jpg), random gif cycling and special routine pato-gira (media/special/gifs/pato-gira → 60s timer, cube://special)
└── tests/              # Integration tests
```
