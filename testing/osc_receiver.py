#!/usr/bin/env python3
"""
OSC Receiver - Phase 1 Testing Infrastructure
Receives and validates OSC heartbeat messages from ESP32 simulator.

Reference: p1-tst-trd.md, Requirements R7-R13
"""

import argparse
import re
import signal
import sys
import time
import threading
from pythonosc import dispatcher
from pythonosc import osc_server


class HeartbeatReceiver:
    """Receives and validates OSC heartbeat messages."""

    def __init__(self, port=8000, stats_interval=10):
        self.port = port
        self.stats_interval = stats_interval

        # Statistics tracking (R9)
        self.total_messages = 0
        self.valid_messages = 0
        self.invalid_messages = 0

        # Per-sensor tracking (arrays indexed by sensor ID 0-3)
        self.sensor_counts = [0, 0, 0, 0]
        self.sensor_ibi_sums = [0.0, 0.0, 0.0, 0.0]

        # Timing
        self.start_time = time.time()
        self.stats_lock = threading.Lock()

        # Shutdown flag
        self.shutting_down = False

    def validate_message(self, address, ibi_value):
        """
        Validate OSC message format and content (R8).

        Returns: (is_valid, sensor_id, error_message)
        """
        # Validate address pattern: /heartbeat/[0-3]
        pattern = r'^/heartbeat/([0-3])$'
        match = re.match(pattern, address)

        if not match:
            return False, None, f"Invalid address pattern: {address}"

        sensor_id = int(match.group(1))

        # Validate sensor ID (0-3)
        if sensor_id < 0 or sensor_id > 3:
            return False, sensor_id, f"Sensor ID out of range: {sensor_id}"

        # Validate IBI range (300-3000ms)
        if ibi_value < 300 or ibi_value > 3000:
            return False, sensor_id, f"IBI out of range: {ibi_value}ms (sensor {sensor_id})"

        return True, sensor_id, None

    def handle_heartbeat_message(self, address, *args):
        """
        Handle incoming OSC message (R7, R8, R9, R10).

        Called by OSC dispatcher for /heartbeat/* messages.
        """
        with self.stats_lock:
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
            bpm = 60000.0 / ibi_value

            # Print message (R10)
            print(f"[{address}] IBI: {ibi_value} ms, BPM: {bpm:.1f}")

    def calculate_sensor_stats(self, sensor_id):
        """Calculate average IBI and BPM for a sensor."""
        count = self.sensor_counts[sensor_id]
        if count == 0:
            return 0, 0.0

        avg_ibi = self.sensor_ibi_sums[sensor_id] / count
        avg_bpm = 60000.0 / avg_ibi if avg_ibi > 0 else 0.0

        return avg_ibi, avg_bpm

    def print_statistics(self):
        """Print statistics report (R11)."""
        with self.stats_lock:
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
        with self.stats_lock:
            print(f"RECEIVER_FINAL_STATS: total={self.total_messages}, valid={self.valid_messages}, "
                  f"invalid={self.invalid_messages}, sensor_0={self.sensor_counts[0]}, "
                  f"sensor_1={self.sensor_counts[1]}, sensor_2={self.sensor_counts[2]}, "
                  f"sensor_3={self.sensor_counts[3]}")

    def periodic_stats_printer(self, server):
        """Background thread to print statistics periodically."""
        next_print = time.time() + self.stats_interval

        while not self.shutting_down:
            time.sleep(1)

            if time.time() >= next_print:
                self.print_statistics()
                next_print = time.time() + self.stats_interval

    def run(self):
        """Start the OSC receiver (R7, R13)."""
        # Create dispatcher and bind handler
        disp = dispatcher.Dispatcher()
        disp.map("/heartbeat/*", self.handle_heartbeat_message)

        # Create OSC server (R7)
        server = osc_server.ThreadingOSCUDPServer(
            ("0.0.0.0", self.port),  # Listen on all interfaces
            disp
        )

        print(f"OSC Receiver listening on port {self.port}")
        print(f"Statistics interval: {self.stats_interval} seconds")
        print(f"Waiting for messages... (Ctrl+C to stop)")
        print()

        # Start periodic statistics printer in background thread
        stats_thread = threading.Thread(
            target=self.periodic_stats_printer,
            args=(server,),
            daemon=True
        )
        stats_thread.start()

        try:
            # Run server (blocks until KeyboardInterrupt)
            server.serve_forever()
        except KeyboardInterrupt:
            # Signal handling (R13)
            print("\n\nShutting down...")
            self.shutting_down = True
            server.shutdown()

            # Print final statistics (R11, R11b)
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
    if args.port < 1024 or args.port > 65535:
        print("ERROR: Receiver: Port must be in range 1024-65535", file=sys.stderr)
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
