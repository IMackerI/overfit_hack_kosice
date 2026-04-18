#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p .logs .run .mongo-data

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

: "${BOT_TOKEN:?BOT_TOKEN must be set in .env}"
: "${WEBHOOK_SECRET:?WEBHOOK_SECRET must be set in .env}"

if [[ -n "${NGROK_AUTHTOKEN:-}" ]]; then
  ngrok config add-authtoken "$NGROK_AUTHTOKEN" >/dev/null
fi

MONGO_PID_FILE="$ROOT/.run/mongod.pid"
APP_PID_FILE="$ROOT/.run/app.pid"
NGROK_PID_FILE="$ROOT/.run/ngrok.pid"
NGROK_URL_FILE="$ROOT/.run/ngrok_url.txt"

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

wait_for_http() {
  local url="$1"
  local tries="${2:-30}"
  for ((i = 0; i < tries; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

if ss -ltn '( sport = :27017 )' | grep -q 27017; then
  echo "MongoDB already running on 27017"
else
  mongod \
    --dbpath "$ROOT/.mongo-data" \
    --bind_ip 127.0.0.1 \
    --port 27017 \
    --fork \
    --logpath "$ROOT/.logs/mongod.log" \
    --pidfilepath "$MONGO_PID_FILE"
  echo "Started MongoDB"
fi

if [[ -f "$APP_PID_FILE" ]] && is_pid_running "$(cat "$APP_PID_FILE")"; then
  echo "App already running"
else
  nohup env PYTHONPATH=src uv run python src/app.py > "$ROOT/.logs/app.log" 2>&1 &
  echo $! > "$APP_PID_FILE"
  echo "Started Flask app"
fi

wait_for_http "http://127.0.0.1:5001/" 30

if [[ -f "$NGROK_PID_FILE" ]] && is_pid_running "$(cat "$NGROK_PID_FILE")"; then
  echo "ngrok already running"
else
  nohup ngrok http 5001 --log=stdout > "$ROOT/.logs/ngrok.log" 2>&1 &
  echo $! > "$NGROK_PID_FILE"
  echo "Started ngrok"
fi

wait_for_http "http://127.0.0.1:4040/api/tunnels" 30

PUBLIC_URL="$({ python - <<'PY'
import json
from urllib.error import URLError
from urllib.request import urlopen

try:
    with urlopen('http://127.0.0.1:4040/api/tunnels') as response:
        data = json.load(response)
except URLError:
    data = {}

for tunnel in data.get('tunnels', []):
    url = tunnel.get('public_url', '')
    if url.startswith('https://'):
        print(url)
        break
PY
} | tail -n 1)"

if [[ -z "$PUBLIC_URL" ]]; then
  echo "Could not determine ngrok public URL." >&2
  echo "If ngrok is installed but not authenticated, set NGROK_AUTHTOKEN in .env." >&2
  echo "See .logs/ngrok.log for details." >&2
  exit 1
fi

printf '%s\n' "$PUBLIC_URL" > "$NGROK_URL_FILE"

WEBHOOK_URL="$PUBLIC_URL/webhook/$WEBHOOK_SECRET"
curl -fsS "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  --data-urlencode "url=$WEBHOOK_URL" \
  > "$ROOT/.logs/set_webhook.json"

echo ""
echo "App:        http://127.0.0.1:5001"
echo "ngrok:      $PUBLIC_URL"
echo "Webhook:    $WEBHOOK_URL"
echo "Logs:       $ROOT/.logs"
