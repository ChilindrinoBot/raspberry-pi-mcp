import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.notification_client import list_notifications, send_notification
from client.config import SERVER_URL


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class ListNotificationsClientTests(unittest.TestCase):
    @patch("client.notification_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """Client must connect to the configured HTTP URL, not an in-process object."""
        ctx, mock_client = _make_client_mock()
        mock_contents = type("Obj", (), {"text": "Available notification sounds:\nnotification1.mp3"})()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": [mock_contents]})()
        MockClient.return_value = ctx

        asyncio.run(list_notifications())

        MockClient.assert_called_once_with(SERVER_URL)

    @patch("client.notification_client.Client")
    def test_returns_notification_list(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_contents = type("Obj", (), {"text": "Available notification sounds:\nnotification1.mp3"})()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": [mock_contents]})()
        MockClient.return_value = ctx

        result = asyncio.run(list_notifications())

        self.assertIn("notification1.mp3", result)

    @patch("client.notification_client.Client")
    def test_returns_no_sounds_found_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(list_notifications())

        self.assertEqual(result, "No notification sounds found.")


class SendNotificationClientTests(unittest.TestCase):
    @patch("client.notification_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """send_notification must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "ok"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(send_notification())

        MockClient.assert_called_once_with(SERVER_URL)

    @patch("client.notification_client.Client")
    def test_send_notification_default(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Playing notification: notification1.mp3"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(send_notification())

        mock_client.call_tool.assert_called_once_with("notify_audio", {"random_sound": False})
        self.assertEqual(result["status"], "success")

    @patch("client.notification_client.Client")
    def test_send_notification_random(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Playing notification: notification2.mp3"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(send_notification(random_sound=True))

        mock_client.call_tool.assert_called_once_with("notify_audio", {"random_sound": True})
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
