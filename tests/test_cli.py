import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tears_kiosk.cli import kiosk_command, main
from tears_kiosk.config import KioskConfig, save_config
from tears_kiosk.hammerspoon import HammerspoonStatus


DEFAULT_HAMMERSPOON_STATUS = HammerspoonStatus(
    installed=False,
    config_exists=False,
    backup_count=0,
)


class CliTests(unittest.TestCase):
    @patch("tears_kiosk.cli.config_path")
    @patch("tears_kiosk.cli.launch_agent_path")
    @patch("tears_kiosk.cli.get_hammerspoon_status", return_value=DEFAULT_HAMMERSPOON_STATUS)
    @patch("tears_kiosk.cli.load_config", return_value=None)
    def test_status_without_config(
        self,
        load_config,
        get_hammerspoon_status,
        launch_agent_path,
        config_path,
    ):
        with patch("sys.stdout", new=io.StringIO()) as stdout:
            result = main(["status"])

        self.assertEqual(result, 0)
        self.assertIn("nicht eingerichtet", stdout.getvalue())
        self.assertIn("Hammerspoon: nicht installiert", stdout.getvalue())

    @patch("tears_kiosk.cli.config_path", return_value=Path("/tmp/config.json"))
    @patch("tears_kiosk.cli.launch_agent_path", return_value=Path("/tmp/agent.plist"))
    @patch(
        "tears_kiosk.cli.get_hammerspoon_status",
        return_value=HammerspoonStatus(installed=True, config_exists=True, backup_count=1),
    )
    @patch(
        "tears_kiosk.cli.load_config",
        return_value=KioskConfig(url="https://example.com"),
    )
    def test_status_with_config(
        self,
        load_config,
        get_hammerspoon_status,
        launch_agent_path,
        config_path,
    ):
        with patch("sys.stdout", new=io.StringIO()) as stdout:
            result = main(["status"])

        self.assertEqual(result, 0)
        self.assertIn("Website: https://example.com", stdout.getvalue())
        self.assertIn("Hammerspoon: installiert", stdout.getvalue())
        self.assertIn("Hammerspoon-Config-Backups: 1", stdout.getvalue())

    @patch("tears_kiosk.cli.disable_hammerspoon_autolaunch_and_quit")
    @patch("tears_kiosk.cli.remove_launch_agent", return_value=True)
    @patch("tears_kiosk.cli.delete_config", return_value=True)
    def test_disable(self, delete_config, remove_launch_agent, disable_hammerspoon):
        with patch("sys.stdout", new=io.StringIO()) as stdout:
            result = main(["disable"])

        self.assertEqual(result, 0)
        self.assertIn("deaktiviert", stdout.getvalue())
        disable_hammerspoon.assert_called_once()

    @patch("tears_kiosk.cli.load_launch_agent")
    @patch("tears_kiosk.cli.write_launch_agent", return_value=Path("/tmp/agent.plist"))
    @patch("tears_kiosk.cli.save_config")
    @patch("tears_kiosk.cli.prompt_int", side_effect=[1800, 90])
    @patch("tears_kiosk.cli.prompt_bool", return_value=True)
    @patch("tears_kiosk.cli.prompt_url", return_value="https://example.com")
    @patch("tears_kiosk.cli.ensure_hammerspoon")
    @patch("tears_kiosk.cli.ensure_chrome")
    def test_configure_runs_chrome_and_hammerspoon_setup(
        self,
        ensure_chrome,
        ensure_hammerspoon,
        prompt_url,
        prompt_bool,
        prompt_int,
        save_config,
        write_launch_agent,
        load_launch_agent,
    ):
        from tears_kiosk.cli import configure

        with patch("sys.stdout", new=io.StringIO()):
            config = configure()

        self.assertEqual(config.url, "https://example.com")
        ensure_chrome.assert_called_once()
        ensure_hammerspoon.assert_called_once()

    @patch("tears_kiosk.cli.shutil.which", return_value="/usr/local/bin/kiosk")
    def test_kiosk_command_prefers_installed_console_script(self, which):
        command = kiosk_command()

        self.assertEqual(command.arguments, ["/usr/local/bin/kiosk"])
        self.assertIsNone(command.working_directory)

    @patch("tears_kiosk.cli.sys.executable", "/usr/bin/python3")
    @patch("tears_kiosk.cli.sys.argv", ["/repo/tears_kiosk/cli.py"])
    @patch("tears_kiosk.cli.shutil.which", return_value=None)
    def test_kiosk_command_uses_python_module_for_source_checkout(self, which):
        command = kiosk_command()

        self.assertEqual(command.arguments, ["/usr/bin/python3", "-m", "tears_kiosk.cli"])
        self.assertEqual(command.working_directory, Path("/repo"))


if __name__ == "__main__":
    unittest.main()
