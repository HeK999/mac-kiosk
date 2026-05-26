"""macOS system integration for Chrome kiosk mode.

Creator: Simon Krieger
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import time

from .config import KioskConfig


CHROME_APP_NAME = "Google Chrome"
CHROME_APP_PATHS = (
    Path("/Applications/Google Chrome.app"),
    Path.home() / "Applications" / "Google Chrome.app",
)


def chrome_installed() -> bool:
    return any(path.exists() for path in CHROME_APP_PATHS)


def homebrew_executable() -> str | None:
    brew = shutil.which("brew")
    if brew:
        return brew

    for path in (Path("/opt/homebrew/bin/brew"), Path("/usr/local/bin/brew")):
        if path.exists():
            return str(path)

    return None


def install_homebrew() -> None:
    subprocess.run(
        [
            "/bin/bash",
            "-c",
            "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)",
        ],
        check=True,
    )


def install_chrome_with_homebrew() -> None:
    brew = homebrew_executable()
    if brew is None:
        install_homebrew()
        brew = homebrew_executable()

    if brew is None:
        raise RuntimeError("Homebrew wurde installiert, aber `brew` wurde nicht gefunden.")

    subprocess.run([brew, "install", "--cask", "google-chrome"], check=True)


def ensure_chrome() -> None:
    if chrome_installed():
        return
    install_chrome_with_homebrew()


def stop_chrome() -> None:
    subprocess.run(
        ["killall", CHROME_APP_NAME],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(20):
        result = subprocess.run(
            ["pgrep", "-x", CHROME_APP_NAME],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return
        time.sleep(0.5)


def start_chrome_kiosk(url: str) -> None:
    subprocess.run(
        ["open", "-na", CHROME_APP_NAME, "--args", "--kiosk", f"--app={url}"],
        check=True,
    )
    time.sleep(2)
    subprocess.run(
        ["osascript", "-e", 'tell application "Google Chrome" to activate'],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def reload_chrome_tab() -> bool:
    result = subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "Google Chrome" to reload active tab of front window',
        ],
        check=False,
    )
    return result.returncode == 0


def get_idle_seconds() -> int | None:
    result = subprocess.run(
        ["ioreg", "-c", "IOHIDSystem"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None

    match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', result.stdout)
    if not match:
        return None

    return int(match.group(1)) // 1_000_000_000


def wait_until_due(seconds: int) -> None:
    remaining = max(0, seconds)
    while remaining > 0:
        sleep_for = min(5, remaining)
        time.sleep(sleep_for)
        remaining -= sleep_for


def wait_for_idle_threshold(min_idle_seconds: int) -> None:
    while True:
        idle_seconds = get_idle_seconds()
        if idle_seconds is None:
            time.sleep(5)
            continue
        if idle_seconds >= min_idle_seconds:
            return
        time.sleep(min(5, min_idle_seconds - idle_seconds))


def run_kiosk(config: KioskConfig) -> None:
    stop_chrome()
    start_chrome_kiosk(config.url)

    if not config.auto_refresh_enabled:
        while True:
            time.sleep(3600)

    while True:
        wait_until_due(config.refresh_interval_seconds)
        wait_for_idle_threshold(config.min_idle_seconds)
        while not reload_chrome_tab():
            time.sleep(5)
