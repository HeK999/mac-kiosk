"""Validation and permissions for optional kiosk startup scripts."""

from __future__ import annotations

import os
from pathlib import Path
import stat


def prepare_startup_script(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(
            "Bitte den vollstaendigen, absoluten Pfad angeben "
            "(z. B. /Users/name/scripts/start.sh; kein ~)."
        )
    if path.suffix not in {".sh", ".py"}:
        raise ValueError("Das Startskript muss eine .sh- oder .py-Datei sein.")
    if not path.is_file():
        raise ValueError(f"Startskript ist keine vorhandene Datei: {path}")

    mode = stat.S_IMODE(path.stat().st_mode)
    required = stat.S_IRUSR | stat.S_IXUSR
    if mode & required != required:
        path.chmod(mode | required)
    if not os.access(path, os.R_OK | os.X_OK):
        raise PermissionError(f"Startskript ist nicht lesbar und ausfuehrbar: {path}")
    return path
