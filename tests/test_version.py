import re
import unittest
from pathlib import Path

import kiosk


class VersionTests(unittest.TestCase):
    def test_runtime_and_project_versions_are_0_1_6(self):
        pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)

        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "0.1.6")
        self.assertEqual(kiosk.__version__, "0.1.6")


if __name__ == "__main__":
    unittest.main()
