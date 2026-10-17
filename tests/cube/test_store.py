import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from server.display import cube as cube_module


class StoreSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._patcher = patch(
            "server.display.cube.config.STATE_DB_FILE",
            Path(self._tmp.name) / "state.db",
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def test_round_trip_dict(self) -> None:
        value = {"theme": "dark", "volume": 8}

        cube_module.store.set_setting("ui_prefs", value)

        self.assertEqual(cube_module.store.get_setting("ui_prefs"), value)

    def test_round_trip_int(self) -> None:
        cube_module.store.set_setting("last_volume", 60)

        self.assertEqual(cube_module.store.get_setting("last_volume"), 60)

    def test_missing_key_returns_default(self) -> None:
        self.assertIsNone(cube_module.store.get_setting("nope"))
        self.assertEqual(cube_module.store.get_setting("nope", "fallback"), "fallback")

    def test_overwrite_replaces_value(self) -> None:
        cube_module.store.set_setting("k", 1)
        cube_module.store.set_setting("k", 2)

        self.assertEqual(cube_module.store.get_setting("k"), 2)

    def test_corrupt_value_returns_default(self) -> None:
        db = sqlite3.connect(str(cube_module.config.STATE_DB_FILE))
        with db:
            db.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT INTO kv (key, value) VALUES ('broken', 'not json{')")

        self.assertEqual(cube_module.store.get_setting("broken", "fallback"), "fallback")

    def test_delete_removes_key(self) -> None:
        cube_module.store.set_setting("temp", 1)
        cube_module.store.delete_setting("temp")

        self.assertIsNone(cube_module.store.get_setting("temp"))
        cube_module.store.delete_setting("temp")


class CubeConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._patcher = patch(
            "server.display.cube.config.STATE_DB_FILE",
            Path(self._tmp.name) / "state.db",
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def test_starts_empty(self) -> None:
        self.assertEqual(
            cube_module.store.get_cube_config(),
            {"schedule": None, "active_mode": None},
        )

    def test_update_merges_fields(self) -> None:
        cube_module.store.update_cube_config(
            schedule={"time1": "07:00", "time2": "23:00", "enabled": True}
        )
        cube_module.store.update_cube_config(
            active_mode={"kind": "random_gif", "seconds": 60}
        )

        self.assertEqual(
            cube_module.store.get_cube_config(),
            {
                "schedule": {"time1": "07:00", "time2": "23:00", "enabled": True},
                "active_mode": {"kind": "random_gif", "seconds": 60},
            },
        )

    def test_normalizes_rows_to_hours_only(self) -> None:
        cube_module.store.set_setting(
            "cube_config",
            {
                "schedule": {
                    "time1": "07:00",
                    "time2": "23:00",
                    "enabled": True,
                    "extra": "junk",
                },
                "stray_key": 70,
            },
        )

        config = cube_module.store.get_cube_config()

        self.assertEqual(
            config["schedule"], {"time1": "07:00", "time2": "23:00", "enabled": True}
        )
        # Second read is stable.
        self.assertEqual(cube_module.store.get_cube_config(), config)

    def test_ignores_stray_keys(self) -> None:
        cube_module.store.set_setting(
            "unrelated_key",
            {"time1": "07:00", "time2": "23:00", "enabled": True},
        )

        config = cube_module.store.get_cube_config()

        self.assertIsNone(config["schedule"])
        # Second read keeps the normalized row.
        self.assertEqual(cube_module.store.get_cube_config(), config)

    def test_ignores_non_dict_unified_row(self) -> None:
        cube_module.store.set_setting("cube_config", [1, 2, 3])

        self.assertEqual(
            cube_module.store.get_cube_config(),
            {"schedule": None, "active_mode": None},
        )


if __name__ == "__main__":
    unittest.main()
