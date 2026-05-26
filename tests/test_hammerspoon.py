import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tears_kiosk import hammerspoon


class HammerspoonTests(unittest.TestCase):
    @patch("tears_kiosk.hammerspoon.HAMMERSPOON_APP_PATHS")
    def test_hammerspoon_installed_detects_known_path(self, paths):
        existing = Mock()
        missing = Mock()
        existing.exists.return_value = True
        missing.exists.return_value = False
        paths.__iter__.return_value = iter([missing, existing])

        self.assertTrue(hammerspoon.hammerspoon_installed())

    @patch("tears_kiosk.hammerspoon.subprocess.run")
    @patch("tears_kiosk.hammerspoon.homebrew_executable", return_value="/opt/homebrew/bin/brew")
    def test_install_hammerspoon_uses_homebrew_cask(self, homebrew_executable, run):
        hammerspoon.install_hammerspoon_with_homebrew()

        run.assert_called_once_with(
            ["/opt/homebrew/bin/brew", "install", "--cask", "hammerspoon"],
            check=True,
        )

    def test_packaged_init_lua_is_readable(self):
        content = hammerspoon.packaged_init_lua()

        self.assertIn("hs.autoLaunch(true)", content)
        self.assertIn("startEdgeBlocker()", content)

    def test_install_hammerspoon_config_writes_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".hammerspoon" / "init.lua"
            written = hammerspoon.install_hammerspoon_config(path)

            content = path.read_text(encoding="utf-8")

        self.assertEqual(written, path)
        self.assertIn("EDGE_BLOCKER_ENABLED", content)

    def test_install_hammerspoon_config_backs_up_existing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / ".hammerspoon"
            path = config_dir / "init.lua"
            config_dir.mkdir()
            path.write_text("-- existing config\n", encoding="utf-8")

            hammerspoon.install_hammerspoon_config(path)
            backups = list(config_dir.glob("init.lua.backup-*"))

            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "-- existing config\n")
            self.assertIn("hs.autoLaunch(true)", path.read_text(encoding="utf-8"))

    def test_install_hammerspoon_config_skips_identical_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".hammerspoon" / "init.lua"
            path.parent.mkdir()
            path.write_text(hammerspoon.packaged_init_lua(), encoding="utf-8")

            written = hammerspoon.install_hammerspoon_config(path)
            backups = list(path.parent.glob("init.lua.backup-*"))

        self.assertIsNone(written)
        self.assertEqual(backups, [])

    @patch("tears_kiosk.hammerspoon.time.sleep")
    @patch("tears_kiosk.hammerspoon.subprocess.run")
    @patch("tears_kiosk.hammerspoon.hammerspoon_installed", return_value=True)
    def test_disable_autolaunch_and_quit(self, installed, run, sleep):
        hammerspoon.disable_hammerspoon_autolaunch_and_quit()

        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(["open", "-g", "-a", "Hammerspoon"], commands)
        self.assertIn(
            [
                "osascript",
                "-e",
                'tell application "Hammerspoon" to execute lua code "hs.autoLaunch(false)"',
            ],
            commands,
        )
        self.assertIn(["osascript", "-e", 'tell application "Hammerspoon" to quit'], commands)
        self.assertIn(["killall", "Hammerspoon"], commands)


if __name__ == "__main__":
    unittest.main()

