#!/usr/bin/env python3
"""
Amor PPG Sampler - Live recording and looping of PPG sensor data

ARCHITECTURE:
- Records PPG data from real sensors (0-3) to binary files
- Replays recordings as virtual channels (4-7)
- State machine: idle → recording → assignment_mode → playback
- OSC control via PORT_CONTROL (8003)
- SO_REUSEPORT on PORT_PPG (8000) for coexistence with processor

COMPONENTS:
- PPGRecorder: Records /ppg/{0-3} messages to data/ directory
- VirtualChannel: Replays binary file as /ppg/{4-7} in loop
- SamplerController: State machine and OSC control

STATE MACHINE:
1. idle: No recording, no assignment pending
2. recording(source_ppg): Capturing data from PPG N
3. assignment_mode(buffer_path): Waiting for destination selection (30s timeout)

TRANSITIONS:
- idle + /sampler/record/toggle → recording
- recording + same toggle → assignment_mode (30s timeout)
- recording + different toggle → ignore (concurrent prevention)
- assignment_mode + /sampler/assign → idle, start playback
- assignment_mode + timeout → idle (discard buffer)
- active virtual + /sampler/toggle → stop playback

OSC PROTOCOL:
Input (PORT_CONTROL 8003):
    /sampler/record/toggle [source_ppg]  # 0-3: start/stop recording
    /sampler/assign [dest_channel]       # 4-7: assign buffer, start playback
    /sampler/toggle [dest_channel]       # 4-7: toggle playback

Output (PORT_CONTROL 8003):
    /sampler/status/recording [source_ppg] [active]    # 1=started, 0=stopped
    /sampler/status/assignment [active]                # 1=entered, 0=exited
    /sampler/status/playback [dest_channel] [active]   # 1=playing, 0=stopped

FILE FORMAT:
    data/sampler_YYYYMMDD_HHMMSS_ppgN.bin
    Same format as capture.py (PPGL magic, version 1)
"""

import os
import struct
import sys
import signal
import threading
import time
from datetime import datetime
from typing import Optional, BinaryIO, List, Tuple, Dict
from pythonosc import dispatcher
from pythonosc.udp_client import SimpleUDPClient
from amor import osc


# ============================================================================
# PPG RECORDER
# ============================================================================

class PPGRecorder:
    """Records PPG data from a specific source channel to binary file.

    Listens on PORT_PPG (8000) with SO_REUSEPORT for /ppg/{source_ppg}.
    Writes to data/sampler_YYYYMMDD_HHMMSS_ppgN.bin.
    Auto-stops after 60 seconds.
    """

    # Binary format constants (must match capture.py)
    MAGIC = b'PPGL'
    VERSION = 1
    HEADER_SIZE = 8
    RECORD_SIZE = 24  # 4 bytes timestamp + 5×4 bytes samples
    MAX_DURATION_SEC = 60

    def __init__(self, source_ppg: int, output_dir: str = "data"):
        """Initialize recorder.

        Args:
            source_ppg: PPG channel to record (0-3)
            output_dir: Directory for output files
        """
        if not 0 <= source_ppg <= 3:
            raise ValueError(f"Source PPG must be 0-3, got {source_ppg}")

        self.source_ppg = source_ppg
        self.output_dir = output_dir
        self.log_file: Optional[str] = None
        self.file_handle: Optional[BinaryIO] = None
        self.record_count = 0
        self.start_time: Optional[float] = None
        self.running = False
        self.lock = threading.Lock()  # Protect concurrent access to file/state

    def start(self) -> str:
        """Create output directory and open log file.

        Returns:
            Path to created log file
        """
        with self.lock:
            if self.running:
                raise RuntimeError("Recorder already started")

            os.makedirs(self.output_dir, exist_ok=True)

            # Generate timestamped filename with microseconds to avoid collisions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            self.log_file = os.path.join(
                self.output_dir,
                f"sampler_{timestamp}_ppg{self.source_ppg}.bin"
            )

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
            self.running = True
            print(f"RECORDING: PPG {self.source_ppg} → {self.log_file}")

            return self.log_file

    def _write_header(self):
        """Write binary file header."""
        header = struct.pack(
            '<4sBBH',  # little-endian: 4 bytes magic, byte version, byte ppg_id, short reserved
            self.MAGIC,
            self.VERSION,
            self.source_ppg,
            0  # reserved
        )
        self.file_handle.write(header)

    def add_record(self, timestamp_ms: int, samples: List[int]) -> bool:
        """Write a record to file.

        Args:
            timestamp_ms: ESP32 timestamp in milliseconds
            samples: List of 5 ADC samples

        Returns:
            True if record written, False if max duration reached
        """
        with self.lock:
            if not self.running:
                return False

            # Check duration limit
            elapsed = time.time() - self.start_time
            if elapsed >= self.MAX_DURATION_SEC:
                print(f"RECORDING: Max duration ({self.MAX_DURATION_SEC}s) reached, stopping")
                self.running = False
                return False

            # Write record
            record = struct.pack('<i5i', timestamp_ms, *samples)
            self.file_handle.write(record)
            self.record_count += 1

            # Flush every 10 records to prevent data loss
            if self.record_count % 10 == 0:
                self.file_handle.flush()

            return True

    def stop(self):
        """Stop recording and close file."""
        with self.lock:
            if self.file_handle is None:
                return  # Already stopped

            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None

            self.running = False
            elapsed = time.time() - self.start_time if self.start_time else 0
            print(f"RECORDING STOPPED: {self.record_count} records, {elapsed:.1f}s")


# ============================================================================
# VIRTUAL CHANNEL
# ============================================================================

class VirtualChannel:
    """Plays back a binary PPG file as a virtual channel in loop.

    Sends /ppg/{dest_channel} messages to PORT_PPG (8000).
    Uses relative timing from original recording.
    Runs in dedicated thread.
    """

    # Binary format constants (must match capture.py)
    MAGIC = b'PPGL'
    VERSION = 1
    HEADER_SIZE = 8
    RECORD_SIZE = 24

    def __init__(self, dest_channel: int, log_file: str, host: str = "127.0.0.1", port: int = 8000):
        """Initialize virtual channel.

        Args:
            dest_channel: Virtual channel ID (4-7)
            log_file: Path to binary log file
            host: OSC destination host
            port: OSC destination port
        """
        if not 4 <= dest_channel <= 7:
            raise ValueError(f"Destination channel must be 4-7, got {dest_channel}")

        self.dest_channel = dest_channel
        self.log_file = log_file
        self.host = host
        self.port = port
        self.records: List[Tuple[int, List[int]]] = []
        self.client: Optional[SimpleUDPClient] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()  # Protect running flag

    def load(self):
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

            # Read all records
            while True:
                record_data = f.read(self.RECORD_SIZE)
                if len(record_data) < self.RECORD_SIZE:
                    break

                timestamp_ms, s0, s1, s2, s3, s4 = struct.unpack('<i5i', record_data)
                self.records.append((timestamp_ms, [s0, s1, s2, s3, s4]))

        if not self.records:
            raise ValueError("No records found in log file")

        print(f"LOADED: {len(self.records)} records from {self.log_file} for channel {self.dest_channel}")

    def start(self):
        """Start playback in background thread."""
        with self.lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.thread.start()
        print(f"PLAYBACK STARTED: Virtual channel {self.dest_channel}")

    def stop(self):
        """Stop playback."""
        with self.lock:
            if not self.running:
                return
            self.running = False
            thread_to_join = self.thread

        # Join thread outside lock to avoid blocking
        if thread_to_join:
            thread_to_join.join(timeout=2.0)
            if thread_to_join.is_alive():
                print(f"WARNING: Playback thread {self.dest_channel} did not stop cleanly")
            else:
                with self.lock:
                    self.thread = None
        print(f"PLAYBACK STOPPED: Virtual channel {self.dest_channel}")

    def _playback_loop(self):
        """Main playback loop (runs in thread)."""
        self.client = SimpleUDPClient(self.host, self.port)
        address = f"/ppg/{self.dest_channel}"

        while True:
            with self.lock:
                if not self.running:
                    break

            start_time = time.time()
            first_timestamp = self.records[0][0]

            for timestamp_ms, samples in self.records:
                with self.lock:
                    if not self.running:
                        break

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


# ============================================================================
# SAMPLER CONTROLLER
# ============================================================================

class SamplerController:
    """State machine controller for PPG sampling and looping.

    Manages:
    - Recording state (idle/recording/assignment_mode)
    - Active virtual channels (4-7)
    - OSC control and status messaging
    - Assignment timeout (30 seconds)
    """

    ASSIGNMENT_TIMEOUT_SEC = 30

    def __init__(self, output_dir: str = "data"):
        """Initialize sampler controller.

        Args:
            output_dir: Directory for recording files (default: "data")
        """
        # State machine (protected by lock for thread safety)
        self.state_lock = threading.Lock()
        self.state = 'idle'  # idle | recording | assignment_mode
        self.recording_source: Optional[int] = None  # PPG 0-3
        self.recording_buffer: Optional[str] = None  # File path
        self.recorder: Optional[PPGRecorder] = None
        self.assignment_timer: Optional[threading.Timer] = None
        self.output_dir = output_dir  # Directory for recordings

        # Active virtual channels (protected by lock)
        self.virtual_channels: Dict[int, VirtualChannel] = {}  # dest_channel → VirtualChannel

        # OSC clients
        self.control_client = osc.BroadcastUDPClient("255.255.255.255", osc.PORT_CONTROL)

        # Statistics
        self.stats = osc.MessageStatistics()

        # Shutdown flag
        self.running = True

    def handle_record_toggle(self, source_ppg: int):
        """Handle /sampler/record/toggle message.

        Args:
            source_ppg: PPG channel to record (0-3)
        """
        if not 0 <= source_ppg <= 3:
            print(f"WARNING: Invalid source PPG {source_ppg}, must be 0-3")
            return

        with self.state_lock:
            if self.state == 'idle':
                # Start recording
                try:
                    self.recorder = PPGRecorder(source_ppg, output_dir=self.output_dir)
                    self.recording_buffer = self.recorder.start()
                    self.recording_source = source_ppg
                    self.state = 'recording'

                    # Send status update
                    self.control_client.send_message("/sampler/status/recording", [source_ppg, 1])
                    self.stats.increment('recordings_started')
                except Exception as e:
                    print(f"ERROR: Failed to start recording: {e}")
                    self.state = 'idle'
                    self.recorder = None

            elif self.state == 'recording':
                if source_ppg != self.recording_source:
                    # Ignore concurrent recording attempt
                    print(f"WARNING: Already recording PPG {self.recording_source}, ignoring PPG {source_ppg}")
                    return

                # Stop recording, enter assignment mode
                self.recorder.stop()
                self.state = 'assignment_mode'

                # Send status updates
                self.control_client.send_message("/sampler/status/recording", [self.recording_source, 0])
                self.control_client.send_message("/sampler/status/assignment", [1])

                # Start assignment timeout
                self._start_assignment_timeout()
                self.stats.increment('recordings_completed')

            elif self.state == 'assignment_mode':
                # Ignore - already in assignment mode
                print(f"WARNING: Already in assignment mode, ignoring toggle")

    def handle_assign(self, dest_channel: int):
        """Handle /sampler/assign message.

        Args:
            dest_channel: Virtual channel to assign (4-7)
        """
        if not 4 <= dest_channel <= 7:
            print(f"WARNING: Invalid destination channel {dest_channel}, must be 4-7")
            return

        with self.state_lock:
            if self.state != 'assignment_mode':
                print(f"WARNING: Not in assignment mode, ignoring assign to channel {dest_channel}")
                return

            # Cancel assignment timeout
            self._cancel_assignment_timeout()

            # Remove existing virtual channel if running
            old_vc = None
            if dest_channel in self.virtual_channels:
                old_vc = self.virtual_channels[dest_channel]
                del self.virtual_channels[dest_channel]

        # Stop old virtual channel outside lock (may block)
        if old_vc:
            old_vc.stop()

        with self.state_lock:
            # Create and start new virtual channel
            try:
                vc = VirtualChannel(dest_channel, self.recording_buffer)
                vc.load()
                vc.start()
                self.virtual_channels[dest_channel] = vc

                # Send status updates
                self.control_client.send_message("/sampler/status/assignment", [0])
                self.control_client.send_message("/sampler/status/playback", [dest_channel, 1])

                self.stats.increment('assignments_completed')
            except Exception as e:
                print(f"ERROR: Failed to start virtual channel {dest_channel}: {e}")

            # Return to idle
            self.state = 'idle'
            self.recording_source = None
            self.recording_buffer = None
            self.recorder = None

    def handle_toggle(self, dest_channel: int):
        """Handle /sampler/toggle message.

        Args:
            dest_channel: Virtual channel to toggle (4-7)
        """
        if not 4 <= dest_channel <= 7:
            print(f"WARNING: Invalid destination channel {dest_channel}, must be 4-7")
            return

        with self.state_lock:
            if dest_channel not in self.virtual_channels:
                print(f"WARNING: Channel {dest_channel} not playing, ignoring toggle")
                return
            vc = self.virtual_channels[dest_channel]
            del self.virtual_channels[dest_channel]

        # Stop outside lock (may block up to 2 seconds)
        vc.stop()

        # Send status update
        self.control_client.send_message("/sampler/status/playback", [dest_channel, 0])
        self.stats.increment('playback_stopped')

    def handle_ppg_message(self, address: str, *args):
        """Handle /ppg/{source_ppg} message during recording.

        Args:
            address: OSC address (/ppg/N)
            args: [sample0, sample1, sample2, sample3, sample4, timestamp_ms]
        """
        with self.state_lock:
            if self.state != 'recording':
                return

            recording_source = self.recording_source
            recorder = self.recorder

        # Parse PPG ID from address
        is_valid, ppg_id, error_msg = osc.validate_ppg_address(address)
        if not is_valid:
            return

        # Only record from the source we're listening to
        if ppg_id != recording_source:
            return

        # Validate args (6 values: 5 samples + timestamp)
        if len(args) != 6:
            return

        try:
            samples = [int(args[i]) for i in range(5)]
            timestamp_ms = int(args[5])
        except (ValueError, TypeError):
            return

        # Write record
        if not recorder.add_record(timestamp_ms, samples):
            # Max duration reached, enter assignment mode
            with self.state_lock:
                # Only transition if we're still in recording state with this recorder
                if self.state == 'recording' and self.recorder == recorder:
                    recorder.stop()
                    self.state = 'assignment_mode'

                    # Send status updates
                    self.control_client.send_message("/sampler/status/recording", [self.recording_source, 0])
                    self.control_client.send_message("/sampler/status/assignment", [1])

                    # Start assignment timeout
                    self._start_assignment_timeout()

    def _start_assignment_timeout(self):
        """Start 30-second assignment timeout."""
        def timeout_handler():
            with self.state_lock:
                if self.state == 'assignment_mode':
                    print(f"TIMEOUT: Assignment mode timed out after {self.ASSIGNMENT_TIMEOUT_SEC}s")
                    self.control_client.send_message("/sampler/status/assignment", [0])
                    self.state = 'idle'
                    self.recording_source = None
                    self.recording_buffer = None
                    self.recorder = None
                    self.stats.increment('assignment_timeouts')

        self.assignment_timer = threading.Timer(self.ASSIGNMENT_TIMEOUT_SEC, timeout_handler)
        self.assignment_timer.start()

    def _cancel_assignment_timeout(self):
        """Cancel assignment timeout."""
        if self.assignment_timer:
            self.assignment_timer.cancel()
            self.assignment_timer = None

    def shutdown(self):
        """Shutdown sampler gracefully."""
        print("\nShutting down sampler...")
        self.running = False

        with self.state_lock:
            # Cancel timeout
            self._cancel_assignment_timeout()

            # Stop recording if active
            if self.recorder and self.state == 'recording':
                self.recorder.stop()

            # Stop all virtual channels
            virtual_channels_copy = list(self.virtual_channels.values())

        # Stop virtual channels outside lock (may take time)
        for vc in virtual_channels_copy:
            vc.stop()

        with self.state_lock:
            self.virtual_channels.clear()

        # Print statistics
        self.stats.print_stats("SAMPLER STATISTICS")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point for sampler."""
    import argparse

    parser = argparse.ArgumentParser(description="AMOR PPG Sampler - Live recording and looping")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Directory for recording files (default: data)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("AMOR PPG SAMPLER")
    print("=" * 60)

    controller = SamplerController(output_dir=args.output_dir)

    # Safe wrapper functions for OSC handlers (prevent crashes on missing/invalid arguments)
    def safe_record_toggle(addr, *args):
        if len(args) < 1:
            print("WARNING: /sampler/record/toggle missing argument")
            return
        try:
            source_ppg = int(args[0])
            controller.handle_record_toggle(source_ppg)
        except (ValueError, TypeError) as e:
            print(f"WARNING: /sampler/record/toggle invalid argument type: {e}")

    def safe_assign(addr, *args):
        if len(args) < 1:
            print("WARNING: /sampler/assign missing argument")
            return
        try:
            dest_channel = int(args[0])
            controller.handle_assign(dest_channel)
        except (ValueError, TypeError) as e:
            print(f"WARNING: /sampler/assign invalid argument type: {e}")

    def safe_toggle(addr, *args):
        if len(args) < 1:
            print("WARNING: /sampler/toggle missing argument")
            return
        try:
            dest_channel = int(args[0])
            controller.handle_toggle(dest_channel)
        except (ValueError, TypeError) as e:
            print(f"WARNING: /sampler/toggle invalid argument type: {e}")

    # Setup OSC dispatcher for control messages
    control_disp = dispatcher.Dispatcher()
    control_disp.map("/sampler/record/toggle", safe_record_toggle)
    control_disp.map("/sampler/assign", safe_assign)
    control_disp.map("/sampler/toggle", safe_toggle)

    # Setup OSC dispatcher for PPG messages (recording input)
    ppg_disp = dispatcher.Dispatcher()
    ppg_disp.map("/ppg/*", controller.handle_ppg_message)

    # Create OSC servers
    control_server = osc.ReusePortBlockingOSCUDPServer(
        ("0.0.0.0", osc.PORT_CONTROL),
        control_disp
    )

    ppg_server = osc.ReusePortBlockingOSCUDPServer(
        ("0.0.0.0", osc.PORT_PPG),
        ppg_disp
    )

    # Setup signal handlers
    def signal_handler(sig, frame):
        controller.shutdown()
        # Shutdown OSC servers
        control_server.shutdown()
        ppg_server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start servers in threads
    control_thread = threading.Thread(target=control_server.serve_forever, daemon=True)
    ppg_thread = threading.Thread(target=ppg_server.serve_forever, daemon=True)

    control_thread.start()
    ppg_thread.start()

    print(f"Listening for control messages on port {osc.PORT_CONTROL}")
    print(f"Listening for PPG data on port {osc.PORT_PPG} (ReusePort)")
    print(f"Virtual channels 4-7 will send to port {osc.PORT_PPG}")
    print("\nSampler ready. Press Ctrl+C to exit.")
    print()

    # Keep main thread alive
    try:
        while controller.running:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.shutdown()
        # Shutdown OSC servers
        control_server.shutdown()
        ppg_server.shutdown()


if __name__ == "__main__":
    main()
