"""Command line interface for the kiosk launcher.

Creator: Simon Krieger
"""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path
import shutil
import sys
from typing import NamedTuple

from .config import (
    DEFAULT_MIN_IDLE_SECONDS,
    DEFAULT_EDGE_BLOCKER_PASSWORD_HASH,
    DEFAULT_EDGE_BLOCKER_PASSWORD_SALT,
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    DEFAULT_STARTUP_SCRIPT_DELAY_SECONDS,
    KioskConfig,
    create_edge_blocker_password,
    config_path,
    delete_config,
    load_config,
    normalize_url,
    save_config,
)
from .launch_agent import (
    launch_agent_path,
    load_launch_agent,
    remove_launch_agent,
    write_launch_agent,
)
from .hammerspoon import (
    disable_hammerspoon_autolaunch_and_quit,
    ensure_hammerspoon,
    get_hammerspoon_status,
)
from .system import ensure_chrome, run_kiosk
from .startup import prepare_startup_script


class KioskCommand(NamedTuple):
    arguments: list[str]
    working_directory: Path | None = None


def print_status() -> KioskConfig | None:
    hammerspoon = get_hammerspoon_status()
    config = load_config()
    if config is None:
        print("Kiosk ist nicht eingerichtet.")
        print_hammerspoon_status(hammerspoon)
        return None

    refresh = "aktiv" if config.auto_refresh_enabled else "deaktiviert"
    print("Kiosk ist eingerichtet.")
    print(f"Website: {config.url}")
    print(f"Startskript: {config.startup_script_path or 'keines'}")
    if config.startup_script_path:
        print(f"Wartezeit vor Kiosk-Start: {config.startup_script_delay_seconds}s")
    print(f"Auto-Reload: {refresh}")
    if config.auto_refresh_enabled:
        print(f"Reload-Intervall: {config.refresh_interval_seconds}s")
        print(f"Mindest-Inaktivitaet: {config.min_idle_seconds}s")
    print(f"Config: {config_path()}")
    print(f"LaunchAgent: {launch_agent_path()}")
    print_hammerspoon_status(hammerspoon)
    return config


def print_hammerspoon_status(status) -> None:
    installed = "installiert" if status.installed else "nicht installiert"
    config = "vorhanden" if status.config_exists else "fehlt"
    print(f"Hammerspoon: {installed}")
    print(f"Hammerspoon-Config: {config}")
    if status.backup_count:
        print(f"Hammerspoon-Config-Backups: {status.backup_count}")


def prompt_bool(prompt: str, default: bool) -> bool:
    suffix = "J/n" if default else "j/N"
    while True:
        answer = input(f"{prompt} [{suffix}]: ").strip().lower()
        if not answer:
            return default
        if answer in {"j", "ja", "y", "yes"}:
            return True
        if answer in {"n", "nein", "no"}:
            return False
        print("Bitte mit ja oder nein antworten.")


def prompt_int(prompt: str, default: int, minimum: int = 1) -> int:
    while True:
        answer = input(f"{prompt} [{default}]: ").strip()
        if not answer:
            return default
        try:
            value = int(answer)
        except ValueError:
            print("Bitte eine ganze Zahl eingeben.")
            continue
        if value < minimum:
            print(f"Bitte eine Zahl >= {minimum} eingeben.")
            continue
        return value


def prompt_url(existing: str | None = None) -> str:
    suffix = f" [{existing}]" if existing else ""
    while True:
        answer = input(f"Welche Website soll angezeigt werden?{suffix}: ").strip()
        if not answer and existing:
            return existing
        try:
            return normalize_url(answer)
        except ValueError as exc:
            print(exc)


def kiosk_command() -> KioskCommand:
    executable = shutil.which("kiosk")
    if executable:
        return KioskCommand([executable])

    script_path = Path(sys.argv[0]).resolve()
    if script_path.name == "cli.py" and script_path.parent.name == "kiosk":
        return KioskCommand([sys.executable, "-m", "kiosk.cli"], script_path.parent.parent)

    return KioskCommand([sys.executable, str(script_path)])


def prompt_startup_script(existing: str = "") -> str:
    suffix = f" [{existing}; - zum Entfernen]" if existing else " [leer = keines]"
    while True:
        answer = input(
            "Optionales Startskript: vollstaendigen, absoluten Pfad zu einer "
            f".sh- oder .py-Datei angeben (z. B. /Users/name/start.sh){suffix}: "
        ).strip()
        if answer == "-":
            return ""
        value = answer or existing
        if not value:
            return ""
        try:
            return str(prepare_startup_script(value))
        except (ValueError, OSError) as exc:
            print(f"Startskript kann nicht verwendet werden: {exc}")


def prompt_edge_blocker_password(
    existing: KioskConfig | None = None,
) -> tuple[str, str]:
    if existing is None:
        prompt = "Passwort fuer Edge-Blocker [Enter = 951951]: "
    else:
        prompt = "Neues Edge-Blocker-Passwort [Enter = beibehalten]: "

    while True:
        password = getpass.getpass(prompt)
        if not password:
            if existing is not None:
                return (
                    existing.edge_blocker_password_salt,
                    existing.edge_blocker_password_hash,
                )
            return (
                DEFAULT_EDGE_BLOCKER_PASSWORD_SALT,
                DEFAULT_EDGE_BLOCKER_PASSWORD_HASH,
            )

        confirmation = getpass.getpass("Passwort wiederholen: ")
        if password == confirmation:
            return create_edge_blocker_password(password)
        print("Die Passwoerter stimmen nicht ueberein.")


def configure(existing: KioskConfig | None = None) -> KioskConfig:
    print("Pruefe Google Chrome...")
    ensure_chrome()
    password_salt, password_hash = prompt_edge_blocker_password(existing)
    print("Pruefe Hammerspoon...")
    ensure_hammerspoon(password_salt, password_hash)
    print(
        "Hinweis: Hammerspoon benoetigt eventuell Zugriff unter "
        "Systemeinstellungen > Datenschutz & Sicherheit > Bedienungshilfen."
    )

    url = prompt_url(existing.url if existing else None)
    startup_script_path = prompt_startup_script(existing.startup_script_path if existing else "")
    startup_script_delay_seconds = DEFAULT_STARTUP_SCRIPT_DELAY_SECONDS
    if startup_script_path:
        startup_script_delay_seconds = prompt_int(
            "Wie viele Sekunden nach dem Start des Skripts soll der Kiosk geladen werden?",
            existing.startup_script_delay_seconds if existing else DEFAULT_STARTUP_SCRIPT_DELAY_SECONDS,
            minimum=0,
        )
    auto_refresh_enabled = prompt_bool(
        "Soll die Seite automatisch neu geladen werden?",
        existing.auto_refresh_enabled if existing else True,
    )

    refresh_interval_seconds = DEFAULT_REFRESH_INTERVAL_SECONDS
    min_idle_seconds = DEFAULT_MIN_IDLE_SECONDS
    if existing:
        refresh_interval_seconds = existing.refresh_interval_seconds
        min_idle_seconds = existing.min_idle_seconds

    if auto_refresh_enabled:
        refresh_interval_seconds = prompt_int(
            "Nach wie vielen Sekunden soll neu geladen werden?",
            refresh_interval_seconds,
        )
        min_idle_seconds = prompt_int(
            "Wie viele Sekunden soll nach der letzten Interaktion gewartet werden?",
            min_idle_seconds,
        )

    config = KioskConfig(
        url=url,
        auto_refresh_enabled=auto_refresh_enabled,
        refresh_interval_seconds=refresh_interval_seconds,
        min_idle_seconds=min_idle_seconds,
        startup_script_path=startup_script_path,
        startup_script_delay_seconds=startup_script_delay_seconds,
        edge_blocker_password_salt=password_salt,
        edge_blocker_password_hash=password_hash,
    )
    save_config(config)

    command = kiosk_command()
    plist_path = write_launch_agent(command.arguments, working_directory=command.working_directory)
    load_launch_agent(plist_path)

    print("Kiosk wurde eingerichtet.")
    print(f"Website: {config.url}")
    print(f"Autostart: {plist_path}")
    return config


def disable() -> None:
    removed_agent = remove_launch_agent()
    removed_config = delete_config()
    disable_hammerspoon_autolaunch_and_quit()
    if removed_agent or removed_config:
        print("Kiosk wurde deaktiviert.")
    else:
        print("Kiosk war nicht eingerichtet.")


def interactive() -> int:
    config = print_status()
    if config is None:
        if prompt_bool("Kiosk jetzt einrichten?", True):
            configure()
        return 0

    print("")
    print("Optionen:")
    print("1) Einstellungen aendern")
    print("2) Kiosk deaktivieren")
    print("3) Abbrechen")

    while True:
        choice = input("Auswahl [3]: ").strip() or "3"
        if choice == "1":
            configure(config)
            return 0
        if choice == "2":
            disable()
            return 0
        if choice == "3":
            return 0
        print("Bitte 1, 2 oder 3 eingeben.")


def run_command() -> int:
    config = load_config()
    if config is None:
        print("Kiosk ist nicht eingerichtet. Starte zuerst `kiosk`.", file=sys.stderr)
        return 1
    run_kiosk(config)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kiosk")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status", help="Status und konfigurierte Website anzeigen")
    subparsers.add_parser("run", help="Kiosk mit gespeicherter Konfiguration starten")
    subparsers.add_parser("disable", help="Autostart und Konfiguration entfernen")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        print_status()
        return 0
    if args.command == "run":
        return run_command()
    if args.command == "disable":
        disable()
        return 0
    return interactive()


if __name__ == "__main__":
    raise SystemExit(main())
