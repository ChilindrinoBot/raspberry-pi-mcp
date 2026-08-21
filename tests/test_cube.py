import unittest
from unittest.mock import Mock, patch

from server.display.cube import (
    _fetch_cube_images,
    list_cube_images,
    _fetch_cube_space,
    get_cube_free_space,
    _set_cube_image,
    set_cube_image,
    CUBE_BASE_URL,
)

SAMPLE_HTML = (
    "<html><body>"
    "<a href='/gif1.gif'>Gif One</a>"
    "<a href='/image1.jpg'>Image One</a>"
    "<a href='gif2.gif'>Gif Two</a>"
    "</body></html>"
)


class FetchCubeImagesTests(unittest.TestCase):
    def test_returns_image_paths_stripped(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = SAMPLE_HTML.encode()

            images = _fetch_cube_images()

            self.assertIn("gif1.gif", images)
            self.assertIn("image1.jpg", images)
            self.assertIn("gif2.gif", images)
            self.assertNotIn("/gif1.gif", images)

    def test_strips_leading_slashes_from_relative_paths(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"<a href='sub/img.jpg'>img</a>"

            images = _fetch_cube_images()

            self.assertEqual(images, ["sub/img.jpg"])

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_images()

            self.assertIn("connection refused", str(ctx.exception))


class ListCubeImagesTests(unittest.TestCase):
    @patch("server.display.cube._fetch_cube_images", return_value=["gif1.gif", "image1.jpg"])
    def test_returns_image_list(self, mock_fetch: Mock) -> None:
        result = list_cube_images()

        self.assertIn("Available Cube images:", result)
        self.assertIn("gif1.gif", result)
        self.assertIn("image1.jpg", result)
        mock_fetch.assert_called_once()

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = list_cube_images()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube._fetch_cube_images", return_value=[])
    def test_returns_no_images_found_when_empty(self, mock_fetch: Mock) -> None:
        result = list_cube_images()

        self.assertEqual(result, "No images found on the Cube.")
        mock_fetch.assert_called_once()

    @patch("server.display.cube._fetch_cube_images", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = list_cube_images()

        self.assertIn("Failed to fetch images from Cube", result)
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


class SetCubeImageHelperTests(unittest.TestCase):
    def test_set_request_targets_image_directory(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"OK"

            _set_cube_image("gif1.gif")

            called_url = mock_urlopen.call_args[0][0]
            self.assertIn("/set?img=", called_url)
            self.assertIn("/image/gif1.gif", called_url)


class SetCubeImageTests(unittest.TestCase):
    @patch("server.display.cube._set_cube_image", return_value="OK")
    @patch("server.display.cube._fetch_cube_images", return_value=["gif1.gif", "image1.jpg"])
    def test_success_when_image_exists(self, mock_images: Mock, mock_set: Mock) -> None:
        result = set_cube_image("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube image set to: gif1.gif", result["message"])
        self.assertIn("Device response: OK", result["message"])
        mock_images.assert_called_once()
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube._set_cube_image", return_value="OK")
    @patch("server.display.cube._fetch_cube_images", return_value=["gif1.gif", "image1.jpg"])
    def test_strips_leading_slash_before_validating(self, mock_images: Mock, mock_set: Mock) -> None:
        result = set_cube_image("/gif1.gif")

        self.assertEqual(result["status"], "success")
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube._set_cube_image")
    @patch("server.display.cube._fetch_cube_images", return_value=["gif1.gif", "image1.jpg"])
    def test_rejects_image_not_in_list(self, mock_images: Mock, mock_set: Mock) -> None:
        result = set_cube_image("unknown.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image not found on Cube", result["message"])
        self.assertIn("unknown.gif", result["message"])
        mock_images.assert_called_once()
        mock_set.assert_not_called()

    @patch("server.display.cube._set_cube_image", return_value="FAIL")
    @patch("server.display.cube._fetch_cube_images", return_value=["gif1.gif"])
    def test_rejects_cube_failure_response(self, mock_images: Mock, mock_set: Mock) -> None:
        result = set_cube_image("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to set image", result["message"])
        self.assertIn("FAIL", result["message"])
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube._set_cube_image", return_value="")
    @patch("server.display.cube._fetch_cube_images", return_value=["gif1.gif"])
    def test_success_when_cube_responds_empty(self, mock_images: Mock, mock_set: Mock) -> None:
        result = set_cube_image("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Cube image set to: gif1.gif")

    @patch("server.display.cube._set_cube_image", side_effect=RuntimeError("connection refused"))
    @patch("server.display.cube._fetch_cube_images", return_value=["gif1.gif"])
    def test_returns_error_when_set_fails(self, mock_images: Mock, mock_set: Mock) -> None:
        result = set_cube_image("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to set image on Cube", result["message"])

    @patch("server.display.cube._fetch_cube_images", side_effect=RuntimeError("timeout"))
    def test_returns_error_when_verification_fails(self, mock_images: Mock) -> None:
        result = set_cube_image("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to verify image availability", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = set_cube_image("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])

    def test_returns_error_when_image_empty(self) -> None:
        with patch("server.display.cube._fetch_cube_images") as mock_images:
            result = set_cube_image("  ")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image name is required", result["message"])
        mock_images.assert_not_called()


if __name__ == "__main__":
    unittest.main()
