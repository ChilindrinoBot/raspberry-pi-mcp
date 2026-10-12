import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from client.cube_client import (
    show_temporary_gif,
    show_temporary_gif_with_audio,
)


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


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


class ShowTemporaryGifWithAudioClientTests(unittest.TestCase):
    GIF_DATA = b"GIF89a" + (240).to_bytes(2, "little") + (240).to_bytes(2, "little") + b"\x00\x00\x00"
    AUDIO_DATA = b"RIFF....WAVE"

    def _write_temp_files(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        gif = Path(tmp_dir.name) / "test.gif"
        gif.write_bytes(self.GIF_DATA)
        audio = Path(tmp_dir.name) / "test.mp3"
        audio.write_bytes(self.AUDIO_DATA)
        return gif, audio

    def _ok(self, mock_client):
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "shown"}}
        )()

    @patch("client.cube_client.Client")
    def test_sends_image_and_audio(self, MockClient) -> None:
        gif, audio = self._write_temp_files()
        ctx, mock_client = _make_client_mock()
        self._ok(mock_client)
        MockClient.return_value = ctx

        asyncio.run(show_temporary_gif_with_audio(str(gif), str(audio), seconds=10))

        name, args = mock_client.call_tool.call_args[0]
        self.assertEqual(name, "show_temporary_gif_with_audio")
        self.assertEqual(args["filename"], "test.gif")
        self.assertEqual(args["audio_name"], "test.mp3")
        self.assertEqual(args["seconds"], 10)
        self.assertNotIn("restore_after_audio", args)
        self.assertEqual(base64.b64decode(args["data"]), self.GIF_DATA)
        self.assertEqual(base64.b64decode(args["audio_data"]), self.AUDIO_DATA)

    @patch("client.cube_client.Client")
    def test_sends_no_seconds_by_default(self, MockClient) -> None:
        gif, audio = self._write_temp_files()
        ctx, mock_client = _make_client_mock()
        self._ok(mock_client)
        MockClient.return_value = ctx

        asyncio.run(show_temporary_gif_with_audio(str(gif), str(audio)))

        _name, args = mock_client.call_tool.call_args[0]
        self.assertIsNone(args["seconds"])
        self.assertNotIn("restore_after_audio", args)

    @patch("client.cube_client.Client")
    def test_raises_when_image_missing(self, MockClient) -> None:
        _gif, audio = self._write_temp_files()
        ctx, mock_client = _make_client_mock()
        MockClient.return_value = ctx

        with self.assertRaises(FileNotFoundError):
            asyncio.run(show_temporary_gif_with_audio("/nonexistent/test.gif", str(audio)))
        mock_client.call_tool.assert_not_called()


if __name__ == "__main__":
    unittest.main()
