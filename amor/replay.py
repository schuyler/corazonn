#!/usr/bin/env python3
"""
PPG Data Replay - Replays recorded PPG sensor data from binary log files

ARCHITECTURE:
- Reads binary log files created by amor.capture module
- Sends OSC messages to port 8000 as /ppg/{ppg_id}
- Functions as a virtual PPG sensor (replaces ESP32 input)
- Supports one-shot or continuous loop playback
- Uses relative timing from original recording

USAGE:
    python3 -m amor.replay data/ppg_20251112_143052.bin
    python3 -m amor.replay data/ppg_20251112_143052.bin --loop
    python3 -m amor.replay data/ppg_20251112_143052.bin --port 8000

INPUT:
    Binary files: data/ppg_YYYYMMDD_HHMMSS.bin

    File format:
    - Header (8 bytes):
        Magic: "PPGL" (4 bytes)
        Version: 1 (1 byte)
        PPG ID: 0-3 (1 byte)
        Reserved: 0x0000 (2 bytes)

    - Records (24 bytes each):
        timestamp_ms: int32 (4 bytes)
        sample[0-4]: int32 × 5 (20 bytes)

OUTPUT OSC MESSAGES:
    Address: /ppg/{ppg_id}
    Arguments: [sample0, sample1, sample2, sample3, sample4, timestamp_ms]
    Port: 8000 (default)
    - Same format as ESP32 PPG sensor output
"""

import argparse
import os
import struct
import sys
import time
from typing import List, Optional, Tuple
from pythonosc.udp_client import SimpleUDPClient
from amor.log import get_logger

logger = get_logger("replay")


class PPGReplay:
    """Replays recorded PPG sensor data from binary log files."""

    # Binary format constants (must match capture.py)
    MAGIC = b'PPGL'
    VERSION = 1
    HEADER_SIZE = 8
    RECORD_SIZE = 24

    def __init__(self, log_file: str, host: str = "127.0.0.1", port: int = 8000, loop: bool = False) -> None:
        """
        Initialize PPG replay.

        Args:
            log_file: Path to binary log file
            host: OSC destination host
            port: OSC destination port (default 8000)
            loop: Enable continuous loop playback
        """
        self.log_file: str = log_file
        self.host: str = host
        self.port: int = port
        self.loop_enabled: bool = loop
        self.ppg_id: Optional[int] = None
        self.records: List[Tuple[int, List[int]]] = []
        self.client: Optional[SimpleUDPClient] = None

    def load(self) -> None:
        """Load and parse binary log file."""
        if not os.path.exists(self.log_file):
            raise FileNotFoundError(f"Log file not found: {self.log_file}")

        with open(self.log_file, 'rb') as f:
            # Read and validate header
            header_data = f.read(self.HEADER_SIZE)
            if len(header_data) < self.HEADER_SIZE:
                raise ValueError("Invalid file: header too short")

            magic, version, ppg_id, reserved = struct.unpack('<4sBBH', header_data)

            if magic != self.MAGIC:
                raise ValueError(f"Invalid file format: magic={magic}")
            if version != self.VERSION:
                raise ValueError(f"Unsupported version: {version}")

            self.ppg_id = ppg_id

            # Read all records
            while True:
                record_data = f.read(self.RECORD_SIZE)
                if len(record_data) < self.RECORD_SIZE:
                    break

                timestamp_ms, s0, s1, s2, s3, s4 = struct.unpack('<i5i', record_data)
                self.records.append((timestamp_ms, [s0, s1, s2, s3, s4]))

        if not self.records:
            raise ValueError("No records found in log file")

        logger.info(f"Loaded {len(self.records)} records from {self.log_file}")
        logger.info(f"PPG ID: {self.ppg_id}")
        logger.info(f"Duration: ~{len(self.records) * 0.1:.1f}s")

    def play(self) -> None:
        """Play back recorded data with relative timing."""
        self.client = SimpleUDPClient(self.host, self.port)

        address = f"/ppg/{self.ppg_id}"
        iteration = 0

        try:
            while True:
                iteration += 1
                if self.loop_enabled:
                    logger.info(f"=== Loop iteration {iteration} ===")

                start_time = time.time()
                first_timestamp = self.records[0][0]

                for i, (timestamp_ms, samples) in enumerate(self.records):
                    # Calculate relative timing from start of recording
                    relative_ms = timestamp_ms - first_timestamp
                    target_time = start_time + (relative_ms / 1000.0)

                    # Sleep until target playback time
                    sleep_duration = target_time - time.time()
                    if sleep_duration > 0:
                        time.sleep(sleep_duration)

                    # Send OSC message (samples + timestamp)
                    message = samples + [timestamp_ms]
                    self.client.send_message(address, message)

                    # Progress indicator
                    if (i + 1) % 10 == 0 or i == len(self.records) - 1:
                        elapsed = time.time() - start_time
                        logger.info(f"Played {i + 1}/{len(self.records)} records ({elapsed:.1f}s)")

                # Exit if not looping
                if not self.loop_enabled:
                    logger.info("Playback complete")
                    break

        except KeyboardInterrupt:
            logger.info("Playback stopped")

    def run(self) -> None:
        """Load file and start playback."""
        self.load()

        if self.loop_enabled:
            logger.info("Starting loop playback (Press Ctrl+C to stop)")
        else:
            logger.info("Starting one-shot playback")

        self.play()


def main() -> None:
    """Parse arguments and start replay."""
    parser = argparse.ArgumentParser(
        description="Replay recorded PPG sensor data from binary log files"
    )
    parser.add_argument(
        'log_file',
        type=str,
        help='Path to binary log file (e.g., data/ppg_20251112_143052.bin)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='OSC destination host (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='OSC destination port (default: 8000)'
    )
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Enable continuous loop playback'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Configure logger with specified log level
    logger.setLevel(args.log_level)

    # Create and start replay
    replay = PPGReplay(
        log_file=args.log_file,
        host=args.host,
        port=args.port,
        loop=args.loop
    )

    try:
        replay.run()
    except FileNotFoundError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
