#!/usr/bin/env bash
set -euo pipefail
# start-kiosk.sh
#
# Launch the backend (gunicorn) and open Chromium in kiosk mode. Designed to
# be executed as the kiosk user (e.g. `steve`) after an X session is available.

# Configuration (edit if necessary)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$APP_DIR/.venv"
URL="http://127.0.0.1:8000/"
GUNICORN="$VENV/bin/gunicorn"
CHROMIUM="/usr/bin/chromium-browser"
LOG_DIR="/tmp"

echo "[kiosk] starting from $APP_DIR"
cd "$APP_DIR"

# Create venv if missing (helpful on first-run)
if [ ! -d "$VENV" ]; then
  echo "[kiosk] creating venv at $VENV"
  python -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r requirements.txt
fi

# Start Gunicorn if available
if [ -x "$GUNICORN" ]; then
  if ! pgrep -f "gunicorn.*app:create_app" >/dev/null 2>&1; then
    echo "[kiosk] launching gunicorn"
    nohup "$GUNICORN" --workers 2 --bind 127.0.0.1:8000 'app:create_app()' > "$LOG_DIR/dryer-gunicorn.log" 2>&1 &
    sleep 1
  else
    echo "[kiosk] gunicorn already running"
  fi
else
  echo "[kiosk] warning: gunicorn not found at $GUNICORN; backend won't be started"
fi

# Wait a moment for the web server
sleep 1

# Ensure DISPLAY is set (assumes an X session on :0)
export DISPLAY=${DISPLAY:-:0}
export XAUTHORITY=${XAUTHORITY:-"$HOME/.Xauthority"}

# Start Chromium in kiosk mode
if command -v "$CHROMIUM" >/dev/null 2>&1; then
  echo "[kiosk] launching Chromium kiosk to $URL"
  # Common flags: --kiosk, --incognito, --noerrdialogs, --disable-infobars
  exec "$CHROMIUM" --kiosk --incognito --noerrdialogs --disable-translate --disable-infobars "$URL"
else
  echo "[kiosk] chromium not found at $CHROMIUM. Install chromium-browser and try again."
  exit 1
fi
