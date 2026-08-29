import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.cube_client import get_special_status, start_special_routine, stop_special_routine


def _make_client_mock():
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class GetSpecialStatusClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_reads_special_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": [type("Obj", (), {"text": "Special routine: running"})()]})()
        MockClient.return_value = ctx
        result = asyncio.run(get_special_status())
        mock_client.read_resource.assert_called_once_with("cube://special")
        self.assertIn("running", result)

    @patch("client.cube_client.Client")
    def test_fallback_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx
        result = asyncio.run(get_special_status())
        self.assertEqual(result, "No special routine information available for the Cube.")


class StartSpecialRoutineClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_calls_tool_with_60s_default(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": {"status": "success", "message": "started"}})()
        MockClient.return_value = ctx
        asyncio.run(start_special_routine("pato-gira"))
        mock_client.call_tool.assert_called_once_with("start_special_routine", {"routine": "pato-gira", "seconds": 60})

    @patch("client.cube_client.Client")
    def test_calls_with_custom_seconds(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": {"status": "success", "message": "started"}})()
        MockClient.return_value = ctx
        asyncio.run(start_special_routine("pato-gira", seconds=10))
        mock_client.call_tool.assert_called_once_with("start_special_routine", {"routine": "pato-gira", "seconds": 10})


class StopSpecialRoutineClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_calls_stop_tool(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": {"status": "success", "message": "stopped"}})()
        MockClient.return_value = ctx
        result = asyncio.run(stop_special_routine())
        mock_client.call_tool.assert_called_once_with("stop_special_routine", {})
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
