#!/usr/bin/env python3
"""
OSC Test Sender - Phase 1 Testing Infrastructure
Standalone OSC sender for testing Pd patch without ESP32 dependency.

Reference: phase1-trd.md, Requirements R33-R40
"""

import argparse
import random
import sys
import threading
import time
from pythonosc import udp_client

# Constants (R36)
MIN_IBI = 600  # 100 BPM
MAX_IBI = 1200  # 50 BPM
VARIANCE_FACTOR = 0.10  # ±10%

# Global state (shared across threads)
sensor_message_counts = {}
print_lock = threading.Lock()
shutdown_event = threading.Event()


# === Core IBI Generation Functions (R36) ===

def random_base_ibi():
    """
    Generate random base IBI in range 600-1200ms.

    Returns:
        Base IBI in milliseconds (int)
    """
    return random.randint(MIN_IBI, MAX_IBI)


def generate_ibi_with_variance(base_ibi):
    """
    Generate IBI value with ±10% random variance per beat.

    Args:
        base_ibi: Base IBI value in milliseconds

    Returns:
        IBI with variance applied (int)
    """
    variance = random.uniform(-VARIANCE_FACTOR, VARIANCE_FACTOR) * base_ibi
    return int(base_ibi + variance)


def generate_ibi():
    """
    Generate IBI value with random base and variance.

    Implements R36: Random IBI in range 600-1200ms with ±10% variation per beat.

    Returns:
        Final IBI value in milliseconds (int)
    """
    base_ibi = random_base_ibi()
    return generate_ibi_with_variance(base_ibi)


# === Output Functions (R38) ===

def print_message(sensor_id, ibi, count):
    """
    Thread-safe printing of sent messages.

    Implements R38: Print format "Sent /heartbeat/N <ibi>"

    Args:
        sensor_id: Sensor ID (0 to sensors-1)
        ibi: IBI value sent
        count: Message count for this sensor
    """
    with print_lock:
        print(f"Sent /heartbeat/{sensor_id} {ibi}")


# === Sensor Thread Function (R34, R35, R36, R37, R38) ===

def sensor_thread(sensor_id, target_ip, target_port):
    """
    Thread function simulating a single sensor sending heartbeats.

    Continuously generates heartbeat messages with random IBI timing
    until shutdown_event is set.

    Implements:
    - R34: Send to 127.0.0.1:<port>
    - R35: Generate /heartbeat/N messages
    - R36: Random IBI 600-1200ms with ±10% variation
    - R37: Independent timing (separate thread per sensor)
    - R38: Print sent messages

    Args:
        sensor_id: Sensor ID (0 to sensors-1)
        target_ip: Destination IP address (127.0.0.1)
        target_port: Destination UDP port
    """
    # Create OSC client for this sensor (R34)
    client = udp_client.SimpleUDPClient(target_ip, target_port)
    address = f"/heartbeat/{sensor_id}"  # R35

    # Initialize message counter
    sensor_message_counts[sensor_id] = 0

    # Main sensor loop
    while not shutdown_event.is_set():
        # Generate random IBI with variance (R36)
        ibi = generate_ibi()

        # Send OSC message (R34, R35)
        try:
            client.send_message(address, ibi)
        except Exception as e:
            with print_lock:
                print(f"ERROR: Sensor {sensor_id}: Failed to send message: {e}",
                      file=sys.stderr)
            # Continue running even if send fails

        # Update counter and print (R38)
        sensor_message_counts[sensor_id] += 1
        print_message(sensor_id, ibi, sensor_message_counts[sensor_id])

        # Sleep for IBI duration to simulate realistic timing (R37)
        # Use milliseconds, convert to seconds for time.sleep()
        time.sleep(ibi / 1000.0)


# === Command-Line Interface (R33) ===

def parse_arguments(args=None):
    """
    Parse command-line arguments.

    Implements R33: Accept --port <int> and --sensors <int> arguments.

    Args:
        args: Optional list of arguments (for testing). If None, uses sys.argv.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='OSC Test Sender - Standalone heartbeat message generator for testing Pd patch',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --port 8000 --sensors 4
  %(prog)s --port 8000 --sensors 1

Requirements:
  - Sends to 127.0.0.1:<port> (R34)
  - Generates /heartbeat/N messages for N in range(sensors) (R35)
  - IBI values: 600-1200ms with ±10%% variation per beat (R36)
  - Independent timing per sensor (R37)
  - Prints each sent message (R38)
  - Runs until Ctrl-C (R39)
        """
    )

    parser.add_argument('--port', type=int, required=True,
                       help='Destination UDP port (required)')
    parser.add_argument('--sensors', type=int, default=1,
                       help='Number of sensors to simulate (default: 1)')

    return parser.parse_args(args)


def validate_arguments(args):
    """
    Validate parsed arguments.

    Args:
        args: Parsed arguments namespace

    Returns:
        (is_valid, error_message)
    """
    # Validate port
    if args.port < 1 or args.port > 65535:
        return False, f"Invalid port: {args.port} (must be 1-65535)"

    # Validate sensor count
    if args.sensors < 1:
        return False, f"Invalid sensor count: {args.sensors} (must be >= 1)"

    return True, None


def format_final_statistics(counts):
    """
    Format final statistics in parseable format.

    Args:
        counts: Dictionary of message counts {sensor_id: count}

    Returns:
        Formatted statistics string
    """
    total = sum(counts.values())
    sensor_stats = ", ".join([f"sensor_{sid}={count}"
                              for sid, count in sorted(counts.items())])
    return f"OSC_SENDER_FINAL_STATS: {sensor_stats}, total={total}"


# === Main Function ===

def main():
    """
    Main entry point for OSC test sender.

    Implements R39: Run until Ctrl-C with graceful shutdown.
    """
    # Parse and validate arguments (R33)
    args = parse_arguments()
    is_valid, error_msg = validate_arguments(args)

    if not is_valid:
        print(f"ERROR: OSC Sender: {error_msg}", file=sys.stderr)
        sys.exit(1)

    # Print startup information
    target_ip = "127.0.0.1"  # R34
    print(f"Sending to {target_ip}:{args.port} with {args.sensors} sensors")

    # Create and start sensor threads (R37)
    threads = []
    for sensor_id in range(args.sensors):
        thread = threading.Thread(
            target=sensor_thread,
            args=(sensor_id, target_ip, args.port),
            name=f"Sensor-{sensor_id}"
        )
        thread.daemon = True  # Allow main thread to exit
        threads.append(thread)
        thread.start()

    # Wait for keyboard interrupt (R39)
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

        # Print final statistics
        print("\n" + format_final_statistics(sensor_message_counts))


if __name__ == '__main__':
    main()
