#!/usr/bin/env python3
"""
Test that final statistics print even with multiple SIGINTs during shutdown.
This tests the specific bug fix for handling KeyboardInterrupt during thread.join().
"""

import subprocess
import time
import signal
import sys
import re
import os

def test_multiple_sigint():
    """Test that final statistics output works even with rapid SIGINTs"""

    print("Starting simulator...")
    # Start simulator without ignoring SIGINT
    proc = subprocess.Popen(
        ['python3', '/home/user/corazonn/testing/esp32_simulator.py',
         '--sensors', '2', '--bpm', '60,72'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Let it run for 2 seconds
    time.sleep(2)

    # Send first SIGINT
    print("Sending first SIGINT...")
    proc.send_signal(signal.SIGINT)

    # Send second SIGINT shortly after (simulating impatient user)
    time.sleep(0.1)
    print("Sending second SIGINT (during shutdown)...")
    proc.send_signal(signal.SIGINT)

    # Wait for process to finish and collect output
    try:
        output, _ = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
        print("FAIL: Process timed out (hung during shutdown)")
        return False

    print("\n=== SIMULATOR OUTPUT ===")
    print(output)
    print("=== END OUTPUT ===\n")

    # Check for final statistics line
    stats_pattern = r'SIMULATOR_FINAL_STATS: sensor_0=(\d+), sensor_1=(\d+), sensor_2=(\d+), sensor_3=(\d+), total=(\d+)'
    match = re.search(stats_pattern, output)

    if match:
        sensor_0, sensor_1, sensor_2, sensor_3, total = map(int, match.groups())
        print("SUCCESS: Final statistics found despite multiple SIGINTs")
        print(f"  Sensor 0: {sensor_0} messages")
        print(f"  Sensor 1: {sensor_1} messages")
        print(f"  Total: {total} messages")

        # Verify active sensors sent messages
        if sensor_0 > 0 and sensor_1 > 0:
            print("PASS: All active sensors sent messages")
        else:
            print("FAIL: Not all active sensors sent messages")
            return False

        # Verify total matches sum
        if total == sensor_0 + sensor_1 + sensor_2 + sensor_3:
            print("PASS: Total matches sum of sensor counts")
        else:
            print("FAIL: Total doesn't match sum")
            return False

        return True
    else:
        print("FAIL: Final statistics line not found in output")
        print("This is the critical bug - stats should ALWAYS print on shutdown")
        return False

if __name__ == '__main__':
    try:
        success = test_multiple_sigint()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
