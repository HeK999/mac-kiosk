import tempfile
import unittest
import io
from pathlib import Path
from unittest.mock import Mock, call, patch

from kiosk import hammerspoon


class HammerspoonTests(unittest.TestCase):
    @patch("kiosk.hammerspoon.HAMMERSPOON_APP_PATHS")
    def test_hammerspoon_installed_detects_known_path(self, paths):
        existing = Mock()
        missing = Mock()
        existing.exists.return_value = True
        missing.exists.return_value = False
        paths.__iter__.return_value = iter([missing, existing])

        self.assertTrue(hammerspoon.hammerspoon_installed())

    @patch("kiosk.hammerspoon.subprocess.run")
    @patch("kiosk.hammerspoon.homebrew_executable", return_value="/opt/homebrew/bin/brew")
    def test_install_hammerspoon_uses_homebrew_cask(self, homebrew_executable, run):
        hammerspoon.install_hammerspoon_with_homebrew()

        run.assert_called_once_with(
            ["/opt/homebrew/bin/brew", "install", "--cask", "hammerspoon"],
            check=True,
        )

    def test_hammerspoon_release_for_mojave(self):
        self.assertEqual(hammerspoon.hammerspoon_release_for_macos((10, 14)), "0.9.91")

    def test_hammerspoon_release_for_catalina(self):
        self.assertEqual(hammerspoon.hammerspoon_release_for_macos((10, 15)), "0.9.96")

    def test_hammerspoon_release_for_big_sur(self):
        self.assertEqual(hammerspoon.hammerspoon_release_for_macos((11, 0)), "0.9.100")

    def test_hammerspoon_release_for_monterey(self):
        self.assertEqual(hammerspoon.hammerspoon_release_for_macos((12, 0)), "1.0.0")

    def test_hammerspoon_release_for_ventura_or_newer(self):
        self.assertEqual(hammerspoon.hammerspoon_release_for_macos((13, 0)), "1.1.0")
        self.assertEqual(hammerspoon.hammerspoon_release_for_macos((14, 0)), "1.1.0")

    @patch("kiosk.hammerspoon.install_hammerspoon_from_github_release")
    @patch("kiosk.hammerspoon.install_hammerspoon_with_homebrew")
    @patch("kiosk.hammerspoon.homebrew_executable", return_value="/opt/homebrew/bin/brew")
    @patch("kiosk.hammerspoon.hammerspoon_installed", return_value=False)
    def test_ensure_hammerspoon_app_uses_homebrew_when_available(
        self,
        installed,
        homebrew_executable,
        install_homebrew,
        install_release,
    ):
        hammerspoon.ensure_hammerspoon_app()

        install_homebrew.assert_called_once()
        install_release.assert_not_called()

    @patch("kiosk.hammerspoon.install_hammerspoon_from_github_release")
    @patch("kiosk.hammerspoon.install_hammerspoon_with_homebrew")
    @patch("kiosk.hammerspoon.homebrew_executable", return_value=None)
    @patch("kiosk.hammerspoon.hammerspoon_installed", return_value=False)
    def test_ensure_hammerspoon_app_uses_release_when_homebrew_missing(
        self,
        installed,
        homebrew_executable,
        install_homebrew,
        install_release,
    ):
        hammerspoon.ensure_hammerspoon_app()

        install_homebrew.assert_not_called()
        install_release.assert_called_once()

    @patch("kiosk.hammerspoon.install_hammerspoon_from_github_release")
    @patch(
        "kiosk.hammerspoon.install_hammerspoon_with_homebrew",
        side_effect=RuntimeError("brew failed"),
    )
    @patch("kiosk.hammerspoon.homebrew_executable", return_value="/opt/homebrew/bin/brew")
    @patch("kiosk.hammerspoon.hammerspoon_installed", return_value=False)
    def test_ensure_hammerspoon_app_falls_back_when_homebrew_fails(
        self,
        installed,
        homebrew_executable,
        install_homebrew,
        install_release,
    ):
        with patch("sys.stdout", new=io.StringIO()):
            hammerspoon.ensure_hammerspoon_app()

        install_homebrew.assert_called_once()
        install_release.assert_called_once()

    @patch("kiosk.hammerspoon.copy_hammerspoon_app", return_value=Path("/Applications/Hammerspoon.app"))
    @patch("kiosk.hammerspoon.macos_version", return_value=(10, 14))
    @patch("kiosk.hammerspoon.subprocess.run")
    def test_install_from_github_release_downloads_unzips_and_copies(
        self,
        run,
        macos_version,
        copy_hammerspoon_app,
    ):
        run.return_value.returncode = 0

        with patch("kiosk.hammerspoon.Path.exists", return_value=True):
            with patch("sys.stdout", new=io.StringIO()):
                installed_path = hammerspoon.install_hammerspoon_from_github_release()

        self.assertEqual(installed_path, Path("/Applications/Hammerspoon.app"))
        commands = [run_call.args[0] for run_call in run.call_args_list]
        self.assertEqual(commands[0][0:2], ["curl", "-fL"])
        self.assertIn(
            "https://github.com/Hammerspoon/hammerspoon/releases/download/0.9.91/Hammerspoon-0.9.91.zip",
            commands[0],
        )
        self.assertEqual(commands[1][0:2], ["/usr/bin/unzip", "-q"])
        copy_hammerspoon_app.assert_called_once()

    @patch("kiosk.hammerspoon.shutil.copytree")
    @patch("kiosk.hammerspoon.shutil.rmtree")
    def test_copy_hammerspoon_app_falls_back_to_user_applications(self, rmtree, copytree):
        source = Path("/tmp/Hammerspoon.app")
        copytree.side_effect = [OSError("no permission"), None]

        with tempfile.TemporaryDirectory() as tmp:
            user_applications = Path(tmp) / "Applications"
            with patch("kiosk.hammerspoon.USER_APPLICATIONS_DIR", user_applications):
                destination = hammerspoon.copy_hammerspoon_app(source)

        self.assertEqual(destination, user_applications / "Hammerspoon.app")
        self.assertEqual(copytree.call_args_list[0], call(source, Path("/Applications/Hammerspoon.app")))
        self.assertEqual(copytree.call_args_list[1], call(source, user_applications / "Hammerspoon.app"))

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

    @patch("kiosk.hammerspoon.time.sleep")
    @patch("kiosk.hammerspoon.subprocess.run")
    @patch("kiosk.hammerspoon.hammerspoon_installed", return_value=True)
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
