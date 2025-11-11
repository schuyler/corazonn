#!/usr/bin/env python3
"""
Test script for sending control messages to Sequencer.

Simulates Launchpad Bridge sending button press messages.

Usage:
    python3 testing/test_sequencer_control.py
"""

import time
from pythonosc import udp_client

# Sequencer control port
SEQUENCER_PORT = 8003


def main():
    """Send test control messages to sequencer."""
    client = udp_client.SimpleUDPClient("127.0.0.1", SEQUENCER_PORT)

    print("Sending test control messages to Sequencer on port", SEQUENCER_PORT)
    print()

    # Test 1: Select different columns for PPG sensors
    print("Test 1: PPG sample selection")
    for ppg_id in range(4):
        column = (ppg_id + 1) % 8  # Select columns 1, 2, 3, 4
        print(f"  Sending /select/{ppg_id} [{column}]")
        client.send_message(f"/select/{ppg_id}", column)
        time.sleep(0.5)

    print()

    # Test 2: Toggle some latching loops
    print("Test 2: Latching loop toggles (loops 0-15)")
    for loop_id in [0, 5, 10, 15]:
        print(f"  Sending /loop/toggle [{loop_id}] (turn ON)")
        client.send_message("/loop/toggle", loop_id)
        time.sleep(0.3)

    time.sleep(1)

    # Toggle them off
    for loop_id in [0, 5, 10, 15]:
        print(f"  Sending /loop/toggle [{loop_id}] (turn OFF)")
        client.send_message("/loop/toggle", loop_id)
        time.sleep(0.3)

    print()

    # Test 3: Momentary loops
    print("Test 3: Momentary loops (loops 16-31)")
    for loop_id in [16, 20, 24, 28]:
        print(f"  Sending /loop/momentary [{loop_id}] [1] (press)")
        client.send_message("/loop/momentary", [loop_id, 1])
        time.sleep(0.5)
        print(f"  Sending /loop/momentary [{loop_id}] [0] (release)")
        client.send_message("/loop/momentary", [loop_id, 0])
        time.sleep(0.3)

    print()

    # Test 4: Change PPG selections back to column 0
    print("Test 4: Reset PPG selections to column 0")
    for ppg_id in range(4):
        print(f"  Sending /select/{ppg_id} [0]")
        client.send_message(f"/select/{ppg_id}", 0)
        time.sleep(0.3)

    print()
    print("Test complete!")


if __name__ == "__main__":
    main()
