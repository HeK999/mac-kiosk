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

    @patch("kiosk.system.FIREFOX_APP_PATHS")
    def test_firefox_installed_detects_known_path(self, paths):
        existing = Mock()
        existing.exists.return_value = True
        paths.__iter__.return_value = iter([existing])

        self.assertTrue(system.firefox_installed())

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

    @patch("kiosk.system.subprocess.run")
    def test_get_idle_seconds_preserves_subsecond_input_timing(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = '    "HIDIdleTime" = 9500000000\n'

        self.assertEqual(system.get_idle_seconds(), 9.5)

    @patch("kiosk.system.time.sleep")
    @patch("kiosk.system.time.monotonic", side_effect=[110, 120, 140, 150, 155, 157])
    @patch("kiosk.system.get_idle_seconds", side_effect=[20, None, 50, 2, 7, 9])
    def test_idle_wait_requires_input_since_last_refresh_and_then_inactivity(
        self, idle, monotonic, sleep,
    ):
        system.wait_for_idle_threshold(9, since=100)

        self.assertEqual(idle.call_count, 6)
        self.assertEqual(sleep.call_args_list, [call(5), call(5), call(5), call(5), call(2)])

    def test_auto_refresh_waits_for_new_input_after_start_and_each_success(self):
        for browser in ("chrome", "firefox"):
            with self.subTest(browser=browser):
                clock = [100.0]
                last_input = [50.0]
                input_times = iter([145.0, 210.0])
                next_input = [next(input_times)]
                reloads = []

                def sleep(seconds):
                    clock[0] += seconds
                    if clock[0] > 300:
                        raise StopIteration
                    if next_input[0] is not None and clock[0] >= next_input[0]:
                        last_input[0] = next_input[0]
                        next_input[0] = next(input_times, None)

                def reload_browser(selected_browser, url):
                    reloads.append((clock[0], selected_browser, url))
                    return True

                config = KioskConfig("https://example.com", browser=browser,
                                     refresh_interval_seconds=30, min_idle_seconds=9)
                with patch("kiosk.system.stop_all_browsers"), \
                        patch("kiosk.system.start_browser_kiosk_with_retries"), \
                        patch("kiosk.system.time.monotonic", side_effect=lambda: clock[0]), \
                        patch("kiosk.system.time.sleep", side_effect=sleep), \
                        patch("kiosk.system.get_idle_seconds",
                              side_effect=lambda: clock[0] - last_input[0]), \
                        patch("kiosk.system.reload_browser", side_effect=reload_browser), \
                        self.assertRaises(StopIteration):
                    system.run_kiosk(config)

                self.assertEqual(reloads, [
                    (154.0, browser, config.url), (219.0, browser, config.url),
                ])

    @patch("kiosk.system.time.monotonic", side_effect=[100, 150, 170])
    @patch("kiosk.system.time.sleep")
    @patch("kiosk.system.wait_for_idle_threshold")
    @patch("kiosk.system.wait_until_due", side_effect=[None, StopIteration])
    @patch("kiosk.system.reload_browser", side_effect=[False, True])
    @patch("kiosk.system.start_browser_kiosk_with_retries")
    @patch("kiosk.system.stop_all_browsers")
    def test_failed_refresh_rechecks_idle_and_keeps_previous_input_baseline(
        self, stop, start, reload_browser, wait, idle, sleep, monotonic,
    ):
        with self.assertRaises(StopIteration):
            system.run_kiosk(KioskConfig("https://example.com", min_idle_seconds=9))

        self.assertEqual(idle.call_args_list, [call(9, since=100), call(9, since=100)])
        self.assertEqual(reload_browser.call_count, 2)
        sleep.assert_called_once_with(5)

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

    @patch("kiosk.system.homebrew_executable", return_value="/usr/local/bin/brew")
    @patch("kiosk.system.subprocess.run")
    def test_install_firefox_uses_firefox_cask(self, run, brew):
        system.install_firefox_with_homebrew()

        run.assert_called_once_with(
            ["/usr/local/bin/brew", "install", "--cask", "firefox"],
            check=True,
        )

    @patch("kiosk.system.install_firefox_with_homebrew")
    @patch("kiosk.system.firefox_installed", return_value=False)
    def test_ensure_browser_installs_only_selected_browser(self, installed, install):
        system.ensure_browser("firefox")

        install.assert_called_once()

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

    @patch("kiosk.system.time.sleep")
    @patch("kiosk.system.subprocess.run")
    def test_start_firefox_uses_kiosk_argument_and_persistent_profile(self, run, sleep):
        system.start_firefox_kiosk("https://example.com")

        self.assertEqual(
            run.call_args_list[0],
            call(
                [
                    "open",
                    "-na",
                    "Firefox",
                    "--args",
                    "--kiosk",
                    "https://example.com",
                ],
                check=True,
            ),
        )
        self.assertNotIn("--private-window", run.call_args_list[0].args[0])

    @patch("kiosk.system.stop_browser")
    def test_stop_all_browsers_stops_chrome_and_firefox(self, stop):
        system.stop_all_browsers()

        self.assertEqual(stop.call_args_list, [call("chrome"), call("firefox")])

    @patch("kiosk.system.subprocess.run")
    def test_stop_firefox_uses_actual_lowercase_process_name(self, run):
        run.return_value.returncode = 1

        system.stop_browser("firefox")

        self.assertEqual(run.call_args_list[0].args[0], ["killall", "firefox"])
        self.assertEqual(run.call_args_list[1].args[0], ["pgrep", "-x", "firefox"])

    @patch("kiosk.system.stop_browser")
    def test_stop_all_browsers_attempts_both_when_one_fails(self, stop):
        stop.side_effect = [RuntimeError("Chrome haengt"), None]

        with self.assertRaisesRegex(RuntimeError, "Chrome haengt"):
            system.stop_all_browsers()

        self.assertEqual(stop.call_args_list, [call("chrome"), call("firefox")])

    @patch("kiosk.system.subprocess.run")
    def test_chrome_reload_uses_configured_url_as_script_argument(self, run):
        run.return_value.returncode = 0
        urls = (
            "https://example.com/start?lang=de&view=1#home",
            'file:///Users/Simon/start%20page.html?value="quoted"',
        )
        for url in urls:
            with self.subTest(url=url):
                run.reset_mock()
                self.assertTrue(system.reload_browser("chrome", url))
                args = run.call_args.args[0]
                self.assertEqual(args[:2], ["osascript", "-e"])
                self.assertEqual(args[3:], [url])
                self.assertNotIn(url, args[2])
                self.assertIn("set URL of kioskTab to startURL", args[2])
                self.assertIn("reload kioskTab", args[2])

    @patch("kiosk.system.subprocess.run")
    def test_chrome_reload_reports_navigation_failure_for_retry(self, run):
        run.return_value.returncode = 1

        self.assertFalse(system.reload_browser("chrome", "https://example.com"))

    @patch("kiosk.system.start_browser_kiosk_with_retries")
    @patch("kiosk.system.stop_browser")
    def test_firefox_reload_restarts_only_firefox(self, stop, start):
        self.assertTrue(system.reload_browser("firefox", "https://example.com"))

        stop.assert_called_once_with("firefox")
        start.assert_called_once_with("firefox", "https://example.com")

    @patch("kiosk.system.reload_browser", return_value=True)
    @patch("kiosk.system.wait_for_idle_threshold")
    @patch("kiosk.system.start_browser_kiosk_with_retries")
    @patch("kiosk.system.stop_all_browsers")
    @patch("kiosk.system.wait_until_due", side_effect=[None, None, StopIteration])
    @patch("kiosk.system.subprocess.Popen")
    @patch("kiosk.system.prepare_startup_script", return_value=Path("/tmp/start script.sh"))
    def test_startup_runs_once_before_chrome_and_not_on_reload(
        self, prepare, popen, wait, stop, start, idle, reload_browser,
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
            call.wait(10), call.popen().poll(), call.stop(),
            call.start("chrome", config.url),
        ])
        reload_browser.assert_called_once_with("chrome", config.url)

    @patch("kiosk.system.start_browser_kiosk_with_retries")
    @patch("kiosk.system.stop_all_browsers")
    @patch("kiosk.system.wait_until_due", side_effect=StopIteration)
    @patch("kiosk.system.subprocess.Popen")
    def test_empty_script_preserves_existing_start_without_delay(self, popen, wait, stop, start):
        config = KioskConfig("https://example.com")
        with self.assertRaises(StopIteration):
            system.run_kiosk(config)
        popen.assert_not_called()
        stop.assert_called_once()
        start.assert_called_once_with("chrome", config.url)
        wait.assert_called_once_with(config.refresh_interval_seconds)

    @patch("kiosk.system.time.sleep", side_effect=StopIteration)
    @patch("kiosk.system.start_browser_kiosk_with_retries")
    @patch("kiosk.system.stop_all_browsers")
    def test_firefox_start_stops_all_browsers_before_launch(self, stop, start, sleep):
        timeline = Mock()
        timeline.attach_mock(stop, "stop")
        timeline.attach_mock(start, "start")
        config = KioskConfig(
            "https://example.com",
            auto_refresh_enabled=False,
            browser="firefox",
        )

        with self.assertRaises(StopIteration):
            system.run_kiosk(config)

        self.assertEqual(
            timeline.mock_calls,
            [call.stop(), call.start("firefox", config.url)],
        )

    @patch("kiosk.system.stop_all_browsers")
    @patch("kiosk.system.wait_until_due")
    @patch("kiosk.system.subprocess.Popen")
    @patch("kiosk.system.prepare_startup_script", return_value=Path("/tmp/start.py"))
    def test_startup_failure_prevents_chrome_start(self, prepare, popen, wait, stop):
        popen.return_value.poll.return_value = 7
        with self.assertRaisesRegex(RuntimeError, "Exit-Code 7"):
            system.run_kiosk(KioskConfig("https://example.com", startup_script_path="/tmp/start.py"))
        stop.assert_not_called()

    @patch("kiosk.system.stop_all_browsers")
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

                with patch("kiosk.system.stop_all_browsers"), \
                        patch("kiosk.system.start_browser_kiosk_with_retries",
                              side_effect=lambda browser, url: chrome_started(url)), \
                        self.assertRaises(StopIteration):
                    system.run_kiosk(config)

    @patch("kiosk.system.reload_browser", side_effect=[True, StopIteration])
    @patch("kiosk.system.wait_for_idle_threshold")
    @patch("kiosk.system.wait_until_due")
    @patch("kiosk.system.start_browser_kiosk_with_retries")
    @patch("kiosk.system.stop_all_browsers")
    @patch("kiosk.system.subprocess.Popen")
    @patch("kiosk.system.prepare_startup_script", return_value=Path("/tmp/start.py"))
    def test_firefox_auto_reload_does_not_run_startup_script_again(
        self, prepare, popen, stop_all, start, wait, idle, reload_browser,
    ):
        popen.return_value.poll.return_value = None
        config = KioskConfig(
            "https://example.com",
            startup_script_path="/tmp/start.py",
            browser="firefox",
        )

        with self.assertRaises(StopIteration):
            system.run_kiosk(config)

        popen.assert_called_once()
        start.assert_called_once_with("firefox", config.url)
        self.assertEqual(
            reload_browser.call_args_list,
            [call("firefox", config.url), call("firefox", config.url)],
        )


if __name__ == "__main__":
    unittest.main()
