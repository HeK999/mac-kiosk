#!/usr/bin/env bash

set -u

REFRESH_INTERVAL_SECONDS="${REFRESH_INTERVAL_SECONDS:-30}"
MIN_IDLE_SECONDS="${MIN_IDLE_SECONDS:-9}"
POLL_SECONDS="${POLL_SECONDS:-5}"

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
  osascript -e 'tell application "Google Chrome" to reload active tab of front window'
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

  while true; do
    if ! idle_seconds="$(get_idle_seconds)"; then
      log "Could not read macOS idle time; retrying in ${POLL_SECONDS}s."
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

    if reload_chrome_tab; then
      log "Reloaded active Chrome tab."
      break
    fi

    log "Chrome reload failed; retrying in ${POLL_SECONDS}s."
    sleep "${POLL_SECONDS}"
  done
done
