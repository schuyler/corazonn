#!/usr/bin/env python3
"""
OSC Receiver - Phase 1 Testing Infrastructure
Receives and validates OSC heartbeat messages from ESP32 simulator.

Reference: p1-tst-trd.md, Requirements R7-R13
"""

import argparse
import re
import sys
import time
from pythonosc import dispatcher
from pythonosc import osc_server


class HeartbeatReceiver:
    """Receives and validates OSC heartbeat messages."""

    # Constants
    MS_PER_MINUTE = 60000  # Milliseconds per minute for BPM calculation

    def __init__(self, port=8000, stats_interval=10):
        self.port = port
        self.stats_interval = stats_interval

        # Precompile regex for performance
        self.address_pattern = re.compile(r'^/heartbeat/([0-3])$')

        # Statistics tracking (R9)
        self.total_messages = 0
        self.valid_messages = 0
        self.invalid_messages = 0

        # Per-sensor tracking (arrays indexed by sensor ID 0-3)
        self.sensor_counts = [0, 0, 0, 0]
        self.sensor_ibi_sums = [0.0, 0.0, 0.0, 0.0]

        # Timing
        self.start_time = time.time()
        self.last_stats_print = time.time()

    def validate_message(self, address, ibi_value):
        """
        Validate OSC message format and content (R8).

        Returns: (is_valid, sensor_id, error_message)
        """
        # Validate IBI type (must be numeric)
        if not isinstance(ibi_value, (int, float)):
            return False, None, f"IBI value is not numeric: {type(ibi_value).__name__}"

        # Validate address pattern: /heartbeat/[0-3]
        match = self.address_pattern.match(address)

        if not match:
            return False, None, f"Invalid address pattern: {address}"

        sensor_id = int(match.group(1))

        # Validate IBI range (300-3000ms)
        if ibi_value < 300 or ibi_value > 3000:
            return False, sensor_id, f"IBI out of range: {ibi_value}ms (sensor {sensor_id})"

        return True, sensor_id, None

    def handle_heartbeat_message(self, address, *args):
        """
        Handle incoming OSC message (R7, R8, R9, R10).

        Called by OSC dispatcher for /heartbeat/* messages.
        Single-threaded - no locking needed.
        """
        # Increment total message count
        self.total_messages += 1

        # Extract IBI value from arguments
        if len(args) == 0:
            self.invalid_messages += 1
            print(f"WARNING: Receiver: No arguments in message: {address}")
            return

        ibi_value = args[0]

        # Validate message (R8)
        is_valid, sensor_id, error_msg = self.validate_message(address, ibi_value)

        if not is_valid:
            self.invalid_messages += 1
            print(f"WARNING: Receiver: {error_msg}")
            return

        # Update statistics (R9)
        self.valid_messages += 1
        self.sensor_counts[sensor_id] += 1
        self.sensor_ibi_sums[sensor_id] += ibi_value

        # Calculate current BPM for this message
        bpm = self.MS_PER_MINUTE / ibi_value

        # Print message (R10)
        print(f"[{address}] IBI: {ibi_value} ms, BPM: {bpm:.1f}")

        # Check if it's time to print periodic statistics (R10)
        current_time = time.time()
        if current_time - self.last_stats_print >= self.stats_interval:
            print()  # Blank line before stats
            self.print_statistics()
            print()  # Blank line after stats
            # Advance by interval to prevent drift
            self.last_stats_print += self.stats_interval

    def calculate_sensor_stats(self, sensor_id):
        """Calculate average IBI and BPM for a sensor."""
        count = self.sensor_counts[sensor_id]
        if count == 0:
            return 0, 0.0

        avg_ibi = self.sensor_ibi_sums[sensor_id] / count
        avg_bpm = self.MS_PER_MINUTE / avg_ibi if avg_ibi > 0 else 0.0

        return avg_ibi, avg_bpm

    def print_statistics(self):
        """Print statistics report (R11). Single-threaded - no locking needed."""
        runtime = time.time() - self.start_time
        msg_rate = self.total_messages / runtime if runtime > 0 else 0.0

        print("=" * 50)
        print("STATISTICS")
        print("=" * 50)
        print(f"Runtime: {runtime:.1f}s")
        print(f"Total messages: {self.total_messages}")
        print(f"Valid: {self.valid_messages}")
        print(f"Invalid: {self.invalid_messages}")
        print(f"Message rate: {msg_rate:.2f} msg/sec")
        print()

        for sensor_id in range(4):
            count = self.sensor_counts[sensor_id]
            if count > 0:
                avg_ibi, avg_bpm = self.calculate_sensor_stats(sensor_id)
                print(f"Sensor {sensor_id}: {count} msgs, avg {avg_ibi:.0f}ms IBI ({avg_bpm:.1f} BPM)")
            else:
                print(f"Sensor {sensor_id}: 0 msgs")

        print("=" * 50)

    def print_final_statistics(self):
        """Print parseable final statistics for integration test (R11b)."""
        print(f"RECEIVER_FINAL_STATS: total={self.total_messages}, valid={self.valid_messages}, "
              f"invalid={self.invalid_messages}, sensor_0={self.sensor_counts[0]}, "
              f"sensor_1={self.sensor_counts[1]}, sensor_2={self.sensor_counts[2]}, "
              f"sensor_3={self.sensor_counts[3]}")

    def run(self):
        """Start the OSC receiver (R7, R13). Single-threaded event loop."""
        # Create dispatcher and bind handler
        disp = dispatcher.Dispatcher()
        disp.map("/heartbeat/*", self.handle_heartbeat_message)

        # Create OSC server (R7) - single-threaded blocking server per R19
        server = osc_server.BlockingOSCUDPServer(
            ("0.0.0.0", self.port),  # Listen on all interfaces
            disp
        )

        print(f"OSC Receiver listening on port {self.port}")
        print(f"Statistics interval: {self.stats_interval} seconds")
        print(f"Waiting for messages... (Ctrl+C to stop)")
        print()

        try:
            # Run server (blocks until KeyboardInterrupt)
            # Single-threaded event loop handles messages sequentially
            server.serve_forever()
        except KeyboardInterrupt:
            # Signal handling (R13)
            print("\n\nShutting down...")
            server.shutdown()

            # Print final statistics (R11, R11b)
            # Check if we just printed periodic stats to avoid double blank lines
            if time.time() - self.last_stats_print < 1.0:
                # Just printed periodic stats, don't add extra blank line
                self.print_statistics()
            else:
                print()
                self.print_statistics()
            print()
            self.print_final_statistics()


def main():
    """Main entry point with argument parsing (R12)."""
    parser = argparse.ArgumentParser(
        description="OSC Receiver - Receives and validates heartbeat messages"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="UDP port to listen on (default: 8000)"
    )
    parser.add_argument(
        "--stats-interval",
        type=int,
        default=10,
        help="Seconds between statistics reports (default: 10)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.port < 1 or args.port > 65535:
        print("ERROR: Receiver: Port must be in range 1-65535", file=sys.stderr)
        sys.exit(1)

    if args.stats_interval < 1:
        print("ERROR: Receiver: Stats interval must be >= 1 second", file=sys.stderr)
        sys.exit(1)

    # Create and run receiver
    receiver = HeartbeatReceiver(port=args.port, stats_interval=args.stats_interval)

    try:
        receiver.run()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Receiver: Port {args.port} already in use", file=sys.stderr)
        else:
            print(f"ERROR: Receiver: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
