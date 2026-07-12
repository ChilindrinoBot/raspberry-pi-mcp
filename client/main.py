import asyncio
import argparse
import sys
import traceback
from .audio_client import play_audio_file, stop_audio
from .notification_client import send_notification, list_notifications
from .alarm_client import list_alarms

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

    # Command 'list'
    list_parser = subparsers.add_parser("list-notifications", help="List available notification sounds")

    # Command 'list-alarms'
    list_alarms_parser = subparsers.add_parser("list-alarms", help="List available alarms")

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
        elif args.command == "list-alarms":
            print("Fetching available alarms...")
            res = await list_alarms()
            print(f"\n{res}")
        else:
            parser.print_help()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    try:
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()