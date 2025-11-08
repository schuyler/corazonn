#!/usr/bin/env python3
"""
ESP32 Simulator - Phase 1 Testing Infrastructure
Simulates 1-4 ESP32 sensor units sending OSC heartbeat messages.

Reference: p1-tst-trd.md, Requirements R1-R6
"""

import argparse
import random
import sys
import threading
import time
from pythonosc import udp_client

# Constants
MS_PER_MINUTE = 60000
MIN_IBI = 300
MAX_IBI = 3000
MIN_BPM = 20
MAX_BPM = 200
VARIANCE_FACTOR = 0.05  # ±5%

# Global state (shared across threads)
sensor_message_counts = [0, 0, 0, 0]
print_lock = threading.Lock()
shutdown_event = threading.Event()


# === Core IBI Calculation Functions (R2) ===

def calculate_base_ibi(bpm):
    """
    Calculate base inter-beat interval from BPM.

    Args:
        bpm: Beats per minute (int or float)

    Returns:
        Base IBI in milliseconds (int)
    """
    return int(MS_PER_MINUTE / bpm)


def generate_ibi_with_variance(base_ibi):
    """
    Generate IBI value with ±5% random variance.

    Args:
        base_ibi: Base IBI value in milliseconds

    Returns:
        IBI with variance applied (int), NOT clamped
    """
    variance = random.uniform(-VARIANCE_FACTOR, VARIANCE_FACTOR) * base_ibi
    return int(base_ibi + variance)


def clamp_ibi(ibi):
    """
    Clamp IBI to valid range (300-3000ms).

    Args:
        ibi: IBI value in milliseconds

    Returns:
        Clamped IBI value (int)
    """
    if ibi < MIN_IBI:
        return MIN_IBI
    if ibi > MAX_IBI:
        return MAX_IBI
    return ibi


def calculate_ibi(bpm):
    """
    Calculate IBI from BPM with variance and clamping.

    Combines base calculation, variance, and clamping per R2.

    Args:
        bpm: Beats per minute

    Returns:
        Final IBI value in milliseconds (int)
    """
    base_ibi = calculate_base_ibi(bpm)
    ibi_with_variance = generate_ibi_with_variance(base_ibi)
    return clamp_ibi(ibi_with_variance)


# === Input Validation Functions (R5) ===

def validate_sensor_count(count):
    """
    Validate sensor count is in range 1-4.

    Args:
        count: Number of sensors

    Returns:
        True if valid, False otherwise
    """
    return 1 <= count <= 4


def validate_bpm_values(bpm_list):
    """
    Validate all BPM values are in range 20-200.

    Args:
        bpm_list: List of BPM values

    Returns:
        True if all valid, False if any invalid
    """
    return all(MIN_BPM <= bpm <= MAX_BPM for bpm in bpm_list)


# === Statistics Functions (R6) ===

def format_final_statistics(counts):
    """
    Format final statistics in parseable format.

    Args:
        counts: List of message counts [sensor_0, sensor_1, sensor_2, sensor_3]

    Returns:
        Formatted statistics string
    """
    total = sum(counts)
    return (f"SIMULATOR_FINAL_STATS: "
            f"sensor_0={counts[0]}, "
            f"sensor_1={counts[1]}, "
            f"sensor_2={counts[2]}, "
            f"sensor_3={counts[3]}, "
            f"total={total}")


def print_message(sensor_id, ibi, count):
    """
    Thread-safe printing of sent messages.

    Args:
        sensor_id: Sensor ID (0-3)
        ibi: IBI value sent
        count: Message count for this sensor
    """
    with print_lock:
        print(f"[Sensor {sensor_id}] Sent /heartbeat/{sensor_id} {ibi} (#{count})")


# === Sensor Thread Function (R1, R3, R4) ===

def sensor_thread(sensor_id, bpm, server_ip, server_port):
    """
    Thread function simulating a single ESP32 sensor.

    Continuously generates heartbeat messages at specified BPM
    until shutdown_event is set.

    Args:
        sensor_id: Sensor ID (0-3)
        bpm: Target beats per minute
        server_ip: Destination IP address
        server_port: Destination UDP port
    """
    # Create OSC client for this sensor (R3)
    client = udp_client.SimpleUDPClient(server_ip, server_port)
    address = f"/heartbeat/{sensor_id}"

    # Main sensor loop
    while not shutdown_event.is_set():
        # Generate IBI with variance (R2)
        ibi = calculate_ibi(bpm)

        # Send OSC message (R3)
        try:
            client.send_message(address, ibi)
        except Exception as e:
            with print_lock:
                print(f"ERROR: Sensor {sensor_id}: Failed to send message: {e}",
                      file=sys.stderr)
            # Continue running even if send fails

        # Update counter and print (R6)
        sensor_message_counts[sensor_id] += 1
        print_message(sensor_id, ibi, sensor_message_counts[sensor_id])

        # Sleep for IBI duration to simulate timing (R4)
        # Use milliseconds, convert to seconds for time.sleep()
        time.sleep(ibi / 1000.0)


# === Command-Line Interface (R5) ===

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='ESP32 Heartbeat Simulator - Simulates 1-4 sensor units sending OSC messages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --sensors 1 --bpm 60
  %(prog)s --sensors 4 --bpm 60,72,58,80
  %(prog)s --sensors 2 --bpm 65,70 --server 192.168.50.100
        """
    )

    parser.add_argument('--sensors', type=int, default=1,
                       help='Number of sensors to simulate (1-4, default: 1)')
    parser.add_argument('--bpm', type=str, default='60',
                       help='Comma-separated BPM values, one per sensor (default: 60)')
    parser.add_argument('--server', type=str, default='127.0.0.1',
                       help='Destination IP address (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000,
                       help='Destination UDP port (default: 8000)')

    return parser.parse_args()


def validate_arguments(args):
    """
    Validate parsed arguments.

    Args:
        args: Parsed arguments namespace

    Returns:
        (is_valid, error_message, bpm_list)
        - is_valid: True if valid, False otherwise
        - error_message: Error description if invalid, None if valid
        - bpm_list: Parsed list of BPM values (if valid)
    """
    # Validate sensor count (R5)
    if not validate_sensor_count(args.sensors):
        return False, f"Invalid sensor count: {args.sensors} (must be 1-4)", None

    # Parse BPM values
    try:
        bpm_list = [int(x.strip()) for x in args.bpm.split(',')]
    except ValueError:
        return False, f"Invalid BPM format: {args.bpm} (must be comma-separated integers)", None

    # Check BPM count matches sensor count
    if len(bpm_list) != args.sensors:
        return False, (f"BPM count mismatch: {len(bpm_list)} values for {args.sensors} sensors "
                      f"(must match)"), None

    # Validate BPM values (R5)
    if not validate_bpm_values(bpm_list):
        invalid = [bpm for bpm in bpm_list if bpm < MIN_BPM or bpm > MAX_BPM]
        return False, f"Invalid BPM values: {invalid} (must be {MIN_BPM}-{MAX_BPM})", None

    return True, None, bpm_list


# === Main Function ===

def main():
    """
    Main entry point for ESP32 simulator.
    """
    # Parse and validate arguments
    args = parse_arguments()
    is_valid, error_msg, bpm_list = validate_arguments(args)

    if not is_valid:
        print(f"ERROR: Simulator: {error_msg}", file=sys.stderr)
        sys.exit(1)

    # Print startup information
    print(f"ESP32 Simulator starting...")
    print(f"  Sensors: {args.sensors}")
    print(f"  BPM values: {bpm_list}")
    print(f"  Target: {args.server}:{args.port}")
    print()

    # Create and start sensor threads (R1)
    threads = []
    for sensor_id in range(args.sensors):
        bpm = bpm_list[sensor_id]
        thread = threading.Thread(
            target=sensor_thread,
            args=(sensor_id, bpm, args.server, args.port),
            name=f"Sensor-{sensor_id}"
        )
        thread.daemon = True  # Allow main thread to exit even if threads running
        threads.append(thread)
        thread.start()

    print(f"All {args.sensors} sensor(s) started. Press Ctrl+C to stop.\n")

    # Wait for keyboard interrupt (R6)
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutdown signal received. Stopping sensors...")

        # Signal all threads to stop
        shutdown_event.set()

        # Wait for threads to finish (with timeout)
        try:
            for thread in threads:
                thread.join(timeout=2.0)
        except KeyboardInterrupt:
            pass  # Already shutting down, ignore subsequent signals

        # Print final statistics (R6) - ALWAYS execute
        print("\n" + format_final_statistics(sensor_message_counts))


if __name__ == '__main__':
    main()
