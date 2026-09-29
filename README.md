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
- kann vor dem Laden der Website einmal pro Kiosk-Start ein `.sh`- oder `.py`-Skript starten
- richtet einen macOS LaunchAgent ein, damit der Kiosk beim Login automatisch startet
- kann die Website automatisch neu laden
- wartet vor dem Reload auf eine einstellbare Inaktivitätszeit
- installiert und konfiguriert Hammerspoon für den Edge-Blocker
- deaktiviert beim Abschalten auch den Kiosk-Autostart und Hammerspoon-Autostart

Die Konfiguration liegt unter:

```sh
~/Library/Application Support/kiosk/config.json
```

Der LaunchAgent liegt im benutzerspezifischen LaunchAgents-Verzeichnis:

```sh
~/Library/LaunchAgents/<kiosk-launch-agent>.plist
```

Den tatsächlich verwendeten Dateinamen zeigt `kiosk status` an.

## Voraussetzungen

- macOS
- Python 3.10 oder neuer
- `pipx`
- Git
- Netzwerkzugriff auf GitHub

Google Chrome wird beim Setup geprüft. Wenn Chrome fehlt, versucht `kiosk`,
Chrome über Homebrew zu installieren.

Hammerspoon wird ebenfalls geprüft. `kiosk` lädt automatisch ein zur
installierten macOS-Version passendes offizielles Hammerspoon-Release von
GitHub herunter und installiert `Hammerspoon.app` direkt. Die offiziellen
Releases sind Universal-Builds für Intel und Apple Silicon; Homebrew wird für
Hammerspoon deshalb nicht benötigt.

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
5. ob ein Startskript verwendet werden soll (Standard: leer)
6. nur bei angegebenem Skript: wie viele Sekunden vor dem Kiosk-Start gewartet
   werden soll (Standard: 10, mindestens 0)
7. ob Auto-Reload aktiv sein soll
8. nach wie vielen Sekunden neu geladen werden soll
9. wie lange seit der letzten Interaktion gewartet werden soll

Wenn noch kein Kiosk eingerichtet ist, führt `kiosk` durch die Einrichtung.
Wenn bereits ein Kiosk eingerichtet ist, zeigt `kiosk` die konfigurierte Website
und bietet an, die Einstellungen zu ändern oder den Kiosk zu deaktivieren.

Für das optionale Startskript muss ein **vollständiger, absoluter Dateipfad**
angegeben werden, z. B. `/Users/simon/scripts/start.sh` oder
`/Users/simon/scripts/start.py`. Relative Pfade und `~` werden nicht akzeptiert.
Vor dem Speichern prüft das Tool, ob die Datei vorhanden ist und auf `.sh` oder
`.py` endet. Fehlende Lese- und Ausführungsrechte des Eigentümers werden ergänzt;
andere Berechtigungen bleiben erhalten. Ist die Datei danach nicht zugänglich
oder schlägt die Korrektur fehl, wird der Pfad nicht akzeptiert.

Ohne Skript bleibt der Start unverändert und es gibt keine zusätzliche Wartezeit.
Beim Ändern der Einstellungen behält Enter den vorhandenen Skriptpfad bei;
`-` entfernt ihn. Die Wartezeit wird nur abgefragt, wenn ein Skript gesetzt ist.

Das Skript wird beim Login bzw. bei `kiosk run` einmal gestartet, nicht bei
automatischen Reloads oder Chrome-Startwiederholungen. `.sh` läuft mit `/bin/bash`,
`.py` mit dem Python-Interpreter von `kiosk` (bei pipx dessen Umgebung).
Das Arbeitsverzeichnis ist der Ordner des Skripts. Die Wartezeit beginnt nach
dem Start des Skripts; danach wird Chrome geöffnet, auch wenn das Skript noch
läuft, etwa als lokaler Webserver. Endet es während der Wartezeit mit einem
Fehler, wird der Kiosk-Start abgebrochen. Beim Autostart erscheinen Ausgaben
und Fehler unter `~/Library/Application Support/kiosk/logs/`.

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

Der Edge-Blocker kann mit `Shift+Alt+K` umgeschaltet werden. Beim
Deaktivieren wird ein Passwort verlangt; das Standardpasswort ist `951951`.
Während `kiosk` eingerichtet oder neu konfiguriert wird, kann ein anderes
Passwort eingegeben werden. Das Passwort selbst wird nicht gespeichert,
sondern nur ein gesalzener SHA-256-Hash. Das erneute Aktivieren und der Befehl
`kiosk disable` benötigen kein Passwort.

Solange der Edge-Blocker aktiv ist, sind nur Buchstaben, Zahlen, Satzzeichen,
Leertaste, Enter, Shift, Alt und die Pfeiltasten freigegeben. Unter anderem
werden Command, Control, Tab, Escape, Funktions- und Sondertasten blockiert,
sodass Systemkombinationen wie `Cmd+Tab` nicht ausgeführt werden. Die
Passworteingabe wird von Hammerspoon selbst maskiert und erlaubt Backspace,
Enter sowie Escape, ohne den Tastaturfilter vorübergehend abzuschalten.

Der Filter ist ein Hammerspoon-Schutz und kein vollständig manipulationssicherer
macOS-Kioskmodus. Wenn eine andere Anwendung macOS Secure Input aktiviert, kann
Hammerspoon Tastaturereignisse vorübergehend nicht abfangen. Für öffentlich
zugängliche Geräte sollte zusätzlich ein eingeschränktes Benutzerkonto oder
eine MDM-Kioskrichtlinie verwendet werden.

`kiosk` installiert automatisch eine zur macOS-Version passende
Hammerspoon-Version. Alle hier verwendeten Releases unterstützen Intel und
Apple Silicon:

- macOS 10.14 und älter: Hammerspoon 0.9.91
- macOS 10.15: Hammerspoon 0.9.96
- macOS 11: Hammerspoon 0.9.100
- macOS 12: Hammerspoon 1.0.0
- macOS 13 und neuer: Hammerspoon 1.1.1

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
