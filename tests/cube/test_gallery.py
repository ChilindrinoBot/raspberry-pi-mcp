import base64
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from server.display import cube as cube_module
from server.display.cube import (
    save_image_in_gallery,
    list_gallery_images,
    list_gallery_gifs,
    show_gallery_image,
    show_gallery_gif,
)


def _image_bytes(fmt: str, width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format=fmt)
    return buffer.getvalue()


class SaveImageInGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = Path(tempfile.mkdtemp())
        patcher = patch.object(cube_module.config, "RANDOM_IMAGE_DIR", self._tmpdir)
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

        with patch.object(cube_module.config, "RANDOM_IMAGE_DIR", nested):
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

    @patch("server.display.cube.images._decode_image", return_value=b"")
    def test_rejects_empty_payload(self, mock_decode: Mock) -> None:
        result = save_image_in_gallery("token", "empty.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image is empty: empty.png", result["message"])

    @patch(
        "server.display.cube.images._fit_image_to_jpg",
        side_effect=RuntimeError("cannot identify image file"),
    )
    def test_returns_error_when_processing_fails(self, mock_fit: Mock) -> None:
        result = save_image_in_gallery(self._encoded(b"data"), "broken.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to process image broken.png", result["message"])
        mock_fit.assert_called_once()

    @patch("server.display.cube.images._fit_image_to_jpg", return_value=b"not-a-jpeg")
    def test_verifies_processed_output_is_jpeg(self, mock_fit: Mock) -> None:
        result = save_image_in_gallery(self._encoded(b"data"), "photo.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Processed image is not a valid JPEG", result["message"])
        self.assertFalse((self._tmpdir / "photo.jpg").exists())

    @patch("server.display.cube.images._fit_image_to_jpg", return_value=_image_bytes("JPEG", 100, 100))
    def test_verifies_processed_output_dimensions(self, mock_fit: Mock) -> None:
        result = save_image_in_gallery(self._encoded(b"data"), "photo.png")

        self.assertEqual(result["status"], "error")
        self.assertIn("Processed image must be 240x240", result["message"])
        self.assertFalse((self._tmpdir / "photo.jpg").exists())


class GalleryResourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._images_dir = Path(tempfile.mkdtemp())
        self._gifs_dir = Path(tempfile.mkdtemp())
        image_patcher = patch.object(cube_module.config, "RANDOM_IMAGE_DIR", self._images_dir)
        gif_patcher = patch.object(cube_module.config, "RANDOM_GIF_DIR", self._gifs_dir)
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

        self.assertEqual(
            result, "Available gallery images:\na.jpeg (0.0 KB)\nb.jpg (0.0 KB)"
        )

    def test_ignores_non_image_files_in_images_gallery(self) -> None:
        (self._images_dir / "photo.jpg").write_bytes(b"jpg")
        (self._images_dir / "notes.txt").write_bytes(b"text")
        (self._images_dir / "clip.gif").write_bytes(b"gif")

        result = list_gallery_images()

        self.assertEqual(result, "Available gallery images:\nphoto.jpg (0.0 KB)")

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

        self.assertEqual(result, "Available gallery gifs:\na.gif (0.0 KB)\nb.gif (0.0 KB)")

    def test_ignores_non_gif_files_in_gifs_gallery(self) -> None:
        (self._gifs_dir / "anim.gif").write_bytes(b"gif")
        (self._gifs_dir / "photo.jpg").write_bytes(b"jpg")
        (self._gifs_dir / "notes.txt").write_bytes(b"text")

        result = list_gallery_gifs()

        self.assertEqual(result, "Available gallery gifs:\nanim.gif (0.0 KB)")

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
        patcher = patch.object(cube_module.config, "RANDOM_IMAGE_DIR", self._tmpdir)
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

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube.state._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube.http._fetch_cube_gifs")
    @patch("server.display.cube.http._upload_cube_image")
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

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube.state._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube.http._fetch_cube_gifs")
    @patch("server.display.cube.http._upload_cube_image")
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

    @patch("server.display.cube.http._upload_cube_image")
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024, 3 * 1024 * 1024))
    def test_rejects_when_free_space_reserve_would_break(
        self, mock_space: Mock, mock_upload: Mock
    ) -> None:
        self._write_jpeg("photo.jpg")

        result = show_gallery_image("photo.jpg")

        self.assertEqual(result["status"], "error")
        self.assertIn("Not enough space on Cube", result["message"])
        self.assertIn("50 KB free reserve", result["message"])
        mock_upload.assert_not_called()

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state._stop_image_mode", return_value=(True, "old.jpg"))
    @patch("server.display.cube.state._stop_random_mode", return_value=(True, "old.gif"))
    @patch("server.display.cube.http._fetch_cube_gifs")
    @patch("server.display.cube.http._upload_cube_image")
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

    @patch("server.display.cube.state._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube.state._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=[])
    @patch("server.display.cube.http._upload_cube_image")
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

    @patch("server.display.cube.http._set_cube_gif", return_value="FAIL busy")
    @patch("server.display.cube.state._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube.state._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube.http._fetch_cube_gifs")
    @patch("server.display.cube.http._upload_cube_image")
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


class ShowGalleryGifTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = Path(tempfile.mkdtemp())
        dir_patcher = patch.object(cube_module.config, "RANDOM_GIF_DIR", self._tmpdir)
        dir_patcher.start()
        self.addCleanup(dir_patcher.stop)

        self._original_running = cube_module.state._TEMP_GIF_RUNNING
        cube_module.state._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        import shutil

        cube_module.state._TEMP_GIF_RUNNING = self._original_running
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_gif(self, name: str, width: int = 240, height: int = 240) -> Path:
        path = self._tmpdir / name
        path.write_bytes(_image_bytes("GIF", width, height))
        return path

    def test_requires_a_name(self) -> None:
        for empty in ("", "   "):
            result = show_gallery_gif(empty)

            self.assertEqual(result["status"], "error")
            self.assertIn("Gif name is required", result["message"])

    def test_reports_missing_gif_with_available_list(self) -> None:
        self._write_gif("known.gif")

        result = show_gallery_gif("unknown")

        self.assertEqual(result["status"], "error")
        self.assertIn("Gif not found in", result["message"])
        self.assertIn("Available: known.gif", result["message"])

    def test_rejects_while_temporary_gif_being_shown(self) -> None:
        self._write_gif("anim.gif")
        cube_module.state._TEMP_GIF_RUNNING = True

        result = show_gallery_gif("anim")

        self.assertEqual(result["status"], "error")
        self.assertIn("temporary gif is already being shown", result["message"])

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube.state._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube.http._fetch_cube_gifs")
    @patch("server.display.cube.http._upload_cube_image")
    def test_shows_240_gif_as_tmp(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
        mock_set: Mock,
    ) -> None:
        self._write_gif("anim.gif")
        mock_gifs.return_value = ["tmp.gif"]

        result = show_gallery_gif("anim")

        self.assertEqual(result["status"], "success")
        self.assertIn("Cube gif set to: tmp.gif (from anim.gif; no timer; it stays until changed)", result["message"])
        upload_name, payload = mock_upload.call_args.args
        self.assertEqual(upload_name, "tmp.gif")
        with Image.open(BytesIO(payload)) as img:
            self.assertEqual(img.format, "GIF")
            self.assertEqual(img.size, (240, 240))
        mock_set.assert_called_once_with("tmp.gif")

    def test_rejects_non_240_gif(self) -> None:
        self._write_gif("big.gif", width=300, height=300)

        result = show_gallery_gif("big.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Gif must be 240x240 (got 300x300)", result["message"])

    def test_rejects_non_gif_file(self) -> None:
        (self._tmpdir / "fake.gif").write_bytes(_image_bytes("JPEG", 240, 240))

        result = show_gallery_gif("fake.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Not a valid GIF", result["message"])

    @patch("server.display.cube.http._upload_cube_image")
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024, 3 * 1024 * 1024))
    def test_rejects_when_free_space_reserve_would_break(
        self, mock_space: Mock, mock_upload: Mock
    ) -> None:
        self._write_gif("anim.gif")

        result = show_gallery_gif("anim.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Not enough space on Cube", result["message"])
        self.assertIn("50 KB free reserve", result["message"])
        mock_upload.assert_not_called()

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state._stop_image_mode", return_value=(True, "old.jpg"))
    @patch("server.display.cube.state._stop_random_mode", return_value=(True, "old.gif"))
    @patch("server.display.cube.http._fetch_cube_gifs")
    @patch("server.display.cube.http._upload_cube_image")
    def test_stops_running_random_modes(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
        mock_set: Mock,
    ) -> None:
        self._write_gif("anim.gif")
        mock_gifs.return_value = ["tmp.gif"]

        result = show_gallery_gif("anim")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random gif mode stopped", result["message"])
        self.assertIn("Random image mode stopped", result["message"])

    @patch("server.display.cube.state._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube.state._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube.http._fetch_cube_gifs", return_value=[])
    @patch("server.display.cube.http._upload_cube_image")
    def test_fails_when_upload_not_confirmed(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
    ) -> None:
        self._write_gif("anim.gif")

        result = show_gallery_gif("anim")

        self.assertEqual(result["status"], "error")
        self.assertIn("Upload could not be confirmed", result["message"])

    @patch("server.display.cube.http._set_cube_gif", return_value="FAIL busy")
    @patch("server.display.cube.state._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube.state._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube.http._fetch_cube_gifs")
    @patch("server.display.cube.http._upload_cube_image")
    def test_fails_when_cube_refuses(
        self,
        mock_upload: Mock,
        mock_gifs: Mock,
        mock_stop_random: Mock,
        mock_stop_image: Mock,
        mock_set: Mock,
    ) -> None:
        self._write_gif("anim.gif")
        mock_gifs.return_value = ["tmp.gif"]

        result = show_gallery_gif("anim")

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to set gif tmp.gif", result["message"])


if __name__ == "__main__":
    unittest.main()
