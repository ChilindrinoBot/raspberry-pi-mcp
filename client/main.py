import asyncio
import argparse
import sys
import traceback
from .audio_client import play_audio_file, stop_audio
from .notification_client import send_notification, list_notifications
from .alarm_client import list_alarms, play_alarm

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