#!/usr/bin/env python3
"""
EKG Visualizer - Live heartbeat IBI display using OSC messages.

Receives OSC heartbeat messages from ESP32 sensors and displays them
in a real-time matplotlib window. Supports monitoring a single sensor
(0-3) over a configurable time window.

Reference: ekg-visualization-design.md
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
from pythonosc import dispatcher
from pythonosc import osc_server


def validate_config(port, sensor_id, window):
    """
    Validate configuration parameters.

    Args:
        port: UDP port number (1-65535)
        sensor_id: Sensor ID (0-3)
        window: Window size in seconds (>= 1)

    Returns:
        True if valid, raises ValueError or AssertionError if invalid
    """
    # Validate port
    if port < 1 or port > 65535:
        raise ValueError(f"Port must be in range 1-65535, got {port}")

    # Validate sensor_id
    if sensor_id < 0 or sensor_id > 3:
        raise ValueError(f"Sensor ID must be in range 0-3, got {sensor_id}")

    # Validate window
    if window < 1:
        raise ValueError(f"Window must be >= 1 second, got {window}")

    return True


def create_argument_parser():
    """Create and return argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="EKG Visualizer - Live heartbeat IBI display"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="UDP port to listen on (default: 8000)"
    )

    parser.add_argument(
        "--sensor-id",
        type=int,
        required=True,
        help="Sensor ID to monitor (0-3, required)"
    )

    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="Time window in seconds (default: 30)"
    )

    return parser


class EKGViewer:
    """Receives and displays OSC heartbeat messages."""

    def __init__(self, port, sensor_id, window):
        """
        Initialize EKG Viewer.

        Args:
            port: UDP port to listen on
            sensor_id: Sensor ID to monitor (0-3)
            window: Time window for display (seconds)
        """
        self.port = port
        self.sensor_id = sensor_id
        self.window_seconds = window

        # Data buffer: deque with auto-eviction
        # Buffer size: up to 200 BPM * window / 60
        buffer_size = int(window * 200 / 60)
        self.data_buffer = deque(maxlen=buffer_size)

        # Thread safety
        self.buffer_lock = threading.Lock()

        # Address pattern regex for validation
        self.address_pattern = re.compile(r'^/heartbeat/([0-3])$')

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

        Validates message format, IBI range, and sensor ID.
        Valid messages are appended to data buffer.

        Args:
            address: OSC address (e.g., "/heartbeat/0")
            *args: Message arguments (first arg should be IBI value)
        """
        # Extract IBI value
        if len(args) == 0:
            return

        ibi_value = args[0]

        # Validate IBI is numeric
        if not isinstance(ibi_value, (int, float)):
            return

        # Validate address pattern and extract sensor ID
        match = self.address_pattern.match(address)
        if not match:
            return

        message_sensor_id = int(match.group(1))

        # Filter by sensor ID
        if message_sensor_id != self.sensor_id:
            return

        # Validate IBI range (300-3000ms)
        if ibi_value < 300 or ibi_value > 3000:
            return

        # Append to buffer with timestamp
        with self.buffer_lock:
            self.data_buffer.append((time.time(), ibi_value))

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

        # Convert to relative timestamps and extract IBI values
        times = [t - self.start_time for t, ibi in data_copy]
        ibis = [ibi for t, ibi in data_copy]

        # Update line data
        self.line.set_data(times, ibis)

        # Auto-scale axes based on data range
        if times:
            # X-axis: show last window_seconds, or all data if less
            x_min = max(0, max(times) - self.window_seconds)
            x_max = max(times)
            # Ensure minimum width to avoid matplotlib warning
            if x_max <= x_min:
                x_max = x_min + 1.0
            self.ax.set_xlim(x_min, x_max)

            # Y-axis: scale to data range with padding
            if ibis:
                y_min = min(ibis)
                y_max = max(ibis)
                y_range = y_max - y_min if y_max > y_min else 100
                padding = y_range * 0.1  # 10% padding
                self.ax.set_ylim(y_min - padding, y_max + padding)

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
        disp.map("/heartbeat/*", self.handle_osc_message)

        # Create threading OSC server
        server = osc_server.ThreadingOSCUDPServer(
            ("0.0.0.0", self.port),
            disp
        )

        print(f"EKG Viewer listening on port {self.port}")
        print(f"Monitoring sensor {self.sensor_id}")
        print(f"Window: {self.window_seconds} seconds")
        print("Waiting for data... (Close window to exit)")

        try:
            # Start server in background thread
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()

            # Setup matplotlib figure and axes
            self.fig, self.ax = plt.subplots()
            self.line, = self.ax.plot([], [], 'b-', linewidth=2)

            # Configure plot appearance
            self.ax.set_xlabel('Time (seconds)')
            self.ax.set_ylabel('IBI (milliseconds)')
            self.ax.set_title(f'EKG Viewer - Sensor {self.sensor_id}')
            self.ax.grid(True)

            # Create animation (30 FPS = 33ms interval)
            self.ani = animation.FuncAnimation(
                self.fig, self.animation_update,
                interval=33, blit=True
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
        validate_config(args.port, args.sensor_id, args.window)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Create and run viewer
    try:
        viewer = EKGViewer(
            port=args.port,
            sensor_id=args.sensor_id,
            window=args.window
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
