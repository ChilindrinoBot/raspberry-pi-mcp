import asyncio
import unittest
from unittest.mock import AsyncMock, patch, call

from client.alarm_client import list_alarms, play_alarm
from client.config import SERVER_URL


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class ListAlarmsClientTests(unittest.TestCase):
    @patch("client.alarm_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """Client must connect to the configured HTTP URL, not an in-process object."""
        ctx, mock_client = _make_client_mock()
        mock_contents = type("Obj", (), {"text": "Available alarms:\nalarm1.mp3"})()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": [mock_contents]})()
        MockClient.return_value = ctx

        asyncio.run(list_alarms())

        MockClient.assert_called_once_with(SERVER_URL)

    @patch("client.alarm_client.Client")
    def test_returns_alarm_list(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_contents = type("Obj", (), {"text": "Available alarms:\nalarm1.mp3"})()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": [mock_contents]})()
        MockClient.return_value = ctx

        result = asyncio.run(list_alarms())

        self.assertIn("alarm1.mp3", result)

    @patch("client.alarm_client.Client")
    def test_returns_no_alarms_found_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(list_alarms())

        self.assertEqual(result, "No alarms found.")


class PlayAlarmClientTests(unittest.TestCase):
    @patch("client.alarm_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """play_alarm must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "playing", "message": "ok"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(play_alarm(stop_time=30))

        MockClient.assert_called_once_with(SERVER_URL)

    @patch("client.alarm_client.Client")
    def test_play_alarm_passes_arguments(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "playing", "message": "ok"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(play_alarm(stop_time=120, random_alarm=True))

        mock_client.call_tool.assert_called_once_with(
            "play_alarm",
            arguments={"stop_time": 120, "random_alarm": True},
        )

    @patch("client.alarm_client.Client")
    def test_returns_structured_content(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        expected = {"status": "playing", "message": "Playing alarm for 10s."}
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": expected})()
        MockClient.return_value = ctx

        result = asyncio.run(play_alarm())

        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
