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

# 🎥 Record a 15 second video at 10 fps
python -m client.main record-video --output video.mp4 --duration 15 --fps 10

# 🧊 Get the gif currently displayed on the Cube
python -m client.main get-cube-gif

# 📂 List the files (gifs and images) stored on the Cube, with sizes in KB
python -m client.main list-cube-contents

# 🗑️ Delete a file from the Cube's memory
python -m client.main delete-cube-file --file tmp.gif

# 💾 Get the free storage space on the Cube display
python -m client.main get-cube-free-space

# 🖼️ Display an image on the Cube (validated, sent as /image/<name>)
python -m client.main set-cube-gif --gif gif1.gif

# 💡 Set the Cube display brightness to a specific level (0-100, default 50)
python -m client.main set-cube-brightness --level 10

# ✨ Get the current brightness level of the Cube display
python -m client.main get-cube-brightness

# 🌙 Turn off the Cube display (brightness 0, remembers the previous level)
python -m client.main turn-cube-off

# ☀️ Turn on the Cube display (restores the remembered brightness, default 50)
python -m client.main turn-cube-on

# 📤 Upload an image to the Cube display (sent Base64-encoded; gif/jpg must be 240x240, other formats are converted)
python -m client.main upload-cube-gif --file path/to/image.gif

# 💾 Save any image in the server's media/images pool, resized/padded to exactly 240x240 JPEG
# (--name usually has no suffix; .jpg is appended automatically, max 25 chars including it)
python -m client.main save-image-in-gallery --file path/to/photo.png --name test

# 📺 Show an image already stored in the server's gallery on the Cube
# (no timer: it stays until another gif or image is set)
python -m client.main show-gallery-image --file test.jpg

# 📺 Show a gif from the server's media/gifs gallery on the Cube as tmp.gif
# (no timer: it stays until another gif or image is set)
python -m client.main show-gallery-gif --file test.gif

# 🖼️ List the images stored in the server's local gallery (media/images)
python -m client.main list-gallery-images

# 🎞️ List the gifs stored in the server's local gallery (media/gifs)
python -m client.main list-gallery-gifs

# ⏱️ Show an image temporarily on the Cube (default 5 s, max 30 s, non-blocking; other formats are converted)
python -m client.main show-cube-gif --file path/to/image.gif --seconds 10

# 🎲 Start cycling random images from media/images as random.jpg (must be 240x240, default 60 s, max 3600 s)
python -m client.main start-random-images --seconds 60

# 🔍 Get which temporary image (random.jpg) is currently being used on the Cube
python -m client.main get-current-random-image

# 🛑 Stop cycling random images on the Cube (the last random.jpg stays displayed)
python -m client.main stop-random-images

# 🎲 Start cycling random gifs from media/gifs as random.gif (default 60 s, max 3600 s)
python -m client.main start-random-gifs --seconds 60

# 🔍 Get which temporary gif (random.gif) is currently being used on the Cube
python -m client.main get-current-random-gif

# 🛑 Stop cycling random gifs on the Cube (the last random.gif stays displayed)
python -m client.main stop-random-gifs

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
from client.video_client import record_video, save_video
from client.cube_client import (
    get_cube_current_gif,
    list_cube_contents,
    delete_cube_file,
    get_cube_free_space,
    set_cube_gif,
    set_cube_brightness,
    get_cube_brightness,
    turn_cube_display_off,
    turn_cube_display_on,
    upload_cube_image,
    save_image_in_gallery,
    show_gallery_image,
    show_gallery_gif,
    show_temporary_gif,
    list_gallery_images,
    list_gallery_gifs,
    get_random_image_status,
    start_random_cube_images,
    stop_random_cube_images,
    get_random_gif_status,
    start_random_cube_gifs,
    stop_random_cube_gifs,
)

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

    # 🎥 Record a 15 second video at 10 fps and save it
    result = await save_video("video.mp4", duration_seconds=15, fps=10)
    print(f"Video saved: {result}")

    # 🎥 Or record a video and get the raw bytes
    video = await record_video(duration_seconds=5, fps=10)
    print(f"Video format: {video['format']}, {len(video['data'])} bytes")

    # 🧊 Get the gif currently displayed on the Cube
    current_gif = await get_cube_current_gif()
    print(f"Cube current gif: {current_gif}")

    # 📂 List the files (gifs and images) stored on the Cube, with sizes in KB
    cube_contents = await list_cube_contents()
    print(f"Cube contents:\n{cube_contents}")

    # 🗑️ Delete a file from the Cube's memory
    delete_result = await delete_cube_file("tmp.gif")
    print(delete_result)

    # 💾 Get the free storage space on the Cube display
    cube_space = await get_cube_free_space()
    print(f"Cube space: {cube_space}")

    # 🧊 Display an image on the Cube (validated, sent as /image/<name>)
    result = await set_cube_gif("gif1.gif")
    print(f"Set Cube gif: {result}")

    # 💡 Set the Cube display brightness to 10% (0-100, default 50)
    result = await set_cube_brightness(10)
    print(f"Set Cube brightness: {result}")

    # 💡 Get the current brightness level of the Cube display
    brightness = await get_cube_brightness()
    print(f"Cube brightness: {brightness}")

    # 🌙 Turn off the Cube display (remembers the previous level)
    result = await turn_cube_display_off()
    print(f"Cube display off: {result}")

    # ☀️ Turn on the Cube display (restores the remembered level, default 50)
    result = await turn_cube_display_on()
    print(f"Cube display on: {result}")

    # 📤 Upload an image to the Cube display.
    # Gif/jpg images must be exactly 240x240; any other format (png, webp...)
    # is converted server-side to a 240x240 JPEG. The file is read locally,
    # Base64-encoded and sent to the server without any filesystem path.
    result = await upload_cube_image("path/to/image.gif")
    print(f"Upload: {result}")

    # 💾 Save any image into the server's media/images pool, resized/padded
    # to exactly 240x240 JPEG. Pass the desired save name (usually without
    # suffix; a trailing .jpg/.png is stripped and ".jpg" is always appended,
    # max 25 characters including the suffix).
    result = await save_image_in_gallery("path/to/photo.png", "test")
    print(f"Save: {result}")

    # 📺 Show an image already stored in the server's gallery on the Cube.
    # Pass the filename inside media/images, with or without the .jpg/.jpeg
    # extension. There is no timer: the image stays until another is set.
    result = await show_gallery_image("test.jpg")
    print(f"Show: {result}")

    # 📺 Show a gif from the server's media/gifs gallery on the Cube as
    # tmp.gif. No timer either: it stays until another gif or image is set.
    result = await show_gallery_gif("003")
    print(f"Show: {result}")

    # 🖼️ List the images stored in the server's local gallery (media/images).
    listing = await list_gallery_images()
    print(f"Gallery images:\n{listing}")

    # 🎞️ List the gifs stored in the server's local gallery (media/gifs).
    listing = await list_gallery_gifs()
    print(f"Gallery gifs:\n{listing}")

    # ⏱️ Show an image temporarily (default 5 s, max 30 s, non-blocking).
    # It is uploaded as tmp.gif/tmp.jpg, displayed and the previous gif is
    # restored automatically in the background. Only one at a time.
    result = await show_temporary_gif("path/to/image.gif", seconds=10)
    print(f"Temporary show: {result}")

    # 🎲 Start cycling random images from media/images as random.jpg.
    # Images must be 240x240. A new random image is uploaded and displayed
    # every N seconds (default 60).
    result = await start_random_cube_images(seconds=60)
    print(f"Random images started: {result}")

    # 🔍 Get which temporary image (random.jpg) is currently being used.
    status = await get_random_image_status()
    print(f"Random image status:\n{status}")

    # 🛑 Stop cycling random images (the last random.jpg stays displayed).
    result = await stop_random_cube_images()
    print(f"Random images stopped: {result}")

    # 🎲 Start cycling random gifs from media/gifs as random.gif.
    # A new random gif is uploaded and displayed every N seconds (default 60).
    result = await start_random_cube_gifs(seconds=60)
    print(f"Random gifs started: {result}")

    # 🔍 Get which temporary gif (random.gif) is currently being used.
    status = await get_random_gif_status()
    print(f"Random gif status:\n{status}")

    # 🛑 Stop cycling random gifs (the last random.gif stays displayed).
    result = await stop_random_cube_gifs()
    print(f"Random gifs stopped: {result}")

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
6. **Video Recording**: The client calls the `record_video` tool with `duration_seconds` and `fps`, receives a Base64-encoded MP4, decodes it, and saves it locally.

## 📋 Requirements
- Python 3.11+
- `mcp` client library
- Access to a running MCP Audio & Camera Server