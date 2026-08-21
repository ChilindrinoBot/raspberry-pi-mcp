import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.cube_client import list_cube_images


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class ListCubeImagesClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """list_cube_images must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube images:\ngif1.gif"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(list_cube_images())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_reads_cube_images_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube images:\ngif1.gif"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(list_cube_images())

        mock_client.read_resource.assert_called_once_with("cube://images")

    @patch("client.cube_client.Client")
    def test_returns_image_list(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube images:\ngif1.gif"})()]}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(list_cube_images())

        self.assertIn("gif1.gif", result)

    @patch("client.cube_client.Client")
    def test_returns_no_images_found_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(list_cube_images())

        self.assertEqual(result, "No images found on the Cube.")


if __name__ == "__main__":
    unittest.main()
