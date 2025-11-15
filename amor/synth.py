#!/usr/bin/env python3
"""
MIDI Synthesis Engine - FluidSynth-based instrument synthesis for Amor.

Generates synthesized audio buffers from beat events using SoundFont samples.
Integrates with audio.py to provide alternative to WAV sample playback.

ARCHITECTURE:
- FluidSynth library for SoundFont synthesis
- Generate discrete audio buffers (note-on → render → note-off)
- Return mono float32 buffers compatible with audio pipeline
- Map BPM to MIDI notes, intensity to velocity

USAGE:
    synth = SynthEngine(config, sample_rate=48000)
    buffer = synth.generate_hit(bpm=72, intensity=0.8)
    # buffer is mono float32 array, ready for panning and effects

CONFIGURATION (samples.yaml):
    synthesis:
      enable: true
      soundfont: sounds/synthesis/default.sf2
      note_mapping:
        bpm_min: 60
        bpm_max: 120
        note_min: 48  # C3
        note_max: 72  # C5
      synth_hit:
        duration_ms: 500
        channel: 0
"""

import numpy as np
from pathlib import Path
from amor.log import get_logger

logger = get_logger("synth")

# Try to import FluidSynth
try:
    import fluidsynth
    SYNTH_AVAILABLE = True
except ImportError:
    SYNTH_AVAILABLE = False
    logger.warning("FluidSynth not available. Install with: pip install pyfluidsynth")


class SynthEngine:
    """FluidSynth-based synthesis engine for generating musical instrument sounds.

    Generates discrete audio buffers from beat events using SoundFont samples.
    Maps heartbeat BPM to MIDI note pitch and intensity to velocity.

    Attributes:
        sample_rate (int): Audio sample rate (Hz)
        config (dict): Synthesis configuration from samples.yaml
        fs (fluidsynth.Synth): FluidSynth synthesizer instance
        sfid (int): Loaded SoundFont ID
        note_min (int): MIDI note at bpm_min
        note_max (int): MIDI note at bpm_max
        bpm_min (float): Minimum BPM for note mapping
        bpm_max (float): Maximum BPM for note mapping
        hit_duration (float): Note duration for synth_hit mode (seconds)
        hit_channel (int): MIDI channel for synth_hit mode
    """

    def __init__(self, config: dict, sample_rate: int = 48000):
        """Initialize synthesis engine.

        Args:
            config: Synthesis configuration dict from samples.yaml
            sample_rate: Audio sample rate (Hz, default 48000)

        Raises:
            RuntimeError: If FluidSynth not available or SoundFont fails to load
            FileNotFoundError: If SoundFont file doesn't exist
        """
        if not SYNTH_AVAILABLE:
            raise RuntimeError(
                "FluidSynth not available. Install with: pip install pyfluidsynth"
            )

        self.sample_rate = sample_rate
        self.config = config

        # Extract configuration
        soundfont_path = config.get('soundfont', 'sounds/synthesis/default.sf2')
        note_mapping = config.get('note_mapping', {})
        self.note_min = note_mapping.get('note_min', 48)  # C3
        self.note_max = note_mapping.get('note_max', 72)  # C5
        self.bpm_min = note_mapping.get('bpm_min', 60)
        self.bpm_max = note_mapping.get('bpm_max', 120)

        hit_config = config.get('synth_hit', {})
        self.hit_duration = hit_config.get('duration_ms', 500) / 1000.0  # Convert to seconds
        self.hit_channel = hit_config.get('channel', 0)

        # Validate SoundFont exists
        sf_path = Path(soundfont_path)
        if not sf_path.exists():
            raise FileNotFoundError(f"SoundFont not found: {soundfont_path}")

        # Initialize FluidSynth
        try:
            self.fs = fluidsynth.Synth(samplerate=float(sample_rate))

            # Start with default driver (real-time synthesis)
            # FluidSynth will choose appropriate driver (alsa on Linux, etc.)
            result = self.fs.start()
            if result != 0:
                raise RuntimeError(f"FluidSynth start() failed with code {result}")

            # Load SoundFont
            self.sfid = self.fs.sfload(str(sf_path))
            if self.sfid == -1:
                raise RuntimeError(f"Failed to load SoundFont: {sf_path}")

            # Select program for channel
            self.fs.program_select(self.hit_channel, self.sfid, 0, 0)  # Bank 0, Program 0

            logger.info(f"SynthEngine initialized:")
            logger.info(f"  SoundFont: {soundfont_path}")
            logger.info(f"  Sample rate: {sample_rate}Hz")
            logger.info(f"  Note mapping: BPM {self.bpm_min}-{self.bpm_max} → MIDI {self.note_min}-{self.note_max}")
            logger.info(f"  Hit duration: {self.hit_duration * 1000:.0f}ms")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize FluidSynth: {e}")

    def _bpm_to_note(self, bpm: float) -> int:
        """Map BPM to MIDI note number using linear interpolation.

        Args:
            bpm: Beats per minute (clamped to bpm_min..bpm_max range)

        Returns:
            MIDI note number (clamped to note_min..note_max range)

        Examples:
            >>> # With bpm_min=60, bpm_max=120, note_min=48, note_max=72
            >>> engine._bpm_to_note(60)
            48
            >>> engine._bpm_to_note(90)
            60
            >>> engine._bpm_to_note(120)
            72
        """
        # Clamp BPM to valid range
        bpm_clamped = max(self.bpm_min, min(self.bpm_max, bpm))

        # Linear interpolation
        bpm_range = self.bpm_max - self.bpm_min
        note_range = self.note_max - self.note_min

        if bpm_range == 0:
            # Edge case: bpm_min == bpm_max
            note = self.note_min
        else:
            note = self.note_min + (bpm_clamped - self.bpm_min) * note_range / bpm_range

        # Round to integer and clamp to MIDI range [0, 127]
        note_int = int(round(note))
        return max(0, min(127, note_int))

    def generate_hit(self, bpm: float, intensity: float) -> np.ndarray:
        """Generate short synthesized note for synth_hit mode.

        Triggers note, renders audio buffer, releases note, returns mono buffer.

        Args:
            bpm: Beats per minute (determines pitch)
            intensity: Signal strength 0.0-1.0 (determines velocity)

        Returns:
            Mono audio buffer as float32 numpy array

        Raises:
            ValueError: If intensity is out of range

        Side effects:
            - Sends MIDI note on/off to FluidSynth
            - Renders audio from FluidSynth internal buffer
        """
        # Validate intensity
        if not 0.0 <= intensity <= 1.0:
            raise ValueError(f"Intensity must be in [0.0, 1.0], got {intensity}")

        # Map parameters to MIDI
        note = self._bpm_to_note(bpm)
        velocity = int(intensity * 127)
        velocity = max(0, min(127, velocity))  # Clamp to MIDI range

        # Calculate buffer size
        num_samples = int(self.hit_duration * self.sample_rate)

        # Trigger note
        self.fs.noteon(self.hit_channel, note, velocity)

        # Render audio buffer (FluidSynth returns interleaved stereo by default)
        buffer_stereo = self.fs.get_samples(num_samples)

        # Release note
        self.fs.noteoff(self.hit_channel, note)

        # Convert to numpy array if not already
        if not isinstance(buffer_stereo, np.ndarray):
            buffer_array = np.array(buffer_stereo, dtype=np.float32)
        else:
            buffer_array = buffer_stereo.astype(np.float32)

        # Validate shape and extract mono
        if buffer_array.ndim == 1:
            # Interleaved stereo [L, R, L, R, ...] → extract left channel
            expected_length = 2 * num_samples
            if len(buffer_array) >= expected_length:
                buffer_mono = buffer_array[::2][:num_samples]
            else:
                raise RuntimeError(
                    f"Buffer too short: expected {expected_length}, got {len(buffer_array)}"
                )
        elif buffer_array.ndim == 2:
            # Separate channels [[L1, L2, ...], [R1, R2, ...]] → take first channel
            buffer_mono = buffer_array[0, :num_samples]
        else:
            raise RuntimeError(f"Unexpected buffer shape: {buffer_array.shape}")

        # Normalize to prevent clipping
        peak = np.abs(buffer_mono).max()
        if peak > 0.9:
            buffer_mono = buffer_mono * (0.9 / peak)
            logger.debug(f"Normalized buffer: peak {peak:.3f} → 0.9")

        logger.debug(
            f"Generated hit: BPM {bpm:.1f} → note {note}, "
            f"intensity {intensity:.2f} → velocity {velocity}, "
            f"duration {len(buffer_mono) / self.sample_rate * 1000:.0f}ms"
        )

        return buffer_mono

    def cleanup(self):
        """Clean up FluidSynth resources.

        Call on shutdown to prevent resource leaks.
        """
        try:
            if hasattr(self, 'fs') and self.fs is not None:
                self.fs.delete()
                self.fs = None
                logger.info("SynthEngine cleaned up")
        except Exception as e:
            logger.warning(f"Failed to cleanup SynthEngine: {e}")
