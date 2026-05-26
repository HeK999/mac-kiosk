import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from mac_kiosk.launch_agent import (
    LABEL,
    build_launch_agent,
    load_launch_agent,
    remove_launch_agent,
    write_launch_agent,
)


class LaunchAgentTests(unittest.TestCase):
    def test_build_launch_agent_starts_kiosk_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = build_launch_agent("/usr/local/bin/kiosk", Path(tmp))

        self.assertEqual(data["Label"], LABEL)
        self.assertEqual(data["ProgramArguments"], ["/usr/local/bin/kiosk", "run"])
        self.assertEqual(data["LimitLoadToSessionType"], "Aqua")
        self.assertEqual(data["ProcessType"], "Interactive")
        self.assertIn("/usr/bin", data["EnvironmentVariables"]["PATH"])
        self.assertTrue(data["RunAtLoad"])

    def test_write_launch_agent_writes_plist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_launch_agent("/usr/local/bin/kiosk", Path(tmp))
            with path.open("rb") as handle:
                data = plistlib.load(handle)

        self.assertEqual(data["ProgramArguments"], ["/usr/local/bin/kiosk", "run"])

    def test_write_launch_agent_accepts_multi_argument_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_launch_agent(
                ["/usr/bin/python3", "-m", "mac_kiosk.cli"],
                Path(tmp),
                Path("/repo"),
            )
            with path.open("rb") as handle:
                data = plistlib.load(handle)

        self.assertEqual(
            data["ProgramArguments"],
            ["/usr/bin/python3", "-m", "mac_kiosk.cli", "run"],
        )
        self.assertEqual(data["WorkingDirectory"], "/repo")

    @patch("mac_kiosk.launch_agent.os.getuid", return_value=501)
    @patch("mac_kiosk.launch_agent.subprocess.run")
    def test_load_launch_agent_reloads_existing_agent(self, run, getuid):
        path = Path("/tmp/com.simonkrieger.mac-kiosk.plist")
        run.return_value.returncode = 0

        load_launch_agent(path)

        self.assertEqual(
            run.mock_calls,
            [
                call(
                    ["launchctl", "bootout", "gui/501", str(path)],
                    check=False,
                    stdout=-3,
                    stderr=-3,
                ),
                call(
                    ["launchctl", "unload", str(path)],
                    check=False,
                    stdout=-3,
                    stderr=-3,
                ),
                call(
                    ["launchctl", "bootstrap", "gui/501", str(path)],
                    check=False,
                    stdout=-3,
                    stderr=-3,
                ),
            ],
        )

    @patch("mac_kiosk.launch_agent.unload_launch_agent")
    def test_remove_launch_agent_removes_file(self, unload_launch_agent):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_launch_agent("/usr/local/bin/kiosk", Path(tmp))
            removed = remove_launch_agent(path)

        self.assertTrue(removed)
        unload_launch_agent.assert_called_once_with(path)


if __name__ == "__main__":
    unittest.main()
