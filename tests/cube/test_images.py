import base64
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

from PIL import Image

from server.display.cube import (
    _image_dimensions,
    _decode_image,
    _fit_image_to_jpg,
    _is_in_cube_filelist,
    _cube_free_space_rejection,
    UPLOAD_FREE_SPACE_BUFFER,
)


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


def _pixel_close(pixel, expected, tolerance: int = 30) -> bool:
    return all(abs(channel - target) <= tolerance for channel, target in zip(pixel[:3], expected))


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


class CubeFreeSpaceTests(unittest.TestCase):
    @patch("server.display.cube.http._fetch_cube_space", return_value=(200_000, 3_000_000))
    def test_returns_none_when_enough_room(self, mock_space: Mock) -> None:
        error = _cube_free_space_rejection(100_000)

        self.assertIsNone(error)
        mock_space.assert_called_once()

    @patch("server.display.cube.http._fetch_cube_space", return_value=(100_000, 3_000_000))
    def test_rejects_when_reserve_would_break(self, mock_space: Mock) -> None:
        size = 100_000 - UPLOAD_FREE_SPACE_BUFFER + 1

        error = _cube_free_space_rejection(size)

        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("Not enough space on Cube", error)
        self.assertIn(f"needs {size} bytes", error)
        self.assertIn("50 KB free reserve", error)
        self.assertIn("only 100000 bytes (97.7 KB) are free", error)

    @patch("server.display.cube.http._fetch_cube_space", side_effect=RuntimeError("timeout"))
    def test_returns_error_when_space_check_fails(self, mock_space: Mock) -> None:
        error = _cube_free_space_rejection(1000)

        assert error is not None
        self.assertIn("Failed to check free space on Cube", error)
        self.assertIn("timeout", error)


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


if __name__ == "__main__":
    unittest.main()
