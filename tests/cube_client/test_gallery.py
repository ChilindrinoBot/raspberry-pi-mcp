import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.cube_client import (
    list_gallery_images,
    list_gallery_gifs,
    show_gallery_image,
    show_gallery_gif,
)


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class ListGalleryClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_reads_gallery_images_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available gallery images:\nfoto.jpg"})()]}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(list_gallery_images())

        mock_client.read_resource.assert_called_once_with("gallery://images")
        self.assertIn("foto.jpg", result)

    @patch("client.cube_client.Client")
    def test_returns_fallback_when_images_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(list_gallery_images())

        self.assertEqual(result, "No gallery image information available.")

    @patch("client.cube_client.Client")
    def test_reads_gallery_gifs_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available gallery gifs:\ngif1.gif"})()]}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(list_gallery_gifs())

        mock_client.read_resource.assert_called_once_with("gallery://gifs")
        self.assertIn("gif1.gif", result)

    @patch("client.cube_client.Client")
    def test_returns_fallback_when_gifs_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(list_gallery_gifs())

        self.assertEqual(result, "No gallery gif information available.")


class ShowGalleryImageClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_sends_gallery_image_filename(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cube image set to: test.jpg"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(show_gallery_image("test"))

        mock_client.call_tool.assert_called_once_with("show_gallery_image", {"filename": "test"})
        self.assertEqual(result["status"], "success")

    @patch("client.cube_client.Client")
    def test_returns_server_error(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj",
            (),
            {"structured_content": {"status": "error", "message": "Image not found in media/images: nope. Available: none."}},
        )()
        MockClient.return_value = ctx

        result = asyncio.run(show_gallery_image("nope"))

        self.assertEqual(result["status"], "error")
        self.assertIn("Image not found", result["message"])


class ShowGalleryGifClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_sends_gallery_gif_filename(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj",
            (),
            {"structured_content": {"status": "success", "message": "Cube gif set to: tmp.gif (from anim.gif)"}},
        )()
        MockClient.return_value = ctx

        result = asyncio.run(show_gallery_gif("anim"))

        mock_client.call_tool.assert_called_once_with("show_gallery_gif", {"filename": "anim"})
        self.assertEqual(result["status"], "success")

    @patch("client.cube_client.Client")
    def test_returns_server_error(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj",
            (),
            {"structured_content": {"status": "error", "message": "Gif not found in media/gifs: nope. Available: none."}},
        )()
        MockClient.return_value = ctx

        result = asyncio.run(show_gallery_gif("nope"))

        self.assertEqual(result["status"], "error")
        self.assertIn("Gif not found", result["message"])


if __name__ == "__main__":
    unittest.main()
