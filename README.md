# kiosk

Creator: Simon Krieger

`kiosk` richtet auf einem Mac einen Chrome-Kiosk ein. Das Tool wird über den
Terminal-Befehl `kiosk` bedient und kann per `pipx` direkt aus dem Git-Repository
installiert werden.

Repository:

```sh
https://github.com/HeK999/mac-kiosk.git
```

## Was der Kiosk macht

- startet Google Chrome im Kiosk-/App-Modus mit einer konfigurierten Website
- richtet einen macOS LaunchAgent ein, damit der Kiosk beim Login automatisch startet
- kann die Website automatisch neu laden
- wartet vor dem Reload auf eine einstellbare Inaktivitätszeit
- installiert und konfiguriert Hammerspoon für den Edge-Blocker
- deaktiviert beim Abschalten auch den Kiosk-Autostart und Hammerspoon-Autostart

Die Konfiguration liegt unter:

```sh
~/Library/Application Support/kiosk/config.json
```

Der LaunchAgent liegt unter:

```sh
~/Library/LaunchAgents/com.simonkrieger.kiosk.plist
```

## Voraussetzungen

- macOS
- Python 3.10 oder neuer
- `pipx`
- Git
- Netzwerkzugriff auf GitHub

Google Chrome wird beim Setup geprüft. Wenn Chrome fehlt, versucht `kiosk`,
Chrome über Homebrew zu installieren.

Hammerspoon wird ebenfalls geprüft. Wenn Homebrew vorhanden ist, wird zuerst
Homebrew verwendet. Wenn Homebrew fehlt oder auf alten Systemen nicht läuft,
lädt `kiosk` automatisch ein passendes offizielles Hammerspoon-Release von
GitHub herunter und installiert `Hammerspoon.app` direkt.

## pipx installieren

### Variante A: Mit Homebrew

Auf Macs, auf denen Homebrew funktioniert:

```sh
brew install pipx
pipx ensurepath
```

Terminal danach neu öffnen.

### Variante B: Ohne Homebrew, für ältere macOS-Systeme

Auf alten Macs, z. B. Mojave, kann Homebrew oder eine sehr neue Python-Version
Probleme machen. In diesem Fall eine passende Python-Version von python.org
installieren, empfohlen ist Python 3.11.

Danach `pipx` mit dieser Python-Version installieren:

```sh
python3.11 -m pip install --user pipx
python3.11 -m pipx ensurepath
```

Falls der Befehl `pipx` danach noch nicht gefunden wird:

```sh
export PATH="$HOME/Library/Python/3.11/bin:$PATH"
```

Für Bash dauerhaft eintragen:

```sh
echo 'export PATH="$HOME/Library/Python/3.11/bin:$PATH"' >> ~/.bash_profile
```

Terminal danach neu öffnen.

Hinweis: Auf alten Systemen sollte keine kaputte oder inkompatible Python-Version
verwendet werden. Wenn beim Installieren Fehler wie `unsupported hash type
blake2b` oder `unsupported hash type blake2s` erscheinen, `pipx` explizit mit
Python 3.11 verwenden.

## kiosk installieren

```sh
pipx install git+https://github.com/HeK999/mac-kiosk.git
```

## Kiosk einrichten

Nach der Installation:

```sh
kiosk
```

Beim ersten Start prüft das Tool:

1. ob bereits ein Kiosk eingerichtet ist
2. ob Google Chrome installiert ist
3. ob Hammerspoon installiert und konfiguriert ist
4. welche Website angezeigt werden soll
5. ob Auto-Reload aktiv sein soll
6. nach wie vielen Sekunden neu geladen werden soll
7. wie lange seit der letzten Interaktion gewartet werden soll

Wenn noch kein Kiosk eingerichtet ist, führt `kiosk` durch die Einrichtung.
Wenn bereits ein Kiosk eingerichtet ist, zeigt `kiosk` die konfigurierte Website
und bietet an, die Einstellungen zu ändern oder den Kiosk zu deaktivieren.

## Befehle

Status anzeigen:

```sh
kiosk status
```

Interaktives Setup oder Menü starten:

```sh
kiosk
```

Kiosk mit gespeicherter Konfiguration starten:

```sh
kiosk run
```

Kiosk deaktivieren:

```sh
kiosk disable
```

## Hammerspoon und Berechtigungen

Hammerspoon wird für den Edge-Blocker verwendet. Die mitgelieferte Config wird
nach `~/.hammerspoon/init.lua` geschrieben.

Wenn dort bereits eine Config existiert, wird sie vorher gesichert:

```sh
~/.hammerspoon/init.lua.backup-YYYYMMDD-HHMMSS
```

macOS kann beim ersten Start von Hammerspoon nach Bedienungshilfen-Rechten
fragen. Falls der Edge-Blocker nicht funktioniert, Hammerspoon hier erlauben:

```text
Systemeinstellungen > Datenschutz & Sicherheit > Bedienungshilfen
```

Auf alten macOS-Versionen installiert `kiosk` automatisch eine passende
Hammerspoon-Version:

- macOS 10.14 und älter: Hammerspoon 0.9.91
- macOS 10.15: Hammerspoon 0.9.96
- macOS 11: Hammerspoon 0.9.100
- macOS 12: Hammerspoon 1.0.0
- macOS 13 und neuer: Hammerspoon 1.1.0

## Aktualisieren

```sh
pipx upgrade kiosk
```

Wenn direkt aus Git installiert wurde und ein Upgrade nicht greift:

```sh
pipx reinstall kiosk
```

## Deinstallieren

Zuerst den Kiosk deaktivieren:

```sh
kiosk disable
```

Danach das Tool entfernen:

```sh
pipx uninstall kiosk
```

`kiosk disable` entfernt den Kiosk-LaunchAgent und deaktiviert Hammerspoon beim
Neustart. Hammerspoon selbst wird nicht deinstalliert.

## Lokale Entwicklung

Im Repository:

```sh
python3 -m unittest discover -v
python3 -m compileall kiosk tests
python3 -m pip install -e . --dry-run
```

Lokal ohne pipx ausführen:

```sh
python3 -m kiosk.cli status
python3 -m kiosk.cli
```
