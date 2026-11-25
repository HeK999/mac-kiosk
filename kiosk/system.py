"""macOS system integration for browser kiosk mode.

Creator: Simon Krieger
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from .config import KioskConfig
from .startup import prepare_startup_script


CHROME_APP_NAME = "Google Chrome"
FIREFOX_APP_NAME = "Firefox"
START_BROWSER_ATTEMPTS = 24
START_BROWSER_RETRY_SECONDS = 5
# Backwards-compatible names for callers that imported the old constants.
START_CHROME_ATTEMPTS = START_BROWSER_ATTEMPTS
START_CHROME_RETRY_SECONDS = START_BROWSER_RETRY_SECONDS
CHROME_APP_PATHS = (
    Path("/Applications/Google Chrome.app"),
    Path.home() / "Applications" / "Google Chrome.app",
)
FIREFOX_APP_PATHS = (
    Path("/Applications/Firefox.app"),
    Path.home() / "Applications" / "Firefox.app",
)
BROWSER_PROCESS_NAMES = {
    "chrome": "Google Chrome",
    "firefox": "firefox",
}
BROWSER_CASKS = {
    "chrome": "google-chrome",
    "firefox": "firefox",
}
BROWSER_DISPLAY_NAMES = {
    "chrome": "Google Chrome",
    "firefox": "Firefox",
}


def chrome_installed() -> bool:
    return any(path.exists() for path in CHROME_APP_PATHS)


def firefox_installed() -> bool:
    return any(path.exists() for path in FIREFOX_APP_PATHS)


def browser_installed(browser: str) -> bool:
    if browser == "chrome":
        return chrome_installed()
    if browser == "firefox":
        return firefox_installed()
    raise ValueError(f"Unbekannter Browser: {browser}")


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


def install_browser_with_homebrew(browser: str) -> None:
    cask = BROWSER_CASKS.get(browser)
    if cask is None:
        raise ValueError(f"Unbekannter Browser: {browser}")

    brew = homebrew_executable()
    if brew is None:
        install_homebrew()
        brew = homebrew_executable()

    if brew is None:
        raise RuntimeError("Homebrew wurde installiert, aber `brew` wurde nicht gefunden.")

    subprocess.run([brew, "install", "--cask", cask], check=True)


def install_chrome_with_homebrew() -> None:
    install_browser_with_homebrew("chrome")


def install_firefox_with_homebrew() -> None:
    install_browser_with_homebrew("firefox")


def ensure_chrome() -> None:
    if not chrome_installed():
        install_chrome_with_homebrew()


def ensure_firefox() -> None:
    if not firefox_installed():
        install_firefox_with_homebrew()


def ensure_browser(browser: str) -> None:
    if browser == "chrome":
        ensure_chrome()
    elif browser == "firefox":
        ensure_firefox()
    else:
        raise ValueError(f"Unbekannter Browser: {browser}")


def stop_browser(browser: str) -> None:
    process_name = BROWSER_PROCESS_NAMES.get(browser)
    if process_name is None:
        raise ValueError(f"Unbekannter Browser: {browser}")

    subprocess.run(
        ["killall", process_name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(20):
        result = subprocess.run(
            ["pgrep", "-x", process_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return
        time.sleep(0.5)

    raise RuntimeError(f"{BROWSER_DISPLAY_NAMES[browser]} konnte nicht beendet werden.")


def stop_chrome() -> None:
    stop_browser("chrome")


def stop_firefox() -> None:
    stop_browser("firefox")


def stop_all_browsers() -> None:
    errors: list[RuntimeError] = []
    for browser in ("chrome", "firefox"):
        try:
            stop_browser(browser)
        except RuntimeError as exc:
            errors.append(exc)
    if errors:
        raise errors[0]


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


def start_firefox_kiosk(url: str) -> None:
    subprocess.run(
        ["open", "-na", FIREFOX_APP_NAME, "--args", "--kiosk", url],
        check=True,
    )
    time.sleep(2)
    subprocess.run(
        ["osascript", "-e", 'tell application "Firefox" to activate'],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_browser_kiosk(browser: str, url: str) -> None:
    if browser == "chrome":
        start_chrome_kiosk(url)
    elif browser == "firefox":
        start_firefox_kiosk(url)
    else:
        raise ValueError(f"Unbekannter Browser: {browser}")


def start_browser_kiosk_with_retries(browser: str, url: str) -> None:
    display_name = BROWSER_DISPLAY_NAMES.get(browser)
    if display_name is None:
        raise ValueError(f"Unbekannter Browser: {browser}")

    for attempt in range(1, START_BROWSER_ATTEMPTS + 1):
        try:
            start_browser_kiosk(browser, url)
            return
        except subprocess.CalledProcessError as exc:
            print(
                f"{display_name} konnte nicht gestartet werden "
                f"(Versuch {attempt}/{START_BROWSER_ATTEMPTS}): {exc}",
                flush=True,
            )
            if attempt == START_BROWSER_ATTEMPTS:
                raise
            time.sleep(START_BROWSER_RETRY_SECONDS)


def start_chrome_kiosk_with_retries(url: str) -> None:
    start_browser_kiosk_with_retries("chrome", url)


def reload_chrome_tab(url: str) -> bool:
    result = subprocess.run(
        [
            "osascript",
            "-e",
            '''on run argv
    tell application "Google Chrome"
        set kioskTab to active tab of front window
        set startURL to item 1 of argv
        if URL of kioskTab is startURL then
            reload kioskTab
        else
            set URL of kioskTab to startURL
        end if
    end tell
end run''',
            url,
        ],
        check=False,
    )
    return result.returncode == 0


def reload_browser(browser: str, url: str) -> bool:
    if browser == "chrome":
        return reload_chrome_tab(url)
    if browser == "firefox":
        stop_browser("firefox")
        start_browser_kiosk_with_retries("firefox", url)
        return True
    raise ValueError(f"Unbekannter Browser: {browser}")


def get_idle_seconds() -> float | None:
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

    return int(match.group(1)) / 1_000_000_000


def wait_until_due(seconds: int) -> None:
    remaining = max(0, seconds)
    while remaining > 0:
        sleep_for = min(5, remaining)
        time.sleep(sleep_for)
        remaining -= sleep_for


def wait_for_idle_threshold(min_idle_seconds: int, since: float | None = None) -> None:
    while True:
        # Sample the clock before ioreg so its runtime cannot look like input.
        observed_at = time.monotonic()
        idle_seconds = get_idle_seconds()
        if idle_seconds is None:
            time.sleep(5)
            continue
        if since is not None and idle_seconds >= observed_at - since:
            time.sleep(5)
            continue
        if idle_seconds >= min_idle_seconds:
            return
        time.sleep(min(5, min_idle_seconds - idle_seconds))


def run_kiosk(config: KioskConfig) -> None:
    if config.startup_script_path:
        if config.startup_script_delay_seconds < 0:
            raise ValueError("Die Wartezeit vor dem Kiosk-Start darf nicht negativ sein.")
        path = prepare_startup_script(config.startup_script_path)
        interpreter = "/bin/bash" if path.suffix == ".sh" else sys.executable
        print(f"Starte Startskript: {path}", flush=True)
        startup_process = subprocess.Popen([interpreter, str(path)], cwd=path.parent)
        wait_until_due(config.startup_script_delay_seconds)
        returncode = startup_process.poll()
        if returncode is not None and returncode != 0:
            raise RuntimeError(f"Startskript fehlgeschlagen (Exit-Code {returncode}): {path}")

    stop_all_browsers()
    last_refresh_at = time.monotonic()
    start_browser_kiosk_with_retries(config.browser, config.url)

    if not config.auto_refresh_enabled:
        while True:
            time.sleep(3600)

    while True:
        wait_until_due(config.refresh_interval_seconds)
        while True:
            wait_for_idle_threshold(config.min_idle_seconds, since=last_refresh_at)
            refresh_started_at = time.monotonic()
            if reload_browser(config.browser, config.url):
                last_refresh_at = refresh_started_at
                break
            time.sleep(5)
