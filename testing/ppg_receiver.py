#!/usr/bin/env python3
"""
PPG Receiver - Amor Phase 1 Testing Infrastructure
Receives and validates OSC PPG messages from ESP32 firmware.

Reference: docs/firmware/amor-technical-reference.md
"""

import argparse
import re
import sys
import time
from pythonosc import dispatcher
from pythonosc import osc_server


class PPGReceiver:
    """Receives and validates OSC PPG sample messages."""

    def __init__(self, port=8000, stats_interval=10):
        self.port = port
        self.stats_interval = stats_interval

        # Precompile regex for performance
        self.address_pattern = re.compile(r'^/ppg/([0-3])$')

        # Statistics tracking
        self.total_messages = 0
        self.valid_messages = 0
        self.invalid_messages = 0

        # Per-sensor tracking (arrays indexed by PPG ID 0-3)
        self.sensor_counts = [0, 0, 0, 0]
        self.sensor_sample_counts = [0, 0, 0, 0]  # Total samples received
        self.sensor_min = [4095, 4095, 4095, 4095]  # Min ADC value per sensor
        self.sensor_max = [0, 0, 0, 0]  # Max ADC value per sensor
        self.sensor_sum = [0, 0, 0, 0]  # Sum for mean calculation

        # Timing tracking for message rate
        self.sensor_first_timestamp = [None, None, None, None]
        self.sensor_last_timestamp = [None, None, None, None]
        self.sensor_message_intervals = [[], [], [], []]  # For rate calculation

        # Overall timing
        self.start_time = time.time()
        self.last_stats_print = time.time()

    def validate_message(self, address, args):
        """
        Validate OSC message format and content.

        Expected format: /ppg/{ppg_id} [sample1, sample2, sample3, sample4, sample5, timestamp_ms]

        Returns: (is_valid, ppg_id, samples, timestamp_ms, error_message)
        """
        # Validate address pattern: /ppg/[0-3]
        match = self.address_pattern.match(address)
        if not match:
            return False, None, None, None, f"Invalid address pattern: {address}"

        ppg_id = int(match.group(1))

        # Validate argument count (should be 6: 5 samples + timestamp)
        if len(args) != 6:
            return False, ppg_id, None, None, f"Expected 6 arguments, got {len(args)} (PPG {ppg_id})"

        # Validate all arguments are integers
        for i, arg in enumerate(args):
            if not isinstance(arg, int):
                return False, ppg_id, None, None, f"Argument {i} is not integer: {type(arg).__name__} (PPG {ppg_id})"

        samples = args[0:5]
        timestamp_ms = args[5]

        # Validate ADC range (0-4095 for 12-bit)
        for i, sample in enumerate(samples):
            if sample < 0 or sample > 4095:
                return False, ppg_id, None, None, f"Sample {i} out of range: {sample} (PPG {ppg_id})"

        # Timestamp should be positive (millis() is always positive before rollover)
        if timestamp_ms < 0:
            return False, ppg_id, None, None, f"Invalid timestamp: {timestamp_ms} (PPG {ppg_id})"

        return True, ppg_id, samples, timestamp_ms, None

    def handle_ppg_message(self, address, *args):
        """
        Handle incoming OSC message.

        Called by OSC dispatcher for /ppg/* messages.
        Single-threaded - no locking needed.
        """
        current_time = time.time()

        # Increment total message count
        self.total_messages += 1

        # Validate message
        is_valid, ppg_id, samples, timestamp_ms, error_msg = self.validate_message(address, args)

        if not is_valid:
            self.invalid_messages += 1
            print(f"WARNING: Receiver: {error_msg}")
            return

        # Update statistics
        self.valid_messages += 1
        self.sensor_counts[ppg_id] += 1
        self.sensor_sample_counts[ppg_id] += len(samples)

        # Track timing for message rate calculation
        if self.sensor_first_timestamp[ppg_id] is None:
            self.sensor_first_timestamp[ppg_id] = current_time
        else:
            # Calculate interval since last message
            last_time = self.sensor_last_timestamp[ppg_id]
            if last_time is not None:
                interval = current_time - last_time
                self.sensor_message_intervals[ppg_id].append(interval)
                # Keep only last 100 intervals to prevent memory growth
                if len(self.sensor_message_intervals[ppg_id]) > 100:
                    self.sensor_message_intervals[ppg_id].pop(0)

        self.sensor_last_timestamp[ppg_id] = current_time

        # Update min/max/sum for each sample
        for sample in samples:
            self.sensor_min[ppg_id] = min(self.sensor_min[ppg_id], sample)
            self.sensor_max[ppg_id] = max(self.sensor_max[ppg_id], sample)
            self.sensor_sum[ppg_id] += sample

        # Print message with sample values
        samples_str = ", ".join(str(s) for s in samples)
        mean = sum(samples) / len(samples)
        print(f"[{address}] Samples: [{samples_str}] (mean: {mean:.0f}, timestamp: {timestamp_ms}ms)")

        # Check if it's time to print periodic statistics
        if current_time - self.last_stats_print >= self.stats_interval:
            print()  # Blank line before stats
            self.print_statistics()
            print()  # Blank line after stats
            # Advance by interval to prevent drift
            self.last_stats_print += self.stats_interval

    def calculate_sensor_stats(self, ppg_id):
        """Calculate statistics for a sensor."""
        count = self.sensor_counts[ppg_id]
        if count == 0:
            return None

        sample_count = self.sensor_sample_counts[ppg_id]
        mean = self.sensor_sum[ppg_id] / sample_count if sample_count > 0 else 0
        min_val = self.sensor_min[ppg_id] if self.sensor_min[ppg_id] != 4095 else 0
        max_val = self.sensor_max[ppg_id]
        amplitude = max_val - min_val

        # Calculate message rate (bundles per second)
        intervals = self.sensor_message_intervals[ppg_id]
        if len(intervals) > 0:
            avg_interval = sum(intervals) / len(intervals)
            msg_rate = 1.0 / avg_interval if avg_interval > 0 else 0.0
        else:
            msg_rate = 0.0

        # Calculate sample rate (individual samples per second)
        # Each message contains 5 samples
        sample_rate = msg_rate * 5.0

        return {
            'count': count,
            'sample_count': sample_count,
            'mean': mean,
            'min': min_val,
            'max': max_val,
            'amplitude': amplitude,
            'msg_rate': msg_rate,
            'sample_rate': sample_rate
        }

    def print_statistics(self):
        """Print statistics report. Single-threaded - no locking needed."""
        runtime = time.time() - self.start_time
        msg_rate = self.total_messages / runtime if runtime > 0 else 0.0

        print("=" * 60)
        print("PPG RECEIVER STATISTICS")
        print("=" * 60)
        print(f"Runtime: {runtime:.1f}s")
        print(f"Total messages: {self.total_messages}")
        print(f"Valid: {self.valid_messages}")
        print(f"Invalid: {self.invalid_messages}")
        print(f"Overall message rate: {msg_rate:.2f} msg/sec")
        print()

        for ppg_id in range(4):
            stats = self.calculate_sensor_stats(ppg_id)
            if stats:
                print(f"PPG {ppg_id}:")
                print(f"  Messages: {stats['count']} ({stats['msg_rate']:.1f} msg/sec)")
                print(f"  Samples: {stats['sample_count']} ({stats['sample_rate']:.1f} samples/sec)")
                print(f"  ADC range: {stats['min']}-{stats['max']} (amplitude: {stats['amplitude']})")
                print(f"  Mean value: {stats['mean']:.0f}")
            else:
                print(f"PPG {ppg_id}: 0 messages")

        print("=" * 60)

    def print_final_statistics(self):
        """Print parseable final statistics for integration test."""
        print(f"PPG_RECEIVER_FINAL_STATS: total={self.total_messages}, valid={self.valid_messages}, "
              f"invalid={self.invalid_messages}, ppg_0={self.sensor_counts[0]}, "
              f"ppg_1={self.sensor_counts[1]}, ppg_2={self.sensor_counts[2]}, "
              f"ppg_3={self.sensor_counts[3]}")

    def run(self):
        """Start the OSC receiver. Single-threaded event loop."""
        # Create dispatcher and bind handler
        disp = dispatcher.Dispatcher()
        disp.map("/ppg/*", self.handle_ppg_message)

        # Create OSC server - single-threaded blocking server
        server = osc_server.BlockingOSCUDPServer(
            ("0.0.0.0", self.port),  # Listen on all interfaces
            disp
        )

        print(f"PPG Receiver listening on port {self.port}")
        print(f"Expecting /ppg/{{0-3}} messages with 5 samples + timestamp")
        print(f"Statistics interval: {self.stats_interval} seconds")
        print(f"Waiting for messages... (Ctrl+C to stop)")
        print()

        try:
            # Run server (blocks until KeyboardInterrupt)
            # Single-threaded event loop handles messages sequentially
            server.serve_forever()
        except KeyboardInterrupt:
            # Signal handling
            print("\n\nShutting down...")
            server.shutdown()

            # Print final statistics
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
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="PPG Receiver - Receives and validates raw PPG sample messages"
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
        print("ERROR: PPG Receiver: Port must be in range 1-65535", file=sys.stderr)
        sys.exit(1)

    if args.stats_interval < 1:
        print("ERROR: PPG Receiver: Stats interval must be >= 1 second", file=sys.stderr)
        sys.exit(1)

    # Create and run receiver
    receiver = PPGReceiver(port=args.port, stats_interval=args.stats_interval)

    try:
        receiver.run()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: PPG Receiver: Port {args.port} already in use", file=sys.stderr)
        else:
            print(f"ERROR: PPG Receiver: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
