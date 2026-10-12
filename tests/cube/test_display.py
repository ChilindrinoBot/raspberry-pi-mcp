import unittest
from unittest.mock import Mock, call, patch

from server.display import cube as cube_module
from server.display.cube import (
    set_cube_gif,
    get_cube_brightness,
    get_cube_current_gif,
    set_cube_brightness,
    turn_cube_display_off,
    turn_cube_display_on,
    BRIGHTNESS_DEFAULT,
)


class SetCubeGifTests(unittest.TestCase):
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif", "image1.jpg"])
    def test_success_when_gif_exists(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube gif set to: gif1.gif", result["message"])
        self.assertIn("Device response: OK", result["message"])
        mock_gifs.assert_called_once()
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif", "image1.jpg"])
    def test_strips_leading_slash_before_validating(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("/gif1.gif")

        self.assertEqual(result["status"], "success")
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube.http._set_cube_gif")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif", "image1.jpg"])
    def test_rejects_gif_not_in_list(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("unknown.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Gif not found on Cube", result["message"])
        self.assertIn("unknown.gif", result["message"])
        mock_gifs.assert_called_once()
        mock_set.assert_not_called()

    @patch("server.display.cube.http._set_cube_gif", return_value="FAIL")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_rejects_cube_failure_response(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to set gif", result["message"])
        self.assertIn("FAIL", result["message"])
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube.http._set_cube_gif", return_value="")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_success_when_cube_responds_empty(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Cube gif set to: gif1.gif")

    @patch("server.display.cube.http._set_cube_gif", side_effect=RuntimeError("connection refused"))
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_returns_error_when_set_fails(self, mock_gifs: Mock, mock_set: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to set gif on Cube", result["message"])

    @patch("server.display.cube.http._fetch_cube_gifs", side_effect=RuntimeError("timeout"))
    def test_returns_error_when_verification_fails(self, mock_gifs: Mock) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to verify gif availability", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])

    def test_returns_error_when_gif_empty(self) -> None:
        with patch("server.display.cube.http._fetch_cube_gifs") as mock_gifs:
            result = set_cube_gif("  ")

        self.assertEqual(result["status"], "error")
        self.assertIn("Gif name is required", result["message"])
        mock_gifs.assert_not_called()


class GetCubeBrightnessTests(unittest.TestCase):
    @patch("server.display.cube.http._fetch_cube_brightness", return_value=75)
    def test_returns_current_brightness(self, mock_fetch: Mock) -> None:
        result = get_cube_brightness()

        self.assertEqual(result, "Current Cube brightness: 75")
        mock_fetch.assert_called_once()

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = get_cube_brightness()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube.http._fetch_cube_brightness", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = get_cube_brightness()

        self.assertIn("Failed to fetch brightness from Cube", result)
        self.assertIn("timeout", result)
        mock_fetch.assert_called_once()


class GetCubeCurrentGifTests(unittest.TestCase):
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_returns_current_gif_without_image_prefix(self, mock_fetch: Mock) -> None:
        result = get_cube_current_gif()

        self.assertEqual(result, "Current Cube gif: test.gif")
        mock_fetch.assert_called_once()

    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/other/tmp.gif")
    def test_keeps_paths_outside_image_dir(self, mock_fetch: Mock) -> None:
        result = get_cube_current_gif()

        self.assertEqual(result, "Current Cube gif: other/tmp.gif")

    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="")
    def test_returns_no_gif_when_empty(self, mock_fetch: Mock) -> None:
        result = get_cube_current_gif()

        self.assertEqual(result, "No gif is currently set on the Cube.")

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = get_cube_current_gif()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube.http._fetch_cube_current_gif", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = get_cube_current_gif()

        self.assertIn("Failed to fetch current gif from Cube", result)
        self.assertIn("timeout", result)
        mock_fetch.assert_called_once()


class SetCubeBrightnessTests(unittest.TestCase):
    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_success_with_device_response(self, mock_set: Mock) -> None:
        result = set_cube_brightness(75)

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 75", result["message"])
        self.assertIn("Device response: OK", result["message"])
        mock_set.assert_called_once_with(75)

    @patch("server.display.cube.http._set_cube_brightness", return_value="")
    def test_success_when_cube_responds_empty(self, mock_set: Mock) -> None:
        result = set_cube_brightness(30)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Cube brightness set to: 30")

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_defaults_to_50_when_no_level_given(self, mock_set: Mock) -> None:
        result = set_cube_brightness()

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 50", result["message"])
        mock_set.assert_called_once_with(BRIGHTNESS_DEFAULT)
        self.assertEqual(BRIGHTNESS_DEFAULT, 50)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_clamps_level_below_zero_to_zero(self, mock_set: Mock) -> None:
        result = set_cube_brightness(-5)

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 0", result["message"])
        mock_set.assert_called_once_with(0)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_clamps_level_above_hundred_to_hundred(self, mock_set: Mock) -> None:
        result = set_cube_brightness(150)

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube brightness set to: 100", result["message"])
        mock_set.assert_called_once_with(100)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_accepts_boundary_levels(self, mock_set: Mock) -> None:
        result_min = set_cube_brightness(0)
        result_max = set_cube_brightness(100)

        self.assertEqual(result_min["status"], "success")
        self.assertEqual(result_max["status"], "success")
        mock_set.assert_has_calls([call(0), call(100)])

    @patch("server.display.cube.http._set_cube_brightness", return_value="FAIL")
    def test_rejects_cube_failure_response(self, mock_set: Mock) -> None:
        result = set_cube_brightness(20)

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to set brightness", result["message"])
        self.assertIn("FAIL", result["message"])
        mock_set.assert_called_once_with(20)

    @patch("server.display.cube.http._set_cube_brightness", side_effect=RuntimeError("connection refused"))
    def test_returns_error_when_set_fails(self, mock_set: Mock) -> None:
        result = set_cube_brightness(60)

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to set brightness on Cube", result["message"])
        self.assertIn("connection refused", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = set_cube_brightness(40)

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])


class TurnCubeDisplayOffTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = cube_module.state._REMEMBERED_BRIGHTNESS
        cube_module.state._REMEMBERED_BRIGHTNESS = None

    def tearDown(self) -> None:
        cube_module.state._REMEMBERED_BRIGHTNESS = self._original

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_brightness", return_value=30)
    def test_remembers_brightness_before_turning_off(self, mock_fetch: Mock, mock_set: Mock) -> None:
        result = turn_cube_display_off()

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube display turned off", result["message"])
        self.assertIn("restored to 30", result["message"])
        mock_set.assert_called_once_with(0)
        self.assertEqual(cube_module.state._REMEMBERED_BRIGHTNESS, 30)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_brightness", side_effect=RuntimeError("timeout"))
    def test_falls_back_to_remembered_value_when_device_query_fails(self, mock_fetch: Mock, mock_set: Mock) -> None:
        cube_module.state._REMEMBERED_BRIGHTNESS = 75

        result = turn_cube_display_off()

        self.assertEqual(result["status"], "success")
        self.assertIn("restored to 75", result["message"])
        mock_set.assert_called_once_with(0)
        self.assertEqual(cube_module.state._REMEMBERED_BRIGHTNESS, 75)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_brightness", side_effect=RuntimeError("timeout"))
    def test_falls_back_to_default_when_nothing_remembered(self, mock_fetch: Mock, mock_set: Mock) -> None:
        result = turn_cube_display_off()

        self.assertEqual(result["status"], "success")
        self.assertIn(f"restored to {BRIGHTNESS_DEFAULT}", result["message"])
        mock_set.assert_called_once_with(0)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_brightness", return_value=0)
    def test_does_not_overwrite_memory_with_zero_on_double_off(self, mock_fetch: Mock, mock_set: Mock) -> None:
        cube_module.state._REMEMBERED_BRIGHTNESS = 30

        result = turn_cube_display_off()

        self.assertEqual(result["status"], "success")
        self.assertIn("restored to 30", result["message"])
        self.assertEqual(cube_module.state._REMEMBERED_BRIGHTNESS, 30)

    @patch("server.display.cube.http._set_cube_brightness", return_value="FAIL")
    @patch("server.display.cube.http._fetch_cube_brightness", return_value=30)
    def test_rejects_cube_failure_response(self, mock_fetch: Mock, mock_set: Mock) -> None:
        result = turn_cube_display_off()

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to turn off display", result["message"])
        mock_set.assert_called_once_with(0)

    @patch("server.display.cube.http._set_cube_brightness", side_effect=RuntimeError("connection refused"))
    @patch("server.display.cube.http._fetch_cube_brightness", return_value=30)
    def test_returns_error_when_set_fails(self, mock_fetch: Mock, mock_set: Mock) -> None:
        result = turn_cube_display_off()

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to turn off Cube display", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = turn_cube_display_off()

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])


class TurnCubeDisplayOnTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = cube_module.state._REMEMBERED_BRIGHTNESS
        cube_module.state._REMEMBERED_BRIGHTNESS = None

    def tearDown(self) -> None:
        cube_module.state._REMEMBERED_BRIGHTNESS = self._original

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_restores_remembered_brightness(self, mock_set: Mock) -> None:
        cube_module.state._REMEMBERED_BRIGHTNESS = 75

        result = turn_cube_display_on()

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube display turned on at brightness 75", result["message"])
        mock_set.assert_called_once_with(75)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_defaults_to_50_when_nothing_remembered(self, mock_set: Mock) -> None:
        result = turn_cube_display_on()

        self.assertEqual(result["status"], "success")
        self.assertIn(f"turned on at brightness {BRIGHTNESS_DEFAULT}", result["message"])
        mock_set.assert_called_once_with(BRIGHTNESS_DEFAULT)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_defaults_to_50_when_remembered_is_zero(self, mock_set: Mock) -> None:
        cube_module.state._REMEMBERED_BRIGHTNESS = 0

        result = turn_cube_display_on()

        self.assertEqual(result["status"], "success")
        mock_set.assert_called_once_with(BRIGHTNESS_DEFAULT)

    @patch("server.display.cube.http._set_cube_brightness", return_value="OK")
    def test_clamps_out_of_range_remembered_value(self, mock_set: Mock) -> None:
        cube_module.state._REMEMBERED_BRIGHTNESS = 150

        result = turn_cube_display_on()

        self.assertEqual(result["status"], "success")
        self.assertIn("turned on at brightness 100", result["message"])
        mock_set.assert_called_once_with(100)

    @patch("server.display.cube.http._set_cube_brightness", return_value="FAIL")
    def test_rejects_cube_failure_response(self, mock_set: Mock) -> None:
        cube_module.state._REMEMBERED_BRIGHTNESS = 40

        result = turn_cube_display_on()

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to turn on display", result["message"])
        mock_set.assert_called_once_with(40)

    @patch("server.display.cube.http._set_cube_brightness", side_effect=RuntimeError("connection refused"))
    def test_returns_error_when_set_fails(self, mock_set: Mock) -> None:
        result = turn_cube_display_on()

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to turn on Cube display", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = turn_cube_display_on()

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])


class RandomModeInteractionFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._originals = (
            cube_module.state._RANDOM_MODE_RUNNING,
            cube_module.state._RANDOM_CURRENT_GIF,
            cube_module.state._RANDOM_IMAGE_MODE_RUNNING,
            cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED,
            cube_module.state._RANDOM_CURRENT_IMAGE,
            cube_module.state._TEMP_GIF_RUNNING,
        )
        cube_module.state._RANDOM_MODE_RUNNING = False
        cube_module.state._RANDOM_CURRENT_GIF = None
        cube_module.state._RANDOM_IMAGE_MODE_RUNNING = False
        cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED = False
        cube_module.state._RANDOM_CURRENT_IMAGE = None
        cube_module.state._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        (
            cube_module.state._RANDOM_MODE_RUNNING,
            cube_module.state._RANDOM_CURRENT_GIF,
            cube_module.state._RANDOM_IMAGE_MODE_RUNNING,
            cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED,
            cube_module.state._RANDOM_CURRENT_IMAGE,
            cube_module.state._TEMP_GIF_RUNNING,
        ) = self._originals


class SetCubeGifStopsRandomModeTests(RandomModeInteractionFixture):
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_stops_running_random_mode_and_reports_it(
        self, mock_gifs: Mock, mock_set: Mock
    ) -> None:
        cube_module.state._RANDOM_MODE_RUNNING = True
        cube_module.state._RANDOM_CURRENT_GIF = "gifx.gif"

        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random gif mode stopped.", result["message"])
        self.assertFalse(cube_module.state._RANDOM_MODE_RUNNING)
        mock_set.assert_called_once_with("gif1.gif")

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_keeps_message_unchanged_when_random_not_running(
        self, mock_gifs: Mock, mock_set: Mock
    ) -> None:
        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertNotIn("Random gif mode stopped", result["message"])

    @patch("server.display.cube.http._set_cube_gif")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_does_not_stop_random_mode_when_validation_fails(
        self, mock_gifs: Mock, mock_set: Mock
    ) -> None:
        cube_module.state._RANDOM_MODE_RUNNING = True

        result = set_cube_gif("unknown.gif")

        self.assertEqual(result["status"], "error")
        self.assertTrue(cube_module.state._RANDOM_MODE_RUNNING)
        mock_set.assert_not_called()

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["gif1.gif"])
    def test_stops_running_random_image_mode_and_reports_it(
        self, mock_gifs: Mock, mock_set: Mock
    ) -> None:
        cube_module.state._RANDOM_IMAGE_MODE_RUNNING = True
        cube_module.state._RANDOM_CURRENT_IMAGE = "imagex.jpg"

        result = set_cube_gif("gif1.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random image mode stopped.", result["message"])
        self.assertFalse(cube_module.state._RANDOM_IMAGE_MODE_RUNNING)
        self.assertFalse(cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED)
        mock_set.assert_called_once_with("gif1.gif")


if __name__ == "__main__":
    unittest.main()
