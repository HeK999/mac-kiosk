"""Hammerspoon setup and teardown.

Creator: Simon Krieger
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib import resources
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time

from .system import homebrew_executable


HAMMERSPOON_APP_NAME = "Hammerspoon"
HAMMERSPOON_APP_PATHS = (
    Path("/Applications/Hammerspoon.app"),
    Path.home() / "Applications" / "Hammerspoon.app",
)
HAMMERSPOON_CONFIG_DIR = Path.home() / ".hammerspoon"
HAMMERSPOON_CONFIG_PATH = HAMMERSPOON_CONFIG_DIR / "init.lua"
APPLICATIONS_DIR = Path("/Applications")
USER_APPLICATIONS_DIR = Path.home() / "Applications"


@dataclass(frozen=True)
class HammerspoonStatus:
    installed: bool
    config_exists: bool
    backup_count: int


def hammerspoon_installed() -> bool:
    return any(path.exists() for path in HAMMERSPOON_APP_PATHS)


def parse_macos_version(version: str) -> tuple[int, int]:
    parts = version.split(".")
    major = int(parts[0]) if parts and parts[0] else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    return major, minor


def macos_version() -> tuple[int, int]:
    version = platform.mac_ver()[0]
    if version:
        return parse_macos_version(version)

    result = subprocess.run(
        ["sw_vers", "-productVersion"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0 and result.stdout.strip():
        return parse_macos_version(result.stdout.strip())

    return 0, 0


def hammerspoon_release_for_macos(version: tuple[int, int]) -> str:
    major, minor = version
    if major == 10 and minor < 15:
        return "0.9.91"
    if major == 10:
        return "0.9.96"
    if major == 11:
        return "0.9.100"
    if major == 12:
        return "1.0.0"
    return "1.1.0"


def hammerspoon_download_url(release: str) -> str:
    return (
        "https://github.com/Hammerspoon/hammerspoon/releases/download/"
        f"{release}/Hammerspoon-{release}.zip"
    )


def install_hammerspoon_with_homebrew() -> None:
    brew = homebrew_executable()
    if brew is None:
        raise RuntimeError("Homebrew ist nicht installiert.")

    subprocess.run([brew, "install", "--cask", "hammerspoon"], check=True)


def copy_hammerspoon_app(source: Path) -> Path:
    destination = APPLICATIONS_DIR / "Hammerspoon.app"
    try:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        return destination
    except OSError:
        destination = USER_APPLICATIONS_DIR / "Hammerspoon.app"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        return destination


def install_hammerspoon_from_github_release() -> Path:
    detected_macos_version = macos_version()
    release = hammerspoon_release_for_macos(detected_macos_version)
    version_text = ".".join(str(part) for part in detected_macos_version)
    url = hammerspoon_download_url(release)
    print(f"Installiere Hammerspoon {release} fuer macOS {version_text}.")

    with tempfile.TemporaryDirectory(prefix="mac-kiosk-hammerspoon-") as tmp:
        temp_dir = Path(tmp)
        archive = temp_dir / f"Hammerspoon-{release}.zip"
        extracted_app = temp_dir / "Hammerspoon.app"

        download = subprocess.run(
            ["curl", "-fL", url, "-o", str(archive)],
            check=False,
        )
        if download.returncode != 0:
            raise RuntimeError(
                "Hammerspoon konnte nicht heruntergeladen werden. "
                f"Oeffne diese URL manuell: {url}"
            )

        unzip = subprocess.run(
            ["/usr/bin/unzip", "-q", str(archive), "-d", str(temp_dir)],
            check=False,
        )
        if unzip.returncode != 0:
            raise RuntimeError(f"Hammerspoon konnte nicht entpackt werden: {archive}")

        if not extracted_app.exists():
            raise RuntimeError(f"Hammerspoon.app wurde im Archiv nicht gefunden: {archive}")

        return copy_hammerspoon_app(extracted_app)


def ensure_hammerspoon_app() -> None:
    if hammerspoon_installed():
        return

    if homebrew_executable() is not None:
        try:
            install_hammerspoon_with_homebrew()
            return
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"Homebrew-Installation von Hammerspoon fehlgeschlagen: {exc}")

    install_hammerspoon_from_github_release()


def packaged_init_lua() -> str:
    return (
        resources.files("mac_kiosk.assets")
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
