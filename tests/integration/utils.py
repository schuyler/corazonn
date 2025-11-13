"""Integration test utilities for Amor system.

Provides utilities for running integration tests:
- OSCMessageCapture: Thread-safe OSC message capture for validation
- ComponentProcess: Subprocess management for individual components
- ComponentManager: Multi-component orchestration with lifecycle management

Reference: docs/integration-testing-design.md
"""

import time
import threading
import subprocess
import signal
from collections import deque
from pythonosc import dispatcher
from amor import osc


class OSCMessageCapture:
    """Captures OSC messages for validation in integration tests.

    Uses ReusePortThreadingOSCUDPServer to capture messages on a specific port
    with SO_REUSEPORT, allowing multiple listeners on the same port (e.g., audio
    engine and test capture can both listen to port 8001).

    Thread-safe design with lock-protected message buffer and helper methods
    for waiting on messages or querying captured data.

    Example:
        capture = OSCMessageCapture(port=8001)
        capture.start()

        # Wait for beat message
        ts, addr, args = capture.wait_for_message("/beat/0", timeout=2.0)
        assert args[0] > 0  # timestamp

        capture.stop()

    Reference: docs/integration-testing-design.md:164-185
    """

    def __init__(self, port: int):
        """Initialize message capture.

        Args:
            port: UDP port to listen on (uses SO_REUSEPORT)
        """
        self.port = port
        self.messages = deque(maxlen=1000)  # Prevent unbounded growth
        self.lock = threading.Lock()
        self.server = None
        self.server_thread = None

    def start(self):
        """Start capture server in background thread.

        Creates ReusePortThreadingOSCUDPServer and runs it in daemon thread.
        Server immediately begins capturing all messages on the port.
        """
        disp = dispatcher.Dispatcher()
        disp.map("/*", self._capture_handler)

        self.server = osc.ReusePortThreadingOSCUDPServer(
            ("0.0.0.0", self.port),
            disp
        )

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(0.1)  # Allow server to start

    def _capture_handler(self, address, *args):
        """Thread-safe message capture handler.

        Called by OSC server thread for each received message.
        Stores (timestamp, address, args) tuple in deque.

        Args:
            address: OSC address pattern (e.g., "/beat/0")
            *args: Message arguments
        """
        with self.lock:
            self.messages.append((time.time(), address, args))

    def wait_for_message(self, address_pattern: str, timeout: float = 5.0):
        """Wait for message matching address pattern within timeout.

        Polls captured messages every 50ms until match found or timeout.

        Args:
            address_pattern: Address prefix to match (e.g., "/beat/0")
            timeout: Maximum seconds to wait

        Returns:
            Tuple of (timestamp, address, args) for first matching message

        Raises:
            TimeoutError: If no matching message received within timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            with self.lock:
                for ts, addr, args in self.messages:
                    if addr.startswith(address_pattern):
                        return (ts, addr, args)
            time.sleep(0.05)
        raise TimeoutError(f"No message matching {address_pattern} within {timeout}s")

    def get_messages_by_address(self, address_pattern: str):
        """Get all captured messages matching address pattern.

        Args:
            address_pattern: Address prefix to match (e.g., "/beat/")

        Returns:
            List of (timestamp, address, args) tuples
        """
        with self.lock:
            return [(ts, addr, args) for ts, addr, args in self.messages
                    if addr.startswith(address_pattern)]

    def clear(self):
        """Clear all captured messages.

        Thread-safe operation to reset message buffer.
        """
        with self.lock:
            self.messages.clear()

    def stop(self):
        """Stop capture server and cleanup resources.

        Shuts down OSC server thread gracefully.
        """
        if self.server:
            self.server.shutdown()


class ComponentProcess:
    """Manages a subprocess running an Amor component.

    Provides lifecycle management (start, stop, status) for a single component
    process. Handles graceful shutdown with SIGTERM and forceful kill if needed.

    Example:
        proc = ComponentProcess("processor",
                               ["python3", "-m", "amor.processor"])
        proc.start()
        # ... run tests ...
        proc.stop()

    Reference: testing/test_shutdown_stats.py:16-32
    """

    def __init__(self, name: str, command: list):
        """Initialize component process manager.

        Args:
            name: Human-readable component name (for logging)
            command: Command line arguments as list
        """
        self.name = name
        self.command = command
        self.process = None

    def start(self):
        """Start component process.

        Spawns subprocess with SIGINT ignored (to prevent Ctrl+C propagation
        in test environment). Waits 500ms for initialization.
        """
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
        )
        time.sleep(0.5)  # Allow startup

    def stop(self):
        """Stop component process gracefully.

        Sends SIGTERM and waits up to 5 seconds. If process doesn't exit,
        forcefully kills with SIGKILL.
        """
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def is_running(self):
        """Check if process is still running.

        Returns:
            bool: True if process is running, False if exited or not started
        """
        return self.process and self.process.poll() is None


class ComponentManager:
    """Manages multiple component processes for integration testing.

    Orchestrates lifecycle of emulators and Amor components. Provides high-level
    methods for adding common components and context manager for automatic cleanup.

    Example:
        with ComponentManager() as manager:
            manager.add_ppg_emulator(ppg_id=0, bpm=75)
            manager.add_processor()
            manager.start_all()
            # ... run tests ...
        # Automatic cleanup on exit

    Reference: Procfile.test orchestration pattern
    """

    def __init__(self):
        """Initialize component manager with empty component registry."""
        self.components = {}

    def add_ppg_emulator(self, ppg_id: int, bpm: float = 75):
        """Add PPG emulator to managed components.

        Args:
            ppg_id: Sensor ID (0-3)
            bpm: Heart rate in beats per minute
        """
        name = f"ppg{ppg_id}"
        command = [
            "python3", "-m", "amor.simulator.ppg_emulator",
            "--ppg-id", str(ppg_id),
            "--bpm", str(bpm)
        ]
        self.components[name] = ComponentProcess(name, command)

    def add_processor(self, input_port: int = None, beats_port: int = None):
        """Add processor component to managed components.

        Args:
            input_port: Override default PPG input port (8000)
            beats_port: Override default beat output port (8001)
        """
        command = ["python3", "-m", "amor.processor"]
        if input_port is not None:
            command.extend(["--input-port", str(input_port)])
        if beats_port is not None:
            command.extend(["--beats-port", str(beats_port)])
        self.components["processor"] = ComponentProcess("processor", command)

    def add_audio(self, port: int = None):
        """Add audio engine to managed components.

        Args:
            port: Override default beat input port (8001)
        """
        command = ["python3", "-m", "amor.audio"]
        if port is not None:
            command.extend(["--port", str(port)])
        self.components["audio"] = ComponentProcess("audio", command)

    def add_sequencer(self, control_port: int = None, config_path: str = None, state_path: str = None):
        """Add sequencer component to managed components.

        Args:
            control_port: Override default control port (8003)
            config_path: Override default config path
            state_path: Override default state path
        """
        command = ["python3", "-m", "amor.sequencer"]
        if control_port is not None:
            command.extend(["--control-port", str(control_port)])
        if config_path is not None:
            command.extend(["--config", config_path])
        if state_path is not None:
            command.extend(["--state-path", state_path])
        self.components["sequencer"] = ComponentProcess("sequencer", command)

    def add_launchpad_emulator(self, control_port: int = None):
        """Add launchpad emulator to managed components.

        Args:
            control_port: Override default control port (8003)
        """
        command = ["python3", "-m", "amor.simulator.launchpad_emulator"]
        if control_port is not None:
            command.extend(["--control-port", str(control_port)])
        self.components["launchpad"] = ComponentProcess("launchpad", command)

    def add_lighting(self, port: int = None, config_path: str = None):
        """Add lighting engine to managed components.

        Args:
            port: Override default beat input port (8001)
            config_path: Override default config (uses lighting.test.yaml)
        """
        command = ["python3", "-m", "amor.lighting"]
        if port is not None:
            command.extend(["--port", str(port)])
        if config_path is not None:
            command.extend(["--config", config_path])
        else:
            # Default to test config
            command.extend(["--config", "amor/config/lighting.test.yaml"])
        self.components["lighting"] = ComponentProcess("lighting", command)

    def add_kasa_emulator(self, multi: bool = True):
        """Add Kasa bulb emulator to managed components.

        Args:
            multi: Run 4 bulbs for full zone testing (default: True)
        """
        command = ["python3", "-m", "amor.simulator.kasa_emulator"]
        if multi:
            command.append("--multi")
        self.components["kasa"] = ComponentProcess("kasa", command)

    def start_all(self):
        """Start all managed components.

        Starts components sequentially and waits 2s for initialization.
        Components start in order added.
        """
        for component in self.components.values():
            component.start()
        time.sleep(2)  # Allow all components to initialize

    def stop_all(self):
        """Stop all managed components.

        Stops components in reverse order (LIFO) for clean shutdown.
        """
        for component in reversed(list(self.components.values())):
            component.stop()

    def __enter__(self):
        """Context manager entry - returns self for use in 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup even on exception."""
        self.stop_all()
