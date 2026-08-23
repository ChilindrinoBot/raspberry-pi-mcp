import asyncio
import argparse
import sys
import traceback
import httpx


from .audio_client import play_audio_file, stop_audio
from .notification_client import send_notification, list_notifications
from .alarm_client import list_alarms, play_alarm
from .speaker_client import mute, unmute, set_volume, get_volume
from .micphone_client import mute_mic, unmute_mic, set_mic_volume, get_mic_volume, get_mic_mute_state
from .image_client import save_photo
from .video_client import save_video
from .cube_client import (
    get_cube_current_gif,
    list_cube_gifs,
    get_cube_free_space,
    set_cube_gif,
    set_cube_brightness,
    get_cube_brightness,
    turn_cube_display_off,
    turn_cube_display_on,
    upload_cube_image,
    save_image_in_gallery,
    show_temporary_gif,
    get_random_gif_status,
    start_random_cube_gifs,
    stop_random_cube_gifs,
    get_random_image_status,
    start_random_cube_images,
    stop_random_cube_images,
    list_gallery_images,
    list_gallery_gifs,
)


_CONNECTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
        ConnectionRefusedError,
    )

_CONNECTION_EXCEPTIONS = (ConnectionRefusedError,)


def _is_connection_error(exc: BaseException) -> bool:
    """Recursively unwrap ExceptionGroup / __cause__ / __context__ looking for
    any exception instance or type contained in _CONNECTION_EXCEPTIONS."""
    if isinstance(exc, _CONNECTION_EXCEPTIONS):
        return True
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_connection_error(sub) for sub in exc.exceptions)
    cause = exc.__cause__
    if cause is not None:
        return _is_connection_error(cause)
    context = exc.__context__
    if context is not None:
        return _is_connection_error(context)
    return False


async def run_cli():
    parser = argparse.ArgumentParser(description="MCP Audio Client CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command 'play'
    play_parser = subparsers.add_parser("play", help="Play an audio file")
    play_parser.add_argument("--file", required=True, help="Path to the audio file")

    # Command 'stop'
    subparsers.add_parser("stop", help="Stop current audio playback")

    # Command 'notify'
    notify_parser = subparsers.add_parser("notify", help="Play a notification sound")
    notify_parser.add_argument("--random", action="store_true", help="Pick a random notification sound")

    # Command 'list-notifications'
    list_parser = subparsers.add_parser("list-notifications", help="List available notification sounds")


    # Command 'play-alarm'
    alarm_parser = subparsers.add_parser("play-alarm", help="Play an alarm sound")
    alarm_parser.add_argument("--random", action="store_true", default=False, help="Pick a random alarm")
    alarm_parser.add_argument("--stop-time", type=int, default=60, help="Time in seconds to stop the alarm")

    # Command 'list-alarms'
    list_alarms_parser = subparsers.add_parser("list-alarms", help="List available alarms")

    # Command 'mute'
    subparsers.add_parser("mute", help="Mute the audio output")

    # Command 'unmute'
    subparsers.add_parser("unmute", help="Unmute the audio output")

    # Command 'set-volume'
    volume_parser = subparsers.add_parser("set-volume", help="Set the volume level (0-100)")
    volume_parser.add_argument("--level", type=int, required=True, help="Volume level (0-100)")

    # Command 'get-volume'
    subparsers.add_parser("get-volume", help="Get the current volume level")

    # Command 'mute-mic'
    subparsers.add_parser("mute-mic", help="Mute the microphone")

    # Command 'unmute-mic'
    subparsers.add_parser("unmute-mic", help="Unmute the microphone")

    # Command 'set-mic-volume'
    mic_volume_parser = subparsers.add_parser("set-mic-volume", help="Set the microphone volume level (0-100)")
    mic_volume_parser.add_argument("--level", type=int, required=True, help="Microphone volume level (0-100)")

    # Command 'get-mic-volume'
    subparsers.add_parser("get-mic-volume", help="Get the current microphone volume level")

    # Command 'get-mic-mute-state'
    subparsers.add_parser("get-mic-mute-state", help="Get the current microphone mute state")

    # Command 'take-photo'
    photo_parser = subparsers.add_parser("take-photo", help="Capture a photo from the Raspberry Pi camera")
    photo_parser.add_argument("--output", required=True, help="Path where the photo will be saved (e.g. photo.jpg)")

    # Command 'record-video'
    video_parser = subparsers.add_parser("record-video", help="Record a video from the Raspberry Pi camera")
    video_parser.add_argument("--output", required=True, help="Path where the video will be saved (e.g. video.mp4)")
    video_parser.add_argument("--duration", type=int, default=5, help="Recording length in seconds (1-30)")
    video_parser.add_argument("--fps", type=int, default=10, help="Framerate in frames per second (1-30)")

    # Command 'get-cube-gif'
    subparsers.add_parser("get-cube-gif", help="Get the gif currently displayed on the Cube")

    # Command 'list-cube-gifs'
    subparsers.add_parser("list-cube-gifs", help="List gifs available on the Cube display")

    # Command 'get-cube-free-space'
    subparsers.add_parser("get-cube-free-space", help="Get the free storage space on the Cube display")

    # Command 'set-cube-gif'
    cube_image_parser = subparsers.add_parser("set-cube-gif", help="Display a gif on the Cube display")
    cube_image_parser.add_argument("--gif", required=True, help="Gif name or path available on the Cube")

    # Command 'set-cube-brightness'
    cube_brightness_parser = subparsers.add_parser(
        "set-cube-brightness", help="Set the Cube display brightness level (0-100)"
    )
    cube_brightness_parser.add_argument(
        "--level", type=int, default=50, help="Brightness level (0-100, default: 50)"
    )

    # Command 'get-cube-brightness'
    subparsers.add_parser("get-cube-brightness", help="Get the current brightness level of the Cube display")

    # Command 'turn-cube-off'
    subparsers.add_parser(
        "turn-cube-off", help="Turn off the Cube display (brightness 0, remembers previous level)"
    )

    # Command 'turn-cube-on'
    subparsers.add_parser(
        "turn-cube-on", help="Turn on the Cube display (restores remembered brightness, default 50)"
    )

    # Command 'upload-cube-gif'
    cube_upload_parser = subparsers.add_parser(
        "upload-cube-gif",
        help="Upload an image to the Cube display (gif/jpg must be 240x240; other formats are converted)",
    )
    cube_upload_parser.add_argument("--file", required=True, help="Local path of the image to upload")

    # Command 'show-cube-gif'
    cube_temp_parser = subparsers.add_parser(
        "show-cube-gif",
        help="Show an image temporarily on the Cube display (gif/jpg must be 240x240; other formats are converted)",
    )
    cube_temp_parser.add_argument("--file", required=True, help="Local path of the gif or jpg/jpeg image to show")
    cube_temp_parser.add_argument(
        "--seconds",
        type=int,
        default=5,
        help="Seconds to show the image before restoring the previous gif (default 5, max 30)",
    )

    # Command 'save-image-in-gallery'
    cube_save_parser = subparsers.add_parser(
        "save-image-in-gallery",
        help="Save an image in media/images resized/padded to 240x240 as JPEG",
    )
    cube_save_parser.add_argument(
        "--file", required=True, help="Local path of the image to save (any format: png, gif, webp, jpg...)"
    )
    cube_save_parser.add_argument(
        "--name",
        required=True,
        help="Save name (usually without suffix; .jpg is added automatically, max 25 chars)",
    )

    # Command 'list-gallery-images'
    subparsers.add_parser(
        "list-gallery-images",
        help="List images stored in the server's media/images gallery",
    )

    # Command 'list-gallery-gifs'
    subparsers.add_parser(
        "list-gallery-gifs",
        help="List gifs stored in the server's media/gifs gallery",
    )

    # Command 'start-random-gifs'
    random_gif_parser = subparsers.add_parser(
        "start-random-gifs",
        help="Cycle random gifs from media/gifs on the Cube as random.gif",
    )
    random_gif_parser.add_argument(
        "--seconds",
        type=int,
        default=60,
        help="Seconds each gif is shown before switching to another random gif (default 60)",
    )

    # Command 'stop-random-gifs'
    subparsers.add_parser("stop-random-gifs", help="Stop cycling random gifs on the Cube")

    # Command 'get-current-random-gif'
    subparsers.add_parser(
        "get-current-random-gif", help="Get which temporary gif (random.gif) is being used"
    )

    # Command 'start-random-images'
    random_image_parser = subparsers.add_parser(
        "start-random-images",
        help="Cycle random images from media/images on the Cube as random.jpg",
    )
    random_image_parser.add_argument(
        "--seconds",
        type=int,
        default=60,
        help="Seconds each image is shown before switching to another random image (default 60)",
    )

    # Command 'stop-random-images'
    subparsers.add_parser("stop-random-images", help="Stop cycling random images on the Cube")

    # Command 'get-current-random-image'
    subparsers.add_parser(
        "get-current-random-image", help="Get which temporary image (random.jpg) is being used"
    )

    args = parser.parse_args()

    try:
        if args.command == "play":
            print(f"Attempting to play: {args.file}...")
            res = await play_audio_file(args.file)
            print(f"Server Response: {res}")
        elif args.command == "stop":
            print("Requesting to stop audio...")
            res = await stop_audio()
            print(f"Server Response: {res}")
        elif args.command == "notify":
            print("Requesting notification sound...")
            res = await send_notification(random_sound=args.random)
            print(f"Server Response: {res}")
        elif args.command == "list-notifications":
            print("Fetching available notification sounds...")
            res = await list_notifications()
            print(f"\n{res}")
        elif args.command == "play-alarm":
            print("Requesting to play an alarm...")
            res = await play_alarm(stop_time=args.stop_time, random_alarm=args.random)
            print(f"Server Response: {res}")
        elif args.command == "list-alarms":
            print("Fetching available alarms...")
            res = await list_alarms()
            print(f"\n{res}")
        elif args.command == "mute":
            print("Requesting to mute audio...")
            res = await mute()
            print(f"Server Response: {res}")
        elif args.command == "unmute":
            print("Requesting to unmute audio...")
            res = await unmute()
            print(f"Server Response: {res}")
        elif args.command == "set-volume":
            print(f"Requesting to set volume to {args.level}%...")
            res = await set_volume(args.level)
            print(f"Server Response: {res}")
        elif args.command == "get-volume":
            print("Fetching current volume level...")
            res = await get_volume()
            print(f"\n{res}")
        elif args.command == "mute-mic":
            print("Requesting to mute microphone...")
            res = await mute_mic()
            print(f"Server Response: {res}")
        elif args.command == "unmute-mic":
            print("Requesting to unmute microphone...")
            res = await unmute_mic()
            print(f"Server Response: {res}")
        elif args.command == "set-mic-volume":
            print(f"Requesting to set microphone volume to {args.level}%...")
            res = await set_mic_volume(args.level)
            print(f"Server Response: {res}")
        elif args.command == "get-mic-volume":
            print("Fetching current microphone volume level...")
            res = await get_mic_volume()
            print(f"\n{res}")
        elif args.command == "get-mic-mute-state":
            print("Fetching current microphone mute state...")
            res = await get_mic_mute_state()
            print(f"\n{res}")
        elif args.command == "take-photo":
            print("Capturing photo from Raspberry Pi camera...")
            res = await save_photo(args.output)
            print(f"Server Response: {res}")
        elif args.command == "record-video":
            print(f"Recording {args.duration}s video @{args.fps}fps...")
            res = await save_video(args.output, duration_seconds=args.duration, fps=args.fps)
            print(f"Server Response: {res}")
        elif args.command == "get-cube-gif":
            print("Fetching current Cube gif...")
            res = await get_cube_current_gif()
            print(f"\n{res}")
        elif args.command == "list-cube-gifs":
            print("Fetching gifs available on the Cube...")
            res = await list_cube_gifs()
            print(f"\n{res}")
        elif args.command == "get-cube-free-space":
            print("Fetching free space on the Cube...")
            res = await get_cube_free_space()
            print(f"\n{res}")
        elif args.command == "set-cube-gif":
            print(f"Setting Cube gif to {args.gif}...")
            res = await set_cube_gif(args.gif)
            print(f"Server Response: {res}")
        elif args.command == "set-cube-brightness":
            print(f"Setting Cube brightness to {args.level}...")
            res = await set_cube_brightness(args.level)
            print(f"Server Response: {res}")
        elif args.command == "get-cube-brightness":
            print("Fetching current Cube brightness level...")
            res = await get_cube_brightness()
            print(f"\n{res}")
        elif args.command == "turn-cube-off":
            print("Turning off the Cube display...")
            res = await turn_cube_display_off()
            print(f"Server Response: {res}")
        elif args.command == "turn-cube-on":
            print("Turning on the Cube display...")
            res = await turn_cube_display_on()
            print(f"Server Response: {res}")
        elif args.command == "upload-cube-gif":
            print(f"Uploading {args.file} to the Cube...")
            res = await upload_cube_image(args.file)
            print(f"Server Response: {res}")
        elif args.command == "show-cube-gif":
            print(f"Showing {args.file} on the Cube for {args.seconds}s...")
            res = await show_temporary_gif(args.file, args.seconds)
            print(f"Server Response: {res}")
        elif args.command == "save-image-in-gallery":
            print(f"Saving {args.file} as {args.name}.jpg (240x240 JPEG)...")
            res = await save_image_in_gallery(args.file, args.name)
            print(f"Server Response: {res}")
        elif args.command == "start-random-gifs":
            print(f"Cycling random gifs every {args.seconds}s...")
            res = await start_random_cube_gifs(args.seconds)
            print(f"Server Response: {res}")
        elif args.command == "stop-random-gifs":
            print("Stopping random gif cycling...")
            res = await stop_random_cube_gifs()
            print(f"Server Response: {res}")
        elif args.command == "get-current-random-gif":
            print("Fetching current random gif status...")
            res = await get_random_gif_status()
            print(f"\n{res}")
        elif args.command == "start-random-images":
            print(f"Cycling random images every {args.seconds}s...")
            res = await start_random_cube_images(args.seconds)
            print(f"Server Response: {res}")
        elif args.command == "stop-random-images":
            print("Stopping random image cycling...")
            res = await stop_random_cube_images()
            print(f"Server Response: {res}")
        elif args.command == "get-current-random-image":
            print("Fetching current random image status...")
            res = await get_random_image_status()
            print(f"\n{res}")
        elif args.command == "list-gallery-images":
            print("Fetching gallery images...")
            res = await list_gallery_images()
            print(f"\n{res}")
        elif args.command == "list-gallery-gifs":
            print("Fetching gallery gifs...")
            res = await list_gallery_gifs()
            print(f"\n{res}")
        else:
            parser.print_help()
    except BaseException as e:
        from client.config import SERVER_URL

        if _is_connection_error(e):
            print(
                f"\nError: Cannot connect to the MCP server at {SERVER_URL}\n"
                f"Make sure the server is running:  python -m server.main",
                file=sys.stderr,
            )
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)



def main():
    try:
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()