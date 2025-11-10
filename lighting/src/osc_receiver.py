"""OSC receiver module for heart rate and lighting effects.

This module handles OSC (Open Sound Control) message reception and calculates
lighting effects based on heart rate data.
"""

import logging
import re
from functools import partial
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from backends.base import LightingBackend

# Initialize logger for this module
logger = logging.getLogger(__name__)


def bpm_to_hue(bpm: float) -> int:
    """Map heart rate (BPM) to light hue color.

    Maps BPM values to hue degrees using linear interpolation:
    - 40 BPM  → 240° (blue, calm)
    - 80 BPM  → 120° (green, neutral)
    - 120 BPM → 0°   (red, excited)

    BPM values outside the 40-120 range are clamped to the boundaries.

    Algorithm (from TRD Section 6.1, R22):
    1. Clamp BPM to [40, 120] range
    2. Map to hue using linear interpolation:
       hue = 240 - ((bpm_clamped - 40) / 80) * 240
    3. Return as integer

    Args:
        bpm: Heart rate in beats per minute (float or int)

    Returns:
        Hue value in degrees (0-360), as integer

    Examples:
        >>> bpm_to_hue(40)
        240
        >>> bpm_to_hue(80)
        120
        >>> bpm_to_hue(120)
        0
        >>> bpm_to_hue(30)  # Clamped to 40
        240
        >>> bpm_to_hue(150)  # Clamped to 120
        0
    """
    # R21: Clamp BPM to valid range [40, 120]
    bpm_clamped = max(40, min(120, bpm))

    # R22: Linear mapping from BPM to hue degrees
    hue = 240 - ((bpm_clamped - 40) / 80) * 240

    return int(hue)


def handle_pulse(address: str, ibi_ms: int, backend: LightingBackend, config: dict) -> None:
    """Handle incoming OSC pulse message from PD audio pipeline.

    Validates IBI, parses zone, calculates BPM/hue, and delegates to backend.

    TRD References:
    - R17: Parse /light/N/pulse address pattern
    - R18: Validate IBI in [300, 3000] milliseconds range
    - R19: Wrap in try/except, log all errors
    - R20: Calculate BPM from IBI
    - R21-R22: Use bpm_to_hue() for hue calculation
    - R32: Use backend to get bulb and execute pulse

    Args:
        address: OSC address (e.g., "/light/0/pulse")
        ibi_ms: Inter-beat interval in milliseconds
        backend: LightingBackend instance for execution
        config: Configuration dict

    Returns:
        None
    """
    try:
        # R17: Parse zone from address pattern /light/N/pulse
        match = re.match(r'/light/(\d+)/pulse', address)
        if not match:
            logger.error(f"Invalid OSC address format: {address}")
            return

        zone = int(match.group(1))

        # R18: Validate IBI range [300, 3000] milliseconds
        if not (300 <= ibi_ms <= 3000):
            logger.warning(f"Invalid IBI {ibi_ms}ms for zone {zone} (valid range: 300-3000ms)")
            return

        # R32: Get bulb ID for this zone
        bulb_id = backend.get_bulb_for_zone(zone)
        if bulb_id is None:
            logger.warning(f"No bulb configured for zone {zone}")
            return

        # R20: Calculate BPM from IBI
        bpm = 60000 / ibi_ms

        # R21-R22: Calculate hue from BPM
        hue = bpm_to_hue(bpm)

        # Log debug info
        logger.debug(f"Pulse received: zone={zone}, ibi={ibi_ms}ms, bpm={bpm:.1f}, hue={hue}°")

        # R32: Execute pulse effect on backend
        backend.pulse(bulb_id, hue, zone)

    except Exception as e:
        # R19: Catch and log all exceptions
        logger.error(f"Error handling OSC pulse message: {e}", exc_info=True)


def start_osc_server(config: dict, backend: LightingBackend) -> None:
    """Start blocking OSC server listening for pulse messages.

    Creates dispatcher, maps /light/*/pulse handler, and starts server.
    This function blocks indefinitely until interrupted.

    TRD References:
    - R15: Listen on configured port
    - R16: Bind to 0.0.0.0 (all interfaces)
    - R17: Handle /light/N/pulse messages

    Args:
        config: Configuration dict with 'osc.listen_port' key
        backend: LightingBackend instance for pulse execution

    Returns:
        None (blocks indefinitely)
    """
    # Create dispatcher for routing OSC messages
    dispatcher = Dispatcher()

    # Create partial handler with backend and config pre-filled
    handler = partial(handle_pulse, backend=backend, config=config)

    # R17: Map /light/*/pulse wildcard address to handler
    dispatcher.map("/light/*/pulse", handler)

    # Get port from config (R15)
    port = config['osc']['listen_port']

    # Create server: bind to 0.0.0.0 on configured port (R16)
    server = BlockingOSCUDPServer(("0.0.0.0", port), dispatcher)

    logger.info(f"OSC server listening on port {port}")

    # Start blocking server (will run until interrupted)
    server.serve_forever()
