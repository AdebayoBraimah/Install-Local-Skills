#!/usr/bin/env bash
# alert-me Stop hook: notify ntfy topic ab-mac when a LONG turn ends.
#
# Two modes, wired to two hook events in ~/.claude/settings.json:
#   start  (UserPromptSubmit) - stamp the turn start time for this session
#   stop   (Stop)             - if the turn ran >= threshold, push a notification
#
# Unlike the alert-me skill, this runs in the harness, so it still fires when
# the model never gets to act (abort, crash, kill mid-turn).
#
# Threshold: ALERT_ME_MIN_SECONDS (default 120).
# Never blocks the turn: always exits 0.

set -uo pipefail

MODE="${1:-stop}"
STATE_DIR="$HOME/.claude/hooks/alert-me/state"
SENDER="$HOME/.agents/skills/ntfy-notify/scripts/ntfy_send.sh"
TOPIC="ab-mac"
MIN_SECONDS="${ALERT_ME_MIN_SECONDS:-120}"

input="$(cat 2>/dev/null || true)"

field() {
  printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null || true
}

session_id="$(field '.session_id')"
[ -n "$session_id" ] || session_id="unknown"
# Keep the id filesystem-safe.
session_id="$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9._-' '_')"
stamp_file="$STATE_DIR/$session_id"

case "$MODE" in
  start)
    mkdir -p "$STATE_DIR" 2>/dev/null || exit 0
    date +%s > "$stamp_file" 2>/dev/null || true
    # Drop stamps older than a day so the dir does not grow forever.
    find "$STATE_DIR" -type f -mtime +1 -delete 2>/dev/null || true
    exit 0
    ;;
  stop)
    [ -f "$stamp_file" ] || exit 0
    start="$(cat "$stamp_file" 2>/dev/null || echo 0)"
    rm -f "$stamp_file" 2>/dev/null || true
    case "$start" in ''|*[!0-9]*) exit 0 ;; esac
    [ "$start" -gt 0 ] || exit 0

    elapsed=$(( $(date +%s) - start ))
    [ "$elapsed" -ge "$MIN_SECONDS" ] || exit 0

    mins=$(( elapsed / 60 ))
    secs=$(( elapsed % 60 ))
    if [ "$mins" -gt 0 ]; then
      duration="${mins}m ${secs}s"
    else
      duration="${secs}s"
    fi

    cwd="$(field '.cwd')"
    [ -n "$cwd" ] || cwd="$PWD"
    project="$(basename "$cwd")"

    body="Stopped after ${duration} in ${project}. Check whether it finished or needs you."

    if [ -x "$SENDER" ]; then
      "$SENDER" --topic "$TOPIC" --title "Claude Code — ${project}" "$body" >/dev/null 2>&1 \
        || curl -fsS -d "$body" "https://ntfy.sh/$TOPIC" >/dev/null 2>&1 || true
    else
      curl -fsS -d "$body" "https://ntfy.sh/$TOPIC" >/dev/null 2>&1 || true
    fi
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
