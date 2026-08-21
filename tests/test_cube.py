import unittest
from unittest.mock import Mock, patch

from server.display.cube import (
    _fetch_cube_gifs,
    list_cube_gifs,
    _fetch_cube_space,
    get_cube_free_space,
    _set_cube_gif,
    set_cube_gif,
    CUBE_BASE_URL,
)

SAMPLE_HTML = (
    "<html><body>"
    "<a href='/gif1.gif'>Gif One</a>"
    "<a href='/image1.jpg'>Image One</a>"
    "<a href='gif2.gif'>Gif Two</a>"
    "</body></html>"
)


class FetchCubeGifsTests(unittest.TestCase):
    def test_returns_gif_paths_stripped(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = SAMPLE_HTML.encode()

            gifs = _fetch_cube_gifs()

            self.assertIn("gif1.gif", gifs)
            self.assertIn("gif2.gif", gifs)
            self.assertNotIn("/gif1.gif", gifs)

    def test_strips_leading_slashes_from_relative_paths(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"<a href='sub/gif1.gif'>gif1</a>"

            gifs = _fetch_cube_gifs()

            self.assertEqual(gifs, ["sub/gif1.gif"])

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_gifs()

            self.assertIn("connection refused", str(ctx.exception))


class ListCubeGifsTests(unittest.TestCase):
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif", "image1.jpg"])
    def test_returns_gif_list(self, mock_fetch: Mock) -> None:
        result = list_cube_gifs()

        self.assertIn("Available Cube gifs:", result)
        self.assertIn("gif1.gif", result)
        self.assertIn("image1.jpg", result)
        mock_fetch.assert_called_once()

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = list_cube_gifs()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube._fetch_cube_gifs", return_value=[])
    def test_returns_no_gifs_found_when_empty(self, mock_fetch: Mock) -> None:
        result = list_cube_gifs()

        self.assertEqual(result, "No gifs found on the Cube.")
        mock_fetch.assert_called_once()

    @patch("server.display.cube._fetch_cube_gifs", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = list_cube_gifs()

        self.assertIn("Failed to fetch gifs from Cube", result)
        self.assertIn("timeout", result)
        mock_fetch.assert_called_once()


class FetchCubeSpaceTests(unittest.TestCase):
    def test_returns_free_and_total_bytes(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b'{"total":3121152,"free":925196}'

            free, total = _fetch_cube_space()

            self.assertEqual(free, 925196)
            self.assertEqual(total, 3121152)

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_space()

            self.assertIn("connection refused", str(ctx.exception))


class GetCubeFreeSpaceTests(unittest.TestCase):
    @patch("server.display.cube._fetch_cube_space", return_value=(925196, 3121152))
    def test_returns_free_space_in_kb(self, mock_fetch: Mock) -> None:
        result = get_cube_free_space()

        self.assertIn("Free space on Cube:", result)
        self.assertIn("903 KB", result)
        self.assertIn("total: 3048 KB", result)
        mock_fetch.assert_called_once()

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = get_cube_free_space()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube._fetch_cube_space", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = get_cube_free_space()

        self.assertIn("Failed to fetch free space from Cube", result)
        self.assertIn("timeout", result)
        mock_fetch.assert_called_once()


class SetCubeGifHelperTests(unittest.TestCase):
    def test_set_request_targets_gif_directory(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"OK"

            _set_cube_gif("gif1.gif")

            called_url = mock_urlopen.call_args[0][0]
            self.assertIn("/set?img=", called_url)
            self.assertIn("/image/gif1.gif", called_url)


class SetCubeGifTests(unittest.TestCase):
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif", "image1.jpg"])
    def test_success_when_gif_exists(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube gif set to: gif1.gif", result["message"])
        self.assertIn("Device response: OK", result["message"])
        mock_gifs.assert_called_once()
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif", "image1.jpg"])
    def test_strips_leading_slash_before_validating(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("/gif1.gif")

        self.assertEqual(result["status"], "success")
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube._set_cube_gif")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif", "image1.jpg"])
    def test_rejects_gif_not_in_list(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("unknown.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Gif not found on Cube", result["message"])
        self.assertIn("unknown.gif", result["message"])
        mock_gifs.assert_called_once()
        mock_set.assert_not_called()

    @patch("server.display.cube._set_cube_gif", return_value="FAIL")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_rejects_cube_failure_response(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to set gif", result["message"])
        self.assertIn("FAIL", result["message"])
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube._set_cube_gif", return_value="")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_success_when_cube_responds_empty(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Cube gif set to: gif1.gif")

    @patch("server.display.cube._set_cube_gif", side_effect=RuntimeError("connection refused"))
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_returns_error_when_set_fails(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to set gif on Cube", result["message"])

    @patch("server.display.cube._fetch_cube_gifs", side_effect=RuntimeError("timeout"))
    def test_returns_error_when_verification_fails(self, mock_gifs: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to verify gif availability", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])

    def test_returns_error_when_gif_empty(self) -> None:
        with patch("server.display.cube._fetch_cube_gifs") as mock_gifs:
            result = set_cube_gif("  ")

        self.assertEqual(result["status"], "error")
        self.assertIn("Gif name is required", result["message"])
        mock_gifs.assert_not_called()


if __name__ == "__main__":
    unittest.main()
