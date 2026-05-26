import json
import tempfile
import unittest
from pathlib import Path

from mac_kiosk.config import (
    DEFAULT_MIN_IDLE_SECONDS,
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    KioskConfig,
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

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            original = KioskConfig(
                url="https://example.com",
                auto_refresh_enabled=False,
                refresh_interval_seconds=42,
                min_idle_seconds=9,
            )
            save_config(original, path)
            loaded = load_config(path)

        self.assertEqual(loaded, original)


if __name__ == "__main__":
    unittest.main()

