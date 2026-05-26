import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tears_kiosk.launch_agent import LABEL, build_launch_agent, remove_launch_agent, write_launch_agent


class LaunchAgentTests(unittest.TestCase):
    def test_build_launch_agent_starts_kiosk_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = build_launch_agent("/usr/local/bin/kiosk", Path(tmp))

        self.assertEqual(data["Label"], LABEL)
        self.assertEqual(data["ProgramArguments"], ["/usr/local/bin/kiosk", "run"])
        self.assertTrue(data["RunAtLoad"])

    def test_write_launch_agent_writes_plist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_launch_agent("/usr/local/bin/kiosk", Path(tmp))
            with path.open("rb") as handle:
                data = plistlib.load(handle)

        self.assertEqual(data["ProgramArguments"], ["/usr/local/bin/kiosk", "run"])

    @patch("tears_kiosk.launch_agent.unload_launch_agent")
    def test_remove_launch_agent_removes_file(self, unload_launch_agent):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_launch_agent("/usr/local/bin/kiosk", Path(tmp))
            removed = remove_launch_agent(path)

        self.assertTrue(removed)
        unload_launch_agent.assert_called_once_with(path)


if __name__ == "__main__":
    unittest.main()

