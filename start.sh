#!/usr/bin/env bash
# Creator: Simon Krieger

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REFRESH_SCRIPT="${SCRIPT_DIR}/chrome-auto-refresh.sh"
KIOSK_URL="${KIOSK_URL:-https://example.com/}"
CHROME_APP_NAME="Google Chrome"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

close_other_terminal_windows() {
  local current_tty
  local current_tty_name

  current_tty="$(tty 2>/dev/null || true)"
  if [[ -z "${current_tty}" || "${current_tty}" == "not a tty" ]]; then
    return 0
  fi

  current_tty_name="${current_tty#/dev/}"

  osascript >/dev/null 2>&1 <<APPLESCRIPT || true
tell application "Terminal"
  set keepTtyFull to "${current_tty}"
  set keepTtyName to "${current_tty_name}"

  repeat with terminalWindow in windows
    set shouldClose to true

    repeat with terminalTab in tabs of terminalWindow
      try
        set tabTty to tty of terminalTab
        if tabTty is keepTtyFull or tabTty is keepTtyName or tabTty ends with keepTtyName then
          set shouldClose to false
        end if
      end try
    end repeat

    if shouldClose then
      try
        close terminalWindow
      end try
    end if
  end repeat
end tell
APPLESCRIPT
}

if [[ ! -x "${REFRESH_SCRIPT}" ]]; then
  log "Refresh script is missing or not executable: ${REFRESH_SCRIPT}"
  exit 1
fi

killall "${CHROME_APP_NAME}" >/dev/null 2>&1 || true

for _ in {1..20}; do
  if ! pgrep -x "${CHROME_APP_NAME}" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

log "Starting Chrome kiosk at ${KIOSK_URL}."
if ! open -na "${CHROME_APP_NAME}" --args --kiosk --app="${KIOSK_URL}"; then
  log "Could not start ${CHROME_APP_NAME}. Check that Google Chrome is installed in /Applications or ~/Applications."
  exit 1
fi

sleep 2
osascript -e 'tell application "Google Chrome" to activate' || true

close_other_terminal_windows

exec "${REFRESH_SCRIPT}"
