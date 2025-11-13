#!/usr/bin/env python3
"""
Amor OSC Infrastructure - Shared OSC networking and validation utilities.

Provides common OSC server classes, message validation, constants, and statistics
tracking used across processor, audio, and viewer modules.

Classes:
    - ReusePortBlockingOSCUDPServer: Blocking OSC server with SO_REUSEPORT
    - ReusePortThreadingOSCUDPServer: Threading OSC server with SO_REUSEPORT
    - MessageStatistics: Thread-safe message counter with formatted output

Functions:
    - validate_ppg_address(address): Validate /ppg/{0-3} address pattern
    - validate_beat_address(address): Validate /beat/{0-3} address pattern
    - validate_acquire_address(address): Validate /acquire/{0-3} address pattern
    - validate_release_address(address): Validate /release/{0-3} address pattern
    - validate_port(port): Validate port in range 1-65535
    - validate_ppg_id(ppg_id): Validate PPG ID in range 0-3

Constants:
    - PORT_PPG: PPG data broadcast (8000)
    - PORT_BEATS: Beat events broadcast (8001)
    - PORT_CONTROL: Control message bus (8003)
    - PORT_ESP32_ADMIN: ESP32 firmware admin port (8006)
    - PPG_PANS: Stereo panning positions for each PPG sensor
    - ADC_MIN, ADC_MAX: 12-bit ADC value range
    - SAMPLE_RATE_HZ: PPG sampling rate
"""

import re
import socket
import threading
from typing import Optional, Tuple
from pythonosc import osc_server
from pythonosc import udp_client


# ============================================================================
# CONSTANTS
# ============================================================================

# OSC port allocation - broadcast bus architecture with SO_REUSEPORT
# All ports use broadcast (255.255.255.255) + SO_REUSEPORT for 1:N delivery
PORT_PPG = 8000        # PPG data broadcast (ESP32 → Processor + Viewer)
PORT_BEATS = 8001      # Beat events broadcast (Processor → Audio + Lighting + Viewer)
PORT_CONTROL = 8003    # Control bus broadcast (Sequencer ↔ Audio ↔ Launchpad)
                       #   Messages: /select/*, /loop/*, /route/*, /led/*, /program/*
PORT_ESP32_ADMIN = 8006  # ESP32 admin commands (Admin → ESP32 units)

# Stereo panning positions for each PPG channel (8 total)
# -1.0 = hard left, 0.0 = center, 1.0 = hard right
# Channels 4-7 (virtual) inherit pan positions from 0-3 (real sensors)
PPG_PANS = {
    0: -1.0,   # Real sensor 0: Hard left
    1: -0.33,  # Real sensor 1: Center-left
    2: 0.33,   # Real sensor 2: Center-right
    3: 1.0,    # Real sensor 3: Hard right
    4: -1.0,   # Virtual channel 4: Hard left (inherits from 0)
    5: -0.33,  # Virtual channel 5: Center-left (inherits from 1)
    6: 0.33,   # Virtual channel 6: Center-right (inherits from 2)
    7: 1.0     # Virtual channel 7: Hard right (inherits from 3)
}

# 12-bit ADC range from ESP32
ADC_MIN = 0
ADC_MAX = 4095

# PPG sampling rate
SAMPLE_RATE_HZ = 50

# Port validation range
PORT_MIN = 1
PORT_MAX = 65535

# Pre-compiled regex patterns for address validation
# Support 8 PPG channels: 0-3 (real sensors), 4-7 (virtual channels)
PPG_ADDRESS_PATTERN = re.compile(r'^/ppg/([0-7])$')
BEAT_ADDRESS_PATTERN = re.compile(r'^/beat/([0-7])$')
ACQUIRE_ADDRESS_PATTERN = re.compile(r'^/acquire/([0-7])$')
RELEASE_ADDRESS_PATTERN = re.compile(r'^/release/([0-7])$')


# ============================================================================
# SO_REUSEPORT SERVER CLASSES
# ============================================================================

class ReusePortBlockingOSCUDPServer(osc_server.BlockingOSCUDPServer):
    """BlockingOSCUDPServer with SO_REUSEPORT socket option enabled.

    Extends pythonosc's BlockingOSCUDPServer to enable the SO_REUSEPORT socket
    option, allowing multiple processes to bind to the same UDP port. This enables
    port sharing in distributed systems where multiple listeners need to receive
    the same OSC messages.

    The SO_REUSEPORT option is only available on Linux and newer BSD variants.
    On systems without support, binding proceeds without the option (degrades
    gracefully to standard single-process binding).

    Typical usage:
    - sensor_processor.py listens on port 8000 with SO_REUSEPORT
    - ppg_viewer.py can simultaneously listen on same port 8000
    - Both processes receive identical /ppg/* messages from ESP32 units
    """

    def server_bind(self):
        """Bind server socket with SO_REUSEPORT socket option.

        Attempts to enable SO_REUSEPORT before binding. If the socket module
        doesn't have SO_REUSEPORT (on older systems), binding proceeds without it.

        This allows the socket to bind to a port even if other sockets are
        already bound to the same port, provided all use SO_REUSEPORT.
        """
        if hasattr(socket, 'SO_REUSEPORT'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()


class ReusePortThreadingOSCUDPServer(osc_server.ThreadingOSCUDPServer):
    """ThreadingOSCUDPServer with SO_REUSEPORT socket option enabled.

    Extends pythonosc's ThreadingOSCUDPServer to enable the SO_REUSEPORT socket
    option, allowing multiple processes to bind to the same UDP port. This enables
    port sharing where multiple visualization or monitoring applications can
    simultaneously listen to the same OSC data stream.

    The SO_REUSEPORT option is only available on Linux and newer BSD variants.
    On systems without support, binding proceeds without the option (degrades
    gracefully to standard single-process binding).

    Typical usage in visualization:
    - ESP32 units send /ppg/* messages to port 8000
    - sensor_processor.py listens on port 8000 with SO_REUSEPORT enabled
    - ppg_viewer.py can simultaneously listen on same port 8000 with SO_REUSEPORT
    - Both processes receive identical /ppg/* messages from ESP32 units
    """

    def server_bind(self):
        """Bind server socket with SO_REUSEPORT socket option.

        Attempts to enable SO_REUSEPORT before binding. If the socket module
        doesn't have SO_REUSEPORT (on older systems), binding proceeds without it.

        This allows the socket to bind to a port even if other sockets are
        already bound to the same port, provided all use SO_REUSEPORT.
        """
        if hasattr(socket, 'SO_REUSEPORT'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()


# ============================================================================
# BROADCAST UDP CLIENT
# ============================================================================

class BroadcastUDPClient(udp_client.SimpleUDPClient):
    """UDP client with SO_BROADCAST enabled for broadcasting OSC messages.

    Extends pythonosc's SimpleUDPClient to enable the SO_BROADCAST socket option,
    allowing messages to be sent to broadcast addresses (e.g., 255.255.255.255).
    This enables multiple receivers with SO_REUSEPORT to all receive the same
    messages without kernel load-balancing.

    Typical usage:
    - processor.py sends beat messages to 255.255.255.255:8001
    - Multiple viewers with SO_REUSEPORT all receive beat messages
    - Each viewer filters by PPG ID to display only relevant beats

    Args:
        address: Target IP address (use "255.255.255.255" for broadcast)
        port: Target UDP port
    """

    def __init__(self, address: str, port: int):
        """Initialize broadcast client with SO_BROADCAST enabled."""
        super().__init__(address, port)
        # Enable broadcast on the socket
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def close(self):
        """Close the UDP socket."""
        if hasattr(self, '_sock') and self._sock:
            self._sock.close()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure socket cleanup on context exit."""
        self.close()
        return False


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_ppg_address(address: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """Validate PPG message OSC address pattern.

    Checks if address matches /ppg/[0-3] pattern and extracts PPG ID.

    Args:
        address: OSC address string (e.g., "/ppg/0")

    Returns:
        Tuple of (is_valid, ppg_id, error_message):
            - is_valid: True if address matches pattern
            - ppg_id: Extracted sensor ID 0-3, None if invalid
            - error_message: Human-readable error if invalid, None if valid

    Examples:
        >>> validate_ppg_address("/ppg/0")
        (True, 0, None)
        >>> validate_ppg_address("/ppg/5")
        (False, None, "Invalid address pattern: /ppg/5")
    """
    match = PPG_ADDRESS_PATTERN.match(address)
    if not match:
        return False, None, f"Invalid address pattern: {address}"
    ppg_id = int(match.group(1))
    return True, ppg_id, None


def validate_beat_address(address: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """Validate beat message OSC address pattern.

    Checks if address matches /beat/[0-3] pattern and extracts PPG ID.

    Args:
        address: OSC address string (e.g., "/beat/0")

    Returns:
        Tuple of (is_valid, ppg_id, error_message):
            - is_valid: True if address matches pattern
            - ppg_id: Extracted sensor ID 0-3, None if invalid
            - error_message: Human-readable error if invalid, None if valid

    Examples:
        >>> validate_beat_address("/beat/2")
        (True, 2, None)
        >>> validate_beat_address("/beat/invalid")
        (False, None, "Invalid address pattern: /beat/invalid")
    """
    match = BEAT_ADDRESS_PATTERN.match(address)
    if not match:
        return False, None, f"Invalid address pattern: {address}"
    ppg_id = int(match.group(1))
    return True, ppg_id, None


def validate_acquire_address(address: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """Validate acquire message OSC address pattern.

    Checks if address matches /acquire/[0-3] pattern and extracts PPG ID.

    Args:
        address: OSC address string (e.g., "/acquire/0")

    Returns:
        Tuple of (is_valid, ppg_id, error_message):
            - is_valid: True if address matches pattern
            - ppg_id: Extracted sensor ID 0-3, None if invalid
            - error_message: Human-readable error if invalid, None if valid

    Examples:
        >>> validate_acquire_address("/acquire/2")
        (True, 2, None)
        >>> validate_acquire_address("/acquire/invalid")
        (False, None, "Invalid address pattern: /acquire/invalid")
    """
    match = ACQUIRE_ADDRESS_PATTERN.match(address)
    if not match:
        return False, None, f"Invalid address pattern: {address}"
    ppg_id = int(match.group(1))
    return True, ppg_id, None


def validate_release_address(address: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """Validate release message OSC address pattern.

    Checks if address matches /release/[0-3] pattern and extracts PPG ID.

    Args:
        address: OSC address string (e.g., "/release/0")

    Returns:
        Tuple of (is_valid, ppg_id, error_message):
            - is_valid: True if address matches pattern
            - ppg_id: Extracted sensor ID 0-3, None if invalid
            - error_message: Human-readable error if invalid, None if valid

    Examples:
        >>> validate_release_address("/release/2")
        (True, 2, None)
        >>> validate_release_address("/release/invalid")
        (False, None, "Invalid address pattern: /release/invalid")
    """
    match = RELEASE_ADDRESS_PATTERN.match(address)
    if not match:
        return False, None, f"Invalid address pattern: {address}"
    ppg_id = int(match.group(1))
    return True, ppg_id, None


def validate_port(port: int) -> None:
    """Validate UDP port number is in valid range.

    Args:
        port: Port number to validate

    Raises:
        ValueError: If port is outside range 1-65535

    Examples:
        >>> validate_port(8000)  # OK
        >>> validate_port(0)  # Raises ValueError
        >>> validate_port(70000)  # Raises ValueError
    """
    if port < PORT_MIN or port > PORT_MAX:
        raise ValueError(f"Port must be in range {PORT_MIN}-{PORT_MAX}, got {port}")


def validate_ppg_id(ppg_id: int) -> None:
    """Validate PPG sensor ID is in valid range.

    Args:
        ppg_id: PPG sensor ID to validate (0-7: real sensors 0-3, virtual channels 4-7)

    Raises:
        ValueError: If ppg_id is outside range 0-7

    Examples:
        >>> validate_ppg_id(0)  # OK (real sensor)
        >>> validate_ppg_id(3)  # OK (real sensor)
        >>> validate_ppg_id(4)  # OK (virtual channel)
        >>> validate_ppg_id(7)  # OK (virtual channel)
        >>> validate_ppg_id(8)  # Raises ValueError
    """
    if ppg_id < 0 or ppg_id > 7:
        raise ValueError(f"PPG ID must be in range 0-7, got {ppg_id}")


# ============================================================================
# MESSAGE STATISTICS
# ============================================================================

class MessageStatistics:
    """Thread-safe message statistics tracker with formatted output.

    Maintains counters for various message categories and provides formatted
    statistics display on shutdown. All counter increments are thread-safe.

    Typical counters:
        - total_messages: All received OSC messages
        - valid_messages: Messages that passed validation
        - invalid_messages: Messages that failed validation
        - dropped_messages: Messages rejected (stale timestamps, etc.)
        - beat_messages: Beat detection messages sent/processed
        - played_messages: Successfully played audio beats

    Attributes:
        counters (dict): Dictionary of counter_name -> count
        lock (threading.Lock): Thread-safe increment protection

    Examples:
        >>> stats = MessageStatistics()
        >>> stats.increment('total_messages')
        >>> stats.increment('valid_messages')
        >>> stats.print_stats("Audio Engine")
    """

    def __init__(self):
        """Initialize statistics tracker with empty counters."""
        self.counters = {}
        self.lock = threading.Lock()

    def increment(self, counter_name: str, amount: int = 1) -> None:
        """Increment a counter by specified amount (thread-safe).

        Args:
            counter_name: Name of counter to increment
            amount: Amount to increment (default: 1)

        Side effects:
            Creates counter if it doesn't exist (initialized to 0 before increment)
        """
        with self.lock:
            self.counters[counter_name] = self.counters.get(counter_name, 0) + amount

    def get(self, counter_name: str) -> int:
        """Get current value of a counter (thread-safe).

        Args:
            counter_name: Name of counter to retrieve

        Returns:
            Current counter value, or 0 if counter doesn't exist
        """
        with self.lock:
            return self.counters.get(counter_name, 0)

    def print_stats(self, title: str = "STATISTICS") -> None:
        """Print formatted statistics to console.

        Outputs counters with consistent formatting:
        - Header with title
        - All counters in sorted order
        - Footer separator

        Args:
            title: Title for statistics block (default: "STATISTICS")

        Output format:
            ============================================================
            TITLE
            ============================================================
            counter_name: value
            ...
            ============================================================
        """
        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)

        # Snapshot counters under lock (fast)
        with self.lock:
            snapshot = dict(self.counters)

        # Print without holding lock (slow I/O)
        for name in sorted(snapshot.keys()):
            # Convert snake_case to Title Case for display
            display_name = name.replace('_', ' ').title()
            print(f"{display_name}: {snapshot[name]}")

        print("=" * 60)
