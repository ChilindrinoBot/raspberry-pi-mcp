import asyncio
import argparse
import sys
import traceback
from .audio_client import play_audio_file, stop_audio
from .notification_client import send_notification, list_notifications
from .alarm_client import list_alarms, play_alarm
from .speaker_client import mute, unmute, set_volume, get_volume
from .micphone_client import mute_mic, unmute_mic, set_mic_volume, get_mic_volume, get_mic_mute_state
from .image_client import save_photo
from .video_client import save_video

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
        else:
            parser.print_help()
    except Exception as e:
        from client.config import SERVER_URL

        # ExceptionGroup is raised by anyio/TaskGroup on connection failures.
        # Unwrap it to find the root cause.
        causes: list[BaseException] = (
            list(e.exceptions) if isinstance(e, BaseExceptionGroup) else [e]
        )
        is_connection_error = any(
            isinstance(c, (ConnectionRefusedError, OSError)) for c in causes
        )
        if is_connection_error:
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