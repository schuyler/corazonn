"""
Amor - Audio-visual heartbeat synchronization system.

Modules:
    osc: Shared OSC infrastructure (servers, validation, constants)
    processor: PPG signal processing and beat detection
    audio: Audio playback engine with stereo panning
    viewer: Real-time PPG waveform visualization
"""

__version__ = "0.1.0"

# Export commonly used items from osc module
from amor.osc import (
    PORT_PPG,
    PORT_AUDIO,
    PORT_LIGHTING,
    PPG_PANS,
    ADC_MIN,
    ADC_MAX,
    SAMPLE_RATE_HZ,
    ReusePortBlockingOSCUDPServer,
    ReusePortThreadingOSCUDPServer,
    MessageStatistics,
    validate_ppg_address,
    validate_beat_address,
    validate_port,
    validate_ppg_id,
)

__all__ = [
    "PORT_PPG",
    "PORT_AUDIO",
    "PORT_LIGHTING",
    "PPG_PANS",
    "ADC_MIN",
    "ADC_MAX",
    "SAMPLE_RATE_HZ",
    "ReusePortBlockingOSCUDPServer",
    "ReusePortThreadingOSCUDPServer",
    "MessageStatistics",
    "validate_ppg_address",
    "validate_beat_address",
    "validate_port",
    "validate_ppg_id",
]
