# tears-kiosk

Creator: Simon Krieger

macOS Chrome kiosk launcher with a `kiosk` terminal command.

## Installation

```sh
pipx install git+<repo-url>
```

## Usage

```sh
kiosk
kiosk status
kiosk run
kiosk disable
```

`kiosk` opens an interactive setup and management menu. The setup stores its configuration in `~/Library/Application Support/tears-kiosk/config.json` and installs a LaunchAgent that starts `kiosk run` at login.

The setup also installs and configures Hammerspoon for the kiosk edge-blocker behavior. macOS may ask you to grant Hammerspoon Accessibility permissions.
