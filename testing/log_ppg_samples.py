#!/usr/bin/env python3
"""
PPG Sample Logger - Log raw PPG samples to file for analysis

Listens to /ppg/{0-3} messages and logs raw samples with timestamps
to CSV format for offline analysis.

USAGE:
    # Log all sensors to ppg_samples.csv
    python3 testing/log_ppg_samples.py

    # Log specific sensor
    python3 testing/log_ppg_samples.py --ppg-id 0

    # Custom output file
    python3 testing/log_ppg_samples.py --output data.csv

OUTPUT FORMAT:
    CSV with columns: ppg_id, timestamp_ms, sample_value
    Each row is one sample from the 5-sample bundle

Press Ctrl+C to stop logging.
"""

import argparse
import sys
import csv
import time
from pythonosc import dispatcher, osc_server


class PPGLogger:
    """Log raw PPG samples to CSV file."""

    def __init__(self, output_file, ppg_id=None):
        self.output_file = output_file
        self.ppg_id = ppg_id  # None = log all sensors
        self.sample_count = 0
        self.csv_file = None
        self.csv_writer = None

    def start(self):
        """Open CSV file and write header."""
        self.csv_file = open(self.output_file, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['ppg_id', 'timestamp_ms', 'sample_value'])
        print(f"Logging to {self.output_file}")
        if self.ppg_id is not None:
            print(f"Filtering: PPG {self.ppg_id} only")
        else:
            print("Logging: All PPG sensors (0-3)")
        print("Press Ctrl+C to stop\n")

    def handle_ppg_message(self, address, *args):
        """Handle incoming PPG message."""
        # Parse address to get PPG ID
        try:
            ppg_id = int(address.split('/')[-1])
        except (ValueError, IndexError):
            return

        # Filter by PPG ID if specified
        if self.ppg_id is not None and ppg_id != self.ppg_id:
            return

        # Validate message format
        if len(args) != 6:
            return

        samples = args[0:5]
        timestamp_ms = args[5]

        # Log each sample with interpolated timestamp
        for i, sample in enumerate(samples):
            sample_timestamp_ms = timestamp_ms + (i * 20)
            self.csv_writer.writerow([ppg_id, sample_timestamp_ms, sample])
            self.sample_count += 1

        # Flush every 50 samples to ensure data is written
        if self.sample_count % 50 == 0:
            self.csv_file.flush()
            print(f"Logged {self.sample_count} samples...", end='\r')

    def stop(self):
        """Close CSV file and print summary."""
        if self.csv_file:
            self.csv_file.close()
        print(f"\n\nLogged {self.sample_count} samples to {self.output_file}")


def main():
    parser = argparse.ArgumentParser(description="Log PPG samples to CSV")
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='OSC port to listen on (default: 8000)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='ppg_samples.csv',
        help='Output CSV file (default: ppg_samples.csv)'
    )
    parser.add_argument(
        '--ppg-id',
        type=int,
        choices=[0, 1, 2, 3],
        help='Only log specific PPG sensor (default: log all)'
    )

    args = parser.parse_args()

    logger = PPGLogger(args.output, args.ppg_id)
    logger.start()

    # Create OSC server
    disp = dispatcher.Dispatcher()
    disp.map("/ppg/*", logger.handle_ppg_message)

    server = osc_server.BlockingOSCUDPServer(("0.0.0.0", args.port), disp)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        server.shutdown()
        logger.stop()


if __name__ == "__main__":
    main()
