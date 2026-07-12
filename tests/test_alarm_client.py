import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.alarm_client import list_alarms


def _mock_read_resource(result):
    mock_client = AsyncMock()
    mock_client.read_resource = AsyncMock(return_value=result)
    return mock_client


class ListAlarmsClientTests(unittest.TestCase):
    @patch("client.alarm_client.Client")
    def test_returns_alarm_list(self, MockClient) -> None:
        mock_contents = type("Obj", (), {"text": "Available alarms:\nalarm1.mp3"})()
        mock_result = type("Obj", (), {"contents": [mock_contents]})()

        mock_client = _mock_read_resource(mock_result)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = asyncio.run(list_alarms())
        self.assertIn("alarm1.mp3", result)

    @patch("client.alarm_client.Client")
    def test_returns_no_alarms_found_when_empty(self, MockClient) -> None:
        mock_result = type("Obj", (), {"contents": []})()

        mock_client = _mock_read_resource(mock_result)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = asyncio.run(list_alarms())
        self.assertEqual(result, "No alarms found.")


if __name__ == "__main__":
    unittest.main()
