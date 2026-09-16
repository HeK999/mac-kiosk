import io
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from kiosk.cli import configure, kiosk_command, main, prompt_startup_script
from kiosk.config import KioskConfig, save_config
from kiosk.hammerspoon import HammerspoonStatus


DEFAULT_HAMMERSPOON_STATUS = HammerspoonStatus(
    installed=False,
    config_exists=False,
    backup_count=0,
)


class CliTests(unittest.TestCase):
    @patch("kiosk.cli.config_path")
    @patch("kiosk.cli.launch_agent_path")
    @patch("kiosk.cli.get_hammerspoon_status", return_value=DEFAULT_HAMMERSPOON_STATUS)
    @patch("kiosk.cli.load_config", return_value=None)
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

    @patch("kiosk.cli.config_path", return_value=Path("/tmp/config.json"))
    @patch("kiosk.cli.launch_agent_path", return_value=Path("/tmp/agent.plist"))
    @patch(
        "kiosk.cli.get_hammerspoon_status",
        return_value=HammerspoonStatus(installed=True, config_exists=True, backup_count=1),
    )
    @patch(
        "kiosk.cli.load_config",
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

    @patch("kiosk.cli.disable_hammerspoon_autolaunch_and_quit")
    @patch("kiosk.cli.remove_launch_agent", return_value=True)
    @patch("kiosk.cli.delete_config", return_value=True)
    def test_disable(self, delete_config, remove_launch_agent, disable_hammerspoon):
        with patch("sys.stdout", new=io.StringIO()) as stdout:
            result = main(["disable"])

        self.assertEqual(result, 0)
        self.assertIn("deaktiviert", stdout.getvalue())
        disable_hammerspoon.assert_called_once()

    @patch("kiosk.cli.load_launch_agent")
    @patch("kiosk.cli.write_launch_agent", return_value=Path("/tmp/agent.plist"))
    @patch("kiosk.cli.save_config")
    @patch("kiosk.cli.prompt_int", side_effect=[1800, 90])
    @patch("kiosk.cli.prompt_bool", return_value=True)
    @patch("kiosk.cli.prompt_url", return_value="https://example.com")
    @patch("kiosk.cli.ensure_hammerspoon")
    @patch("kiosk.cli.ensure_chrome")
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
        from kiosk.cli import configure

        with patch("sys.stdout", new=io.StringIO()), patch("builtins.input", return_value=""):
            config = configure()

        self.assertEqual(config.url, "https://example.com")
        ensure_chrome.assert_called_once()
        ensure_hammerspoon.assert_called_once()

    def test_configure_optional_startup_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "start.py"
            script.touch()
            cases = [
                (None, ["example.com", "", "n"], "", 10),
                (None, ["example.com", str(script), "", "n"], str(script), 10),
                (None, ["example.com", str(script), "-1", "abc", "0", "n"], str(script), 0),
                (KioskConfig("https://example.com", startup_script_path=str(script),
                             startup_script_delay_seconds=23),
                 ["", "", "", "n"], str(script), 23),
                (KioskConfig("https://example.com", startup_script_path=str(script)),
                 ["", "-", "n"], "", 10),
            ]
            for existing, answers, expected_path, expected_delay in cases:
                with self.subTest(answers=answers), ExitStack() as stack:
                    for name in ("ensure_chrome", "ensure_hammerspoon", "save_config",
                                 "write_launch_agent", "load_launch_agent", "kiosk_command"):
                        stack.enter_context(patch(f"kiosk.cli.{name}"))
                    prompt = stack.enter_context(patch("builtins.input", side_effect=answers))
                    stack.enter_context(patch("sys.stdout", new=io.StringIO()))
                    config = configure(existing)
                    self.assertEqual(config.startup_script_path, expected_path)
                    self.assertEqual(config.startup_script_delay_seconds, expected_delay)
                    self.assertEqual(prompt.call_count, len(answers))

    def test_script_prompt_rejects_invalid_path_before_accepting(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "start.sh"
            script.touch()
            with patch("builtins.input", side_effect=["relative.sh", str(script)]) as prompt, \
                    patch("sys.stdout", new=io.StringIO()) as stdout:
                result = prompt_startup_script()
            self.assertEqual(result, str(script))
            self.assertIn("kann nicht verwendet werden", stdout.getvalue())
            self.assertIn("vollstaendigen, absoluten Pfad", prompt.call_args.args[0])

    def test_script_prompt_does_not_accept_failed_permission_correction(self):
        with patch("kiosk.cli.prepare_startup_script", side_effect=PermissionError("chmod")), \
                patch("builtins.input", side_effect=["/tmp/start.sh", ""]), \
                patch("sys.stdout", new=io.StringIO()) as stdout:
            self.assertEqual(prompt_startup_script(), "")
        self.assertIn("chmod", stdout.getvalue())

    @patch("kiosk.cli.shutil.which", return_value="/usr/local/bin/kiosk")
    def test_kiosk_command_prefers_installed_console_script(self, which):
        command = kiosk_command()

        self.assertEqual(command.arguments, ["/usr/local/bin/kiosk"])
        self.assertIsNone(command.working_directory)

    @patch("kiosk.cli.sys.executable", "/usr/bin/python3")
    @patch("kiosk.cli.sys.argv", ["/repo/kiosk/cli.py"])
    @patch("kiosk.cli.shutil.which", return_value=None)
    def test_kiosk_command_uses_python_module_for_source_checkout(self, which):
        command = kiosk_command()

        self.assertEqual(command.arguments, ["/usr/bin/python3", "-m", "kiosk.cli"])
        self.assertEqual(command.working_directory, Path("/repo"))


if __name__ == "__main__":
    unittest.main()
