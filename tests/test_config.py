import json
import tempfile
import unittest
from pathlib import Path

from kiosk.config import (
    DEFAULT_EDGE_BLOCKER_PASSWORD_HASH,
    DEFAULT_EDGE_BLOCKER_PASSWORD_SALT,
    DEFAULT_MIN_IDLE_SECONDS,
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    DEFAULT_STARTUP_SCRIPT_DELAY_SECONDS,
    KioskConfig,
    create_edge_blocker_password,
    hash_edge_blocker_password,
    load_config,
    normalize_url,
    save_config,
)


class ConfigTests(unittest.TestCase):
    def test_normalize_url_keeps_http_and_https(self):
        self.assertEqual(normalize_url("http://example.com"), "http://example.com")
        self.assertEqual(normalize_url("https://example.com"), "https://example.com")

    def test_normalize_url_adds_https(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com")

    def test_normalize_url_rejects_empty_value(self):
        with self.assertRaises(ValueError):
            normalize_url(" ")

    def test_load_config_applies_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"url": "example.com"}), encoding="utf-8")

            config = load_config(path)

        self.assertEqual(config.url, "https://example.com")
        self.assertTrue(config.auto_refresh_enabled)
        self.assertEqual(config.refresh_interval_seconds, DEFAULT_REFRESH_INTERVAL_SECONDS)
        self.assertEqual(config.min_idle_seconds, DEFAULT_MIN_IDLE_SECONDS)
        self.assertEqual(config.startup_script_path, "")
        self.assertEqual(config.startup_script_delay_seconds, DEFAULT_STARTUP_SCRIPT_DELAY_SECONDS)
        self.assertEqual(
            config.edge_blocker_password_salt, DEFAULT_EDGE_BLOCKER_PASSWORD_SALT
        )
        self.assertEqual(
            config.edge_blocker_password_hash, DEFAULT_EDGE_BLOCKER_PASSWORD_HASH
        )

    def test_default_edge_blocker_password_is_951951(self):
        self.assertEqual(
            hash_edge_blocker_password("951951", DEFAULT_EDGE_BLOCKER_PASSWORD_SALT),
            DEFAULT_EDGE_BLOCKER_PASSWORD_HASH,
        )

    def test_create_edge_blocker_password_uses_random_salt(self):
        first_salt, first_hash = create_edge_blocker_password("secret")
        second_salt, second_hash = create_edge_blocker_password("secret")

        self.assertNotEqual(first_salt, second_salt)
        self.assertNotEqual(first_hash, second_hash)
        self.assertEqual(first_hash, hash_edge_blocker_password("secret", first_salt))

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            original = KioskConfig(
                url="https://example.com",
                auto_refresh_enabled=False,
                refresh_interval_seconds=42,
                min_idle_seconds=9,
                startup_script_path="/Users/simon/start.py",
                startup_script_delay_seconds=25,
                edge_blocker_password_salt="custom-salt",
                edge_blocker_password_hash="custom-hash",
            )
            save_config(original, path)
            loaded = load_config(path)

        self.assertEqual(loaded, original)


if __name__ == "__main__":
    unittest.main()
