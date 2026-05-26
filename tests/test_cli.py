import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tears_kiosk.cli import main
from tears_kiosk.config import KioskConfig, save_config


class CliTests(unittest.TestCase):
    @patch("tears_kiosk.cli.config_path")
    @patch("tears_kiosk.cli.launch_agent_path")
    @patch("tears_kiosk.cli.load_config", return_value=None)
    def test_status_without_config(self, load_config, launch_agent_path, config_path):
        with patch("sys.stdout", new=io.StringIO()) as stdout:
            result = main(["status"])

        self.assertEqual(result, 0)
        self.assertIn("nicht eingerichtet", stdout.getvalue())

    @patch("tears_kiosk.cli.config_path", return_value=Path("/tmp/config.json"))
    @patch("tears_kiosk.cli.launch_agent_path", return_value=Path("/tmp/agent.plist"))
    @patch(
        "tears_kiosk.cli.load_config",
        return_value=KioskConfig(url="https://example.com"),
    )
    def test_status_with_config(self, load_config, launch_agent_path, config_path):
        with patch("sys.stdout", new=io.StringIO()) as stdout:
            result = main(["status"])

        self.assertEqual(result, 0)
        self.assertIn("Website: https://example.com", stdout.getvalue())

    @patch("tears_kiosk.cli.remove_launch_agent", return_value=True)
    @patch("tears_kiosk.cli.delete_config", return_value=True)
    def test_disable(self, delete_config, remove_launch_agent):
        with patch("sys.stdout", new=io.StringIO()) as stdout:
            result = main(["disable"])

        self.assertEqual(result, 0)
        self.assertIn("deaktiviert", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

