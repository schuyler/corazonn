#!/usr/bin/env python3
"""
PPG Test Sink - Receives beat messages from sensor_processor.py
Simple sink to verify beat detection output.
"""

import argparse
import sys
import time
from pythonosc import dispatcher
from pythonosc import osc_server


class BeatSink:
    """Receives and validates beat messages from sensor processor."""

    def __init__(self, port=8001):
        self.port = port
        self.total_beats = 0
        self.beats_per_sensor = [0, 0, 0, 0]
        self.start_time = time.time()

    def handle_beat_message(self, address, *args):
        """Handle incoming /beat/{ppg_id} message."""
        # Extract PPG ID from address
        try:
            ppg_id = int(address.split('/')[-1])
        except (ValueError, IndexError):
            print(f"WARNING: Invalid beat address: {address}")
            return

        # Validate arguments
        if len(args) != 3:
            print(f"WARNING: Expected 3 arguments, got {len(args)}")
            return

        timestamp, bpm, intensity = args

        # Validate types
        if not isinstance(timestamp, float) or not isinstance(bpm, float) or not isinstance(intensity, float):
            print(f"WARNING: Invalid argument types")
            return

        # Update statistics
        self.total_beats += 1
        self.beats_per_sensor[ppg_id] += 1

        print(f"BEAT: PPG {ppg_id}, BPM: {bpm:.1f}, Timestamp: {timestamp:.3f}s, Intensity: {intensity:.2f}")

    def run(self):
        """Start the OSC server."""
        disp = dispatcher.Dispatcher()
        disp.map("/beat/*", self.handle_beat_message)

        server = osc_server.BlockingOSCUDPServer(
            ("0.0.0.0", self.port),
            disp
        )

        print(f"Beat Sink listening on port {self.port}")
        print(f"Waiting for /beat/{{0-3}} messages...")
        print()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            server.shutdown()
            self.print_statistics()

    def print_statistics(self):
        """Print final statistics."""
        runtime = time.time() - self.start_time
        print("\n" + "=" * 60)
        print("BEAT SINK STATISTICS")
        print("=" * 60)
        print(f"Runtime: {runtime:.1f}s")
        print(f"Total beats: {self.total_beats}")
        for i in range(4):
            print(f"PPG {i}: {self.beats_per_sensor[i]} beats")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Beat Sink - Receives beat messages")
    parser.add_argument("--port", type=int, default=8001, help="UDP port to listen on (default: 8001)")
    args = parser.parse_args()

    if args.port < 1 or args.port > 65535:
        print("ERROR: Port must be in range 1-65535", file=sys.stderr)
        sys.exit(1)

    sink = BeatSink(port=args.port)

    try:
        sink.run()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Port {args.port} already in use", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
