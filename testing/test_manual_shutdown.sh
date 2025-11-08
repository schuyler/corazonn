#!/bin/bash
# Test script to verify graceful shutdown

cd /home/user/corazonn/testing

# Run simulator for 5 seconds then send SIGINT once
python3 esp32_simulator.py --sensors 4 --bpm 60,72,58,80 &
SIMPID=$!

sleep 5

# Send single SIGINT (Ctrl+C)
kill -INT $SIMPID

# Wait for process to finish
wait $SIMPID

echo "Exit code: $?"
