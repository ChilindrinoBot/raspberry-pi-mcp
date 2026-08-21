import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.cube_client import (
    list_cube_gifs,
    get_cube_free_space,
    set_cube_gif,
    set_cube_brightness,
    get_cube_brightness,
)


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class ListCubeGifsClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """list_cube_gifs must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube gifs:\ngif1.gif"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(list_cube_gifs())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_reads_cube_gifs_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube gifs:\ngif1.gif"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(list_cube_gifs())

        mock_client.read_resource.assert_called_once_with("cube://gifs")

    @patch("client.cube_client.Client")
    def test_returns_gif_list(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube gifs:\ngif1.gif"})()]}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(list_cube_gifs())

        self.assertIn("gif1.gif", result)

    @patch("client.cube_client.Client")
    def test_returns_no_gifs_found_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(list_cube_gifs())

        self.assertEqual(result, "No gifs found on the Cube.")


class GetCubeFreeSpaceClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """get_cube_free_space must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Free space on Cube: 903 KB"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(get_cube_free_space())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_reads_free_space_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Free space on Cube: 903 KB"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(get_cube_free_space())

        mock_client.read_resource.assert_called_once_with("cube://free-space")

    @patch("client.cube_client.Client")
    def test_returns_free_space(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Free space on Cube: 903 KB (total: 3047 KB)"})()]}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(get_cube_free_space())

        self.assertIn("Free space on Cube:", result)
        self.assertIn("903 KB", result)

    @patch("client.cube_client.Client")
    def test_returns_no_space_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(get_cube_free_space())

        self.assertEqual(result, "No space information available for the Cube.")


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


if __name__ == "__main__":
    unittest.main()
