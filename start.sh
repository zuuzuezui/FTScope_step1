#!/bin/bash
# Start script used by Docker / Render
# - ouvre un port HTTP minimal pour que Render détecte un port ouvert
# - lance ensuite core1.py (le bot)
set -euo pipefail

PORT="${PORT:-10000}"

# Start a minimal static HTTP server in background to keep the container "web" and expose $PORT.
# This is a simple trick: python -m http.server is fine (serves current directory).
# If tu as Flask ou un vrai endpoint, remplace cette ligne.
echo "Starting minimal HTTP server on port ${PORT} (background)..."
# redirect output to /dev/null to keep logs cleaner (adjust if you want logs)
python3 -m http.server "${PORT}" >/dev/null 2>&1 &

HTTP_PID=$!
echo "HTTP server started (pid ${HTTP_PID})"

# Give http server a moment
sleep 0.5

# Run the main script (core1.py)
echo "Launching core1.py..."
python3 core1.py

# When core1.py exits, we gracefully stop the background http server
echo "core1.py exited. Stopping HTTP server (pid ${HTTP_PID})..."
kill "${HTTP_PID}" 2>/dev/null || true
wait "${HTTP_PID}" 2>/dev/null || true
echo "Done."

ss