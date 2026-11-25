#!/usr/bin/env bash
# Creator: Simon Krieger

set -u

REFRESH_INTERVAL_SECONDS="${REFRESH_INTERVAL_SECONDS:-30}"
MIN_IDLE_SECONDS="${MIN_IDLE_SECONDS:-9}"
POLL_SECONDS="${POLL_SECONDS:-5}"
KIOSK_URL="${KIOSK_URL:-https://example.com/}"
# Bash's timer and idle readings have one-second resolution. Use the upper
# bound so rounding cannot count input from before the last load as new input.
LAST_REFRESH_SECONDS=$((SECONDS + 1))

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

get_idle_seconds() {
  local idle_ns

  idle_ns="$(
    ioreg -c IOHIDSystem 2>/dev/null |
      awk '/HIDIdleTime/ { print $NF; exit }'
  )"

  if [[ -z "${idle_ns}" || ! "${idle_ns}" =~ ^[0-9]+$ ]]; then
    return 1
  fi

  printf '%d\n' "$((idle_ns / 1000000000))"
}

reload_chrome_tab() {
  osascript - "${KIOSK_URL}" <<'APPLESCRIPT'
on run argv
  tell application "Google Chrome"
    set kioskTab to active tab of front window
    set startURL to item 1 of argv
    if URL of kioskTab is startURL then
      reload kioskTab
    else
      set URL of kioskTab to startURL
    end if
  end tell
end run
APPLESCRIPT
}

wait_until_due() {
  local seconds_remaining="$1"
  local sleep_for

  while ((seconds_remaining > 0)); do
    sleep_for="${POLL_SECONDS}"
    if ((sleep_for > seconds_remaining)); then
      sleep_for="${seconds_remaining}"
    fi

    sleep "${sleep_for}"
    seconds_remaining=$((seconds_remaining - sleep_for))
  done
}

wait_for_idle_threshold() {
  local idle_seconds
  local seconds_until_idle
  local sleep_for
  local observed_at

  while true; do
    observed_at="${SECONDS}"
    if ! idle_seconds="$(get_idle_seconds)"; then
      log "Could not read macOS idle time; retrying in ${POLL_SECONDS}s."
      sleep "${POLL_SECONDS}"
      continue
    fi

    if ((idle_seconds >= observed_at - LAST_REFRESH_SECONDS)); then
      sleep "${POLL_SECONDS}"
      continue
    fi

    if ((idle_seconds >= MIN_IDLE_SECONDS)); then
      return 0
    fi

    seconds_until_idle=$((MIN_IDLE_SECONDS - idle_seconds))
    sleep_for="${seconds_until_idle}"
    if ((sleep_for > POLL_SECONDS)); then
      sleep_for="${POLL_SECONDS}"
    fi

    log "Input was active ${idle_seconds}s ago; postponing refresh for at least ${seconds_until_idle}s."
    sleep "${sleep_for}"
  done
}

log "Chrome auto-refresh started. Interval: ${REFRESH_INTERVAL_SECONDS}s, minimum idle: ${MIN_IDLE_SECONDS}s."

while true; do
  wait_until_due "${REFRESH_INTERVAL_SECONDS}"

  while true; do
    wait_for_idle_threshold

    refresh_started_at=$((SECONDS + 1))
    if reload_chrome_tab; then
      LAST_REFRESH_SECONDS="${refresh_started_at}"
      log "Loaded configured Chrome start page: ${KIOSK_URL}"
      break
    fi

    log "Chrome reload failed; retrying in ${POLL_SECONDS}s."
    sleep "${POLL_SECONDS}"
  done
done
