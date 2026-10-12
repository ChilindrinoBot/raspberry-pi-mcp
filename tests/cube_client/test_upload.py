import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from client.cube_client import (
    upload_cube_image,
    save_image_in_gallery,
)


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class UploadCubeImageClientTests(unittest.TestCase):
    GIF_DATA = b"GIF89a" + (240).to_bytes(2, "little") + (240).to_bytes(2, "little") + b"\x00\x00\x00"

    def _write_temp_gif(self) -> Path:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        path = Path(tmp_dir.name) / "test.gif"
        path.write_bytes(self.GIF_DATA)
        return path

    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """upload_cube_image must connect to the configured HTTP URL."""
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Image uploaded to Cube: test.gif"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(upload_cube_image(str(path)))

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_sends_base64_data_and_filename_without_path(self, MockClient) -> None:
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Image uploaded to Cube: test.gif"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(upload_cube_image(str(path)))

        args = mock_client.call_tool.call_args[0][1]
        self.assertEqual(args["filename"], "test.gif")
        self.assertNotIn(str(path), args["data"])
        # The sent payload must decode back to the original file bytes.
        self.assertEqual(base64.b64decode(args["data"]), self.GIF_DATA)

    @patch("client.cube_client.Client")
    def test_returns_success(self, MockClient) -> None:
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        expected = {"status": "success", "message": "Image uploaded to Cube: test.gif"}
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": expected})()
        MockClient.return_value = ctx

        result = asyncio.run(upload_cube_image(str(path)))

        self.assertEqual(result, expected)

    @patch("client.cube_client.Client")
    def test_returns_when_server_rejects(self, MockClient) -> None:
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj",
            (),
            {"structured_content": {"status": "error", "message": "Image must be 240x240 (got 100x100): test.gif."}},
        )()
        MockClient.return_value = ctx

        result = asyncio.run(upload_cube_image(str(path)))

        self.assertEqual(result["status"], "error")
        self.assertIn("Image must be 240x240", result["message"])

    def test_raises_when_file_missing(self) -> None:
        with self.assertRaises(OSError):
            asyncio.run(upload_cube_image("/nonexistent/path/test.gif"))


class SaveImageInGalleryClientTests(unittest.TestCase):
    PNG_DATA = b"\x89PNG\r\n\x1a\n" + b"fakepngdata"

    def _write_temp_png(self) -> Path:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        path = Path(tmp_dir.name) / "photo.png"
        path.write_bytes(self.PNG_DATA)
        return path

    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """save_image_in_gallery must connect to the configured HTTP URL."""
        path = self._write_temp_png()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "saved"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(save_image_in_gallery(str(path), "vacaciones"))

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_sends_base64_data_and_requested_name(self, MockClient) -> None:
        path = self._write_temp_png()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "saved"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(save_image_in_gallery(str(path), "vacaciones"))

        name, args = mock_client.call_tool.call_args[0]
        self.assertEqual(name, "save_image_in_gallery")
        self.assertEqual(args["name"], "vacaciones")
        self.assertNotIn(str(path), args["data"])
        # The sent payload must decode back to the original file bytes.
        self.assertEqual(base64.b64decode(args["data"]), self.PNG_DATA)

    @patch("client.cube_client.Client")
    def test_returns_success(self, MockClient) -> None:
        path = self._write_temp_png()
        ctx, mock_client = _make_client_mock()
        expected = {
            "status": "success",
            "message": "Image saved to media/images: vacaciones.jpg (240x240 JPEG).",
        }
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": expected})()
        MockClient.return_value = ctx

        result = asyncio.run(save_image_in_gallery(str(path), "vacaciones"))

        self.assertEqual(result, expected)

    @patch("client.cube_client.Client")
    def test_returns_when_server_rejects(self, MockClient) -> None:
        path = self._write_temp_png()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj",
            (),
            {
                "structured_content": {
                    "status": "error",
                    "message": "Image name is too long: photo.jpg (26 characters). Max is 25 characters.",
                }
            },
        )()
        MockClient.return_value = ctx

        result = asyncio.run(save_image_in_gallery(str(path), "photo"))

        self.assertEqual(result["status"], "error")
        self.assertIn("Image name is too long", result["message"])

    def test_raises_when_file_missing(self) -> None:
        with self.assertRaises(OSError):
            asyncio.run(save_image_in_gallery("/nonexistent/path/photo.png", "photo"))


if __name__ == "__main__":
    unittest.main()
