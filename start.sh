#!/usr/bin/env bash
set -euo pipefail


# Convert CRLF to LF if present (prévenir env: 'bash\r' errors)
if grep -q $'\r' "$0" 2>/dev/null; then
echo "[start.sh] Detected CRLF in this script — converting to LF"
sed -i 's/\r$//' "$0" || true
fi


have_cmd() { command -v "$1" >/dev/null 2>&1; }


# Show basic debug info
: "${HEADLESS:=1}"
: "${CHROME_BIN:=/usr/bin/chromium}"
: "${WEB_CONCURRENCY:=1}"
export HEADLESS CHROME_BIN WEB_CONCURRENCY


echo "[start.sh] HEADLESS=${HEADLESS}, CHROME_BIN=${CHROME_BIN}, WEB_CONCURRENCY=${WEB_CONCURRENCY}"


# Try to list sockets if possible (non-fatal)
if have_cmd ss; then
ss -tuln || true
elif have_cmd netstat; then
netstat -tuln || true
elif have_cmd lsof; then
lsof -i -P -n || true
else
echo "[start.sh] no ss/netstat/lsof found (non-fatal)"
fi


# Launch minimal HTTP server if needed (décommenter si utilisé)
# python3 -m http.server 10000 &


# Launch app (unbuffered stdout/stderr)
PYTHON_CMD=${PYTHON_CMD:-python3}
if ! have_cmd "$PYTHON_CMD"; then
echo "[start.sh] Warning: $PYTHON_CMD not found in PATH"
fi


echo "[start.sh] Launching core1.py..."
exec "$PYTHON_CMD" -u core1.pys
