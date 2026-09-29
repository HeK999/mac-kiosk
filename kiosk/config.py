"""Configuration handling for the kiosk CLI.

Creator: Simon Krieger
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import secrets


APP_NAME = "kiosk"
DEFAULT_REFRESH_INTERVAL_SECONDS = 1800
DEFAULT_MIN_IDLE_SECONDS = 90
DEFAULT_STARTUP_SCRIPT_DELAY_SECONDS = 10
DEFAULT_EDGE_BLOCKER_PASSWORD_SALT = "kiosk-edge-blocker-default-v1"
DEFAULT_EDGE_BLOCKER_PASSWORD_HASH = (
    "a01a9783b8583ed821952e3d9d0207d5173545e7a0910c7b3ac23cf41b2f1474"
)


def hash_edge_blocker_password(password: str, salt: str) -> str:
    value = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def create_edge_blocker_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    return salt, hash_edge_blocker_password(password, salt)


@dataclass(frozen=True)
class KioskConfig:
    url: str
    auto_refresh_enabled: bool = True
    refresh_interval_seconds: int = DEFAULT_REFRESH_INTERVAL_SECONDS
    min_idle_seconds: int = DEFAULT_MIN_IDLE_SECONDS
    startup_script_path: str = ""
    startup_script_delay_seconds: int = DEFAULT_STARTUP_SCRIPT_DELAY_SECONDS
    edge_blocker_password_salt: str = DEFAULT_EDGE_BLOCKER_PASSWORD_SALT
    edge_blocker_password_hash: str = DEFAULT_EDGE_BLOCKER_PASSWORD_HASH


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
        startup_script_path=str(data.get("startup_script_path", "")),
        startup_script_delay_seconds=int(
            data.get("startup_script_delay_seconds", DEFAULT_STARTUP_SCRIPT_DELAY_SECONDS)
        ),
        edge_blocker_password_salt=str(
            data.get(
                "edge_blocker_password_salt", DEFAULT_EDGE_BLOCKER_PASSWORD_SALT
            )
        ),
        edge_blocker_password_hash=str(
            data.get(
                "edge_blocker_password_hash", DEFAULT_EDGE_BLOCKER_PASSWORD_HASH
            )
        ),
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
