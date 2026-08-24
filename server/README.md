# 🖥️ MCP Audio & Camera Server

The **Audio & Camera Server** is an MCP-compliant server that provides low-level access to the host machine's audio hardware and camera. It is designed to be deployed on resource-constrained devices like a Raspberry Pi.

## 🛠️ Key Features

- **Remote Playback**: Stream audio bytes via Base64 encoding.
- **Local File Playback**: Trigger playback of files already present on the server's filesystem.
- **Notification System**: Play pre-defined system notification sounds with random selection.
- **Hardware Control**: Mute/Unmute and volume adjustments for both speakers and microphone.
- **Photo Capture**: Capture photos from the Raspberry Pi camera and return them Base64-encoded.
- **Video Recording**: Record short video clips from the Raspberry Pi camera and return them Base64-encoded. Duration (1–30 s) and framerate (1–30 fps) are controllable; a low framerate keeps the payload small.
- **Cube Current Gif**: Report the gif currently displayed on the Cube via its `/img.json` endpoint.
- **Cube Display Listing**: List the files (gifs and images) stored on the Cube display — with their sizes in KB — via HTTP.
- **Cube File Deletion**: Delete a file stored in the Cube's memory (not the local gallery) via its `/delete?file=` endpoint. The canonical `/image/<name>` path is always sent, and success is only reported after re-checking the Cube's file list (up to 3 attempts, 1 s apart), because the firmware updates its index lazily and its responses are unreliable ("OK" for no-ops, "Fail" even when the delete succeeds).
- **Cube Storage Reporting**: Report the free and total storage space on the Cube display.
- **Cube Brightness Control**: Set the Cube display brightness (0–100, default 50) via its `/set?brt=` endpoint and query the current level via `/brt.json`.
- **Cube Display Power**: Turn the display off (brightness 0) remembering the previous level in memory, and turn it back on restoring that level (default 50 if nothing is remembered). The memory is in-process and resets when the server restarts.
- **Cube Image Upload**: Receive images Base64-encoded from the client (no server-side filesystem path involved). Gif/jpg images are validated (.gif/.jpg/.jpeg, exactly 240x240, checked with Pillow); any other format (png, webp, bmp...) is automatically converted to an exact 240x240 JPEG and its name gets a `.jpg` suffix. Before uploading, the Cube's free space is checked so at least a 50 KB reserve always stays free; otherwise the upload is rejected. The image is then uploaded to the Cube's `/image` directory via `/doUpload`, and the upload is confirmed by checking the file appears in the Cube's file list before reporting success.
- **Cube Local Image Saving**: `save_image_in_gallery` receives any image Base64-encoded plus a desired save name (usually suffix-less; a trailing image suffix like `.jpg`/`.png` is stripped and `.jpg` is always appended; the final name must be at most 25 characters). The image is scaled down preserving its aspect ratio until it fits 240x240, padded with black (sides or top/bottom as needed) up to exactly 240x240, transparent areas are composited over black, and the result is verified to be a valid JPEG before being stored into the local `media/images` pool used by the random image mode.
- **Local Gallery Listing**: Two resources report the contents of the server's local galleries as separate functions: `gallery://images` lists the `.jpg`/`.jpeg` files in `media/images` and `gallery://gifs` lists the `.gif` files in `media/gifs`, both sorted by name with each file's size in KB.
- **Cube Gallery Image Show**: `show_gallery_image` receives the name of an image already stored in `media/images`, uploads it to the Cube under its own name and displays it permanently — there is no timer, so it stays on screen until another gif or image is set. The lookup accepts the name with or without the `.jpg`/`.jpeg` suffix; images that are not 240x240 JPEGs yet are converted first (scaled down and padded with black). Before uploading it checks the Cube has room while keeping the 50 KB free reserve. The upload is confirmed via the Cube's file list before the /set request, and any running random mode (gifs or images) is stopped so the requested image stays on screen.
- **Cube Gallery Gif Show**: `show_gallery_gif` receives the name of a gif already stored in `media/gifs`, uploads it to the Cube as `tmp.gif` and displays it permanently — no timer, nothing is remembered or restored. The lookup accepts the name with or without the `.gif` suffix; the file must be a valid 240x240 GIF. While a temporary gif is being shown the call is rejected, and before uploading it checks the Cube has room while keeping the 50 KB free reserve; any running random mode (gifs or images) is stopped so the requested gif stays on screen.
- **Cube Temporary Gif**: Show an image momentarily: remembers the current gif, uploads the new image as `tmp.gif`/`tmp.jpg` with full validations (other formats are converted to 240x240 JPEG) and displays it. The call is non-blocking — a background job restores the previous gif after the configured time (default 5 s, max 30 s). While a temporary gif is being shown, new temporary shows are rejected until it finishes (in-process flag, like audio process control). Any running random mode (gifs or images) is suspended during the show and resumed afterwards.
- **Cube Random Image Mode**: Cycle random images from `media/images` on the Cube display. `start_random_images` uploads a random jpg/jpeg image as `random.jpg` (images must be exactly 240x240) and displays it, then swaps it for another random image every N seconds (default 60 s, clamped to 5–3600) in an endless loop; consecutive repeats are avoided when possible. The mode pauses automatically while the Cube display is off (or unreachable) and resumes when it is back on, and is suspended while a temporary gif is shown and resumed afterwards. Starting it stops the random gif mode first, since both share one screen. `set_cube_gif` stops it entirely, while `show_temporary_gif` only suspends it. `stop_random_images` ends the loop. The current image is tracked in-process and reset when the server restarts.
- **Cube Random Gif Mode**: Cycle random gifs from `media/gifs` on the Cube display. `start_random_gifs` uploads a random gif as `random.gif` and displays it, then swaps it for another random gif every N seconds (default 60 s, clamped to 5–3600) in an endless loop. The mode pauses automatically while the Cube display is off (or unreachable) and resumes when it is back on, and is suspended while a temporary gif is shown and resumed afterwards. Starting it stops the random image mode first, since both share one screen. `set_cube_gif` stops the mode entirely, while `show_temporary_gif` only suspends it. `stop_random_gifs` ends the loop. The current gif is tracked in-process and reset when the server restarts.
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
| `set_cube_gif` | Displays an image on the Cube (URL `/set?img=/image/<name>`) after validating the image exists in the Cube's file list; stops any running random mode (gifs or images) so the requested gif stays on screen | `gif` (str) |
| `set_cube_brightness` | Sets the Cube display brightness via URL `/set?brt=<level>` (clamped to 0–100, default 50) | `level` (int, optional) |
| `delete_cube_file` | Deletes a file from the Cube's memory via `/delete?file=/image/<name>` after confirming it exists in the Cube's file list; verifies it is gone from the list (up to 3 checks, 1 s apart) before reporting success | `filename` (str) |
| `turn_cube_display_off` | Turns off the Cube display (brightness 0) remembering the previous level in memory | None |
| `turn_cube_display_on` | Turns on the Cube display restoring the remembered brightness (default 50 if none) | None |
| `upload_cube_image` | Decodes a Base64-encoded image sent by the client, validates it (.gif/.jpg/.jpeg, 240x240; other formats are converted to 240x240 JPEG), checks free space (keeping a 50 KB reserve) and uploads it to the Cube's /image dir via `/doUpload` | `data` (str), `filename` (str) |
| `save_image_in_gallery` | Saves any Base64-encoded image into the local `media/images` pool: resizes/pads it to exactly 240x240 JPEG with black padding and verifies the result. `name` is the desired save name (usually without suffix; a trailing image suffix is stripped and `.jpg` appended, max 25 chars including it) | `data` (str), `name` (str) |
| `show_gallery_image` | Shows an image from the local `media/images` gallery on the Cube under its own name, with no timer (it stays until changed). Looks the image up by filename with or without the .jpg/.jpeg suffix, converts it if it is not a 240x240 JPEG yet, confirms the upload via the Cube's file list and stops any running random mode | `filename` (str) |
| `show_gallery_gif` | Shows a gif from the local `media/gifs` gallery on the Cube as tmp.gif, with no timer (it stays until changed). Looks the gif up by filename with or without the .gif suffix, requires a valid 240x240 GIF, confirms the upload via the Cube's file list, rejects while a temporary gif is being shown and stops any running random mode | `filename` (str) |
| `show_temporary_gif` | Shows a Base64-encoded image temporarily and returns immediately: uploads it as tmp.gif/tmp.jpg (other formats are converted to 240x240 JPEG), displays it for N seconds (default 5, clamped to 1–30) and restores the previous gif in a background job. One temporary gif at a time. Any running random mode (gifs or images) is suspended during the show and resumed afterwards | `data` (str), `filename` (str), `seconds` (int, optional) |
| `start_random_images` | Starts cycling random jpg/jpeg images from `media/images` on the Cube: uploads one as `random.jpg` (must be 240x240) and displays it, then swaps it for another random image every N seconds (default 60, clamped to 5–3600). The loop pauses while the Cube display is off and suspends while a temporary gif is shown. Consecutive repeats are avoided when possible. Stops the random gif mode if it was running | `seconds` (int, optional) |
| `stop_random_images` | Stops the random image cycling started by `start_random_images`. The last `random.jpg` stays displayed | None |
| `start_random_gifs` | Starts cycling random gifs from `media/gifs` on the Cube: uploads one as `random.gif` and displays it, then swaps it for another random gif every N seconds (default 60, clamped to 5–3600). The loop pauses while the Cube display is off and suspends while a temporary gif is shown. Consecutive repeats are avoided when possible. Stops the random image mode if it was running | `seconds` (int, optional) |
| `stop_random_gifs` | Stops the random gif cycling started by `start_random_gifs`. The last `random.gif` stays displayed | None |
| `take_photo` | Captures a photo from the Raspberry Pi camera and returns it Base64-encoded | None |
| `record_video` | Records a video clip and returns it Base64-encoded (clamped to 1–30 s, 1–30 fps) | `duration_seconds` (int), `fps` (int) |

## 📚 Resources

The server exposes the following MCP resources:

- `notifications://list`: Returns a text list of all available notification audio files on the server.
- `alarms://list`: Returns a text list of all available alarm audio files on the server.
- `speaker://volume`: Returns the current audio output volume level (0-100) as text, e.g. `Current volume: 75%`.
- `micphone://mute-state`: Returns the current microphone mute state as text, e.g. `Microphone is muted.` or `Microphone is unmuted.`.
- `micphone://volume`: Returns the current microphone volume level (0-100) as text, e.g. `Current microphone volume: 75%`.
- `cube://current-gif`: Returns the gif currently displayed on the Cube as text, e.g. `Current Cube gif: test.gif`.
- `cube://contents`: Returns a text list of the files (gifs and images) currently stored on the Cube display, one per line with its size in KB as reported by `/filelist` (e.g. `tmp.gif (274 KB)`).
- `cube://free-space`: Returns the free storage space on the Cube display in KB, e.g. `Free space on Cube: 903 KB (total: 3048 KB)`.
- `cube://brightness`: Returns the current brightness level of the Cube display (0-100) as text, e.g. `Current Cube brightness: 10`.
- `cube://brightness`: Returns the current brightness level of the Cube display (0-100) as text, e.g. `Current Cube brightness: 10`.
- `cube://random-image`: Returns the state of the random image mode as text, e.g. `Random image mode: running` with the current temporary image being used (`Current temporary image: foto.jpg (uploaded as random.jpg)`). It also reports `running (paused: Cube display is off)` or `running (suspended: temporary gif being shown)` while the loop is held, and `stopped` otherwise.
- `cube://random-gif`: Returns the state of the random gif mode as text, e.g. `Random gif mode: running` with the current temporary gif being used (`Current temporary gif: gifz.gif (uploaded as random.gif)`). It also reports `running (paused: Cube display is off)` or `running (suspended: temporary gif being shown)` while the loop is held, and `stopped` otherwise.
- `gallery://images`: Returns a text list of the images stored in the server's local `media/images` gallery (the pool used by `save_image_in_gallery` and the random image mode), e.g. `Available gallery images:` followed by one entry per line like `photo.jpg (45.2 KB)`.
- `gallery://gifs`: Returns a text list of the gifs stored in the server's local `media/gifs` gallery (the pool used by the random gif mode), e.g. `Available gallery gifs:` followed by one entry per line like `anim.gif (70.6 KB)`.

## ⚙️ Installation

### Dependencies
The server relies on `ffplay` for decoding multiple audio formats:
```bash
sudo apt install ffmpeg
```

For camera capture, the server needs one of:
- `rpicam-vid` (newest Raspberry Pi OS with libcamera, Bookworm+)
- `libcamera-vid` (modern Raspberry Pi OS)
- `raspivid` (legacy Raspberry Pi OS)

Install with:
```bash
sudo apt install rpicam-apps   # Bookworm+ (rpicam-vid)
# or
sudo apt install libcamera-apps   # older Pi OS (libcamera-vid)
# or
sudo apt install raspberrypi-userland  # legacy Pi OS (raspivid)
```

Video remuxing to MP4 also requires `ffmpeg`:
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
- **Photo Pipeline**: The server captures a photo via `rpicam-still`, `libcamera-still` or `raspistill` $\rightarrow$ reads the JPEG bytes $\rightarrow$ returns them Base64-encoded to the client.
- **Photo Performance**: Captures at 1280x720 @ JPEG quality 85 (≈150 KB) with a 100 ms timeout override (default is ~5 s), making capture, Base64 encoding, and HTTP transfer fast.
- **Video Pipeline**: The server records H.264 via `rpicam-vid`, `libcamera-vid` or `raspivid` (raw stream) $\rightarrow$ remuxes to MP4 with ffmpeg $\rightarrow$ returns the bytes Base64-encoded to the client. If ffmpeg is missing, it gracefully falls back to sending the raw H.264 stream.
- **Video Timing Fix**: The raw H.264 stream carries a broken SPS VUI rate, so ffmpeg is invoked with `-r <fps>` as an **input** option to stamp correct timestamps; otherwise the MP4 is ~0 s long and players only show a single frame.
- **Video Limits**: Duration is clamped to `[1, 30]` s and framerate to `[1, 30]` fps; payloads above 50 MB are rejected.
- **Process Management**: Uses `pgrep` and `pkill` to ensure only one audio source is active at a time.
- **Memory Safety**: Implements a `MAX_AUDIO_BYTES` limit (10MB) to prevent memory exhaustion.
- **Upload Reliability**: `/doUpload` posts wait up to 120 s for the device to acknowledge (`UPLOAD_TIMEOUT_SECONDS`, with a short 10 s connect phase via `UPLOAD_CONNECT_TIMEOUT_SECONDS`) and are retried once (`UPLOAD_ATTEMPTS = 2`) on transport-level failures such as read timeouts, because the Cube can stall momentarily while writing an upload to flash. HTTP error responses are not retried.
- **Free Space Reserve**: Every upload path (`upload_cube_image`, `show_temporary_gif`, random modes, `show_gallery_image`, `show_gallery_gif`) queries `/space.json` first via `_cube_free_space_rejection` and rejects the upload when it would leave less than `UPLOAD_FREE_SPACE_BUFFER` (50 KB) free on the device.
