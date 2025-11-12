#!/usr/bin/env python3
"""
PPG Visualizer - Live PPG waveform display with beat detection visualization.

Receives raw PPG sample bundles and beat detection messages from sensor_processor
via OSC and displays them in a real-time matplotlib window. Monitors a single PPG
sensor (0-3) over a configurable time window.

FEATURES:
- Real-time waveform visualization (blue line)
- Adaptive threshold line (red dashed) calculated from last 100 samples
- Beat detection markers (green vertical lines) showing detected heartbeats
- BPM display (text overlay) showing current heart rate
- Configurable Y-axis range (default 0-4095 for 12-bit ADC)
- Window size selector for zooming into specific time ranges

ARCHITECTURE:
- Dual OSC servers with SO_REUSEPORT for PPG data:
  - Port N (default 8000): Receives /ppg/* messages (raw PPG samples)
  - Port N+1 (default 8001): Receives /beat/* messages (beat detection)
- Threading: Both servers run in daemon threads, matplotlib animates at 60 FPS
- Per-frame updates: Threshold calculation, beat marker positioning, BPM display

INPUT OSC MESSAGES:

PPG messages (port 8000):
    Address: /ppg/{ppg_id}  where ppg_id is 0-3
    Arguments: [sample0, sample1, sample2, sample3, sample4, timestamp_ms]
    - Samples: int values 0-4095 (12-bit ADC from ESP32)
    - Timestamp: int milliseconds on ESP32

Beat messages (port 8001):
    Address: /beat/{ppg_id}  where ppg_id is 0-3
    Arguments: [timestamp, bpm, intensity]
    - Timestamp: float, Unix time (seconds)
    - BPM: float, heart rate in beats per minute
    - Intensity: float, reserved for future use

USAGE:
    # Monitor sensor 0 with default settings
    python3 -m amor.viewer --ppg-id 0

    # Monitor sensor 1 with 60-second window and custom Y-axis
    python3 -m amor.viewer --ppg-id 1 --window 60 --min 1000 --max 3500

    # Listen on custom port (requires matching sensor_processor ports)
    python3 -m amor.viewer --ppg-id 0 --port 9000

COMMAND-LINE ARGUMENTS:
    --port N        UDP port for PPG data (default: 8000)
    --ppg-id N      PPG sensor ID to monitor, 0-3 (required)
    --window N      Time window in seconds (default: 30)
    --min N         Minimum Y-axis value (default: 0)
    --max N         Maximum Y-axis value (default: 4095)

VISUALIZATION ALGORITHM:
1. PPG Signal: Blue line updated every frame from data buffer
2. Threshold: Calculated using detector module constants (matches detector.py)
3. Beat Markers: Green vertical lines at beat timestamps within visible window
4. BPM Display: Text overlay updated from latest beat message

DEBUGGING TIPS:
- Green lines should align with signal peaks (upward threshold crossings)
- BPM value should match actual heart rate within ±10%
- Threshold should adapt to signal amplitude changes
- Check console for port binding errors if plot doesn't appear

Reference: amor-technical-reference.md
"""

import argparse
import sys
import threading
import time
from collections import deque

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.ticker import MaxNLocator
from pythonosc import dispatcher
from pythonosc import osc_server
import numpy as np

from amor import osc
from amor.detector import THRESHOLD_WINDOW, MAD_THRESHOLD_K


def validate_config(port, ppg_id, window, y_min, y_max):
    """Validate command-line configuration parameters.

    Checks all user inputs are within valid ranges for proper operation.
    Raises ValueError with descriptive message on first validation failure.

    Args:
        port (int): UDP port number (must be 1-65535)
        ppg_id (int): PPG sensor ID (must be 0-3)
        window (int): Time window in seconds (must be >= 1)
        y_min (int): Minimum Y-axis value (must be < y_max)
        y_max (int): Maximum Y-axis value (must be > y_min)

    Raises:
        ValueError: If any parameter is outside valid range
    """
    # Validate using osc module functions
    osc.validate_port(port)
    osc.validate_ppg_id(ppg_id)

    # Validate window
    if window < 1:
        raise ValueError(f"Window must be >= 1 second, got {window}")

    # Validate y-axis range
    if y_min >= y_max:
        raise ValueError(f"Y-axis minimum ({y_min}) must be less than maximum ({y_max})")


def create_argument_parser():
    """Create command-line argument parser for ppg_viewer.

    Defines all CLI options with descriptions, defaults, and type conversions.
    Used by main() to parse and validate user input.

    Returns:
        argparse.ArgumentParser: Configured parser with all ppg_viewer options
    """
    parser = argparse.ArgumentParser(
        description="PPG Visualizer - Live PPG waveform display"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="UDP port to listen on (default: 8000)"
    )

    parser.add_argument(
        "--ppg-id",
        type=int,
        required=True,
        help="PPG sensor ID to monitor (0-3, required)"
    )

    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="Time window in seconds (default: 30)"
    )

    parser.add_argument(
        "--min",
        type=int,
        default=0,
        help="Minimum Y-axis value (default: 0)"
    )

    parser.add_argument(
        "--max",
        type=int,
        default=4095,
        help="Maximum Y-axis value (default: 4095)"
    )

    return parser


class PPGViewer:
    """Manages PPG visualization with beat detection overlay.

    Runs dual OSC servers (PPG data and beat detection), maintains sample and beat
    buffers with thread-safe access, and animates matplotlib visualization. Filters
    messages by PPG sensor ID and renders waveform with threshold line, beat markers,
    and BPM display updated at 60 FPS.

    Attributes:
        port (int): Base UDP port for PPG data (beat server uses port+1)
        ppg_id (int): Target PPG sensor ID (0-3)
        window_seconds (int): Time window for display (seconds)
        y_min, y_max (int): Y-axis range for signal
        data_buffer (deque): Thread-safe buffer of (timestamp, sample) tuples
        beats (deque): Thread-safe buffer of beat timestamps
        current_bpm (float): Latest BPM from beat messages
    """

    def __init__(self, port, ppg_id, window, y_min, y_max):
        """Initialize PPG Viewer with configuration and buffers.

        Creates thread-safe buffers for PPG samples and beat data, initializes
        regex patterns for OSC message validation, and prepares matplotlib objects.

        Args:
            port (int): Base UDP port for PPG data (beat server uses port+1)
            ppg_id (int): PPG sensor ID to monitor (0-3)
            window (int): Time window for display in seconds
            y_min (int): Minimum Y-axis value for signal visualization
            y_max (int): Maximum Y-axis value for signal visualization

        Initializes:
            - data_buffer: Circular deque sized for window * 50Hz sampling
            - buffer_lock: Threading lock for buffer access
            - beats deque: Stores beat timestamps for marker rendering
            - beat_lock: Threading lock for beat access
            - Address patterns: Regex for /ppg/* and /beat/* message validation
        """
        self.port = port
        self.ppg_id = ppg_id
        self.window_seconds = window
        self.y_min = y_min
        self.y_max = y_max

        # Data buffer: deque with auto-eviction
        # Buffer size: samples per second (50Hz) * window
        buffer_size = int(window * 50)
        self.data_buffer = deque(maxlen=buffer_size)

        # Thread safety
        self.buffer_lock = threading.Lock()

        # Beat data for visualization
        self.beats = deque(maxlen=100)
        self.current_bpm = None
        self.beat_lock = threading.Lock()

        # Address pattern regex for validation
        # Address patterns now handled by osc.validate_ppg_address()
        # Address patterns now handled by osc.validate_beat_address()

        # Matplotlib objects (initialized in run())
        self.fig = None
        self.ax = None
        self.line = None
        self.threshold_line = None
        self.beat_marker_line = None
        self.bpm_text = None
        self.ani = None

    def handle_osc_message(self, address, *args):
        """Handle incoming PPG sample bundle message.

        Validates message format, checks PPG sample range (0-4095), filters by PPG ID,
        and appends samples to thread-safe buffer with interpolated timestamps.
        Each sample bundle typically contains 5 samples representing 100ms at 50Hz.

        Validation steps:
        1. Check minimum argument count (1 sample + timestamp)
        2. Validate address matches /ppg/[0-3] pattern
        3. Filter by configured ppg_id (drop if not target sensor)
        4. Verify timestamp is numeric
        5. Verify all samples are numeric and in ADC range 0-4095

        Buffering:
        - Samples may arrive in bundles (e.g., 5 samples per message)
        - Assumes even spacing within bundle period (100ms / sample_count)
        - Calculates individual timestamp for each sample using linear interpolation
        - Uses current time as reference, subtracts sample interval for earlier samples

        Args:
            address (str): OSC address (e.g., "/ppg/0")
            *args: Variable arguments [sample0, sample1, ..., timestamp_ms]
                - All samples must be 0-4095 (12-bit ADC value)
                - Last argument is ESP32 millisecond timestamp

        Side effects:
            - Appends to data_buffer with buffer_lock
            - Silent return on validation failure (drops invalid samples)
        """
        # Need at least 2 args (1 sample + timestamp)
        if len(args) < 2:
            return

        # Validate address pattern and extract PPG ID
        is_valid, message_ppg_id, _ = osc.validate_ppg_address(address)
        if not is_valid:
            return

        # Filter by PPG ID
        if message_ppg_id != self.ppg_id:
            return

        # Extract samples (all but last arg) and timestamp (last arg)
        samples = args[:-1]
        timestamp_ms = args[-1]

        # Validate timestamp is numeric
        if not isinstance(timestamp_ms, (int, float)):
            return

        # Validate all samples are numeric and in ADC range (0-4095)
        for sample in samples:
            if not isinstance(sample, (int, float)):
                return
            if sample < 0 or sample > 4095:
                return

        # Convert ESP32 millis() to seconds for display
        # Use current time as base, calculate relative time from millis
        current_time = time.time()

        # Append each sample to buffer with interpolated timestamps
        # Assuming samples evenly spaced within the bundle period
        bundle_period = 0.1  # 100ms for 5 samples at 50Hz
        sample_interval = bundle_period / len(samples)

        with self.buffer_lock:
            for i, sample_value in enumerate(samples):
                # Calculate timestamp for this sample
                sample_time = current_time - (len(samples) - i - 1) * sample_interval
                self.data_buffer.append((sample_time, sample_value))

    def handle_beat_message(self, address, *args):
        """Handle incoming beat detection message from sensor_processor.

        Validates message format, filters by PPG ID, extracts beat timestamp and BPM,
        and stores in thread-safe buffer for visualization (green beat markers and
        BPM text display).

        Validation steps:
        1. Check minimum argument count (timestamp + BPM)
        2. Validate address matches /beat/[0-3] pattern
        3. Filter by configured ppg_id (drop if not target sensor)
        4. Verify timestamp and BPM are numeric

        Buffering:
        - Stores beat timestamp for rendering green vertical lines
        - Updates current_bpm for text display
        - Beat buffer maintains last 100 beats (circular buffer)

        Args:
            address (str): OSC address (e.g., "/beat/0")
            *args: Variable arguments [timestamp_ms, bpm, intensity, ...]
                - timestamp_ms: int, Unix time in milliseconds when beat detected
                - bpm: float, heart rate in beats per minute
                - intensity: float, reserved for future use (ignored)

        Side effects:
            - Appends timestamp to beats with beat_lock
            - Updates current_bpm with beat_lock
            - Silent return on validation failure (drops invalid messages)
        """
        if len(args) < 2:
            return

        # Validate address pattern and extract PPG ID
        is_valid, message_ppg_id, _ = osc.validate_beat_address(address)
        if not is_valid:
            return

        # Filter by PPG ID
        if message_ppg_id != self.ppg_id:
            return

        # Extract beat data (timestamp is in milliseconds, convert to seconds)
        timestamp_ms = args[0]
        bpm = args[1]

        # Validate data types
        if not isinstance(timestamp_ms, (int, float)) or not isinstance(bpm, (int, float)):
            return

        # Convert timestamp from milliseconds to seconds
        timestamp = timestamp_ms / 1000.0

        # Debug: show received beat and timestamp age
        age_s = time.time() - timestamp
        print(f"VIEWER: Beat received for PPG {message_ppg_id}, BPM={bpm:.1f}, timestamp={timestamp:.3f}, age={age_s:.3f}s")

        with self.beat_lock:
            self.beats.append(timestamp)
            self.current_bpm = bpm

    def animation_update(self, frame):
        """Update animation frame with latest data and visualization.

        Called by matplotlib FuncAnimation at 60 FPS. Performs all per-frame updates:
        1. Reads PPG samples from buffer (thread-safe with lock)
        2. Converts absolute timestamps to relative (relative to first sample)
        3. Calculates adaptive threshold from last 100 samples
        4. Renders beat markers (green lines) within visible window
        5. Updates BPM text display
        6. Auto-scales axes (X: last window_seconds, Y: fixed y_min to y_max)

        Threshold calculation:
        - Uses THRESHOLD_WINDOW samples: median + k*MAD
        - Where k = MAD_THRESHOLD_K (from detector module)
        - Falls back to all available samples if less than THRESHOLD_WINDOW
        - Line drawn across full visible time window

        Beat markers:
        - Green vertical lines at beat timestamps
        - Only rendered if within visible window
        - Redrawn each frame (old lines removed, new ones added)

        Args:
            frame (int): Frame number from matplotlib FuncAnimation (unused)

        Returns:
            tuple: All modified matplotlib artists for blitting (line, threshold_line,
                   bpm_text, and all beat_lines). Empty tuple if line not initialized.
        """
        # If matplotlib not initialized yet, return empty tuple
        if self.line is None:
            return ()

        # Copy data from buffer for plotting (thread-safe)
        with self.buffer_lock:
            if len(self.data_buffer) == 0:
                return (self.line, self.threshold_line, self.bpm_text)
            data_copy = list(self.data_buffer)

        # Use current time as reference point for relative timing
        current_time = time.time()

        # Convert to relative timestamps (negative = seconds ago)
        times = [t - current_time for t, sample in data_copy]
        samples = [sample for t, sample in data_copy]

        # Update line data
        self.line.set_data(times, samples)

        # Calculate MAD-based adaptive threshold (matches detector.py algorithm)
        # Uses detector module constants to ensure visualization matches detection
        threshold_value = None
        if len(samples) >= THRESHOLD_WINDOW:
            recent_samples = np.array(samples[-THRESHOLD_WINDOW:])
            median = np.median(recent_samples)
            mad = np.median(np.abs(recent_samples - median))
            threshold_value = median + MAD_THRESHOLD_K * mad
        elif len(samples) > 0:
            recent_samples = np.array(samples)
            median = np.median(recent_samples)
            mad = np.median(np.abs(recent_samples - median))
            threshold_value = median + MAD_THRESHOLD_K * mad

        # Update threshold line
        if threshold_value is not None and times:
            x_min = -self.window_seconds
            x_max = 0
            self.threshold_line.set_data([x_min, x_max], [threshold_value, threshold_value])

        # Generate beat marker signal (0 normally, 250 for 300ms after each beat)
        if times:
            with self.beat_lock:
                beats_copy = list(self.beats)

            # Create beat marker signal array
            beat_signal = np.zeros(len(times))
            pulse_duration = 0.3  # 300ms pulse width

            for beat_timestamp in beats_copy:
                beat_relative_time = beat_timestamp - current_time
                # Set signal to 250 for 300ms after beat
                for i, t in enumerate(times):
                    if beat_relative_time <= t < beat_relative_time + pulse_duration:
                        beat_signal[i] = 250

            self.beat_marker_line.set_data(times, beat_signal)

        # Update BPM text
        with self.beat_lock:
            bpm_display = f"BPM: {self.current_bpm:.1f}" if self.current_bpm is not None else "BPM: --"

        self.bpm_text.set_text(bpm_display)

        # Auto-scale axes based on data range
        if times:
            # X-axis: show last window_seconds (negative values, most recent at 0)
            x_min = -self.window_seconds
            x_max = 0
            self.ax.set_xlim(x_min, x_max)

            # Y-axis: fixed range
            self.ax.set_ylim(self.y_min, self.y_max)

        # Return all modified artists
        return (self.line, self.threshold_line, self.beat_marker_line, self.bpm_text)

    def run(self):
        """Start OSC servers and matplotlib animation loop.

        Creates two threading OSC servers and matplotlib visualization:
        - Server 1 (port): Receives /ppg/* messages, uses SO_REUSEPORT for port sharing
        - Server 2 (port+1): Receives /beat/* messages for heartbeat markers
        - Both servers run in daemon threads, processing messages in background
        - Matplotlib animates at 60 FPS, updating waveform, threshold, beats, and BPM
        - Blocking call: Returns when matplotlib window closes or KeyboardInterrupt

        Visualization components:
        1. Blue line: PPG waveform from samples
        2. Red dashed line: Adaptive threshold (mean + 1.2*stddev of last 100 samples)
        3. Green vertical lines: Beat detection markers at timestamps
        4. Beige text box: BPM display (updated from latest beat message)
        5. Grid: Time (seconds) vs. signal amplitude (ADC value)

        Thread safety:
        - OSC servers run in daemon threads, update data/beat buffers
        - Matplotlib animation thread reads buffers with locks
        - All buffer access guarded by threading.Lock() instances

        Cleanup:
        - On window close or KeyboardInterrupt, shutdown both servers
        - Servers receive graceful shutdown signal
        """
        # Create PPG dispatcher (for /ppg/* messages on port 8000)
        ppg_disp = dispatcher.Dispatcher()
        ppg_disp.map("/ppg/*", self.handle_osc_message)

        # Create beat dispatcher (for /beat/* messages on port 8001)
        beat_disp = dispatcher.Dispatcher()
        beat_disp.map("/beat/*", self.handle_beat_message)

        # Create two threading OSC servers
        # Port with SO_REUSEPORT for PPG data
        ppg_server = osc.ReusePortThreadingOSCUDPServer(
            ("0.0.0.0", self.port),
            ppg_disp
        )

        # Port + 1 for beat detection messages
        beat_server = osc_server.ThreadingOSCUDPServer(
            ("0.0.0.0", self.port + 1),
            beat_disp
        )

        print(f"PPG Viewer listening on port {self.port} (PPG data)")
        print(f"Beat listener on port {self.port + 1} (beat detection)")
        print(f"Monitoring PPG sensor {self.ppg_id}")
        print(f"Window: {self.window_seconds} seconds")
        print("Waiting for data... (Close window to exit)")

        try:
            # Start servers in background threads
            ppg_thread = threading.Thread(target=ppg_server.serve_forever, daemon=True)
            ppg_thread.start()

            beat_thread = threading.Thread(target=beat_server.serve_forever, daemon=True)
            beat_thread.start()

            # Setup matplotlib figure and axes
            self.fig, self.ax = plt.subplots()
            self.line, = self.ax.plot([], [], 'b-', linewidth=1, label='PPG Signal')

            # Create threshold line (red dashed)
            self.threshold_line, = self.ax.plot([], [], 'r--', linewidth=1, label='Threshold')

            # Create beat marker line (green pulses)
            self.beat_marker_line, = self.ax.plot([], [], 'g-', linewidth=2, label='Beats')

            # Create BPM text
            self.bpm_text = self.ax.text(0.02, 0.95, 'BPM: --',
                                         transform=self.ax.transAxes,
                                         fontsize=12, verticalalignment='top',
                                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

            # Configure plot appearance
            self.ax.set_xlabel('Time (seconds ago)')
            self.ax.set_ylabel('PPG Signal (ADC value)')
            self.ax.set_title(f'PPG Viewer - Sensor {self.ppg_id}')
            self.ax.grid(True)
            self.ax.legend(loc='upper right')

            # Format x-axis to show integer seconds
            self.ax.xaxis.set_major_locator(MaxNLocator(integer=True))

            # Create animation (60 FPS = 16ms interval)
            self.ani = animation.FuncAnimation(
                self.fig, self.animation_update,
                interval=16, blit=True
            )

            # Show plot (blocks until window closed)
            plt.show()

            # Cleanup on window close
            ppg_server.shutdown()
            beat_server.shutdown()

        except KeyboardInterrupt:
            print("\nShutting down...")
            ppg_server.shutdown()
            beat_server.shutdown()


def main():
    """Main entry point: parse arguments, validate, and start visualization.

    Parses command-line arguments, validates configuration, creates PPGViewer
    instance, and starts the event loop. Handles errors gracefully with
    descriptive error messages.

    Error handling:
    - ValueError from validation: Print error and exit with code 1
    - OSError "Address already in use": Port is bound by another process
        - Suggests checking both port and port+1
    - Other OSError: Network-related error, print and exit with code 1

    Typical workflow:
    1. Create argument parser and parse CLI args
    2. Validate port, ppg_id, window, y_min, y_max ranges
    3. Create PPGViewer with validated config
    4. Call viewer.run() to start OSC servers and matplotlib loop
    5. Return when window closes or Ctrl+C pressed
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate arguments
    try:
        validate_config(args.port, args.ppg_id, args.window, args.min, args.max)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Create and run viewer
    try:
        viewer = PPGViewer(
            port=args.port,
            ppg_id=args.ppg_id,
            window=args.window,
            y_min=args.min,
            y_max=args.max
        )
        viewer.run()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Port {args.port} or {args.port + 1} already in use", file=sys.stderr)
            print(f"  PPG data port: {args.port}", file=sys.stderr)
            print(f"  Beat detection port: {args.port + 1}", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
