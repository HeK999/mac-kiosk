"""Configuration handling for the kiosk CLI.

Creator: Simon Krieger
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


APP_NAME = "mac-kiosk"
DEFAULT_REFRESH_INTERVAL_SECONDS = 1800
DEFAULT_MIN_IDLE_SECONDS = 90


@dataclass(frozen=True)
class KioskConfig:
    url: str
    auto_refresh_enabled: bool = True
    refresh_interval_seconds: int = DEFAULT_REFRESH_INTERVAL_SECONDS
    min_idle_seconds: int = DEFAULT_MIN_IDLE_SECONDS


def app_support_dir(home: Path | None = None) -> Path:
    root = home if home is not None else Path.home()
    return root / "Library" / "Application Support" / APP_NAME


def config_path(home: Path | None = None) -> Path:
    return app_support_dir(home) / "config.json"


def normalize_url(value: str) -> str:
    url = value.strip()
    if not url:
        raise ValueError("Website darf nicht leer sein.")
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def load_config(path: Path | None = None) -> KioskConfig | None:
    cfg_path = path if path is not None else config_path()
    if not cfg_path.exists():
        return None

    with cfg_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    return KioskConfig(
        url=normalize_url(str(data["url"])),
        auto_refresh_enabled=bool(data.get("auto_refresh_enabled", True)),
        refresh_interval_seconds=int(
            data.get("refresh_interval_seconds", DEFAULT_REFRESH_INTERVAL_SECONDS)
        ),
        min_idle_seconds=int(data.get("min_idle_seconds", DEFAULT_MIN_IDLE_SECONDS)),
    )


def save_config(config: KioskConfig, path: Path | None = None) -> Path:
    cfg_path = path if path is not None else config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    with cfg_path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(config), handle, indent=2)
        handle.write("\n")

    return cfg_path


def delete_config(path: Path | None = None) -> bool:
    cfg_path = path if path is not None else config_path()
    if not cfg_path.exists():
        return False
    cfg_path.unlink()
    return True

