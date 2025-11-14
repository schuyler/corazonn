#!/usr/bin/env python3
"""
PPG Data Capture - Records PPG sensor data to binary log files

ARCHITECTURE:
- OSC server on port 8000 (listening for /ppg/{ppg_id} messages)
- Uses SO_REUSEPORT to run alongside processor and other listeners
- Writes binary log files to data/ directory with timestamp-based filenames
- Records only the specified PPG sensor ID

USAGE:
    python3 -m amor.capture --ppg-id 0
    python3 -m amor.capture --ppg-id 1 --output-dir /path/to/logs

INPUT OSC MESSAGES:
    Address: /ppg/{ppg_id}
    Arguments: [sample0, sample1, sample2, sample3, sample4, timestamp_ms]
    - 5 samples: int32 values (0-4095, 12-bit ADC)
    - timestamp_ms: int32, ESP32 milliseconds
    - Sent at 10Hz (one bundle every 100ms)

OUTPUT:
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
"""

import argparse
import os
import struct
import sys
import time
from datetime import datetime
from typing import Optional, BinaryIO
from pythonosc import dispatcher
from amor import osc
from amor.log import get_logger

logger = get_logger("capture")


class PPGCapture:
    """Records PPG sensor data to timestamped binary files."""

    # Binary format constants
    MAGIC = b'PPGL'
    VERSION = 1
    HEADER_SIZE = 8
    RECORD_SIZE = 24  # 4 bytes timestamp + 5×4 bytes samples

    def __init__(self, ppg_id: int, output_dir: str = "data", port: int = 8000) -> None:
        """
        Initialize PPG capture.

        Args:
            ppg_id: PPG sensor ID to record (0-3)
            output_dir: Directory for output files
            port: OSC port to listen on (default 8000)
        """
        osc.validate_ppg_id(ppg_id)

        self.ppg_id: int = ppg_id
        self.output_dir: str = output_dir
        self.port: int = port
        self.log_file: Optional[str] = None
        self.file_handle: Optional[BinaryIO] = None
        self.record_count: int = 0
        self.start_time: Optional[float] = None

    def start(self) -> None:
        """Create output directory and open log file."""
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate timestamped filename with microseconds to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.log_file = os.path.join(self.output_dir, f"ppg_{timestamp}.bin")

        # Open file and write header
        try:
            self.file_handle = open(self.log_file, 'wb')
            self._write_header()
        except Exception as e:
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None
            raise

        self.start_time = time.time()
        logger.info(f"Recording PPG ID {self.ppg_id} to: {self.log_file}")

    def _write_header(self) -> None:
        """Write binary file header."""
        header = struct.pack(
            '<4sBBH',  # little-endian: 4 bytes magic, byte version, byte ppg_id, short reserved
            self.MAGIC,
            self.VERSION,
            self.ppg_id,
            0  # reserved
        )
        self.file_handle.write(header)
        self.file_handle.flush()

    def handle_ppg_message(self, address: str, *args) -> None:
        """
        Handle incoming PPG OSC message.

        Args:
            address: OSC address (e.g., "/ppg/0")
            args: Message arguments [sample0, sample1, sample2, sample3, sample4, timestamp_ms]
        """
        # Parse PPG ID from address
        try:
            ppg_id = int(address.split('/')[-1])
        except (ValueError, IndexError):
            return

        # Filter for our target PPG ID
        if ppg_id != self.ppg_id:
            return

        # Validate message format
        if len(args) != 6:
            logger.warning(f"Invalid message length: {len(args)}")
            return

        # Extract samples and timestamp
        samples = args[0:5]
        timestamp_ms = args[5]

        # Write binary record
        try:
            record = struct.pack(
                '<i5i',  # little-endian: int32 timestamp + 5× int32 samples
                timestamp_ms,
                *samples
            )
            self.file_handle.write(record)
            self.record_count += 1

            # Flush every 10 records (1 second of data)
            if self.record_count % 10 == 0:
                self.file_handle.flush()
                elapsed = time.time() - self.start_time
                logger.info(f"Recorded {self.record_count} bundles ({self.record_count * 5} samples, {elapsed:.1f}s)")

        except Exception as e:
            logger.error(f"Error writing record: {e}")

    def run(self) -> None:
        """Main event loop - listen for PPG messages."""
        disp = dispatcher.Dispatcher()
        disp.map("/ppg/*", self.handle_ppg_message)

        server = osc.ReusePortBlockingOSCUDPServer(
            ("0.0.0.0", self.port),
            disp
        )

        logger.info(f"Listening for /ppg/{self.ppg_id} on port {self.port}")
        logger.info("Press Ctrl+C to stop recording")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Stopping recording...")
        finally:
            server.shutdown()
            self.cleanup()

    def cleanup(self) -> None:
        """Close file and log statistics."""
        if self.file_handle:
            self.file_handle.flush()
            self.file_handle.close()

            if self.start_time:
                elapsed = time.time() - self.start_time
                sample_count = self.record_count * 5
                logger.info("Recording complete:")
                logger.info(f"  File: {self.log_file}")
                logger.info(f"  Records: {self.record_count} bundles")
                logger.info(f"  Samples: {sample_count}")
                logger.info(f"  Duration: {elapsed:.1f}s")
                logger.info(f"  Rate: {self.record_count / elapsed:.1f} bundles/s")


def main() -> None:
    """Parse arguments and start capture."""
    parser = argparse.ArgumentParser(
        description="Record PPG sensor data to binary log files"
    )
    parser.add_argument(
        '--ppg-id',
        type=int,
        required=True,
        choices=[0, 1, 2, 3],
        help='PPG sensor ID to record (0-3)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data',
        help='Output directory for log files (default: data/)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=osc.PORT_PPG,
        help=f'OSC port to listen on (default: {osc.PORT_PPG})'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Log level (default: INFO)'
    )

    args = parser.parse_args()

    # Configure logger with requested level
    logger.setLevel(args.log_level)

    # Create and start capture
    capture = PPGCapture(
        ppg_id=args.ppg_id,
        output_dir=args.output_dir,
        port=args.port
    )

    try:
        capture.start()
        capture.run()
    except OSError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
