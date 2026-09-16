import unittest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, call, patch

from kiosk import system
from kiosk.config import KioskConfig


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

    @patch("kiosk.system.reload_chrome_tab", return_value=True)
    @patch("kiosk.system.wait_for_idle_threshold")
    @patch("kiosk.system.start_chrome_kiosk_with_retries")
    @patch("kiosk.system.stop_chrome")
    @patch("kiosk.system.wait_until_due", side_effect=[None, None, StopIteration])
    @patch("kiosk.system.subprocess.Popen")
    @patch("kiosk.system.prepare_startup_script", return_value=Path("/tmp/start script.sh"))
    def test_startup_runs_once_before_chrome_and_not_on_reload(
        self, prepare, popen, wait, stop, start, idle, reload_tab,
    ):
        popen.return_value.poll.return_value = None  # A long-running server is allowed.
        timeline = Mock()
        for name, mock in (("popen", popen), ("wait", wait), ("stop", stop), ("start", start)):
            timeline.attach_mock(mock, name)
        config = KioskConfig("https://example.com", startup_script_path="/tmp/start script.sh")

        with self.assertRaises(StopIteration):
            system.run_kiosk(config)

        popen.assert_called_once_with(["/bin/bash", config.startup_script_path], cwd=Path("/tmp"))
        timeline.assert_has_calls([
            call.popen(["/bin/bash", config.startup_script_path], cwd=Path("/tmp")),
            call.wait(10), call.popen().poll(), call.stop(), call.start(config.url),
        ])
        reload_tab.assert_called_once()

    @patch("kiosk.system.start_chrome_kiosk_with_retries")
    @patch("kiosk.system.stop_chrome")
    @patch("kiosk.system.wait_until_due", side_effect=StopIteration)
    @patch("kiosk.system.subprocess.Popen")
    def test_empty_script_preserves_existing_start_without_delay(self, popen, wait, stop, start):
        config = KioskConfig("https://example.com")
        with self.assertRaises(StopIteration):
            system.run_kiosk(config)
        popen.assert_not_called()
        stop.assert_called_once()
        start.assert_called_once_with(config.url)
        wait.assert_called_once_with(config.refresh_interval_seconds)

    @patch("kiosk.system.stop_chrome")
    @patch("kiosk.system.wait_until_due")
    @patch("kiosk.system.subprocess.Popen")
    @patch("kiosk.system.prepare_startup_script", return_value=Path("/tmp/start.py"))
    def test_startup_failure_prevents_chrome_start(self, prepare, popen, wait, stop):
        popen.return_value.poll.return_value = 7
        with self.assertRaisesRegex(RuntimeError, "Exit-Code 7"):
            system.run_kiosk(KioskConfig("https://example.com", startup_script_path="/tmp/start.py"))
        stop.assert_not_called()

    @patch("kiosk.system.stop_chrome")
    @patch("kiosk.system.subprocess.Popen")
    def test_missing_script_at_runtime_prevents_launch(self, popen, stop):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            system.run_kiosk(KioskConfig("https://example.com", startup_script_path=f"{tmp}/gone.sh"))
        popen.assert_not_called()
        stop.assert_not_called()

    def test_executes_shell_and_python_scripts_with_spaces_before_opening_chrome(self):
        scripts = {
            ".sh": "printf ready > marker.txt\n",
            ".py": "from pathlib import Path\nPath('marker.txt').write_text('ready')\n",
        }
        for suffix, source in scripts.items():
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as tmp:
                script = Path(tmp) / f"start script{suffix}"
                script.write_text(source)
                config = KioskConfig("https://example.com", startup_script_path=str(script),
                                     startup_script_delay_seconds=1)
                def chrome_started(url):
                    self.assertEqual((Path(tmp) / "marker.txt").read_text(), "ready")
                    raise StopIteration

                with patch("kiosk.system.stop_chrome"), \
                        patch("kiosk.system.start_chrome_kiosk_with_retries", side_effect=chrome_started), \
                        self.assertRaises(StopIteration):
                    system.run_kiosk(config)


if __name__ == "__main__":
    unittest.main()
