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

if [ "$(uname -m)" = "arm64" ]; then
    MINISERVE_BIN="./_site/.server/miniserve-macos-arm64"
else
    MINISERVE_BIN="./_site/.server/miniserve-macos-x86_64"
fi

# The binary should already be executable from how it was bundled (copy2
# preserves the exec bit); this chmod is a defensive no-op in the common
# case, so tolerate failure on read-only media (e.g. a mounted read-only
# DMG or USB stick) instead of aborting under set -e.
chmod +x "$MINISERVE_BIN" || true
"$MINISERVE_BIN" -i 127.0.0.1 -p "$PORT" --index index.html --disable-indexing ./_site &
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
