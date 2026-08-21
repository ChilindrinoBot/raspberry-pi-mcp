import unittest
from unittest.mock import Mock, call, patch

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


if __name__ == "__main__":
    unittest.main()
