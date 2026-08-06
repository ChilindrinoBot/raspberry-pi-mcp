import asyncio
import base64
import unittest
from unittest.mock import AsyncMock, Mock, patch

from client.image_client import take_photo, save_photo
from client.config import SERVER_URL


def _make_client_mock():
    """Return a configured async context-manager mock for mcp.Client."""
    mock_client = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


def _make_photo_response():
    """Return a mock CallToolResult with structured content containing an encoded photo."""
    encoded = base64.b64encode(b"fake jpeg bytes").decode("ascii")
    return type(
        "Obj", (), {"structured_content": {
            "status": "success",
            "format": "jpeg",
            "encoding": "base64",
            "data": encoded,
            "message": "Photo captured successfully.",
        }}
    )()


class TakePhotoClientTests(unittest.TestCase):
    @patch("client.image_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """take_photo must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_photo_response()
        MockClient.return_value = ctx

        asyncio.run(take_photo())

        MockClient.assert_called_once_with(SERVER_URL)

    @patch("client.image_client.Client")
    def test_calls_take_photo_tool(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_photo_response()
        MockClient.return_value = ctx

        asyncio.run(take_photo())

        mock_client.call_tool.assert_called_once_with("take_photo", {})

    @patch("client.image_client.Client")
    def test_returns_decoded_photo_bytes(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_photo_response()
        MockClient.return_value = ctx

        result = asyncio.run(take_photo())

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["format"], "jpeg")
        self.assertEqual(result["data"], b"fake jpeg bytes")

    @patch("client.image_client.Client")
    def test_returns_error_when_server_fails(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "error", "message": "Camera not found"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(take_photo())

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Camera not found")

    @patch("client.image_client.Client")
    def test_returns_error_on_invalid_base64(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {
                "status": "success",
                "format": "jpeg",
                "encoding": "base64",
                "data": "!!!not-base64!!!",
                "message": "Photo captured successfully.",
            }}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(take_photo())

        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid base64", result["message"])


class SavePhotoClientTests(unittest.TestCase):
    @patch("client.image_client.open", new_callable=Mock)
    @patch("client.image_client.Client")
    def test_saves_photo_to_file(self, MockClient, mock_open) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = _make_photo_response()
        MockClient.return_value = ctx

        write_mock = Mock()
        mock_open.return_value.__enter__ = Mock(return_value=write_mock)
        mock_open.return_value.__exit__ = Mock(return_value=None)

        result = asyncio.run(save_photo("/tmp/photo.jpg"))

        mock_open.assert_called_once_with("/tmp/photo.jpg", "wb")
        write_mock.write.assert_called_once_with(b"fake jpeg bytes")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["path"], "/tmp/photo.jpg")

    @patch("client.image_client.Client")
    def test_does_not_write_file_on_error(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "error", "message": "Camera not found"}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(save_photo("/tmp/photo.jpg"))

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Camera not found")


if __name__ == "__main__":
    unittest.main()