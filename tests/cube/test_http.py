import unittest
from unittest.mock import Mock, patch

import httpx

from server.display import cube as cube_module
from server.display.cube import (
    _fetch_cube_files,
    _fetch_cube_gifs,
    _fetch_cube_space,
    _set_cube_gif,
    _fetch_cube_brightness,
    _set_cube_brightness,
    _set_cube_brightness_schedule,
    _fetch_cube_current_gif,
    _upload_cube_image,
)

SAMPLE_HTML = (
    "<table id='list'><tbody>"
    "<tr><th>#</th><th>Name</th><th>Size(KB)</th><th></th><th></th></tr>"
    "<tr><td>1</td><td><a href='/gif1.gif'>Gif One</a></td><td>460</td>"
    "<td>x</td><td>y</td></tr>"
    "<tr><td>2</td><td><a href='/image1.jpg'>Image One</a></td><td>12</td>"
    "<td>x</td><td>y</td></tr>"
    "<tr><td>3</td><td><a href='gif2.gif'>Gif Two</a></td><td>70</td>"
    "<td>x</td><td>y</td></tr>"
    "</tbody></table>"
)


class FetchCubeFilesTests(unittest.TestCase):
    def test_returns_names_with_sizes_in_kb(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = SAMPLE_HTML.encode()

            files = _fetch_cube_files()

        self.assertEqual(
            files, [("gif1.gif", 460), ("image1.jpg", 12), ("gif2.gif", 70)]
        )

    def test_raises_on_connection_error(self) -> None:
        with patch(
            "server.display.cube.http.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_files()

            self.assertIn("connection refused", str(ctx.exception))


class FetchCubeGifsTests(unittest.TestCase):
    def test_returns_gif_paths_stripped(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = SAMPLE_HTML.encode()

            gifs = _fetch_cube_gifs()

            self.assertIn("gif1.gif", gifs)
            self.assertIn("gif2.gif", gifs)
            self.assertNotIn("/gif1.gif", gifs)

    def test_strips_leading_slashes_from_relative_paths(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = (
                b"<tr><td>1</td><td><a href='sub/gif1.gif'>gif1</a></td><td>70</td></tr>"
            )

            gifs = _fetch_cube_gifs()

            self.assertEqual(gifs, ["sub/gif1.gif"])

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.http.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_gifs()

            self.assertIn("connection refused", str(ctx.exception))


class FetchCubeSpaceTests(unittest.TestCase):
    def test_returns_free_and_total_bytes(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b'{"total":3121152,"free":925196}'

            free, total = _fetch_cube_space()

            self.assertEqual(free, 925196)
            self.assertEqual(total, 3121152)

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.http.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_space()

            self.assertIn("connection refused", str(ctx.exception))


class SetCubeGifHelperTests(unittest.TestCase):
    def test_set_request_targets_gif_directory(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"OK"

            _set_cube_gif("gif1.gif")

            called_url = mock_urlopen.call_args[0][0]
            self.assertIn("/set?img=", called_url)
            self.assertIn("/image/gif1.gif", called_url)


class FetchCubeBrightnessTests(unittest.TestCase):
    def test_returns_brightness_as_int_from_string_value(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b'{"brt":"10"}'

            brightness = _fetch_cube_brightness()

            self.assertEqual(brightness, 10)

    def test_normalizes_firmware_off_state_to_zero(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b'{"brt":"-10"}'

            brightness = _fetch_cube_brightness()

            self.assertEqual(brightness, 0)

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.http.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_brightness()

            self.assertIn("connection refused", str(ctx.exception))


class FetchCubeCurrentGifTests(unittest.TestCase):
    def test_returns_gif_path_from_device(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b'{"img":"/image/test.gif"}'

            gif = _fetch_cube_current_gif()

            self.assertEqual(gif, "/image/test.gif")

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.http.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_current_gif()

            self.assertIn("connection refused", str(ctx.exception))


class SetCubeBrightnessHelperTests(unittest.TestCase):
    def test_set_request_targets_brightness_endpoint(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"OK"

            _set_cube_brightness(10)

            called_url = mock_urlopen.call_args[0][0]
            self.assertIn("/set?brt=10", called_url)

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.http.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _set_cube_brightness(50)

            self.assertIn("connection refused", str(ctx.exception))


class SetCubeBrightnessScheduleHelperTests(unittest.TestCase):
    def test_set_request_targets_schedule_endpoint(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"OK"

            _set_cube_brightness_schedule("08:00", "22:00", 50, 20, True)

            called_url = mock_urlopen.call_args[0][0]
            self.assertIn("/set?t1=08:00&t2=22:00&b1=50&b2=20&en=1", called_url)

    def test_disabled_schedule_sends_en_zero(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"OK"

            _set_cube_brightness_schedule("07:30", "21:15", 60, 10, False)

            called_url = mock_urlopen.call_args[0][0]
            self.assertIn("/set?t1=07:30&t2=21:15&b1=60&b2=10&en=0", called_url)

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.http.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _set_cube_brightness_schedule("08:00", "22:00", 50, 20, True)

            self.assertIn("connection refused", str(ctx.exception))


class UploadCubeImageHelperTests(unittest.TestCase):
    @patch("server.display.cube.http.httpx.post")
    def test_gif_posts_to_do_upload_in_image_field(self, mock_post: Mock) -> None:
        _upload_cube_image("tmp.gif", b"gifdata")

        mock_post.assert_called_once()
        self.assertIn("/doUpload?dir=/image", mock_post.call_args[0][0])
        filename, content, content_type = mock_post.call_args[1]["files"]["image"]
        self.assertEqual(filename, "tmp.gif")
        self.assertEqual(content, b"gifdata")
        self.assertEqual(content_type, "image/gif")

    @patch("server.display.cube.http.httpx.post")
    def test_jpg_posts_in_file_field(self, mock_post: Mock) -> None:
        _upload_cube_image("photo.jpg", b"jpgdata")

        mock_post.assert_called_once()
        self.assertIn("/doUpload?dir=/image", mock_post.call_args[0][0])
        self.assertIn("file", mock_post.call_args[1]["files"])

    @patch(
        "server.display.cube.http.httpx.post",
        side_effect=ConnectionRefusedError("connection refused"),
    )
    def test_upload_failure_raises(self, mock_post: Mock) -> None:
        with self.assertRaises(Exception) as ctx:
            _upload_cube_image("tmp.gif", b"gifdata")

        self.assertIn("connection refused", str(ctx.exception))

    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.http.httpx.post")
    def test_retries_once_on_read_timeout(self, mock_post: Mock, mock_sleep: Mock) -> None:
        ok_response = Mock()
        ok_response.raise_for_status.return_value = None
        mock_post.side_effect = [httpx.ReadTimeout("The read operation timed out"), ok_response]

        _upload_cube_image("tmp.gif", b"gifdata")

        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once()
        timeout = mock_post.call_args[1]["timeout"]
        self.assertEqual(timeout.connect, 10)
        self.assertEqual(timeout.read, 120)

    @patch("server.display.cube.state.time.sleep")
    @patch(
        "server.display.cube.http.httpx.post",
        side_effect=httpx.ReadTimeout("The read operation timed out"),
    )
    def test_gives_up_after_all_attempts(self, mock_post: Mock, mock_sleep: Mock) -> None:
        with self.assertRaises(httpx.ReadTimeout):
            _upload_cube_image("tmp.gif", b"gifdata")

        self.assertEqual(mock_post.call_count, cube_module.UPLOAD_ATTEMPTS)

    @patch("server.display.cube.state.time.sleep")
    @patch(
        "server.display.cube.http.httpx.post",
        side_effect=httpx.HTTPStatusError("500", request=Mock(), response=Mock()),
    )
    def test_does_not_retry_http_error_responses(self, mock_post: Mock, mock_sleep: Mock) -> None:
        with self.assertRaises(httpx.HTTPStatusError):
            _upload_cube_image("tmp.gif", b"gifdata")

        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
