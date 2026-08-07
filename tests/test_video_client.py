import asyncio
import base64
import unittest
from unittest.mock import AsyncMock, Mock, patch

from client.video_client import record_video, save_video
from client.config import SERVER_URL


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


def _make_video_response():
    """Return a mock CallToolResult with structured content containing an encoded video."""
    encoded = base64.b64encode(b"fake mp4 bytes").decode("ascii")
    return type(
        "Obj", (), {"structured_content": {
            "status": "success",
            "format": "mp4",
            "encoding": "base64",
            "data": encoded,
            "message": "Video recorded successfully (5s @10fps).",
        }}
    )()


class RecordVideoClientTests(unittest.TestCase):
    @patch("client.video_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """record_video must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_video_response()
        MockClient.return_value = ctx

        asyncio.run(record_video())

        MockClient.assert_called_once_with(SERVER_URL)

    @patch("client.video_client.Client")
    def test_calls_record_video_tool_with_params(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_video_response()
        MockClient.return_value = ctx

        asyncio.run(record_video(duration_seconds=8, fps=1))

        mock_client.call_tool.assert_called_once_with(
            "record_video", {"duration_seconds": 8, "fps": 1}
        )

    @patch("client.video_client.Client")
    def test_uses_default_params_when_not_specified(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_video_response()
        MockClient.return_value = ctx

        asyncio.run(record_video())

        mock_client.call_tool.assert_called_once_with(
            "record_video", {"duration_seconds": 5, "fps": 10}
        )

    @patch("client.video_client.Client")
    def test_returns_decoded_video_bytes(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_video_response()
        MockClient.return_value = ctx

        result = asyncio.run(record_video())

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["format"], "mp4")
        self.assertEqual(result["data"], b"fake mp4 bytes")

    @patch("client.video_client.Client")
    def test_returns_error_when_server_fails(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "error", "message": "Camera not found"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(record_video())

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Camera not found")

    @patch("client.video_client.Client")
    def test_returns_error_on_invalid_base64(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {
                "status": "success",
                "format": "mp4",
                "encoding": "base64",
                "data": "!!!not-base64!!!",
                "message": "Video recorded successfully.",
            }}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(record_video())

        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid base64", result["message"])


class RecordVideoDecodeTests(unittest.TestCase):
    def test_rejects_payload_over_limit(self) -> None:
        with patch("client.video_client.MAX_VIDEO_BYTES", 10):
            from client.video_client import _decode_video_payload, MAX_VIDEO_BYTES

            self.assertEqual(MAX_VIDEO_BYTES, 10)
            encoded = base64.b64encode(b"x" * 100).decode("ascii")
            with self.assertRaises(ValueError) as ctx:
                _decode_video_payload(encoded, max_bytes=10)

            self.assertIn("exceeds the", str(ctx.exception))


class SaveVideoClientTests(unittest.TestCase):
    @patch("client.video_client.open", new_callable=Mock)
    @patch("client.video_client.Client")
    def test_saves_video_to_file(self, MockClient, mock_open) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_video_response()
        MockClient.return_value = ctx

        write_mock = Mock()
        mock_open.return_value.__enter__ = Mock(return_value=write_mock)
        mock_open.return_value.__exit__ = Mock(return_value=None)

        result = asyncio.run(save_video("/tmp/video.mp4"))

        mock_open.assert_called_once_with("/tmp/video.mp4", "wb")
        write_mock.write.assert_called_once_with(b"fake mp4 bytes")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["path"], "/tmp/video.mp4")

    @patch("client.video_client.open", new_callable=Mock)
    @patch("client.video_client.Client")
    def test_save_video_passes_params(self, MockClient, mock_open) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_video_response()
        MockClient.return_value = ctx

        write_mock = Mock()
        mock_open.return_value.__enter__ = Mock(return_value=write_mock)
        mock_open.return_value.__exit__ = Mock(return_value=None)

        asyncio.run(save_video("/tmp/video.mp4", duration_seconds=3, fps=1))

        mock_client.call_tool.assert_called_once_with(
            "record_video", {"duration_seconds": 3, "fps": 1}
        )

    @patch("client.video_client.Client")
    def test_does_not_write_file_on_error(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "error", "message": "Camera not found"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(save_video("/tmp/video.mp4"))

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Camera not found")


if __name__ == "__main__":
    unittest.main()