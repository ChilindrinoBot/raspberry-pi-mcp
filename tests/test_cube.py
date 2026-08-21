import unittest
from unittest.mock import Mock, patch

from server.display.cube import (
    _fetch_cube_images,
    list_cube_images,
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


if __name__ == "__main__":
    unittest.main()
