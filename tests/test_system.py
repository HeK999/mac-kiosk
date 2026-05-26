import unittest
import subprocess
from unittest.mock import Mock, patch

from kiosk import system


class SystemTests(unittest.TestCase):
    @patch("kiosk.system.CHROME_APP_PATHS")
    def test_chrome_installed_detects_known_path(self, paths):
        existing = Mock()
        missing = Mock()
        existing.exists.return_value = True
        missing.exists.return_value = False
        paths.__iter__.return_value = iter([missing, existing])

        self.assertTrue(system.chrome_installed())

    @patch("kiosk.system.install_chrome_with_homebrew")
    @patch("kiosk.system.chrome_installed", return_value=True)
    def test_ensure_chrome_does_not_install_when_present(self, chrome_installed, install):
        system.ensure_chrome()

        install.assert_not_called()

    @patch("kiosk.system.install_chrome_with_homebrew")
    @patch("kiosk.system.chrome_installed", return_value=False)
    def test_ensure_chrome_installs_when_missing(self, chrome_installed, install):
        system.ensure_chrome()

        install.assert_called_once()

    @patch("kiosk.system.subprocess.run")
    def test_get_idle_seconds_parses_ioreg_output(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = '    "HIDIdleTime" = 90000000000\n'

        self.assertEqual(system.get_idle_seconds(), 90)

    @patch("kiosk.system.homebrew_executable", side_effect=[None, "/opt/homebrew/bin/brew"])
    @patch("kiosk.system.install_homebrew")
    @patch("kiosk.system.subprocess.run")
    def test_install_chrome_installs_homebrew_when_missing(self, run, install_homebrew, brew):
        system.install_chrome_with_homebrew()

        install_homebrew.assert_called_once()
        run.assert_called_once_with(
            ["/opt/homebrew/bin/brew", "install", "--cask", "google-chrome"],
            check=True,
        )

    @patch("builtins.print")
    @patch("kiosk.system.time.sleep")
    @patch("kiosk.system.start_chrome_kiosk")
    def test_start_chrome_kiosk_with_retries_recovers_after_transient_failure(
        self,
        start_chrome_kiosk,
        sleep,
        print_mock,
    ):
        start_chrome_kiosk.side_effect = [
            subprocess.CalledProcessError(1, ["open"]),
            None,
        ]

        system.start_chrome_kiosk_with_retries("https://example.com")

        self.assertEqual(start_chrome_kiosk.call_count, 2)
        sleep.assert_called_once_with(system.START_CHROME_RETRY_SECONDS)


if __name__ == "__main__":
    unittest.main()
