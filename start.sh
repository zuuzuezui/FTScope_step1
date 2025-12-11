#!/usr/bin/env bash
set -euo pipefail

# --- normalize this file's line endings so shebang doesn't contain CRLF
# (modify the file in-place, safe on Linux)
if grep -q $'\r' "$0"; then
  echo "[start.sh] Detected CRLF in this script — converting to LF"
  sed -i 's/\r$//' "$0" || true
fi

# --- helper: try to run a command quietly
run_quiet() { command "$@" >/dev/null 2>&1; }

# --- ensure ss / netstat availability (used to inspect sockets)
have_cmd() { command -v "$1" >/dev/null 2>&1; }

ensure_network_tool() {
  if have_cmd ss || have_cmd netstat || have_cmd lsof; then
    return 0
  fi

  echo "[start.sh] 'ss' / 'netstat' / 'lsof' not found — attempting to install iproute2 (provides ss)"
  if have_cmd apt-get; then
    apt-get update && apt-get install -y iproute2 || {
      echo "[start.sh] apt install failed, continuing without ss"
      return 1
    }
  elif have_cmd apk; then
    apk add --no-cache iproute2 || {
      echo "[start.sh] apk add failed, continuing without ss"
      return 1
    }
  elif have_cmd yum; then
    yum install -y iproute || {
      echo "[start.sh] yum install failed, continuing without ss"
      return 1
    }
  else
    echo "[start.sh] No supported package manager found (apt/yum/apk). Skipping install."
    return 1
  fi
}

# --- portable socket-listing function
list_listening_ports() {
  if have_cmd ss; then
    ss -tuln
  elif have_cmd netstat; then
    netstat -tuln
  elif have_cmd lsof; then
    lsof -i -P -n
  else
    echo "[start.sh] No tool available to list sockets"
    return 1
  fi
}

# --- try to ensure tools (best-effort)
ensure_network_tool || true

# --- sensible defaults for env vars (override in Render dashboard / env file)
: "${HEADLESS:=1}"       # default to headless for container environments
: "${CHROME_BIN:=/usr/bin/chromium}"
: "${WEB_CONCURRENCY:=1}"  # simple default
export HEADLESS CHROME_BIN WEB_CONCURRENCY

echo "[start.sh] HEADLESS=${HEADLESS}, CHROME_BIN=${CHROME_BIN}, WEB_CONCURRENCY=${WEB_CONCURRENCY}"

# --- show listening ports (debug info)
echo "[start.sh] Current listening ports (if any):"
list_listening_ports || echo "[start.sh] (could not list ports)"

# --- ensure python is unbuffered for logs
PYTHON_CMD=${PYTHON_CMD:-python3}
if ! command -v $PYTHON_CMD >/dev/null 2>&1; then
  echo "[start.sh] Warning: $PYTHON_CMD not found in PATH"
fi

# --- Minimal HTTP server fallback (if you used one previously)
# If your app expects a background "minimal HTTP server", keep it; otherwise remove.
start_minimal_http_server() {
  # If you have a small script to start a health-port, call it here.
  # Example: python3 -m http.server 10000 &  # uncomment if needed
  return 0
}

start_minimal_http_server || true

# --- Launch main app (adjust command to your app's real entrypoint)
# Use -u so python doesn't buffer stdout/stderr in containers
echo "[start.sh] Launching core1.py..."
exec $PYTHON_CMD -u core1.py
