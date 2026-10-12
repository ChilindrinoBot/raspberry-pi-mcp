import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.cube_client import (
    get_cube_current_gif,
    set_cube_gif,
    set_cube_brightness,
    get_cube_brightness,
    turn_cube_display_off,
    turn_cube_display_on,
)


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class SetCubeGifClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """set_cube_gif must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube gif set to: gif1.gif"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(set_cube_gif("gif1.gif"))

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_calls_set_cube_gif_tool(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube gif set to: gif1.gif"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(set_cube_gif("gif1.gif"))

        mock_client.call_tool.assert_called_once_with("set_cube_gif", {"gif": "gif1.gif"})

    @patch("client.cube_client.Client")
    def test_returns_success(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube gif set to: gif1.gif"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(set_cube_gif("gif1.gif"))

        self.assertEqual(result["status"], "success")
        self.assertIn("gif1.gif", result["message"])

    @patch("client.cube_client.Client")
    def test_returns_when_server_rejects(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "error", "message": "Gif not found on Cube: unknown.gif"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(set_cube_gif("unknown.gif"))

        self.assertEqual(result["status"], "error")
        self.assertIn("Gif not found on Cube", result["message"])


class GetCubeBrightnessClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """get_cube_brightness must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Current Cube brightness: 10"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(get_cube_brightness())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_reads_brightness_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Current Cube brightness: 10"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(get_cube_brightness())

        mock_client.read_resource.assert_called_once_with("cube://brightness")

    @patch("client.cube_client.Client")
    def test_returns_brightness(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Current Cube brightness: 10"})()]}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(get_cube_brightness())

        self.assertIn("Current Cube brightness:", result)
        self.assertIn("10", result)

    @patch("client.cube_client.Client")
    def test_returns_no_brightness_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(get_cube_brightness())

        self.assertEqual(result, "No brightness information available for the Cube.")


class GetCubeCurrentGifClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """get_cube_current_gif must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Current Cube gif: test.gif"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(get_cube_current_gif())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_reads_current_gif_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Current Cube gif: test.gif"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(get_cube_current_gif())

        mock_client.read_resource.assert_called_once_with("cube://current-gif")

    @patch("client.cube_client.Client")
    def test_returns_current_gif(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Current Cube gif: test.gif"})()]}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(get_cube_current_gif())

        self.assertIn("Current Cube gif:", result)
        self.assertIn("test.gif", result)

    @patch("client.cube_client.Client")
    def test_returns_no_gif_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(get_cube_current_gif())

        self.assertEqual(result, "No current gif information available for the Cube.")


class SetCubeBrightnessClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """set_cube_brightness must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube brightness set to: 10"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(set_cube_brightness(10))

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_calls_set_cube_brightness_tool_with_level(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube brightness set to: 75"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(set_cube_brightness(75))

        mock_client.call_tool.assert_called_once_with("set_cube_brightness", {"level": 75})

    @patch("client.cube_client.Client")
    def test_defaults_to_level_50(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube brightness set to: 50"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(set_cube_brightness())

        mock_client.call_tool.assert_called_once_with("set_cube_brightness", {"level": 50})

    @patch("client.cube_client.Client")
    def test_returns_success(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube brightness set to: 10"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(set_cube_brightness(10))

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 10", result["message"])

    @patch("client.cube_client.Client")
    def test_returns_when_server_rejects(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "error", "message": "Failed to set brightness on Cube"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(set_cube_brightness(10))

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to set brightness on Cube", result["message"])


class TurnCubeDisplayOffClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """turn_cube_display_off must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube display turned off."}}
        )()
        MockClient.return_value = ctx

        asyncio.run(turn_cube_display_off())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_calls_turn_cube_display_off_tool(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube display turned off."}}
        )()
        MockClient.return_value = ctx

        asyncio.run(turn_cube_display_off())

        mock_client.call_tool.assert_called_once_with("turn_cube_display_off", {})

    @patch("client.cube_client.Client")
    def test_returns_success(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        expected = {"status": "success", "message": "Cube display turned off. Brightness will be restored to 30."}
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": expected})()
        MockClient.return_value = ctx

        result = asyncio.run(turn_cube_display_off())

        self.assertEqual(result, expected)

    @patch("client.cube_client.Client")
    def test_returns_when_server_rejects(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "error", "message": "Failed to turn off Cube display"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(turn_cube_display_off())

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to turn off Cube display", result["message"])


class TurnCubeDisplayOnClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """turn_cube_display_on must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube display turned on at brightness 50."}}
        )()
        MockClient.return_value = ctx

        asyncio.run(turn_cube_display_on())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_calls_turn_cube_display_on_tool(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube display turned on at brightness 50."}}
        )()
        MockClient.return_value = ctx

        asyncio.run(turn_cube_display_on())

        mock_client.call_tool.assert_called_once_with("turn_cube_display_on", {})

    @patch("client.cube_client.Client")
    def test_returns_success(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        expected = {"status": "success", "message": "Cube display turned on at brightness 75."}
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": expected})()
        MockClient.return_value = ctx

        result = asyncio.run(turn_cube_display_on())

        self.assertEqual(result, expected)

    @patch("client.cube_client.Client")
    def test_returns_when_server_rejects(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "error", "message": "Failed to turn on Cube display"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(turn_cube_display_on())

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to turn on Cube display", result["message"])


if __name__ == "__main__":
    unittest.main()
