#!/usr/bin/env python3
"""
Test that final statistics print correctly with normal single SIGINT shutdown.
"""

import subprocess
import time
import signal
import sys
import re

def test_single_sigint():
    """Test normal shutdown with single SIGINT"""

    print("Starting simulator...")
    proc = subprocess.Popen(
        ['python3', '/home/user/corazonn/testing/esp32_simulator.py',
         '--sensors', '1', '--bpm', '60'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Let it run for 1.5 seconds
    time.sleep(1.5)

    # Send single SIGINT (normal shutdown)
    print("Sending SIGINT...")
    proc.send_signal(signal.SIGINT)

    # Wait for process to finish
    try:
        output, _ = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
        print("FAIL: Process timed out")
        return False

    print("\n=== SIMULATOR OUTPUT ===")
    print(output)
    print("=== END OUTPUT ===\n")

    # Check for final statistics
    stats_pattern = r'SIMULATOR_FINAL_STATS: sensor_0=(\d+), sensor_1=(\d+), sensor_2=(\d+), sensor_3=(\d+), total=(\d+)'
    match = re.search(stats_pattern, output)

    if match:
        sensor_0, sensor_1, sensor_2, sensor_3, total = map(int, match.groups())
        print("PASS: Final statistics found")
        print(f"  Sensor 0: {sensor_0} messages")
        print(f"  Total: {total} messages")
        return sensor_0 > 0 and total == sensor_0
    else:
        print("FAIL: Final statistics not found")
        return False

if __name__ == '__main__':
    success = test_single_sigint()
    sys.exit(0 if success else 1)
