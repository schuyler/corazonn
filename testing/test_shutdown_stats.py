#!/usr/bin/env python3
"""
Test script to verify final statistics output on KeyboardInterrupt
"""

import subprocess
import time
import signal
import sys
import re

def test_final_statistics():
    """Test that simulator outputs proper final statistics on shutdown"""

    # Start simulator
    proc = subprocess.Popen(
        ['python3', '/home/user/corazonn/testing/esp32_simulator.py',
         '--sensors', '4', '--bpm', '60,72,58,80'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
    )

    # Let it run for 3 seconds
    time.sleep(3)

    # Send SIGINT to simulator
    proc.send_signal(signal.SIGINT)

    # Wait for process to finish and collect output
    output, _ = proc.communicate(timeout=5)

    print("=== SIMULATOR OUTPUT ===")
    print(output)
    print("=== END OUTPUT ===\n")

    # Check for final statistics line
    stats_pattern = r'SIMULATOR_FINAL_STATS: sensor_0=(\d+), sensor_1=(\d+), sensor_2=(\d+), sensor_3=(\d+), total=(\d+)'
    match = re.search(stats_pattern, output)

    if match:
        sensor_0, sensor_1, sensor_2, sensor_3, total = map(int, match.groups())
        print("SUCCESS: Final statistics found")
        print(f"  Sensor 0: {sensor_0} messages")
        print(f"  Sensor 1: {sensor_1} messages")
        print(f"  Sensor 2: {sensor_2} messages")
        print(f"  Sensor 3: {sensor_3} messages")
        print(f"  Total: {total} messages")

        # Verify all sensors sent messages
        if all([sensor_0 > 0, sensor_1 > 0, sensor_2 > 0, sensor_3 > 0]):
            print("PASS: All 4 sensors sent messages")
        else:
            print("FAIL: Not all sensors sent messages")
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
        return False

if __name__ == '__main__':
    try:
        success = test_final_statistics()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
