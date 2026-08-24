import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from client.cube_client import (
    get_cube_current_gif,
    list_cube_contents,
    delete_cube_file,
    get_cube_free_space,
    set_cube_gif,
    set_cube_brightness,
    get_cube_brightness,
    turn_cube_display_off,
    turn_cube_display_on,
    upload_cube_image,
    save_image_in_gallery,
    show_gallery_image,
    show_gallery_gif,
    show_temporary_gif,
    list_gallery_images,
    list_gallery_gifs,
)


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


class ListCubeContentsClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """list_cube_contents must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube files:\ngif1.gif (12 KB)"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(list_cube_contents())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_reads_cube_contents_resource(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube files:\ngif1.gif (12 KB)"})()]}
        )()
        MockClient.return_value = ctx

        asyncio.run(list_cube_contents())

        mock_client.read_resource.assert_called_once_with("cube://contents")

    @patch("client.cube_client.Client")
    def test_returns_file_list(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type(
            "Obj", (), {"contents": [type("Obj", (), {"text": "Available Cube files:\ngif1.gif (12 KB)"})()]}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(list_cube_contents())

        self.assertIn("gif1.gif (12 KB)", result)

    @patch("client.cube_client.Client")
    def test_returns_no_files_found_when_empty(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.read_resource.return_value = type("Obj", (), {"contents": []})()
        MockClient.return_value = ctx

        result = asyncio.run(list_cube_contents())

        self.assertEqual(result, "No files found on the Cube.")


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


class DeleteCubeFileClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """delete_cube_file must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Deleted tmp.gif from Cube."}}
        )()
        MockClient.return_value = ctx

        asyncio.run(delete_cube_file("tmp.gif"))

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_calls_delete_cube_file_tool_with_filename(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Deleted tmp.gif from Cube."}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(delete_cube_file("tmp.gif"))

        mock_client.call_tool.assert_called_once_with(
            "delete_cube_file", {"filename": "tmp.gif"}
        )
        self.assertEqual(result["status"], "success")
        self.assertIn("Deleted tmp.gif", result["message"])


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


class ShowTemporaryGifClientTests(unittest.TestCase):
    GIF_DATA = b"GIF89a" + (240).to_bytes(2, "little") + (240).to_bytes(2, "little") + b"\x00\x00\x00"

    def _write_temp_gif(self) -> Path:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        path = Path(tmp_dir.name) / "test.gif"
        path.write_bytes(self.GIF_DATA)
        return path

    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """show_temporary_gif must connect to the configured HTTP URL."""
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "shown"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(show_temporary_gif(str(path)))

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_sends_data_filename_and_seconds(self, MockClient) -> None:
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "shown"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(show_temporary_gif(str(path), seconds=10))

        name, args = mock_client.call_tool.call_args[0]
        self.assertEqual(name, "show_temporary_gif")
        self.assertEqual(args["filename"], "test.gif")
        self.assertEqual(args["seconds"], 10)
        self.assertEqual(base64.b64decode(args["data"]), self.GIF_DATA)

    @patch("client.cube_client.Client")
    def test_defaults_to_5_seconds(self, MockClient) -> None:
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "shown"}}
        )()
        MockClient.return_value = ctx

        asyncio.run(show_temporary_gif(str(path)))

        mock_client.call_tool.assert_called_once_with(
            "show_temporary_gif",
            {"data": base64.b64encode(self.GIF_DATA).decode(), "filename": "test.gif", "seconds": 5},
        )

    @patch("client.cube_client.Client")
    def test_returns_success(self, MockClient) -> None:
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        expected = {
            "status": "success",
            "message": "Temporary gif tmp.gif displayed for 5 seconds. Restored to: test.gif",
        }
        mock_client.call_tool.return_value = type("Obj", (), {"structured_content": expected})()
        MockClient.return_value = ctx

        result = asyncio.run(show_temporary_gif(str(path)))

        self.assertEqual(result, expected)

    @patch("client.cube_client.Client")
    def test_returns_when_server_rejects(self, MockClient) -> None:
        path = self._write_temp_gif()
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj",
            (),
            {"structured_content": {"status": "error", "message": "Unsupported file type: .png. Allowed: .gif, .jpg, .jpeg."}},
        )()
        MockClient.return_value = ctx

        result = asyncio.run(show_temporary_gif(str(path)))

        self.assertEqual(result["status"], "error")
        self.assertIn("Unsupported file type", result["message"])

    def test_raises_when_file_missing(self) -> None:
        with self.assertRaises(OSError):
            asyncio.run(show_temporary_gif("/nonexistent/path/test.gif"))


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
