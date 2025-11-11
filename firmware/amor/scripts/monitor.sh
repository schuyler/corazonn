#!/bin/bash

DEBOUNCE_TIME=2
WATCH_DIRS="src include"
TRIGGER_FILE="/tmp/pio_rebuild_trigger_$$"

cleanup() {
    echo "Shutting down..."
    rm -f "$TRIGGER_FILE"
    pkill -P $$ 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

if ! command -v inotifywait &> /dev/null; then
    echo "Error: inotifywait is not installed. Install with: sudo apt-get install inotify-tools"
    exit 1
fi

# Start file watcher in background - it will kill the monitor when changes detected
(
    while true; do
        inotifywait -r -e modify,create,delete,move --include '.*\.(cpp|h)$' $WATCH_DIRS 2>/dev/null

        # Debounce: wait for burst of changes to settle
        sleep $DEBOUNCE_TIME

        # Consume any additional events that happened during debounce
        while inotifywait -t 0.5 -r -e modify,create,delete,move --include '.*\.(cpp|h)$' $WATCH_DIRS 2>/dev/null; do
            :
        done

        # Signal that we need to rebuild
        touch "$TRIGGER_FILE"

        # Kill the monitor (it's running in foreground in parent)
        pkill -P $$ pio 2>/dev/null
    done
) &

echo "Starting initial monitor (waiting for changes to trigger rebuild)..."

while true; do
    # Start monitor in foreground (not backgrounded)
    pio device monitor

    # Monitor exited - check if it was because of a file change
    if [ -f "$TRIGGER_FILE" ]; then
        echo ""
        echo "Change detected - rebuilding..."
        rm -f "$TRIGGER_FILE"

        echo "Running build and upload..."
        pio run -t upload

        if [ $? -eq 0 ]; then
            echo "Build successful - restarting monitor..."
            sleep 1
        else
            echo "Build failed - restarting monitor anyway..."
            sleep 2
        fi
    else
        # Monitor exited for another reason (user quit, error, etc)
        echo "Monitor exited"
        break
    fi
done
