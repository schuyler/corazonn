"""Test utilities for integration testing."""

import time
import threading
from typing import List, Tuple, Any, Optional
from pythonosc import dispatcher
from amor.osc import ReusePortBlockingOSCUDPServer


class OSCMessageCapture:
    """Captures OSC messages for validation in tests.

    Creates a listening server on the specified port and captures all incoming
    OSC messages with timestamps for later validation.

    Example:
        capture = OSCMessageCapture(port=8001)
        capture.start()
        # ... trigger some actions ...
        time.sleep(1)
        capture.assert_received("/beat/0", timeout=2.0)
        capture.stop()
    """

    def __init__(self, port: int):
        """Initialize message capture server.

        Args:
            port: UDP port to listen on
        """
        self.port = port
        self.messages: List[Tuple[float, str, Tuple[Any, ...]]] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Setup dispatcher to capture all messages
        disp = dispatcher.Dispatcher()
        disp.set_default_handler(self._capture_handler)

        self.server = ReusePortBlockingOSCUDPServer(
            ("0.0.0.0", port),
            disp
        )

    def _capture_handler(self, address: str, *args):
        """Capture incoming OSC message with timestamp.

        Args:
            address: OSC address pattern (e.g., "/beat/0")
            *args: OSC message arguments
        """
        with self._lock:
            self.messages.append((time.time(), address, args))

    def start(self):
        """Start the capture server in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        """Background thread server loop."""
        self.server.timeout = 0.1  # Check running flag periodically
        while self._running:
            self.server.handle_request()

    def stop(self):
        """Stop the capture server and wait for thread to finish."""
        if not self._running and self._thread is None:
            return  # Already stopped

        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        try:
            self.server.server_close()
        except Exception:
            pass  # Already closed

    def clear(self):
        """Clear all captured messages."""
        with self._lock:
            self.messages.clear()

    def get_messages(self, address_pattern: Optional[str] = None) -> List[Tuple[float, str, Tuple[Any, ...]]]:
        """Get captured messages, optionally filtered by address pattern.

        Args:
            address_pattern: Optional prefix to filter messages (e.g., "/beat")

        Returns:
            List of (timestamp, address, args) tuples
        """
        with self._lock:
            if address_pattern is None:
                return list(self.messages)
            return [
                (ts, addr, args)
                for ts, addr, args in self.messages
                if addr.startswith(address_pattern)
            ]

    def wait_for_message(self, address_pattern: str, timeout: float = 5.0) -> bool:
        """Wait for a message matching the address pattern.

        Args:
            address_pattern: OSC address prefix to match
            timeout: Maximum seconds to wait

        Returns:
            True if message received, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.get_messages(address_pattern):
                return True
            time.sleep(0.05)
        return False

    def assert_received(self, address_pattern: str, timeout: float = 5.0):
        """Assert that a message matching address_pattern was received.

        Args:
            address_pattern: OSC address prefix to match
            timeout: Maximum seconds to wait

        Raises:
            AssertionError: If no matching message received within timeout
        """
        if not self.wait_for_message(address_pattern, timeout):
            raise AssertionError(
                f"No message matching '{address_pattern}' received within {timeout}s. "
                f"Captured {len(self.messages)} messages."
            )

    def assert_count(self, address_pattern: str, expected_count: int, timeout: float = 5.0):
        """Assert that exactly expected_count messages were received.

        Args:
            address_pattern: OSC address prefix to match
            expected_count: Expected number of messages
            timeout: Maximum seconds to wait for messages

        Raises:
            AssertionError: If count doesn't match
        """
        start = time.time()
        while time.time() - start < timeout:
            messages = self.get_messages(address_pattern)
            actual_count = len(messages)
            if actual_count >= expected_count:
                break
            time.sleep(0.05)

        # Final check
        messages = self.get_messages(address_pattern)
        actual_count = len(messages)
        if actual_count != expected_count:
            raise AssertionError(
                f"Expected {expected_count} messages matching '{address_pattern}', "
                f"but received {actual_count}"
            )


def assert_within_ms(timestamp_ms: int, max_age_ms: int = 500):
    """Assert that a timestamp is within max_age_ms of current time.

    Used to validate timestamp freshness in beat messages and other
    time-sensitive OSC communications.

    Args:
        timestamp_ms: Timestamp in milliseconds since epoch
        max_age_ms: Maximum allowed age in milliseconds

    Raises:
        AssertionError: If timestamp is too old

    Example:
        # Validate beat timestamp is fresh
        beat_ts = beat_args[1]  # timestamp from beat message
        assert_within_ms(beat_ts, max_age_ms=500)
    """
    now_ms = time.time() * 1000
    age_ms = now_ms - timestamp_ms
    assert age_ms < max_age_ms, f"Timestamp too old: {age_ms:.0f}ms (max: {max_age_ms}ms)"


def assert_latency_ms(start_time_s: float, max_latency_ms: float, label: str = "Operation"):
    """Assert that elapsed time since start_time_s is within max_latency_ms.

    Args:
        start_time_s: Start timestamp in seconds (from time.time())
        max_latency_ms: Maximum allowed latency in milliseconds
        label: Description of operation for error message

    Raises:
        AssertionError: If latency exceeds max_latency_ms

    Example:
        start = time.time()
        # ... wait for something ...
        assert_latency_ms(start, 100.0, "Beat processing")
    """
    elapsed_ms = (time.time() - start_time_s) * 1000
    assert elapsed_ms < max_latency_ms, \
        f"{label} latency too high: {elapsed_ms:.1f}ms (max: {max_latency_ms}ms)"


def assert_bpm_within_tolerance(measured_bpm: float, expected_bpm: float, tolerance_pct: float = 5.0):
    """Assert that measured BPM is within tolerance of expected BPM.

    Args:
        measured_bpm: Measured beats per minute
        expected_bpm: Expected beats per minute
        tolerance_pct: Tolerance as percentage (default 5%)

    Raises:
        AssertionError: If BPM is outside tolerance range

    Example:
        assert_bpm_within_tolerance(73.2, 75.0, tolerance_pct=5.0)
    """
    tolerance = expected_bpm * (tolerance_pct / 100.0)
    min_bpm = expected_bpm - tolerance
    max_bpm = expected_bpm + tolerance

    assert min_bpm <= measured_bpm <= max_bpm, \
        f"BPM {measured_bpm:.1f} outside tolerance range [{min_bpm:.1f}, {max_bpm:.1f}]"
