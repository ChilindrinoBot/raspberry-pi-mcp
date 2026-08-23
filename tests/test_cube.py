import base64
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, call, patch

from PIL import Image

from server.display import cube as cube_module
from server.display.cube import (
    _fetch_cube_gifs,
    list_cube_gifs,
    _fetch_cube_space,
    get_cube_free_space,
    _set_cube_gif,
    set_cube_gif,
    _set_cube_brightness,
    set_cube_brightness,
    _fetch_cube_brightness,
    get_cube_brightness,
    turn_cube_display_off,
    turn_cube_display_on,
    _fetch_cube_current_gif,
    get_cube_current_gif,
    _image_dimensions,
    _decode_image,
    _upload_cube_image,
    _is_in_cube_filelist,
    upload_cube_image,
    _fit_image_to_jpg,
    save_image_in_gallery,
    show_gallery_image,
    show_temporary_gif,
    list_gallery_images,
    list_gallery_gifs,
    _restore_previous_gif,
    BRIGHTNESS_DEFAULT,
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


class FetchCubeBrightnessTests(unittest.TestCase):
    def test_returns_brightness_as_int_from_string_value(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b'{"brt":"10"}'

            brightness = _fetch_cube_brightness()

            self.assertEqual(brightness, 10)

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_brightness()

            self.assertIn("connection refused", str(ctx.exception))


class GetCubeBrightnessTests(unittest.TestCase):
    @patch("server.display.cube._fetch_cube_brightness", return_value=75)
    def test_returns_current_brightness(self, mock_fetch: Mock) -> None:
        result = get_cube_brightness()

        self.assertEqual(result, "Current Cube brightness: 75")
        mock_fetch.assert_called_once()

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = get_cube_brightness()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube._fetch_cube_brightness", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = get_cube_brightness()

        self.assertIn("Failed to fetch brightness from Cube", result)
        self.assertIn("timeout", result)
        mock_fetch.assert_called_once()


class FetchCubeCurrentGifTests(unittest.TestCase):
    def test_returns_gif_path_from_device(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b'{"img":"/image/test.gif"}'

            gif = _fetch_cube_current_gif()

            self.assertEqual(gif, "/image/test.gif")

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _fetch_cube_current_gif()

            self.assertIn("connection refused", str(ctx.exception))


class GetCubeCurrentGifTests(unittest.TestCase):
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_returns_current_gif_without_image_prefix(self, mock_fetch: Mock) -> None:
        result = get_cube_current_gif()

        self.assertEqual(result, "Current Cube gif: test.gif")
        mock_fetch.assert_called_once()

    @patch("server.display.cube._fetch_cube_current_gif", return_value="/other/tmp.gif")
    def test_keeps_paths_outside_image_dir(self, mock_fetch: Mock) -> None:
        result = get_cube_current_gif()

        self.assertEqual(result, "Current Cube gif: other/tmp.gif")

    @patch("server.display.cube._fetch_cube_current_gif", return_value="")
    def test_returns_no_gif_when_empty(self, mock_fetch: Mock) -> None:
        result = get_cube_current_gif()

        self.assertEqual(result, "No gif is currently set on the Cube.")

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = get_cube_current_gif()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube._fetch_cube_current_gif", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = get_cube_current_gif()

        self.assertIn("Failed to fetch current gif from Cube", result)
        self.assertIn("timeout", result)
        mock_fetch.assert_called_once()


class SetCubeBrightnessHelperTests(unittest.TestCase):
    def test_set_request_targets_brightness_endpoint(self) -> None:
        with patch("server.display.cube.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = b"OK"

            _set_cube_brightness(10)

            called_url = mock_urlopen.call_args[0][0]
            self.assertIn("/set?brt=10", called_url)

    def test_fetch_failure_raises(self) -> None:
        with patch(
            "server.display.cube.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _set_cube_brightness(50)

            self.assertIn("connection refused", str(ctx.exception))


class SetCubeBrightnessTests(unittest.TestCase):
    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_success_with_device_response(self, mock_set: Mock) -> None:
        result = set_cube_brightness(75)

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 75", result["message"])
        self.assertIn("Device response: OK", result["message"])
        mock_set.assert_called_once_with(75)

    @patch("server.display.cube._set_cube_brightness", return_value="")
    def test_success_when_cube_responds_empty(self, mock_set: Mock) -> None:
        result = set_cube_brightness(30)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Cube brightness set to: 30")

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_defaults_to_50_when_no_level_given(self, mock_set: Mock) -> None:
        result = set_cube_brightness()

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 50", result["message"])
        mock_set.assert_called_once_with(BRIGHTNESS_DEFAULT)
        self.assertEqual(BRIGHTNESS_DEFAULT, 50)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_clamps_level_below_zero_to_zero(self, mock_set: Mock) -> None:
        result = set_cube_brightness(-5)

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 0", result["message"])
        mock_set.assert_called_once_with(0)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_clamps_level_above_hundred_to_hundred(self, mock_set: Mock) -> None:
        result = set_cube_brightness(150)

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 100", result["message"])
        mock_set.assert_called_once_with(100)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_accepts_boundary_levels(self, mock_set: Mock) -> None:
        result_min = set_cube_brightness(0)
        result_max = set_cube_brightness(100)

        self.assertEqual(result_min["status"], "success")
        self.assertEqual(result_max["status"], "success")
        mock_set.assert_has_calls([call(0), call(100)])

    @patch("server.display.cube._set_cube_brightness", return_value="FAIL")
    def test_rejects_cube_failure_response(self, mock_set: Mock) -> None:
        result = set_cube_brightness(20)

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to set brightness", result["message"])
        self.assertIn("FAIL", result["message"])
        mock_set.assert_called_once_with(20)

    @patch("server.display.cube._set_cube_brightness", side_effect=RuntimeError("connection refused"))
    def test_returns_error_when_set_fails(self, mock_set: Mock) -> None:
        result = set_cube_brightness(60)

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to set brightness on Cube", result["message"])
        self.assertIn("connection refused", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = set_cube_brightness(40)

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])


class TurnCubeDisplayOffTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = cube_module._REMEMBERED_BRIGHTNESS
        cube_module._REMEMBERED_BRIGHTNESS = None

    def tearDown(self) -> None:
        cube_module._REMEMBERED_BRIGHTNESS = self._original

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    @patch("server.display.cube._fetch_cube_brightness", return_value=30)
    def test_remembers_brightness_before_turning_off(self, mock_fetch: Mock, mock_set: Mock) -> None:
        result = turn_cube_display_off()

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube display turned off", result["message"])
        self.assertIn("restored to 30", result["message"])
        mock_set.assert_called_once_with(0)
        self.assertEqual(cube_module._REMEMBERED_BRIGHTNESS, 30)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    @patch("server.display.cube._fetch_cube_brightness", side_effect=RuntimeError("timeout"))
    def test_falls_back_to_remembered_value_when_device_query_fails(self, mock_fetch: Mock, mock_set: Mock) -> None:
        cube_module._REMEMBERED_BRIGHTNESS = 75

        result = turn_cube_display_off()

        self.assertEqual(result["status"], "success")
        self.assertIn("restored to 75", result["message"])
        mock_set.assert_called_once_with(0)
        self.assertEqual(cube_module._REMEMBERED_BRIGHTNESS, 75)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    @patch("server.display.cube._fetch_cube_brightness", side_effect=RuntimeError("timeout"))
    def test_falls_back_to_default_when_nothing_remembered(self, mock_fetch: Mock, mock_set: Mock) -> None:
        result = turn_cube_display_off()

        self.assertEqual(result["status"], "success")
        self.assertIn(f"restored to {BRIGHTNESS_DEFAULT}", result["message"])
        mock_set.assert_called_once_with(0)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    @patch("server.display.cube._fetch_cube_brightness", return_value=0)
    def test_does_not_overwrite_memory_with_zero_on_double_off(self, mock_fetch: Mock, mock_set: Mock) -> None:
        cube_module._REMEMBERED_BRIGHTNESS = 30

        result = turn_cube_display_off()

        self.assertEqual(result["status"], "success")
        self.assertIn("restored to 30", result["message"])
        self.assertEqual(cube_module._REMEMBERED_BRIGHTNESS, 30)

    @patch("server.display.cube._set_cube_brightness", return_value="FAIL")
    @patch("server.display.cube._fetch_cube_brightness", return_value=30)
    def test_rejects_cube_failure_response(self, mock_fetch: Mock, mock_set: Mock) -> None:
        result = turn_cube_display_off()

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to turn off display", result["message"])
        mock_set.assert_called_once_with(0)

    @patch("server.display.cube._set_cube_brightness", side_effect=RuntimeError("connection refused"))
    @patch("server.display.cube._fetch_cube_brightness", return_value=30)
    def test_returns_error_when_set_fails(self, mock_fetch: Mock, mock_set: Mock) -> None:
        result = turn_cube_display_off()

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to turn off Cube display", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = turn_cube_display_off()

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])


class TurnCubeDisplayOnTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = cube_module._REMEMBERED_BRIGHTNESS
        cube_module._REMEMBERED_BRIGHTNESS = None

    def tearDown(self) -> None:
        cube_module._REMEMBERED_BRIGHTNESS = self._original

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_restores_remembered_brightness(self, mock_set: Mock) -> None:
        cube_module._REMEMBERED_BRIGHTNESS = 75

        result = turn_cube_display_on()

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube display turned on at brightness 75", result["message"])
        mock_set.assert_called_once_with(75)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_defaults_to_50_when_nothing_remembered(self, mock_set: Mock) -> None:
        result = turn_cube_display_on()

        self.assertEqual(result["status"], "success")
        self.assertIn(f"turned on at brightness {BRIGHTNESS_DEFAULT}", result["message"])
        mock_set.assert_called_once_with(BRIGHTNESS_DEFAULT)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_defaults_to_50_when_remembered_is_zero(self, mock_set: Mock) -> None:
        cube_module._REMEMBERED_BRIGHTNESS = 0

        result = turn_cube_display_on()

        self.assertEqual(result["status"], "success")
        mock_set.assert_called_once_with(BRIGHTNESS_DEFAULT)

    @patch("server.display.cube._set_cube_brightness", return_value="OK")
    def test_clamps_out_of_range_remembered_value(self, mock_set: Mock) -> None:
        cube_module._REMEMBERED_BRIGHTNESS = 150

        result = turn_cube_display_on()

        self.assertEqual(result["status"], "success")
        self.assertIn("turned on at brightness 100", result["message"])
        mock_set.assert_called_once_with(100)

    @patch("server.display.cube._set_cube_brightness", return_value="FAIL")
    def test_rejects_cube_failure_response(self, mock_set: Mock) -> None:
        cube_module._REMEMBERED_BRIGHTNESS = 40

        result = turn_cube_display_on()

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to turn on display", result["message"])
        mock_set.assert_called_once_with(40)

    @patch("server.display.cube._set_cube_brightness", side_effect=RuntimeError("connection refused"))
    def test_returns_error_when_set_fails(self, mock_set: Mock) -> None:
        result = turn_cube_display_on()

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to turn on Cube display", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = turn_cube_display_on()

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])


def _image_bytes(fmt: str, width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format=fmt)
    return buffer.getvalue()


def _solid_image_bytes(fmt: str, width: int, height: int, color) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format=fmt)
    return buffer.getvalue()


def _rgba_image_bytes(width: int, height: int, color, alpha: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (width, height), color + (alpha,)).save(buffer, format="PNG")
    return buffer.getvalue()


class ImageDimensionsTests(unittest.TestCase):
    def test_reads_gif_size(self) -> None:
        self.assertEqual(_image_dimensions(_image_bytes("GIF", 240, 240)), (240, 240))

    def test_reads_jpeg_size(self) -> None:
        self.assertEqual(_image_dimensions(_image_bytes("JPEG", 240, 240)), (240, 240))

    def test_reads_other_sizes(self) -> None:
        self.assertEqual(_image_dimensions(_image_bytes("GIF", 100, 50)), (100, 50))

    def test_returns_none_for_invalid_data(self) -> None:
        self.assertIsNone(_image_dimensions(b"not an image"))

    def test_returns_none_for_empty_data(self) -> None:
        self.assertIsNone(_image_dimensions(b""))


class UploadCubeImageHelperTests(unittest.TestCase):
    @patch("server.display.cube.httpx.post")
    def test_gif_posts_to_do_upload_in_image_field(self, mock_post: Mock) -> None:
        _upload_cube_image("tmp.gif", b"gifdata")

        mock_post.assert_called_once()
        self.assertIn("/doUpload?dir=/image", mock_post.call_args[0][0])
        filename, content = mock_post.call_args[1]["files"]["image"]
        self.assertEqual(filename, "tmp.gif")
        self.assertEqual(content, b"gifdata")

    @patch("server.display.cube.httpx.post")
    def test_jpg_posts_in_file_field(self, mock_post: Mock) -> None:
        _upload_cube_image("photo.jpg", b"jpgdata")

        mock_post.assert_called_once()
        self.assertIn("/doUpload?dir=/image", mock_post.call_args[0][0])
        self.assertIn("file", mock_post.call_args[1]["files"])

    @patch(
        "server.display.cube.httpx.post",
        side_effect=ConnectionRefusedError("connection refused"),
    )
    def test_upload_failure_raises(self, mock_post: Mock) -> None:
        with self.assertRaises(Exception) as ctx:
            _upload_cube_image("tmp.gif", b"gifdata")

        self.assertIn("connection refused", str(ctx.exception))


class DecodeImageTests(unittest.TestCase):
    def test_roundtrip_decodes_client_payload(self) -> None:
        encoded = base64.b64encode(b"gifdata").decode()

        self.assertEqual(_decode_image(encoded), b"gifdata")

    def test_invalid_base64_raises(self) -> None:
        with self.assertRaises(Exception):
            _decode_image("not-valid-base64!!!")


class IsInCubeFilelistTests(unittest.TestCase):
    def test_matches_plain_entry(self) -> None:
        self.assertTrue(_is_in_cube_filelist("tmp.gif", ["tmp.gif"]))

    def test_matches_entry_inside_image_dir(self) -> None:
        self.assertTrue(_is_in_cube_filelist("test.jpg", ["image/tmp.gif", "image/test.jpg"]))

    def test_is_case_insensitive(self) -> None:
        self.assertTrue(_is_in_cube_filelist("TEST.JPG", ["image/test.jpg"]))

    def test_rejects_partial_name_matches(self) -> None:
        self.assertFalse(_is_in_cube_filelist("test.jpg", ["image/mytest.jpg"]))

    def test_rejects_missing_file(self) -> None:
        self.assertFalse(_is_in_cube_filelist("missing.gif", ["image/tmp.gif"]))


class UploadCubeImageTests(unittest.TestCase):
    def _encoded(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    @patch("server.display.cube._fetch_cube_gifs", return_value=["image/tmp.gif", "image/test.jpg"])
    @patch("server.display.cube._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube._upload_cube_image")
    def test_success_with_encoded_gif_confirms_in_filelist(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Image uploaded to Cube: tmp.gif")
        mock_space.assert_called_once()
        filename, payload = mock_upload.call_args[0]
        self.assertEqual(filename, "tmp.gif")
        self.assertEqual(payload, _image_bytes("GIF", 240, 240))
        mock_gifs.assert_called_once()

    @patch("server.display.cube._fetch_cube_gifs", return_value=["image/photo.jpg"])
    @patch("server.display.cube._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube._upload_cube_image")
    def test_success_with_encoded_jpg(self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("JPEG", 240, 240)), "photo.jpg")

        self.assertEqual(result["status"], "success")
        self.assertIn("Image uploaded to Cube: photo.jpg", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])

    @patch("server.display.cube._fetch_cube_gifs", return_value=["image/photo.jpg"])
    @patch("server.display.cube._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube._upload_cube_image")
    def test_converts_png_to_exact_240_jpeg_instead_of_rejecting(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("PNG", 500, 300)), "photo.png")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Image uploaded to Cube: photo.jpg")
        uploaded_name, payload = mock_upload.call_args[0]
        self.assertEqual(uploaded_name, "photo.jpg")
        with Image.open(BytesIO(payload)) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))

    @patch("server.display.cube._fetch_cube_space")
    def test_returns_error_when_conversion_fails(self, mock_space: Mock) -> None:
        result = upload_cube_image(self._encoded(b"data"), "picture.webp")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to convert image picture.webp to JPEG", result["message"])
        mock_space.assert_not_called()

    def test_returns_error_when_nameless_format_cannot_be_converted(self) -> None:
        result = upload_cube_image(self._encoded(b"data"), "noext")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to convert image noext to JPEG", result["message"])

    def test_converts_png_keeping_basename_with_jpg_suffix(self) -> None:
        with patch("server.display.cube._fetch_cube_gifs", return_value=["image/tmp.jpg"]):
            with patch("server.display.cube._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024)):
                with patch("server.display.cube._upload_cube_image") as mock_upload:
                    result = upload_cube_image(
                        self._encoded(_image_bytes("PNG", 300, 300)), "/etc/passwd/tmp.PNG"
                    )

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_upload.call_args[0][0], "tmp.jpg")

    def test_rejects_empty_filename(self) -> None:
        result = upload_cube_image(self._encoded(b"data"), "  ")

        self.assertEqual(result["status"], "error")
        self.assertIn("Filename is required", result["message"])

    @patch("server.display.cube._fetch_cube_gifs", return_value=["image/tmp.gif"])
    @patch("server.display.cube._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube._upload_cube_image")
    def test_uses_basename_of_sent_filename(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "/etc/passwd/tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_upload.call_args[0][0], "tmp.gif")

    def test_rejects_malformed_base64(self) -> None:
        result = upload_cube_image("not-valid-base64!!!", "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to decode image tmp.gif", result["message"])

    @patch("server.display.cube._decode_image", return_value=b"")
    def test_rejects_empty_payload(self, mock_decode: Mock) -> None:
        result = upload_cube_image("token", "empty.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image is empty: empty.gif", result["message"])

    @patch("server.display.cube._fetch_cube_space")
    def test_rejects_wrong_dimensions(self, mock_space: Mock) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 100, 100)), "small.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image must be 240x240", result["message"])
        self.assertIn("(got 100x100)", result["message"])
        mock_space.assert_not_called()

    @patch("server.display.cube._fetch_cube_space")
    def test_rejects_undetectable_dimensions(self, mock_space: Mock) -> None:
        result = upload_cube_image(self._encoded(b"GIF89a\xff\xff"), "broken.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Could not read image dimensions of broken.gif", result["message"])
        mock_space.assert_not_called()

    @patch("server.display.cube._upload_cube_image")
    @patch("server.display.cube._fetch_cube_space", return_value=(10, 3 * 1024 * 1024))
    def test_rejects_when_not_enough_space(self, mock_space: Mock, mock_upload: Mock) -> None:
        data = _image_bytes("GIF", 240, 240) + b"x" * 100

        result = upload_cube_image(self._encoded(data), "big.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Not enough space on Cube", result["message"])
        self.assertIn(f"needs {len(data)} bytes", result["message"])
        self.assertIn("only 10 bytes are free", result["message"])
        mock_upload.assert_not_called()

    @patch("server.display.cube._fetch_cube_space", side_effect=RuntimeError("timeout"))
    def test_returns_error_when_space_check_fails(self, mock_space: Mock) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to check free space on Cube", result["message"])

    @patch("server.display.cube._fetch_cube_gifs", return_value=["image/tmp.gif"])
    @patch("server.display.cube._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube._upload_cube_image", side_effect=RuntimeError("connection refused"))
    def test_returns_error_when_upload_fails(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to upload image to Cube", result["message"])
        mock_gifs.assert_not_called()

    @patch("server.display.cube._fetch_cube_gifs", side_effect=RuntimeError("timeout"))
    @patch("server.display.cube._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube._upload_cube_image")
    def test_returns_error_when_confirmation_fails(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to verify upload of tmp.gif on Cube", result["message"])

    @patch("server.display.cube._fetch_cube_gifs", return_value=["image/tmp.gif", "image/other.jpg"])
    @patch("server.display.cube._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube._upload_cube_image")
    def test_returns_error_when_file_not_in_filelist(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "missing.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Upload could not be confirmed", result["message"])
        self.assertIn("missing.gif is not in the Cube file list", result["message"])


def _pixel_close(pixel, expected, tolerance: int = 30) -> bool:
    return all(abs(channel - target) <= tolerance for channel, target in zip(pixel[:3], expected))


class FitImageToJpgHelperTests(unittest.TestCase):
    def test_landscape_image_is_padded_top_and_bottom(self) -> None:
        processed = _fit_image_to_jpg(_solid_image_bytes("PNG", 480, 120, "red"))

        with Image.open(BytesIO(processed)) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))
            rgb = img.convert("RGB")
            self.assertTrue(_pixel_close(rgb.getpixel((0, 0)), (0, 0, 0)))
            self.assertTrue(_pixel_close(rgb.getpixel((239, 0)), (0, 0, 0)))
            self.assertTrue(_pixel_close(rgb.getpixel((120, 120)), (255, 0, 0)))

    def test_portrait_image_is_padded_on_the_sides(self) -> None:
        processed = _fit_image_to_jpg(_solid_image_bytes("PNG", 120, 480, "red"))

        with Image.open(BytesIO(processed)) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))
            rgb = img.convert("RGB")
            self.assertTrue(_pixel_close(rgb.getpixel((0, 0)), (0, 0, 0)))
            self.assertTrue(_pixel_close(rgb.getpixel((0, 239)), (0, 0, 0)))
            self.assertTrue(_pixel_close(rgb.getpixel((120, 120)), (255, 0, 0)))

    def test_exact_240_image_fills_canvas_without_padding(self) -> None:
        processed = _fit_image_to_jpg(_solid_image_bytes("JPEG", 240, 240, "red"))

        with Image.open(BytesIO(processed)) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))
            rgb = img.convert("RGB")
            self.assertTrue(_pixel_close(rgb.getpixel((0, 0)), (255, 0, 0)))
            self.assertTrue(_pixel_close(rgb.getpixel((239, 239)), (255, 0, 0)))

    def test_small_image_is_not_upscaled(self) -> None:
        processed = _fit_image_to_jpg(_solid_image_bytes("PNG", 100, 100, "red"))

        with Image.open(BytesIO(processed)) as img:
            rgb = img.convert("RGB")
            self.assertTrue(_pixel_close(rgb.getpixel((50, 50)), (0, 0, 0)))
            self.assertTrue(_pixel_close(rgb.getpixel((75, 75)), (255, 0, 0)))

    def test_transparent_areas_are_flattened_over_black(self) -> None:
        processed = _fit_image_to_jpg(_rgba_image_bytes(480, 480, (255, 0, 0), alpha=0))

        with Image.open(BytesIO(processed)) as img:
            self.assertEqual(img.mode, "RGB")
            rgb = img.convert("RGB")
            self.assertTrue(_pixel_close(rgb.getpixel((120, 120)), (0, 0, 0)))

    def test_invalid_data_raises(self) -> None:
        with self.assertRaises(Exception):
            _fit_image_to_jpg(b"not an image")

    def test_empty_data_raises(self) -> None:
        with self.assertRaises(Exception):
            _fit_image_to_jpg(b"")


class SaveImageInGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = Path(tempfile.mkdtemp())
        patcher = patch.object(cube_module, "RANDOM_IMAGE_DIR", self._tmpdir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _encoded(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    def test_saves_png_as_240x240_jpg_in_images_dir(self) -> None:
        result = save_image_in_gallery(self._encoded(_image_bytes("PNG", 500, 300)), "photo.png")

        self.assertEqual(result["status"], "success")
        saved = self._tmpdir / "photo.jpg"
        self.assertTrue(saved.is_file())
        with Image.open(saved) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))

    def test_saves_with_plain_name_without_suffix(self) -> None:
        result = save_image_in_gallery(self._encoded(_image_bytes("PNG", 500, 300)), "test")

        self.assertEqual(result["status"], "success")
        self.assertTrue((self._tmpdir / "test.jpg").is_file())

    def test_strips_trailing_jpg_suffix_from_name(self) -> None:
        result = save_image_in_gallery(self._encoded(_image_bytes("PNG", 300, 300)), "test.jpg")

        self.assertEqual(result["status"], "success")
        self.assertTrue((self._tmpdir / "test.jpg").is_file())
        self.assertFalse((self._tmpdir / "test.jpg.jpg").exists())

    def test_keeps_dots_when_suffix_is_not_an_image_extension(self) -> None:
        result = save_image_in_gallery(self._encoded(_image_bytes("PNG", 300, 300)), "my.image")

        self.assertEqual(result["status"], "success")
        self.assertTrue((self._tmpdir / "my.image.jpg").is_file())

    def test_normalizes_extension_and_name_to_jpg(self) -> None:
        result = save_image_in_gallery(self._encoded(_image_bytes("GIF", 300, 300)), "pic.JPEG")

        self.assertEqual(result["status"], "success")
        self.assertTrue((self._tmpdir / "pic.jpg").is_file())
        self.assertFalse((self._tmpdir / "pic.JPEG").exists())

    def test_rejects_saved_name_longer_than_25_characters_with_suffix(self) -> None:
        result = save_image_in_gallery(self._encoded(_image_bytes("PNG", 300, 300)), "a" * 22 + ".png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image name is too long", result["message"])
        self.assertIn(f"Max is {cube_module.IMAGE_NAME_MAX_LENGTH} characters", result["message"])

    def test_rejects_saved_name_longer_than_25_characters(self) -> None:
        result = save_image_in_gallery(self._encoded(_image_bytes("PNG", 300, 300)), "a" * 25)

        self.assertEqual(result["status"], "error")
        self.assertIn("Image name is too long", result["message"])
        self.assertIn(f"Max is {cube_module.IMAGE_NAME_MAX_LENGTH} characters", result["message"])

    def test_accepts_saved_name_with_exactly_25_characters(self) -> None:
        result = save_image_in_gallery(self._encoded(_image_bytes("PNG", 300, 300)), "a" * 21)

        self.assertEqual(result["status"], "success")
        self.assertTrue((self._tmpdir / f"{'a' * 21}.jpg").is_file())

    def test_creates_missing_images_dir(self) -> None:
        nested = self._tmpdir / "nested"

        with patch.object(cube_module, "RANDOM_IMAGE_DIR", nested):
            result = save_image_in_gallery(self._encoded(_image_bytes("PNG", 300, 300)), "deep.png")

        self.assertEqual(result["status"], "success")
        self.assertTrue((nested / "deep.jpg").is_file())

    def test_rejects_empty_name(self) -> None:
        result = save_image_in_gallery(self._encoded(b"data"), "   ")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image name is required", result["message"])

    def test_rejects_dotfile_style_name(self) -> None:
        result = save_image_in_gallery(self._encoded(b"data"), ".png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image name is required", result["message"])

    def test_rejects_malformed_base64(self) -> None:
        result = save_image_in_gallery("not-valid-base64!!!", "photo.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to decode image photo.png", result["message"])

    @patch("server.display.cube._decode_image", return_value=b"")
    def test_rejects_empty_payload(self, mock_decode: Mock) -> None:
        result = save_image_in_gallery("token", "empty.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image is empty: empty.png", result["message"])

    @patch(
        "server.display.cube._fit_image_to_jpg",
        side_effect=RuntimeError("cannot identify image file"),
    )
    def test_returns_error_when_processing_fails(self, mock_fit: Mock) -> None:
        result = save_image_in_gallery(self._encoded(b"data"), "broken.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to process image broken.png", result["message"])
        mock_fit.assert_called_once()

    @patch("server.display.cube._fit_image_to_jpg", return_value=b"not-a-jpeg")
    def test_verifies_processed_output_is_jpeg(self, mock_fit: Mock) -> None:
        result = save_image_in_gallery(self._encoded(b"data"), "photo.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Processed image is not a valid JPEG", result["message"])
        self.assertFalse((self._tmpdir / "photo.jpg").exists())

    @patch("server.display.cube._fit_image_to_jpg", return_value=_image_bytes("JPEG", 100, 100))
    def test_verifies_processed_output_dimensions(self, mock_fit: Mock) -> None:
        result = save_image_in_gallery(self._encoded(b"data"), "photo.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Processed image must be 240x240", result["message"])
        self.assertFalse((self._tmpdir / "photo.jpg").exists())


class GalleryResourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._images_dir = Path(tempfile.mkdtemp())
        self._gifs_dir = Path(tempfile.mkdtemp())
        image_patcher = patch.object(cube_module, "RANDOM_IMAGE_DIR", self._images_dir)
        gif_patcher = patch.object(cube_module, "RANDOM_GIF_DIR", self._gifs_dir)
        image_patcher.start()
        gif_patcher.start()
        self.addCleanup(image_patcher.stop)
        self.addCleanup(gif_patcher.stop)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._images_dir, ignore_errors=True)
        shutil.rmtree(self._gifs_dir, ignore_errors=True)

    def test_lists_image_names_sorted(self) -> None:
        (self._images_dir / "b.jpg").write_bytes(b"jpg")
        (self._images_dir / "a.jpeg").write_bytes(b"jpeg")

        result = list_gallery_images()

        self.assertEqual(result, "Available gallery images:\na.jpeg\nb.jpg")

    def test_ignores_non_image_files_in_images_gallery(self) -> None:
        (self._images_dir / "photo.jpg").write_bytes(b"jpg")
        (self._images_dir / "notes.txt").write_bytes(b"text")
        (self._images_dir / "clip.gif").write_bytes(b"gif")

        result = list_gallery_images()

        self.assertEqual(result, "Available gallery images:\nphoto.jpg")

    def test_reports_no_images_when_gallery_empty(self) -> None:
        result = list_gallery_images()

        self.assertTrue(result.startswith("No images found in"))

    def test_reports_no_images_when_gallery_missing(self) -> None:
        import shutil

        shutil.rmtree(self._images_dir, ignore_errors=True)

        result = list_gallery_images()

        self.assertTrue(result.startswith("No images found in"))

    def test_lists_gif_names_sorted(self) -> None:
        (self._gifs_dir / "b.gif").write_bytes(b"gif")
        (self._gifs_dir / "a.gif").write_bytes(b"gif")

        result = list_gallery_gifs()

        self.assertEqual(result, "Available gallery gifs:\na.gif\nb.gif")

    def test_ignores_non_gif_files_in_gifs_gallery(self) -> None:
        (self._gifs_dir / "anim.gif").write_bytes(b"gif")
        (self._gifs_dir / "photo.jpg").write_bytes(b"jpg")
        (self._gifs_dir / "notes.txt").write_bytes(b"text")

        result = list_gallery_gifs()

        self.assertEqual(result, "Available gallery gifs:\nanim.gif")

    def test_reports_no_gifs_when_gallery_empty(self) -> None:
        result = list_gallery_gifs()

        self.assertTrue(result.startswith("No gifs found in"))

    def test_reports_no_gifs_when_gallery_missing(self) -> None:
        import shutil

        shutil.rmtree(self._gifs_dir, ignore_errors=True)

        result = list_gallery_gifs()

        self.assertTrue(result.startswith("No gifs found in"))


class ShowGalleryImageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = Path(tempfile.mkdtemp())
        patcher = patch.object(cube_module, "RANDOM_IMAGE_DIR", self._tmpdir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_jpeg(self, name: str, width: int = 240, height: int = 240) -> Path:
        path = self._tmpdir / name
        path.write_bytes(_image_bytes("JPEG", width, height))
        return path

    def test_requires_a_name(self) -> None:
        for empty in ("", "   "):
            result = show_gallery_image(empty)

            self.assertEqual(result["status"], "error")
            self.assertIn("Image name is required", result["message"])

    def test_reports_missing_image_with_available_list(self) -> None:
        self._write_jpeg("known.jpg")

        result = show_gallery_image("unknown")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image not found in", result["message"])
        self.assertIn("Available: known.jpg", result["message"])

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._fetch_cube_gifs")
    @patch("server.display.cube._upload_cube_image")
    def test_shows_240_jpeg_as_is(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
        mock_set: Mock,
    ) -> None:
        self._write_jpeg("photo.jpg")
        mock_gifs.return_value = ["photo.jpg"]

        result = show_gallery_image("photo")

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube image set to: photo.jpg", result["message"])
        self.assertIn("(no timer; it stays until changed)", result["message"])
        upload_name, payload = mock_upload.call_args.args
        self.assertEqual(upload_name, "photo.jpg")
        with Image.open(BytesIO(payload)) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))
        mock_set.assert_called_once_with("photo.jpg")

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._fetch_cube_gifs")
    @patch("server.display.cube._upload_cube_image")
    def test_converts_non_240_image_before_upload(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
        mock_set: Mock,
    ) -> None:
        (self._tmpdir / "pic.png").write_bytes(_image_bytes("PNG", 500, 300))
        mock_gifs.return_value = ["pic.jpg"]

        result = show_gallery_image("pic.png")

        self.assertEqual(result["status"], "success")
        upload_name, payload = mock_upload.call_args.args
        self.assertEqual(upload_name, "pic.jpg")
        with Image.open(BytesIO(payload)) as img:
            self.assertEqual(img.size, (240, 240))
        mock_set.assert_called_once_with("pic.jpg")

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._fetch_cube_gifs")
    @patch("server.display.cube._upload_cube_image")
    def test_stops_running_random_modes(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
        mock_set: Mock,
    ) -> None:
        self._write_jpeg("photo.jpg")
        mock_gifs.return_value = ["photo.jpg"]
        mock_stop_random.return_value = (True, "old.gif")
        mock_stop_image.return_value = (True, "old.jpg")

        result = show_gallery_image("photo.jpg")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random gif mode stopped", result["message"])
        self.assertIn("Random image mode stopped", result["message"])

    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._fetch_cube_gifs", return_value=[])
    @patch("server.display.cube._upload_cube_image")
    def test_fails_when_upload_not_confirmed(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
    ) -> None:
        self._write_jpeg("photo.jpg")

        result = show_gallery_image("photo")

        self.assertEqual(result["status"], "error")
        self.assertIn("Upload could not be confirmed", result["message"])

    @patch("server.display.cube._set_cube_gif", return_value="FAIL busy")
    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._fetch_cube_gifs")
    @patch("server.display.cube._upload_cube_image")
    def test_fails_when_cube_refuses(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
        mock_set: Mock,
    ) -> None:
        self._write_jpeg("photo.jpg")
        mock_gifs.return_value = ["photo.jpg"]

        result = show_gallery_image("photo")

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to set image photo.jpg", result["message"])


class ShowTemporaryGifTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_running = cube_module._TEMP_GIF_RUNNING
        cube_module._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        cube_module._TEMP_GIF_RUNNING = self._original_running

    def _encoded(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_shows_tmp_and_schedules_background_restore(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("tmp.gif is now displayed for 5 seconds", result["message"])
        self.assertIn("test.gif will be restored automatically", result["message"])
        mock_current.assert_called_once()
        mock_upload.assert_called_once_with(self._encoded(b"gifdata"), "tmp.gif")
        mock_set.assert_called_once_with("tmp.gif")
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("test.gif", 5, False, False),
            daemon=True,
        )
        mock_thread_cls.return_value.start.assert_called_once()
        self.assertTrue(cube_module._TEMP_GIF_RUNNING)

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/photo.jpg")
    def test_maps_jpeg_extension_to_tmp_jpg(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"jpgdata"), "photo.JPEG")

        self.assertEqual(result["status"], "success")
        mock_upload.assert_called_once_with(self._encoded(b"jpgdata"), "tmp.jpg")
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("photo.jpg", 5, False, False),
            daemon=True,
        )

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_clamps_seconds_above_max(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif", seconds=100)

        self.assertEqual(result["status"], "success")
        self.assertIn("displayed for 30 seconds", result["message"])
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("test.gif", 30, False, False),
            daemon=True,
        )

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_clamps_seconds_below_min(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif", seconds=0)

        self.assertEqual(result["status"], "success")
        self.assertIn("displayed for 1 seconds", result["message"])
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("test.gif", 1, False, False),
            daemon=True,
        )

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="")
    def test_reports_no_previous_gif_to_restore(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("No previous gif to restore", result["message"])
        mock_set.assert_called_once_with("tmp.gif")
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("", 5, False, False),
            daemon=True,
        )

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube.upload_cube_image")
    @patch("server.display.cube._fetch_cube_current_gif")
    def test_rejects_when_a_temporary_gif_is_already_running(
        self, mock_current: Mock, mock_upload: Mock, mock_thread_cls: Mock
    ) -> None:
        cube_module._TEMP_GIF_RUNNING = True

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("A temporary gif is already being shown", result["message"])
        mock_current.assert_not_called()
        mock_upload.assert_not_called()
        mock_thread_cls.assert_not_called()

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_converts_png_to_tmp_jpg_before_uploading(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(_image_bytes("PNG", 500, 300)), "picture.png")

        self.assertEqual(result["status"], "success")
        encoded, name = mock_upload.call_args[0]
        self.assertEqual(name, "tmp.jpg")
        with Image.open(BytesIO(base64.b64decode(encoded))) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))

    @patch("server.display.cube.upload_cube_image")
    def test_returns_error_when_conversion_fails(self, mock_upload: Mock) -> None:
        result = show_temporary_gif(self._encoded(b"data"), "picture.webp")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to convert image picture.webp to JPEG", result["message"])
        mock_upload.assert_not_called()

    def test_returns_error_when_nameless_format_cannot_be_converted(self) -> None:
        with patch("server.display.cube.upload_cube_image") as mock_upload:
            result = show_temporary_gif(self._encoded(b"data"), "noext")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to convert image noext to JPEG", result["message"])
        mock_upload.assert_not_called()

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.CUBE_BASE_URL", ""):
            result = show_temporary_gif(self._encoded(b"data"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube.upload_cube_image")
    @patch("server.display.cube._fetch_cube_current_gif", side_effect=RuntimeError("timeout"))
    def test_returns_error_when_current_gif_cannot_be_read(
        self, mock_current: Mock, mock_upload: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to read current gif from Cube", result["message"])
        mock_upload.assert_not_called()
        mock_thread_cls.assert_not_called()

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif")
    @patch(
        "server.display.cube.upload_cube_image",
        return_value={"status": "error", "message": "Image must be 240x240 (got 100x100): tmp.gif."},
    )
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_propagates_upload_error_without_displaying(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image must be 240x240", result["message"])
        mock_set.assert_not_called()
        mock_thread_cls.assert_not_called()
        self.assertFalse(cube_module._TEMP_GIF_RUNNING)

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", side_effect=RuntimeError("connection refused"))
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_returns_error_when_display_fails_and_releases_flag(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to display temporary gif tmp.gif", result["message"])
        mock_thread_cls.assert_not_called()
        self.assertFalse(cube_module._TEMP_GIF_RUNNING)

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="FAIL")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_returns_error_when_display_refused_and_releases_flag(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to display temporary gif", result["message"])
        mock_thread_cls.assert_not_called()
        self.assertFalse(cube_module._TEMP_GIF_RUNNING)


class RestorePreviousGifTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_running = cube_module._TEMP_GIF_RUNNING
        cube_module._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        cube_module._TEMP_GIF_RUNNING = self._original_running

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.time.sleep")
    def test_sleeps_then_restores_previous_gif(self, mock_sleep: Mock, mock_set: Mock) -> None:
        cube_module._TEMP_GIF_RUNNING = True

        _restore_previous_gif("test.gif", 7)

        mock_sleep.assert_called_once_with(7)
        mock_set.assert_called_once_with("test.gif")
        self.assertFalse(cube_module._TEMP_GIF_RUNNING)

    @patch("server.display.cube._set_cube_gif")
    @patch("server.display.cube.time.sleep")
    def test_skips_restore_when_no_previous_gif(self, mock_sleep: Mock, mock_set: Mock) -> None:
        cube_module._TEMP_GIF_RUNNING = True

        _restore_previous_gif("", 3)

        mock_sleep.assert_called_once_with(3)
        mock_set.assert_not_called()
        self.assertFalse(cube_module._TEMP_GIF_RUNNING)

    @patch(
        "server.display.cube._set_cube_gif",
        side_effect=RuntimeError("connection refused"),
    )
    @patch("server.display.cube.time.sleep")
    def test_swallows_restore_errors_and_releases_flag(
        self, mock_sleep: Mock, mock_set: Mock
    ) -> None:
        cube_module._TEMP_GIF_RUNNING = True

        _restore_previous_gif("test.gif", 2)

        self.assertFalse(cube_module._TEMP_GIF_RUNNING)


class RandomModeInteractionFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._originals = (
            cube_module._RANDOM_MODE_RUNNING,
            cube_module._RANDOM_CURRENT_GIF,
            cube_module._RANDOM_IMAGE_MODE_RUNNING,
            cube_module._RANDOM_IMAGE_MODE_SUSPENDED,
            cube_module._RANDOM_CURRENT_IMAGE,
            cube_module._TEMP_GIF_RUNNING,
        )
        cube_module._RANDOM_MODE_RUNNING = False
        cube_module._RANDOM_CURRENT_GIF = None
        cube_module._RANDOM_IMAGE_MODE_RUNNING = False
        cube_module._RANDOM_IMAGE_MODE_SUSPENDED = False
        cube_module._RANDOM_CURRENT_IMAGE = None
        cube_module._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        (
            cube_module._RANDOM_MODE_RUNNING,
            cube_module._RANDOM_CURRENT_GIF,
            cube_module._RANDOM_IMAGE_MODE_RUNNING,
            cube_module._RANDOM_IMAGE_MODE_SUSPENDED,
            cube_module._RANDOM_CURRENT_IMAGE,
            cube_module._TEMP_GIF_RUNNING,
        ) = self._originals


class SetCubeGifStopsRandomModeTests(RandomModeInteractionFixture):
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_stops_running_random_mode_and_reports_it(
        self, mock_gifs: Mock, mock_set: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._RANDOM_CURRENT_GIF = "gifx.gif"

        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random gif mode stopped.", result["message"])
        self.assertFalse(cube_module._RANDOM_MODE_RUNNING)
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_keeps_message_unchanged_when_random_not_running(
        self, mock_gifs: Mock, mock_set: Mock
    ) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertNotIn("Random gif mode stopped", result["message"])

    @patch("server.display.cube._set_cube_gif")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_does_not_stop_random_mode_when_validation_fails(
        self, mock_gifs: Mock, mock_set: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True

        result = set_cube_gif("unknown.gif")

        self.assertEqual(result["status"], "error")
        self.assertTrue(cube_module._RANDOM_MODE_RUNNING)
        mock_set.assert_not_called()

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_stops_running_random_image_mode_and_reports_it(
        self, mock_gifs: Mock, mock_set: Mock
    ) -> None:
        cube_module._RANDOM_IMAGE_MODE_RUNNING = True
        cube_module._RANDOM_CURRENT_IMAGE = "imagex.jpg"

        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random image mode stopped.", result["message"])
        self.assertFalse(cube_module._RANDOM_IMAGE_MODE_RUNNING)
        self.assertFalse(cube_module._RANDOM_IMAGE_MODE_SUSPENDED)
        mock_set.assert_called_once_with("gif1.gif")


class ShowTemporaryGifSuspendsRandomModeTests(RandomModeInteractionFixture):
    def _encoded(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/random.gif")
    def test_suspends_running_random_mode_before_showing_tmp(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._RANDOM_CURRENT_GIF = "gifx.gif"

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random gif mode paused (it will resume automatically).", result["message"])
        self.assertTrue(cube_module._RANDOM_MODE_RUNNING)
        self.assertTrue(cube_module._RANDOM_MODE_SUSPENDED)
        # The previous gif read after suspending is the random.gif upload and
        # the restore job will resume the random mode afterwards.
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("random.gif", 5, True, False),
            daemon=True,
        )

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_no_paused_note_when_random_not_running(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertNotIn("Random gif mode paused", result["message"])
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)

    @patch("server.display.cube.upload_cube_image")
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/random.gif")
    def test_resumes_random_mode_when_upload_fails(
        self, mock_current: Mock, mock_upload: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._suspend_random_mode()
        mock_upload.return_value = {"status": "error", "message": "boom"}

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertTrue(cube_module._RANDOM_MODE_RUNNING)
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)

    @patch(
        "server.display.cube._fetch_cube_current_gif",
        side_effect=RuntimeError("timeout"),
    )
    def test_resumes_random_mode_when_current_gif_read_fails(self, mock_current: Mock) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._suspend_random_mode()

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/random.jpg")
    def test_suspends_running_image_mode_before_showing_tmp(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        cube_module._RANDOM_IMAGE_MODE_RUNNING = True
        cube_module._RANDOM_CURRENT_IMAGE = "imagex.jpg"

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random image mode paused (it will resume automatically).", result["message"])
        self.assertNotIn("Random gif mode paused", result["message"])
        self.assertTrue(cube_module._RANDOM_IMAGE_MODE_RUNNING)
        self.assertTrue(cube_module._RANDOM_IMAGE_MODE_SUSPENDED)
        # The previous gif read after suspending is the random.jpg upload and
        # the restore job will resume the random image mode afterwards.
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("random.jpg", 5, False, True),
            daemon=True,
        )

    @patch("server.display.cube.upload_cube_image")
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/random.jpg")
    def test_resumes_image_mode_when_upload_fails(
        self, mock_current: Mock, mock_upload: Mock
    ) -> None:
        cube_module._RANDOM_IMAGE_MODE_RUNNING = True
        cube_module._suspend_image_mode()
        mock_upload.return_value = {"status": "error", "message": "boom"}

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertTrue(cube_module._RANDOM_IMAGE_MODE_RUNNING)
        self.assertFalse(cube_module._RANDOM_IMAGE_MODE_SUSPENDED)


class RestorePreviousGifResumesRandomTests(RandomModeInteractionFixture):
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.time.sleep")
    def test_resume_random_true_clears_suspension_after_restore(
        self, mock_sleep: Mock, mock_set: Mock
    ) -> None:
        cube_module._TEMP_GIF_RUNNING = True
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._suspend_random_mode()

        cube_module._restore_previous_gif("random.gif", 3, resume_random=True)

        mock_sleep.assert_called_once_with(3)
        mock_set.assert_called_once_with("random.gif")
        self.assertFalse(cube_module._TEMP_GIF_RUNNING)
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)
        self.assertTrue(cube_module._RANDOM_MODE_RUNNING)

    @patch("server.display.cube._set_cube_gif")
    @patch("server.display.cube.time.sleep")
    def test_resume_random_false_leaves_state_alone(
        self, mock_sleep: Mock, mock_set: Mock
    ) -> None:
        cube_module._TEMP_GIF_RUNNING = True

        cube_module._restore_previous_gif("test.gif", 2)

        self.assertFalse(cube_module._TEMP_GIF_RUNNING)
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)
        self.assertFalse(cube_module._RANDOM_MODE_RUNNING)

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.time.sleep")
    def test_resume_image_true_clears_image_suspension_after_restore(
        self, mock_sleep: Mock, mock_set: Mock
    ) -> None:
        cube_module._TEMP_GIF_RUNNING = True
        cube_module._RANDOM_IMAGE_MODE_RUNNING = True
        cube_module._suspend_image_mode()

        cube_module._restore_previous_gif("random.jpg", 3, resume_image=True)

        mock_sleep.assert_called_once_with(3)
        mock_set.assert_called_once_with("random.jpg")
        self.assertFalse(cube_module._TEMP_GIF_RUNNING)
        self.assertFalse(cube_module._RANDOM_IMAGE_MODE_SUSPENDED)
        self.assertTrue(cube_module._RANDOM_IMAGE_MODE_RUNNING)


if __name__ == "__main__":
    unittest.main()
