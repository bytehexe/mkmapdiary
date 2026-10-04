#!/bin/bash
# Starts the bundled viewer server and opens this journal in your browser.
# Close this terminal window to stop viewing.
set -eu

cd "$(dirname "$0")"

PORTS="51342 51343 51344 51345 51346"
PORT=""
for candidate in $PORTS; do
    if ! nc -z 127.0.0.1 "$candidate" 2>/dev/null; then
        PORT="$candidate"
        break
    fi
done

if [ -z "$PORT" ]; then
    echo "Could not find a free port among: $PORTS"
    echo "Close whatever is using one of these ports and try again."
    exit 1
fi

chmod +x ./_site/.server/miniserve-macos
./_site/.server/miniserve-macos -i 127.0.0.1 -p "$PORT" --index index.html --disable-indexing ./_site &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 50); do
    if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
        break
    fi
    sleep 0.1
done

URL="http://127.0.0.1:$PORT/"
open "$URL" >/dev/null 2>&1 || echo "Open this URL in your browser: $URL"

echo "Your travel journal is running at $URL"
echo "Close this window to stop viewing."
wait "$SERVER_PID"
