"""
Amor - Audio-visual heartbeat synchronization system.

Modules:
    osc: Shared OSC infrastructure (servers, validation, constants)
    processor: PPG signal processing and beat detection
    audio: Audio playback engine with stereo panning
    viewer: Real-time PPG waveform visualization
"""

__version__ = "0.1.0"

# Note: Modules are imported on-demand to avoid circular dependencies
# and to allow python -m amor.osc to work without RuntimeWarning.
# Use: from amor import osc, processor, audio, etc.
