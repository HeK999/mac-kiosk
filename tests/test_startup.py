import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kiosk.startup import prepare_startup_script


class StartupTests(unittest.TestCase):
    def test_rejects_relative_paths_and_home_shorthand(self):
        for value in ("start.sh", "scripts/start.py", "~/start.sh", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare_startup_script(value)

    def test_rejects_missing_files_directories_and_unsupported_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "directory.sh"
            directory.mkdir()
            unsupported = Path(tmp) / "start.txt"
            unsupported.touch()
            for path in (Path(tmp) / "missing.py", directory, unsupported):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    prepare_startup_script(str(path))

    def test_adds_only_missing_owner_read_and_execute_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            for suffix in (".sh", ".py"):
                path = Path(tmp) / f"start script{suffix}"
                path.touch()
                for mode in (0o000, 0o200, 0o640, 0o755):
                    with self.subTest(suffix=suffix, mode=oct(mode)):
                        path.chmod(mode)
                        self.assertEqual(prepare_startup_script(str(path)), path)
                        self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode | 0o500)

    def test_does_not_chmod_already_valid_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "start.sh"
            path.touch(mode=0o700)
            with patch.object(Path, "chmod") as chmod:
                prepare_startup_script(str(path))
            chmod.assert_not_called()

    def test_rejects_script_when_access_still_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "start.sh"
            path.touch()
            with patch("kiosk.startup.os.access", return_value=False), \
                    self.assertRaises(PermissionError):
                prepare_startup_script(str(path))
