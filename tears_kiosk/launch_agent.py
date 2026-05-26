"""LaunchAgent management.

Creator: Simon Krieger
"""

from __future__ import annotations

import os
from pathlib import Path
import plistlib
import subprocess

from .config import app_support_dir


LABEL = "com.simonkrieger.tears-kiosk"


def launch_agents_dir(home: Path | None = None) -> Path:
    root = home if home is not None else Path.home()
    return root / "Library" / "LaunchAgents"


def launch_agent_path(home: Path | None = None) -> Path:
    return launch_agents_dir(home) / f"{LABEL}.plist"


def build_launch_agent(kiosk_executable: str, home: Path | None = None) -> dict:
    log_dir = app_support_dir(home) / "logs"
    return {
        "Label": LABEL,
        "ProgramArguments": [kiosk_executable, "run"],
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": str(log_dir / "launch-agent.out.log"),
        "StandardErrorPath": str(log_dir / "launch-agent.err.log"),
    }


def write_launch_agent(kiosk_executable: str, home: Path | None = None) -> Path:
    path = launch_agent_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    (app_support_dir(home) / "logs").mkdir(parents=True, exist_ok=True)

    with path.open("wb") as handle:
        plistlib.dump(build_launch_agent(kiosk_executable, home), handle)

    return path


def load_launch_agent(path: Path | None = None) -> None:
    plist_path = path if path is not None else launch_agent_path()
    gui_target = f"gui/{os.getuid()}"
    result = subprocess.run(
        ["launchctl", "bootstrap", gui_target, str(plist_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        subprocess.run(["launchctl", "load", str(plist_path)], check=False)


def unload_launch_agent(path: Path | None = None) -> None:
    plist_path = path if path is not None else launch_agent_path()
    gui_target = f"gui/{os.getuid()}"
    subprocess.run(
        ["launchctl", "bootout", gui_target, str(plist_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["launchctl", "unload", str(plist_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def remove_launch_agent(path: Path | None = None) -> bool:
    plist_path = path if path is not None else launch_agent_path()
    unload_launch_agent(plist_path)
    if not plist_path.exists():
        return False
    plist_path.unlink()
    return True

