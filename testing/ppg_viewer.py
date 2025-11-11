#!/usr/bin/env python3
"""
PPG Visualizer - Live PPG waveform display using OSC messages.

Receives raw PPG sample bundles from ESP32 sensors via OSC and displays
the continuous waveform in a real-time matplotlib window. Supports
monitoring a single PPG sensor (0-3) over a configurable time window.

Reference: amor-technical-reference.md
"""

import argparse
import re
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


def validate_config(port, ppg_id, window, y_min, y_max):
    """
    Validate configuration parameters.

    Args:
        port: UDP port number (1-65535)
        ppg_id: PPG sensor ID (0-3)
        window: Window size in seconds (>= 1)
        y_min: Minimum Y-axis value
        y_max: Maximum Y-axis value

    Returns:
        True if valid, raises ValueError or AssertionError if invalid
    """
    # Validate port
    if port < 1 or port > 65535:
        raise ValueError(f"Port must be in range 1-65535, got {port}")

    # Validate ppg_id
    if ppg_id < 0 or ppg_id > 3:
        raise ValueError(f"PPG ID must be in range 0-3, got {ppg_id}")

    # Validate window
    if window < 1:
        raise ValueError(f"Window must be >= 1 second, got {window}")

    # Validate y-axis range
    if y_min >= y_max:
        raise ValueError(f"Y-axis minimum ({y_min}) must be less than maximum ({y_max})")

    return True


def create_argument_parser():
    """Create and return argument parser for CLI."""
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
        default=1500,
        help="Minimum Y-axis value (default: 1500)"
    )

    parser.add_argument(
        "--max",
        type=int,
        default=3500,
        help="Maximum Y-axis value (default: 3500)"
    )

    return parser


class PPGViewer:
    """Receives and displays raw PPG sample bundles via OSC."""

    def __init__(self, port, ppg_id, window, y_min, y_max):
        """
        Initialize PPG Viewer.

        Args:
            port: UDP port to listen on
            ppg_id: PPG sensor ID to monitor (0-3)
            window: Time window for display (seconds)
            y_min: Minimum Y-axis value
            y_max: Maximum Y-axis value
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

        # Address pattern regex for validation
        self.address_pattern = re.compile(r'^/ppg/([0-3])$')

        # Matplotlib objects (initialized in run())
        self.fig = None
        self.ax = None
        self.line = None
        self.ani = None

        # Time tracking for relative timestamps
        self.start_time = None

    def handle_osc_message(self, address, *args):
        """
        Handle incoming OSC message.

        Validates message format, PPG sample range, and sensor ID.
        Valid sample bundles are unpacked and appended to data buffer.

        Args:
            address: OSC address (e.g., "/ppg/0")
            *args: Message arguments [sample1, ..., sampleN, timestamp_ms]
                   where N=5 initially, last arg is ESP32 millis()
        """
        # Need at least 2 args (1 sample + timestamp)
        if len(args) < 2:
            return

        # Validate address pattern and extract PPG ID
        match = self.address_pattern.match(address)
        if not match:
            return

        message_ppg_id = int(match.group(1))

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

    def animation_update(self, frame):
        """
        Update animation frame (called by matplotlib FuncAnimation).

        Reads buffer data, converts to relative timestamps, updates plot,
        and auto-scales Y-axis based on data range.

        Args:
            frame: Frame number from matplotlib animation

        Returns:
            Tuple containing updated line object for blitting
        """
        # If matplotlib not initialized yet, return line object tuple or empty
        if self.line is None:
            return ()

        # Copy data from buffer for plotting (thread-safe)
        with self.buffer_lock:
            if len(self.data_buffer) == 0:
                return self.line,
            data_copy = list(self.data_buffer)

        # Initialize start_time on first data point
        if self.start_time is None:
            self.start_time = data_copy[0][0]

        # Convert to relative timestamps and extract PPG sample values
        times = [t - self.start_time for t, sample in data_copy]
        samples = [sample for t, sample in data_copy]

        # Update line data
        self.line.set_data(times, samples)

        # Auto-scale axes based on data range
        if times:
            # X-axis: show last window_seconds, or all data if less
            x_min = max(0, max(times) - self.window_seconds)
            x_max = max(times)
            # Ensure minimum width to avoid matplotlib warning
            if x_max <= x_min:
                x_max = x_min + 1.0
            self.ax.set_xlim(x_min, x_max)

            # Y-axis: fixed range
            self.ax.set_ylim(self.y_min, self.y_max)

        return self.line,

    def run(self):
        """
        Start OSC server and matplotlib animation.

        Sets up:
        1. OSC server with ThreadingOSCUDPServer in background
        2. matplotlib figure, axes, and line plot
        3. FuncAnimation callback (30 FPS)
        4. matplotlib event loop (blocks until window closed)
        """
        # Create OSC dispatcher
        disp = dispatcher.Dispatcher()
        disp.map("/ppg/*", self.handle_osc_message)

        # Create threading OSC server
        server = osc_server.ThreadingOSCUDPServer(
            ("0.0.0.0", self.port),
            disp
        )

        print(f"PPG Viewer listening on port {self.port}")
        print(f"Monitoring PPG sensor {self.ppg_id}")
        print(f"Window: {self.window_seconds} seconds")
        print("Waiting for data... (Close window to exit)")

        try:
            # Start server in background thread
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()

            # Setup matplotlib figure and axes
            self.fig, self.ax = plt.subplots()
            self.line, = self.ax.plot([], [], 'b-', linewidth=1)

            # Configure plot appearance
            self.ax.set_xlabel('Time (seconds)')
            self.ax.set_ylabel('PPG Signal (ADC value)')
            self.ax.set_title(f'PPG Viewer - Sensor {self.ppg_id}')
            self.ax.grid(True)

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
            server.shutdown()

        except KeyboardInterrupt:
            print("\nShutting down...")
            server.shutdown()


def main():
    """Main entry point with argument parsing and validation."""
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
            print(f"ERROR: Port {args.port} already in use", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
