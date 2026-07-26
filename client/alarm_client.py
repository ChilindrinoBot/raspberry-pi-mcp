from mcp import Client
from .config import SERVER_URL


async def list_alarms():
    """Fetches the list of available alarms from the server resource."""
    async with Client(SERVER_URL) as client:
        result = await client.read_resource("alarms://list")

        if not result.contents:
            return "No alarms found."

        return result.contents[0].text


async def play_alarm(stop_time: int = 30, random_alarm: bool = False) -> dict[str, str]:
    """Calls the play_alarm tool on the server."""
    async with Client(SERVER_URL) as client:
        result = await client.call_tool(
            "play_alarm",
            arguments={
                "stop_time": stop_time,
                "random_alarm": random_alarm,
            },
        )
        return result.structured_content
