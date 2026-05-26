"""Hammerspoon setup and teardown.

Creator: Simon Krieger
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib import resources
from pathlib import Path
import subprocess
import time

from .system import homebrew_executable, install_homebrew


HAMMERSPOON_APP_NAME = "Hammerspoon"
HAMMERSPOON_APP_PATHS = (
    Path("/Applications/Hammerspoon.app"),
    Path.home() / "Applications" / "Hammerspoon.app",
)
HAMMERSPOON_CONFIG_DIR = Path.home() / ".hammerspoon"
HAMMERSPOON_CONFIG_PATH = HAMMERSPOON_CONFIG_DIR / "init.lua"


@dataclass(frozen=True)
class HammerspoonStatus:
    installed: bool
    config_exists: bool
    backup_count: int


def hammerspoon_installed() -> bool:
    return any(path.exists() for path in HAMMERSPOON_APP_PATHS)


def install_hammerspoon_with_homebrew() -> None:
    brew = homebrew_executable()
    if brew is None:
        install_homebrew()
        brew = homebrew_executable()

    if brew is None:
        raise RuntimeError("Homebrew wurde installiert, aber `brew` wurde nicht gefunden.")

    subprocess.run([brew, "install", "--cask", "hammerspoon"], check=True)


def ensure_hammerspoon_app() -> None:
    if hammerspoon_installed():
        return
    install_hammerspoon_with_homebrew()


def packaged_init_lua() -> str:
    return (
        resources.files("tears_kiosk.assets")
        .joinpath("hammerspoon_init.lua")
        .read_text(encoding="utf-8")
    )


def backup_path_for(config_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return config_path.with_name(f"{config_path.name}.backup-{timestamp}")


def install_hammerspoon_config(config_path: Path | None = None) -> Path | None:
    target = config_path if config_path is not None else HAMMERSPOON_CONFIG_PATH
    content = packaged_init_lua()
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if existing == content:
            return None
        target.rename(backup_path_for(target))

    target.write_text(content, encoding="utf-8")
    return target


def start_hammerspoon() -> None:
    subprocess.run(["open", "-a", HAMMERSPOON_APP_NAME], check=True)
    time.sleep(2)


def reload_hammerspoon_config() -> None:
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "Hammerspoon" to execute lua code "hs.reload()"',
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_hammerspoon() -> None:
    ensure_hammerspoon_app()
    install_hammerspoon_config()
    start_hammerspoon()
    reload_hammerspoon_config()


def disable_hammerspoon_autolaunch_and_quit() -> None:
    if hammerspoon_installed():
        subprocess.run(
            ["open", "-g", "-a", HAMMERSPOON_APP_NAME],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)

    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "Hammerspoon" to execute lua code "hs.autoLaunch(false)"',
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["osascript", "-e", 'tell application "Hammerspoon" to quit'],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["killall", HAMMERSPOON_APP_NAME],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def get_hammerspoon_status() -> HammerspoonStatus:
    config_dir = HAMMERSPOON_CONFIG_PATH.parent
    backup_count = 0
    if config_dir.exists():
        backup_count = len(list(config_dir.glob("init.lua.backup-*")))

    return HammerspoonStatus(
        installed=hammerspoon_installed(),
        config_exists=HAMMERSPOON_CONFIG_PATH.exists(),
        backup_count=backup_count,
    )

