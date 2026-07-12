import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.notification_client import list_notifications, send_notification


def _mock_read_resource(result):
    mock_client = AsyncMock()
    mock_client.read_resource = AsyncMock(return_value=result)
    return mock_client


def _mock_call_tool(result):
    mock_client = AsyncMock()
    mock_client.call_tool = AsyncMock(return_value=result)
    return mock_client


class ListNotificationsClientTests(unittest.TestCase):
    @patch("client.notification_client.Client")
    def test_returns_notification_list(self, MockClient) -> None:
        mock_contents = type("Obj", (), {"text": "Available notification sounds:\nr2d2.mp3"})()
        mock_result = type("Obj", (), {"contents": [mock_contents]})()

        mock_client = _mock_read_resource(mock_result)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = asyncio.run(list_notifications())
        self.assertIn("r2d2.mp3", result)

    @patch("client.notification_client.Client")
    def test_returns_no_sounds_found_when_empty(self, MockClient) -> None:
        mock_result = type("Obj", (), {"contents": []})()

        mock_client = _mock_read_resource(mock_result)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = asyncio.run(list_notifications())
        self.assertEqual(result, "No notification sounds found.")


class SendNotificationClientTests(unittest.TestCase):
    @patch("client.notification_client.Client")
    def test_send_notification_default(self, MockClient) -> None:
        mock_result = type("Obj", (), {"structured_content": {"status": "success", "message": "Playing notification: r2d2.mp3"}})()

        mock_client = _mock_call_tool(mock_result)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = asyncio.run(send_notification())
        mock_client.call_tool.assert_called_once_with("notify_audio", {"random_sound": False})
        self.assertEqual(result["status"], "success")

    @patch("client.notification_client.Client")
    def test_send_notification_random(self, MockClient) -> None:
        mock_result = type("Obj", (), {"structured_content": {"status": "success", "message": "Playing notification: yamete-kudasai.mp3"}})()

        mock_client = _mock_call_tool(mock_result)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = asyncio.run(send_notification(random_sound=True))
        mock_client.call_tool.assert_called_once_with("notify_audio", {"random_sound": True})
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
