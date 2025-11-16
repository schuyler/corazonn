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

        # Drone configuration
        drone_config = config.get('synth_drone', {})
        self.drone_buffer_duration = drone_config.get('buffer_duration_ms', 150) / 1000.0
        self.drone_fade_in = drone_config.get('fade_in_ms', 500) / 1000.0
        self.drone_fade_out = drone_config.get('fade_out_ms', 500) / 1000.0
        self.drone_reference_bpm = drone_config.get('reference_bpm', 75)
        self.drone_base_note = drone_config.get('base_note', 60)
        self.drone_pitch_bend_range = drone_config.get('pitch_bend_range', 3)
        self.drone_channels = drone_config.get('midi_channels', [0, 1, 2, 3])

        # Per-PPG instrument assignments
        # New format: {midi_bank, root_note, instruments: [prog1, prog2, ...]}
        # Old format: {bank, program}
        ppg_instruments_config = config.get('ppg_instruments', {})
        self.ppg_instruments = {}
        for ppg_id in range(4):
            instrument = ppg_instruments_config.get(ppg_id, {})
            # Store full config dict (supports both old and new formats)
            self.ppg_instruments[ppg_id] = instrument if instrument else {
                'bank': 0,
                'program': 0
            }

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

            # Configure pitch bend range for drone channels
            for channel in self.drone_channels:
                # Set pitch bend sensitivity to configured range (default ±3 semitones)
                # RPN MSB/LSB for pitch bend sensitivity: 0x00, 0x00
                self.fs.cc(channel, 101, 0)  # RPN MSB
                self.fs.cc(channel, 100, 0)  # RPN LSB
                self.fs.cc(channel, 6, self.drone_pitch_bend_range)  # Data entry MSB (semitones)
                self.fs.cc(channel, 38, 0)   # Data entry LSB (cents)

            logger.info(f"SynthEngine initialized:")
            logger.info(f"  SoundFont: {soundfont_path}")
            logger.info(f"  Sample rate: {sample_rate}Hz")
            logger.info(f"  Note mapping: BPM {self.bpm_min}-{self.bpm_max} → MIDI {self.note_min}-{self.note_max}")
            logger.info(f"  Hit duration: {self.hit_duration * 1000:.0f}ms")
            logger.info(f"  Drone buffer duration: {self.drone_buffer_duration * 1000:.0f}ms")
            logger.info(f"  Drone pitch bend range: ±{self.drone_pitch_bend_range} semitones")
            logger.info(f"  PPG instruments:")
            for ppg_id in range(4):
                ppg_config = self.ppg_instruments[ppg_id]
                if 'instruments' in ppg_config:
                    # New format: show instrument list
                    instruments = ppg_config['instruments']
                    midi_bank = ppg_config.get('midi_bank', 0)
                    root_note = ppg_config.get('root_note', 60)
                    logger.info(f"    PPG {ppg_id}: Bank {midi_bank}, Root {root_note}, Instruments {instruments}")
                else:
                    # Old format: single program
                    bank = ppg_config.get('bank', 0)
                    program = ppg_config.get('program', 0)
                    logger.info(f"    PPG {ppg_id}: Bank {bank}, Program {program}")

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

    def generate_hit(self, ppg_id: int, bpm: float, intensity: float) -> np.ndarray:
        """Generate short synthesized note for synth_hit mode.

        Selects PPG-specific instrument, triggers note, renders audio buffer,
        releases note, returns mono buffer.

        Args:
            ppg_id: PPG channel ID (0-3, determines instrument)
            bpm: Beats per minute (determines pitch)
            intensity: Signal strength 0.0-1.0 (determines velocity)

        Returns:
            Mono audio buffer as float32 numpy array

        Raises:
            ValueError: If ppg_id or intensity is out of range

        Side effects:
            - Selects MIDI instrument (program_select)
            - Sends MIDI note on/off to FluidSynth
            - Renders audio from FluidSynth internal buffer
        """
        # Validate ppg_id
        if ppg_id not in self.ppg_instruments:
            raise ValueError(f"ppg_id must be 0-3, got {ppg_id}")

        # Validate intensity
        if not 0.0 <= intensity <= 1.0:
            raise ValueError(f"Intensity must be in [0.0, 1.0], got {intensity}")

        # Select instrument for this PPG (handle both old and new config formats)
        ppg_config = self.ppg_instruments[ppg_id]

        # Extract program and bank (new format uses 'instruments' list, old uses single 'program')
        if 'instruments' in ppg_config:
            # New format: use first instrument from list
            program = ppg_config['instruments'][0]
            midi_bank = ppg_config.get('midi_bank', 0)
        else:
            # Old format: single program
            program = ppg_config.get('program', 0)
            midi_bank = ppg_config.get('bank', 0)

        self.fs.program_select(
            self.hit_channel,
            self.sfid,
            midi_bank,
            program
        )

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
            f"Generated hit: PPG {ppg_id} (bank {instrument['bank']}, prog {instrument['program']}), "
            f"BPM {bpm:.1f} → note {note}, intensity {intensity:.2f} → velocity {velocity}, "
            f"duration {len(buffer_mono) / self.sample_rate * 1000:.0f}ms"
        )

        return buffer_mono

    def generate_note(self, ppg_id: int, instrument_idx: int, note: int, intensity: float) -> np.ndarray:
        """Generate note with explicit instrument and pitch (for scale-based synthesis).

        Selects instrument from PPG's instrument bank, triggers note at specified pitch,
        renders audio buffer, releases note, returns mono buffer.

        Args:
            ppg_id: PPG channel ID (0-3, determines instrument bank)
            instrument_idx: Index into ppg_instruments[ppg_id]['instruments'] list (0-7)
            note: MIDI note number (0-127, calculated from root_note + scale degree)
            intensity: Signal strength 0.0-1.0 (determines velocity)

        Returns:
            Mono audio buffer as float32 numpy array

        Raises:
            ValueError: If ppg_id, instrument_idx, note, or intensity is out of range
            KeyError: If instrument configuration is missing or invalid

        Side effects:
            - Selects MIDI instrument (program_select)
            - Sends MIDI note on/off to FluidSynth
            - Renders audio from FluidSynth internal buffer
        """
        # Validate ppg_id
        if ppg_id not in self.ppg_instruments:
            raise ValueError(f"ppg_id must be 0-3, got {ppg_id}")

        # Get PPG instrument bank config
        ppg_config = self.ppg_instruments[ppg_id]

        # Extract instrument list (new format) or fallback to single program (old format)
        if 'instruments' in ppg_config:
            # New format: list of instruments
            instruments_list = ppg_config['instruments']
            if instrument_idx < 0 or instrument_idx >= len(instruments_list):
                raise ValueError(f"instrument_idx must be 0-{len(instruments_list)-1}, got {instrument_idx}")
            program = instruments_list[instrument_idx]
            midi_bank = ppg_config.get('midi_bank', 0)
        else:
            # Old format: single program (backward compatibility)
            program = ppg_config.get('program', 0)
            midi_bank = ppg_config.get('bank', 0)
            logger.debug(f"Using old config format for PPG {ppg_id}")

        # Validate intensity
        if not 0.0 <= intensity <= 1.0:
            raise ValueError(f"Intensity must be in [0.0, 1.0], got {intensity}")

        # Validate note
        if note < 0 or note > 127:
            raise ValueError(f"MIDI note must be 0-127, got {note}")

        # Select instrument
        self.fs.program_select(
            self.hit_channel,
            self.sfid,
            midi_bank,
            program
        )

        # Map intensity to velocity
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
            f"Generated note: PPG {ppg_id}, instrument {instrument_idx} (bank {midi_bank}, prog {program}), "
            f"note {note}, intensity {intensity:.2f} → velocity {velocity}, "
            f"duration {len(buffer_mono) / self.sample_rate * 1000:.0f}ms"
        )

        return buffer_mono

    def start_drone_note(self, ppg_id: int, instrument_idx: int, note: int, velocity: int = 80) -> None:
        """Start sustained drone note (note stays on until stopped).

        Args:
            ppg_id: PPG channel ID (0-3, determines MIDI channel)
            instrument_idx: Index into ppg_instruments[ppg_id]['instruments'] list
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127, default 80)

        Side effects:
            - Selects instrument on drone channel
            - Sends note_on to FluidSynth (note stays on)
        """
        if ppg_id not in self.ppg_instruments:
            raise ValueError(f"ppg_id must be 0-3, got {ppg_id}")

        channel = self.drone_channels[ppg_id]

        # Select instrument
        ppg_config = self.ppg_instruments[ppg_id]
        if 'instruments' in ppg_config:
            instruments_list = ppg_config['instruments']
            if instrument_idx < 0 or instrument_idx >= len(instruments_list):
                raise ValueError(f"instrument_idx must be 0-{len(instruments_list)-1}, got {instrument_idx}")
            program = instruments_list[instrument_idx]
            midi_bank = ppg_config.get('midi_bank', 0)
        else:
            # Old format fallback
            program = ppg_config.get('program', 0)
            midi_bank = ppg_config.get('bank', 0)

        self.fs.program_select(channel, self.sfid, midi_bank, program)

        # Start sustained note
        self.fs.noteon(channel, note, velocity)

        logger.info(
            f"Started drone: PPG {ppg_id}, channel {channel}, "
            f"instrument {instrument_idx} (bank {midi_bank}, prog {program}), "
            f"note {note}, velocity {velocity}"
        )

    def stop_drone_note(self, ppg_id: int, note: int) -> None:
        """Stop sustained drone note.

        Args:
            ppg_id: PPG channel ID (0-3, determines MIDI channel)
            note: MIDI note number to stop

        Side effects:
            - Sends note_off to FluidSynth
        """
        if ppg_id not in self.ppg_instruments:
            raise ValueError(f"ppg_id must be 0-3, got {ppg_id}")

        channel = self.drone_channels[ppg_id]
        self.fs.noteoff(channel, note)

        logger.info(f"Stopped drone: PPG {ppg_id}, channel {channel}, note {note}")

    def generate_drone_buffer(self, ppg_id: int, duration_ms: float = None) -> np.ndarray:
        """Generate continuous drone buffer chunk from active sustained note.

        Renders audio from currently playing drone note without stopping it.
        Used for buffer chaining to create continuous drone playback.

        Args:
            ppg_id: PPG channel ID (0-3, determines MIDI channel)
            duration_ms: Buffer duration in milliseconds (default: self.drone_buffer_duration)

        Returns:
            Mono audio buffer as float32 numpy array

        Note:
            Drone note must be started with start_drone_note() before calling this.
            Pitch bend and intensity should be set via set_drone_pitch_bend() before rendering.
        """
        if ppg_id not in self.ppg_instruments:
            raise ValueError(f"ppg_id must be 0-3, got {ppg_id}")

        # Calculate buffer size
        duration_sec = (duration_ms / 1000.0) if duration_ms else self.drone_buffer_duration
        num_samples = int(duration_sec * self.sample_rate)

        # Render audio from active drone note
        buffer_stereo = self.fs.get_samples(num_samples)

        # Convert to numpy array if not already
        if not isinstance(buffer_stereo, np.ndarray):
            buffer_array = np.array(buffer_stereo, dtype=np.float32)
        else:
            buffer_array = buffer_stereo.astype(np.float32)

        # Extract mono channel (same as generate_note)
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

        logger.debug(
            f"Generated drone buffer: PPG {ppg_id}, "
            f"duration {len(buffer_mono) / self.sample_rate * 1000:.0f}ms"
        )

        return buffer_mono

    def set_drone_pitch_bend(self, ppg_id: int, bpm: float) -> None:
        """Set pitch bend for drone based on BPM offset from reference.

        Maps BPM linearly to pitch bend range. For every 10 BPM difference,
        apply full pitch_bend_range in cents.

        Example: If pitch_bend_range = 3 semitones and reference_bpm = 75:
            - 75 BPM → 0 cents (center)
            - 85 BPM → +300 cents (+3 semitones)
            - 65 BPM → -300 cents (-3 semitones)

        This produces heterodyne beats at frequency |(BPM1-BPM2)/60| Hz.

        Args:
            ppg_id: PPG channel ID (0-3, determines MIDI channel)
            bpm: Current BPM for this PPG

        Side effects:
            - Sends pitch bend to FluidSynth channel
        """
        if ppg_id not in self.ppg_instruments:
            raise ValueError(f"ppg_id must be 0-3, got {ppg_id}")

        channel = self.drone_channels[ppg_id]

        # Calculate BPM offset
        bpm_offset = bpm - self.drone_reference_bpm

        # Map to cents: ±10 BPM = ±pitch_bend_range semitones
        # Example: ±10 BPM with range=3 → ±300 cents
        max_bpm_offset = 10.0  # BPM range that maps to full pitch bend
        cents = (bpm_offset / max_bpm_offset) * (self.drone_pitch_bend_range * 100.0)

        # Clamp to configured range
        max_cents = self.drone_pitch_bend_range * 100.0
        cents = max(-max_cents, min(max_cents, cents))

        # Convert to MIDI pitch bend (0-16383, 8192 = center)
        pitch_bend_ratio = cents / max_cents
        pitch_bend_value = int(8192 + pitch_bend_ratio * 8192)
        pitch_bend_value = max(0, min(16383, pitch_bend_value))

        # Send pitch bend
        self.fs.pitch_bend(channel, pitch_bend_value)

        logger.debug(
            f"Set drone pitch bend: PPG {ppg_id}, BPM {bpm:.1f}, "
            f"offset {bpm_offset:+.1f}, cents {cents:+.1f}, "
            f"pitch_bend {pitch_bend_value}"
        )

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
