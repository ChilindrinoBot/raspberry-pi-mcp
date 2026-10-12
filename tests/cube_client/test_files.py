import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from client.cube_client import (
    list_cube_contents,
    delete_cube_file,
    clear_cube_contents,
    get_cube_free_space,
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


class ClearCubeContentsClientTests(unittest.TestCase):
    @patch("client.cube_client.Client")
    def test_connects_to_http_server(self, MockClient) -> None:
        """clear_cube_contents must connect to the configured HTTP URL."""
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cleared 2 files from Cube."}}
        )()
        MockClient.return_value = ctx

        asyncio.run(clear_cube_contents())

        MockClient.assert_called_once()

    @patch("client.cube_client.Client")
    def test_calls_clear_cube_contents_tool(self, MockClient) -> None:
        ctx, mock_client = _make_client_mock()
        mock_client.call_tool.return_value = type(
            "Obj", (), {"structured_content": {"status": "success", "message": "Cleared 2 files from Cube."}}
        )()
        MockClient.return_value = ctx

        result = asyncio.run(clear_cube_contents())

        mock_client.call_tool.assert_called_once_with("clear_cube_contents", {})
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
