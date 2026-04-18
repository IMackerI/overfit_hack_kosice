#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

APP_PID_FILE="$ROOT/.run/app.pid"
NGROK_PID_FILE="$ROOT/.run/ngrok.pid"
MONGO_PID_FILE="$ROOT/.run/mongod.pid"

kill_pidfile() {
  local file="$1"
  if [[ -f "$file" ]]; then
    local pid
    pid="$(cat "$file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$file"
  fi
}

if [[ -n "${BOT_TOKEN:-}" ]]; then
  curl -fsS "https://api.telegram.org/bot$BOT_TOKEN/deleteWebhook" > "$ROOT/.logs/delete_webhook.json" || true
fi

kill_pidfile "$NGROK_PID_FILE"
kill_pidfile "$APP_PID_FILE"
kill_pidfile "$MONGO_PID_FILE"

pkill -f "$ROOT/.venv/bin/python3 src/app.py" 2>/dev/null || true
pkill -f "ngrok http 5001" 2>/dev/null || true
pkill -f "mongod --dbpath $ROOT/.mongo-data" 2>/dev/null || true

rm -f "$ROOT/.run/ngrok_url.txt"

echo "Stopped app, ngrok, and MongoDB"
