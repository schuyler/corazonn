#!/usr/bin/env python3
"""
Audio Engine - Amor Phase 2 Audio Playback (rtmixer version)

Receives beat, acquire, and release events from sensor processor, plays overlapping sound samples with stereo panning.

ARCHITECTURE:
- OSC server listening on port 8001 for beat input (/beat/{0-3}, /acquire/{0-3}, /release/{0-3} messages)
- Uses SO_REUSEPORT socket option to allow port sharing across processes
- Loads PPG samples (32 files: 4 PPGs × 8 samples), ambient loops (32 files), and global acquire sample
- Validates message timestamps: plays if <500ms old, drops if older
- Uses rtmixer for true concurrent playback with low-latency mixing
- Per-sensor stereo panning for spatial audio separation
- Statistics tracking for all message types

AUDIO PIPELINE:
1. Load mono WAV samples at startup (44.1kHz or 48kHz, 16-bit)
2. On beat arrival: pan mono → stereo using constant-power law
3. Queue stereo buffer to rtmixer for concurrent playback
4. rtmixer mixes all active buffers in C callback

STEREO PANNING:
- PPG 0: Hard left (-1.0)
- PPG 1: Center-left (-0.33)
- PPG 2: Center-right (0.33)
- PPG 3: Hard right (1.0)

Configurable via osc.PPG_PANS constant.

DEVELOPMENT MODE:
By default, stereo panning and intensity scaling are disabled for easier
development/testing. Enable with --enable-panning and --enable-intensity-scaling flags.

USAGE:
    # Start with default settings (port 8001, sounds/ directory, panning and intensity disabled)
    python3 -m amor.audio

    # Enable stereo panning for spatial audio
    python3 -m amor.audio --enable-panning

    # Enable intensity-based volume scaling
    python3 -m amor.audio --enable-intensity-scaling

    # Enable both panning and intensity scaling
    python3 -m amor.audio --enable-panning --enable-intensity-scaling

    # Custom port and sounds directory
    python3 -m amor.audio --port 8001 --sounds-dir /path/to/sounds --enable-panning

    # Select audio device by substring match (e.g., 'pulse', 'MobilePre', 'HDMI')
    python3 -m amor.audio --device pulse
    python3 -m amor.audio --device MobilePre

INPUT OSC MESSAGES:

Input (port 8001):
    Address: /beat/{ppg_id}  where ppg_id is 0-3
    Arguments: [timestamp_ms, bpm, intensity]
    - Timestamp: int, Unix time (milliseconds) when beat detected
    - BPM: float, heart rate in beats per minute
    - Intensity: float, signal strength 0.0-1.0 (enables volume scaling with --enable-intensity-scaling)
    - Plays routed sample (PPG → sample ID mapping)

    Address: /acquire/{ppg_id}  where ppg_id is 0-3
    Arguments: [timestamp_ms, bpm]
    - Timestamp: int, Unix time (milliseconds) when rhythm acquired
    - BPM: float, heart rate at acquisition
    - Plays global acquire acknowledgement sample (same for all PPGs, spatially panned)

    Address: /release/{ppg_id}  where ppg_id is 0-3
    Arguments: [timestamp_ms]
    - Timestamp: int, Unix time (milliseconds) when rhythm lost
    - Currently silent (no audio feedback)

MESSAGE HANDLING:

1. Timestamp validation (applies to all message types):
   - Calculate age: age_ms = (time.time() - timestamp) * 1000
   - Play if age < 500ms
   - Drop if age >= 500ms

2. Audio playback:
   - Load mono sound samples at startup (WAV format: 44.1kHz or 48kHz, 16-bit, mono)
   - Pan mono → stereo based on osc.PPG_PANS constant
   - Use rtmixer.play_buffer() for non-blocking concurrent playback
   - Multiple messages from same or different PPGs overlap properly

3. Statistics:
   - Total messages received (all types)
   - Valid messages (timestamp < 500ms old)
   - Dropped messages (timestamp >= 500ms old)
   - Successfully played messages

MESSAGE VALIDATION:

Beat messages (/beat/{ppg_id}):
1. Address matches /beat/[0-3] pattern
2. Exactly 3 arguments (timestamp, bpm, intensity)
3. PPG ID (from address) in range 0-3
4. Timestamp is non-negative
5. Timestamp is < 500ms old (age validation)

Acquire messages (/acquire/{ppg_id}):
1. Address matches /acquire/[0-3] pattern
2. Exactly 2 arguments (timestamp, bpm)
3. PPG ID (from address) in range 0-3
4. Timestamp is non-negative
5. Timestamp is < 500ms old (age validation)

Release messages (/release/{ppg_id}):
1. Address matches /release/[0-3] pattern
2. Exactly 1 argument (timestamp)
3. PPG ID (from address) in range 0-3
4. Timestamp is non-negative
5. Timestamp is < 500ms old (age validation)

Edge cases:
- Missing WAV files: prints warning at startup, graceful degradation
- Invalid ppg_id: message rejected
- Stale timestamp: message dropped (not played)
- Future timestamp: accepted and played (per protocol contract)
- Missing acquire sample: acquire messages skipped with warning

DEBUGGING TIPS:

1. Enable verbose output:
   - Check console for "BEAT PLAYED:", "ACQUIRE PLAYED:", "RELEASE:" messages
   - Watch for stale timestamp drops

2. Check statistics on shutdown (Ctrl+C):
   - Total messages (all types), valid, dropped, played
   - Ratio should show how many timestamps are stale

3. Audio verification:
   - Use test_inject_beats.py to send test beats
   - Listen for spatially separated sounds across stereo field
   - Acquire events use global sample, beats use routed samples

Reference: docs/audio/rtmixer-architecture.md
"""

import argparse
import os
import sys
import time
import threading
from collections import deque
from pathlib import Path
from pythonosc import dispatcher
import soundfile as sf
import sounddevice as sd
import numpy as np
import rtmixer
import yaml

from amor import osc
from amor.log import get_logger

logger = get_logger("audio")

# Audio effects (optional dependency on pedalboard)
try:
    from amor.audio_effects import EffectsProcessor
    EFFECTS_AVAILABLE = True
except ImportError as e:
    logger.info(f"Audio effects unavailable (install pedalboard to enable): {e}")
    EFFECTS_AVAILABLE = False


def find_audio_device(substring):
    """Find the first audio device matching a substring.

    Args:
        substring (str): Substring to search for in device names (case-insensitive)

    Returns:
        int: Device index of first match, or None if no match found

    Side effects:
        Prints list of available devices and selected device info

    Examples:
        >>> find_audio_device("pulse")
        6
        >>> find_audio_device("MobilePre")
        4
    """
    devices = sd.query_devices()
    substring_lower = substring.lower()

    # Print available devices for user reference
    logger.info(f"\nSearching for device matching '{substring}'...")
    logger.info("\nAvailable audio devices:")
    for i, device in enumerate(devices):
        marker = "*" if i == sd.default.device[1] else " "
        logger.info(f"{marker}{i:2d} {device['name']}")
    logger.info("")

    # Find first matching device
    for i, device in enumerate(devices):
        if substring_lower in device['name'].lower():
            logger.info(f"Selected device {i}: {device['name']}\n")
            return i

    logger.warning(f"No device found matching '{substring}', using default device\n")
    return None


class LoopManager:
    """Manages ambient loop playback with voice limiting and type-based ejection.

    Handles 32 loops (0-31) split into two types:
    - Latching loops (0-15): Toggle on/off, max 6 concurrent
    - Momentary loops (16-31): Press/release, max 4 concurrent

    When voice limit is reached, oldest loop of that type is stopped before
    starting new one. Uses rtmixer actions for start/stop control.

    Attributes:
        mixer (rtmixer.Mixer): Audio mixer for playback
        loops (dict): Pre-loaded loop audio data {loop_id: ndarray}
        active_loops (dict): Currently playing loops {loop_id: rtmixer action}
        latching_order (deque): Start order for latching loops (oldest first)
        momentary_order (deque): Start order for momentary loops (oldest first)
        latching_limit (int): Max concurrent latching loops (default 6)
        momentary_limit (int): Max concurrent momentary loops (default 4)
    """

    LATCHING_MAX_ID = 15  # Loops 0-15 are latching
    LATCHING_LIMIT = 6     # Max concurrent latching loops
    MOMENTARY_LIMIT = 4    # Max concurrent momentary loops

    def __init__(self, mixer, loops, latching_limit=6, momentary_limit=4):
        """Initialize loop manager.

        Args:
            mixer (rtmixer.Mixer): Audio mixer for playback
            loops (dict): Pre-loaded loop audio data {loop_id: ndarray}
            latching_limit (int): Max concurrent latching loops (default 6)
            momentary_limit (int): Max concurrent momentary loops (default 4)
        """
        self.mixer = mixer
        self.loops = loops
        self.active_loops = {}
        self.latching_order = deque()
        self.momentary_order = deque()
        self.latching_limit = latching_limit
        self.momentary_limit = momentary_limit
        self.lock = threading.Lock()  # Protects all shared state

    def _is_latching(self, loop_id):
        """Check if loop ID is latching type (0-15) or momentary (16-31).

        Args:
            loop_id (int): Loop ID (0-31)

        Returns:
            bool: True if latching, False if momentary
        """
        return loop_id <= self.LATCHING_MAX_ID

    def _get_order_queue(self, loop_id):
        """Get the start order queue for this loop's type.

        Args:
            loop_id (int): Loop ID (0-31)

        Returns:
            deque: latching_order or momentary_order
        """
        return self.latching_order if self._is_latching(loop_id) else self.momentary_order

    def _get_limit(self, loop_id):
        """Get the voice limit for this loop's type.

        Args:
            loop_id (int): Loop ID (0-31)

        Returns:
            int: latching_limit or momentary_limit
        """
        return self.latching_limit if self._is_latching(loop_id) else self.momentary_limit

    def _count_active_of_type(self, loop_id):
        """Count how many loops of this type are currently active.

        Args:
            loop_id (int): Loop ID (0-31)

        Returns:
            int: Number of active loops of this type
        """
        is_latching = self._is_latching(loop_id)
        return sum(1 for lid in self.active_loops.keys()
                   if self._is_latching(lid) == is_latching)

    def start(self, loop_id: int) -> 'Optional[int]':
        """Start playing a loop, ejecting oldest if voice limit reached.

        Args:
            loop_id: Loop ID to start (0-31)

        Returns:
            ID of ejected loop if voice limit was exceeded, None otherwise

        Raises:
            ValueError: If loop_id is invalid or loop not loaded

        Side effects:
            - Starts audio playback via mixer.play_buffer()
            - Stores action in active_loops
            - Adds loop_id to appropriate order queue
            - May stop oldest loop if limit exceeded
        """
        # Validate loop_id
        if not isinstance(loop_id, int) or not 0 <= loop_id <= 31:
            raise ValueError(f"loop_id must be int in range [0, 31], got {loop_id}")

        # Check if loop audio data exists and if already active (thread-safe)
        with self.lock:
            if loop_id not in self.loops:
                raise ValueError(f"Loop {loop_id} not loaded in loops dict")

            # If already active, do nothing
            if loop_id in self.active_loops:
                return None

            # Get loop data under lock
            mono_data = self.loops[loop_id]

        # Prepare new loop playback outside lock (may call mixer.play_buffer)
        try:
            # Loops always pan to center
            stereo_data = pan_mono_to_stereo(mono_data, 0.0, enable_panning=False)
            action = self.mixer.play_buffer(stereo_data, channels=2)
        except Exception as e:
            logger.warning(f"Failed to start loop {loop_id}: {e}")
            return None

        # Update shared state atomically
        with self.lock:
            # Check voice limit and eject if needed
            order_queue = self._get_order_queue(loop_id)
            limit = self._get_limit(loop_id)
            count = self._count_active_of_type(loop_id)
            ejected_loop_id = None

            if count >= limit:
                # Eject oldest loop of this type
                if order_queue:
                    ejected_loop_id = order_queue.popleft()
                    self._stop_internal(ejected_loop_id)
                    loop_type = "latching" if self._is_latching(loop_id) else "momentary"
                    logger.info(f"Loop voice limit reached ({count}/{limit} {loop_type}), ejected loop {ejected_loop_id}")

            # Track new loop as active
            self.active_loops[loop_id] = action
            order_queue.append(loop_id)

            return ejected_loop_id

    def _stop_internal(self, loop_id):
        """Internal method to stop a loop without removing from order queue.

        Args:
            loop_id (int): Loop ID to stop (0-31)
        """
        if loop_id not in self.active_loops:
            return

        try:
            action = self.active_loops[loop_id]
            self.mixer.cancel(action)
        except Exception as e:
            logger.warning(f"Failed to cancel loop {loop_id}: {e}")
        finally:
            del self.active_loops[loop_id]

    def stop(self, loop_id: int) -> None:
        """Stop playing a loop.

        Args:
            loop_id: Loop ID to stop (0-31)

        Raises:
            ValueError: If loop_id is invalid

        Side effects:
            - Stops audio playback via mixer.cancel()
            - Removes from active_loops
            - Removes from order queue
        """
        # Validate loop_id
        if not isinstance(loop_id, int) or not 0 <= loop_id <= 31:
            raise ValueError(f"loop_id must be int in range [0, 31], got {loop_id}")

        with self.lock:
            if loop_id not in self.active_loops:
                return

            # Stop playback
            self._stop_internal(loop_id)

            # Remove from order queue
            order_queue = self._get_order_queue(loop_id)
            if loop_id in order_queue:
                order_queue.remove(loop_id)

    def is_active(self, loop_id: int) -> bool:
        """Check if a loop is currently playing.

        Args:
            loop_id: Loop ID (0-31)

        Returns:
            True if loop is active, False otherwise

        Raises:
            ValueError: If loop_id is invalid
        """
        # Validate loop_id
        if not isinstance(loop_id, int) or not 0 <= loop_id <= 31:
            raise ValueError(f"loop_id must be int in range [0, 31], got {loop_id}")

        with self.lock:
            return loop_id in self.active_loops


class PPGVoiceManager:
    """Manages PPG sample voice limiting with per-channel FIFO ejection.

    Tracks active samples for 8 PPG channels (0-7) and enforces voice limit
    by canceling oldest sample when limit is reached. Uses immediate cancellation
    via rtmixer.cancel() without fade-out.

    Attributes:
        mixer (rtmixer.Mixer): Audio mixer for playback cancellation
        voice_limit (int): Max concurrent samples per PPG channel
        active_samples (dict): {ppg_id: deque([action1, action2, ...])}
        ejection_stats (dict): {ppg_id: total_ejections_count}
        lock (threading.Lock): Protects all shared state
    """

    def __init__(self, mixer, voice_limit=4):
        """Initialize voice manager.

        Args:
            mixer (rtmixer.Mixer): Audio mixer for cancellation
            voice_limit (int): Max concurrent samples per PPG (default 4)

        Raises:
            ValueError: If voice_limit is not in valid range [1, 100]
        """
        if not isinstance(voice_limit, int) or not 1 <= voice_limit <= 100:
            raise ValueError(
                f"voice_limit must be int in range [1, 100], got {voice_limit}"
            )

        self.mixer = mixer
        self.voice_limit = voice_limit
        # Per-PPG deques for FIFO tracking (8 channels: 0-7)
        # Cleanup strategy: Keep at most (voice_limit + 10) actions to prevent
        # unbounded growth while avoiding premature cleanup of active samples
        self.active_samples = {ppg_id: deque() for ppg_id in range(8)}
        self.lock = threading.Lock()
        # Track ejection statistics per PPG
        self.ejection_stats = {ppg_id: 0 for ppg_id in range(8)}

    def track_sample(self, ppg_id: int, action) -> 'Optional[Any]':
        """Track a new sample, ejecting oldest if voice limit reached.

        Args:
            ppg_id: PPG channel ID (0-7)
            action: rtmixer action returned from play_buffer()

        Returns:
            Ejected action if voice limit was exceeded, None otherwise

        Raises:
            ValueError: If ppg_id or action is invalid
            TypeError: If action is not an rtmixer action object

        Side effects:
            - May cancel oldest sample via mixer.cancel()
            - Cleans up completed actions to prevent unbounded growth
            - Updates active_samples tracking and ejection_stats
            - Logs when voice limit reached
        """
        # Validate ppg_id
        if not isinstance(ppg_id, int) or not 0 <= ppg_id <= 7:
            raise ValueError(f"ppg_id must be int in range [0, 7], got {ppg_id}")

        # Validate action is not None
        if action is None:
            raise ValueError("action cannot be None")

        # Validate action type (rtmixer actions have a ringbuffer attribute)
        if not hasattr(action, 'ringbuffer'):
            raise TypeError(
                f"action must be rtmixer.Action, got {type(action).__name__}"
            )

        with self.lock:
            queue = self.active_samples[ppg_id]
            ejected_action = None

            # Cleanup completed actions to prevent unbounded growth
            # Keep at most (voice_limit + 10) actions as safety margin
            max_queue_size = self.voice_limit + 10
            if len(queue) > max_queue_size:
                excess = len(queue) - max_queue_size
                for _ in range(excess):
                    queue.popleft()
                logger.debug(
                    f"PPG {ppg_id} cleanup: removed {excess} completed actions "
                    f"(queue was {len(queue) + excess}, now {len(queue)})"
                )

            # Eject oldest sample if at or above voice limit
            if len(queue) >= self.voice_limit:
                old_count = len(queue)
                ejected_action = queue.popleft()
                # Cancel oldest sample (immediate stop, no fade)
                try:
                    self.mixer.cancel(ejected_action)
                    self.ejection_stats[ppg_id] += 1
                    logger.info(
                        f"PPG {ppg_id} voice limit reached ({old_count}/{self.voice_limit}), "
                        f"ejected oldest sample → queue now {len(queue)}/{self.voice_limit} "
                        f"(total ejections: {self.ejection_stats[ppg_id]})"
                    )
                except Exception as e:
                    logger.warning(f"Failed to cancel sample for PPG {ppg_id}: {e}")

            # Track new sample
            queue.append(action)

            return ejected_action


class DroneManager:
    """Manages continuous drone synthesis with pitch-shifted samples.

    Handles per-channel sustained tones pitched to BPM, with lazy caching
    of pitch-shifted buffers and smooth volume transitions based on intensity.

    Attributes:
        mixer (rtmixer.Mixer): Audio mixer for playback
        drone_samples (dict): Pre-loaded mono drone samples {sample_id: {'audio': ndarray, 'base_freq_hz': float}}
        sample_rate (float): Audio sample rate
        active_drones (dict): {ppg_id: {'action': rtmixer.Action, 'freq_hz': float, 'sample_id': int, 'pan': float}}
        pitch_cache (dict): {(sample_id, freq_hz): pitched_buffer}
        lock (threading.Lock): Protects all shared state
    """

    def __init__(self, mixer, drone_samples, sample_rate):
        """Initialize drone manager.

        Args:
            mixer (rtmixer.Mixer): Audio mixer for playback
            drone_samples (dict): Pre-loaded drone samples {sample_id: {'audio': ndarray, 'base_freq_hz': float}}
            sample_rate (float): Audio sample rate
        """
        self.mixer = mixer
        self.drone_samples = drone_samples
        self.sample_rate = sample_rate
        self.active_drones = {}
        self.pitch_cache = {}
        self.lock = threading.Lock()

    def _quantize_freq(self, freq_hz):
        """Round frequency to nearest 0.5 Hz for cache efficiency.

        Args:
            freq_hz (float): Target frequency in Hz

        Returns:
            float: Quantized frequency
        """
        return round(freq_hz * 2.0) / 2.0

    def _generate_additive_waveform(self, freq_hz, harmonics=4, rolloff=1.5, min_duration=2.0):
        """Generate additive synthesis waveform with harmonics.

        Creates a seamlessly looping waveform by ensuring the buffer contains
        an integer number of periods, preventing clicks at loop boundaries.

        Args:
            freq_hz (float): Fundamental frequency in Hz
            harmonics (int): Number of harmonics to include (default 4)
            rolloff (float): Amplitude rolloff exponent (default 1.5)
                            Amplitude of nth harmonic = 1/n^rolloff
            min_duration (float): Minimum duration in seconds (default 2.0)
                                 Actual duration adjusted to complete full periods

        Returns:
            np.ndarray: Mono audio buffer with additive waveform
        """
        # Calculate duration as integer number of periods for seamless looping
        period = 1.0 / freq_hz
        num_periods = max(1, int(np.ceil(min_duration / period)))

        # Calculate exact number of samples for perfect periodicity
        # samples_per_period must be exact for seamless looping
        samples_per_period = self.sample_rate / freq_hz
        num_samples = int(round(num_periods * samples_per_period))
        duration = num_samples / self.sample_rate

        t = np.linspace(0, duration, num_samples, endpoint=False)
        signal = np.zeros(num_samples, dtype=np.float32)

        # Add fundamental and harmonics with amplitude rolloff
        for n in range(1, harmonics + 1):
            amplitude = 1.0 / (n ** rolloff)
            harmonic_freq = freq_hz * n
            signal += amplitude * np.sin(2 * np.pi * harmonic_freq * t)

        # Normalize to prevent clipping
        max_amplitude = np.max(np.abs(signal))
        if max_amplitude > 0:
            signal = signal / max_amplitude

        return signal.astype(np.float32)

    def _get_additive_buffer(self, freq_hz, harmonics, rolloff):
        """Get additive waveform from cache or generate on-demand.

        Args:
            freq_hz (float): Target frequency in Hz
            harmonics (int): Number of harmonics
            rolloff (float): Amplitude rolloff exponent

        Returns:
            np.ndarray: Mono additive waveform buffer
        """
        cache_key = ('additive', freq_hz, harmonics, rolloff)

        if cache_key in self.pitch_cache:
            return self.pitch_cache[cache_key]

        # Generate waveform
        waveform = self._generate_additive_waveform(freq_hz, harmonics, rolloff)

        # Cache the result
        self.pitch_cache[cache_key] = waveform
        logger.debug(f"Cached additive waveform: {freq_hz:.1f} Hz, {harmonics} harmonics, rolloff {rolloff}")

        return waveform

    def _get_pitched_buffer(self, sample_id, target_freq_hz):
        """Get pitch-shifted buffer from cache or generate on-demand.

        Uses pedalboard.PitchShift to transpose base sample to target frequency.
        First access generates and caches, subsequent accesses return cached buffer.

        Args:
            sample_id (int): Drone sample ID
            target_freq_hz (float): Target frequency in Hz

        Returns:
            np.ndarray: Mono pitch-shifted audio buffer
        """
        cache_key = (sample_id, target_freq_hz)

        if cache_key in self.pitch_cache:
            return self.pitch_cache[cache_key]

        # Get base sample and frequency
        if sample_id not in self.drone_samples:
            raise ValueError(f"Drone sample {sample_id} not loaded")

        drone_info = self.drone_samples[sample_id]
        base_sample = drone_info['audio']
        base_freq_hz = drone_info['base_freq_hz']

        # Calculate semitone shift
        semitones = 12.0 * np.log2(target_freq_hz / base_freq_hz)

        # Pitch shift using pedalboard
        try:
            from pedalboard import PitchShift
            shifter = PitchShift(semitones=semitones)
            pitched = shifter(base_sample, sample_rate=self.sample_rate)
        except Exception as e:
            logger.warning(f"Failed to pitch shift sample {sample_id} by {semitones:.1f} semitones: {e}")
            # Fallback to original sample
            pitched = base_sample

        # Cache the result
        self.pitch_cache[cache_key] = pitched
        logger.debug(f"Cached pitch-shifted sample: ID {sample_id}, {base_freq_hz:.1f}Hz → {target_freq_hz:.1f}Hz ({semitones:+.1f} semitones)")

        return pitched

    def start_drone(self, ppg_id, bpm, sample_id, octave_shift, pan, intensity):
        """Start continuous drone for PPG channel.

        Args:
            ppg_id (int): PPG channel ID (0-7)
            bpm (float): Beats per minute
            sample_id (int): Drone sample ID
            octave_shift (int): Octave shift (multiply freq by 2^octave_shift)
            pan (float): Pan position (-1.0 to 1.0)
            intensity (float): Volume intensity (0.0 to 1.0)
        """
        # Calculate target frequency
        base_freq = bpm / 60.0  # Convert BPM to Hz
        target_freq = base_freq * (2 ** octave_shift)
        target_freq = self._quantize_freq(target_freq)

        with self.lock:
            # Stop existing drone if any
            if ppg_id in self.active_drones:
                self._stop_internal(ppg_id)

            # Get pitched buffer
            try:
                mono_buffer = self._get_pitched_buffer(sample_id, target_freq)
            except Exception as e:
                logger.warning(f"Failed to start drone for PPG {ppg_id}: {e}")
                return

            # Apply volume based on intensity
            mono_buffer = mono_buffer * intensity

            # Pan to stereo
            stereo_buffer = pan_mono_to_stereo(mono_buffer, pan, enable_panning=True)

            # Start playback
            try:
                action = self.mixer.play_buffer(stereo_buffer, channels=2)
            except Exception as e:
                logger.warning(f"Failed to play drone buffer for PPG {ppg_id}: {e}")
                return

            # Track active drone
            self.active_drones[ppg_id] = {
                'action': action,
                'freq_hz': target_freq,
                'intensity': intensity,
                'sample_id': sample_id,
                'pan': pan,
                'octave_shift': octave_shift
            }

            logger.info(f"DRONE START: PPG {ppg_id}, {bpm:.1f} BPM → {target_freq:.1f} Hz (octave +{octave_shift}), intensity {intensity:.2f}")

    def start_additive_drone(self, ppg_id, bpm, octave_shift, harmonics, rolloff, pan, intensity):
        """Start continuous additive synthesis drone for PPG channel.

        Args:
            ppg_id (int): PPG channel ID (0-7)
            bpm (float): Beats per minute
            octave_shift (int): Octave shift (multiply freq by 2^octave_shift)
            harmonics (int): Number of harmonics to include
            rolloff (float): Amplitude rolloff exponent
            pan (float): Pan position (-1.0 to 1.0)
            intensity (float): Volume intensity (0.0 to 1.0)
        """
        # Calculate target frequency
        base_freq = bpm / 60.0
        target_freq = base_freq * (2 ** octave_shift)
        target_freq = self._quantize_freq(target_freq)

        with self.lock:
            # Stop existing drone if any
            if ppg_id in self.active_drones:
                self._stop_internal(ppg_id)

            # Get additive waveform
            try:
                mono_buffer = self._get_additive_buffer(target_freq, harmonics, rolloff)
            except Exception as e:
                logger.warning(f"Failed to generate additive waveform for PPG {ppg_id}: {e}")
                return

            # Apply volume based on intensity
            mono_buffer = mono_buffer * intensity

            # Pan to stereo
            stereo_buffer = pan_mono_to_stereo(mono_buffer, pan, enable_panning=True)

            # Start playback
            try:
                action = self.mixer.play_buffer(stereo_buffer, channels=2)
            except Exception as e:
                logger.warning(f"Failed to play additive drone buffer for PPG {ppg_id}: {e}")
                return

            # Track active drone
            self.active_drones[ppg_id] = {
                'action': action,
                'freq_hz': target_freq,
                'intensity': intensity,
                'mode': 'additive',
                'harmonics': harmonics,
                'rolloff': rolloff,
                'pan': pan,
                'octave_shift': octave_shift
            }

            logger.info(f"ADDITIVE DRONE START: PPG {ppg_id}, {bpm:.1f} BPM → {target_freq:.1f} Hz (octave +{octave_shift}), {harmonics} harmonics, intensity {intensity:.2f}")

    def update_drone(self, ppg_id, bpm, intensity, octave_shift):
        """Update drone frequency and volume when BPM/intensity changes.

        Works for both sample-based and additive drones.

        Args:
            ppg_id (int): PPG channel ID (0-7)
            bpm (float): Beats per minute
            intensity (float): Volume intensity (0.0 to 1.0)
            octave_shift (int): Octave shift
        """
        # Calculate new frequency
        base_freq = bpm / 60.0
        new_freq = base_freq * (2 ** octave_shift)
        new_freq = self._quantize_freq(new_freq)

        with self.lock:
            if ppg_id not in self.active_drones:
                # Drone not active, ignore update
                return

            current_info = self.active_drones[ppg_id]
            current_freq = current_info['freq_hz']
            current_intensity = current_info.get('intensity', 0.0)
            pan = current_info['pan']
            mode = current_info.get('mode', 'sample')

            # Check if frequency changed significantly (after quantization)
            freq_changed = abs(new_freq - current_freq) > 0.1

            # Check if volume changed significantly
            volume_changed = abs(intensity - current_intensity) > 0.15

            # Skip update if neither changed significantly
            if not freq_changed and not volume_changed:
                return

            # Get new buffer based on mode (only if frequency changed)
            try:
                if mode == 'additive':
                    harmonics = current_info['harmonics']
                    rolloff = current_info['rolloff']
                    mono_buffer = self._get_additive_buffer(new_freq, harmonics, rolloff)
                else:
                    # Sample-based mode
                    sample_id = current_info['sample_id']
                    mono_buffer = self._get_pitched_buffer(sample_id, new_freq)
            except Exception as e:
                logger.warning(f"Failed to update drone for PPG {ppg_id}: {e}")
                return

            # Apply volume
            mono_buffer = mono_buffer * intensity

            # Pan to stereo
            stereo_buffer = pan_mono_to_stereo(mono_buffer, pan, enable_panning=True)

            # Start new playback
            try:
                new_action = self.mixer.play_buffer(stereo_buffer, channels=2)
            except Exception as e:
                logger.warning(f"Failed to play updated drone buffer for PPG {ppg_id}: {e}")
                return

            # Cancel old drone (with crossfade to smooth transition)
            old_action = current_info['action']
            try:
                # Longer crossfade (250ms) to hide phase discontinuities
                threading.Timer(0.25, lambda: self.mixer.cancel(old_action)).start()
            except Exception as e:
                logger.warning(f"Failed to cancel old drone for PPG {ppg_id}: {e}")

            # Update state (preserve mode-specific fields)
            if mode == 'additive':
                self.active_drones[ppg_id] = {
                    'action': new_action,
                    'freq_hz': new_freq,
                    'intensity': intensity,
                    'mode': 'additive',
                    'harmonics': current_info['harmonics'],
                    'rolloff': current_info['rolloff'],
                    'pan': pan,
                    'octave_shift': octave_shift
                }
            else:
                self.active_drones[ppg_id] = {
                    'action': new_action,
                    'freq_hz': new_freq,
                    'intensity': intensity,
                    'sample_id': current_info['sample_id'],
                    'pan': pan,
                    'octave_shift': octave_shift
                }

            if freq_changed:
                logger.debug(f"DRONE UPDATE: PPG {ppg_id}, {current_freq:.1f} Hz → {new_freq:.1f} Hz, intensity {intensity:.2f}")

    def stop_drone(self, ppg_id):
        """Stop drone with release envelope.

        Args:
            ppg_id (int): PPG channel ID (0-7)
        """
        with self.lock:
            self._stop_internal(ppg_id)
            logger.info(f"DRONE STOP: PPG {ppg_id}")

    def _stop_internal(self, ppg_id):
        """Internal method to stop a drone without logging.

        Args:
            ppg_id (int): PPG channel ID (0-7)
        """
        if ppg_id not in self.active_drones:
            return

        try:
            action = self.active_drones[ppg_id]['action']
            self.mixer.cancel(action)
        except Exception as e:
            logger.warning(f"Failed to cancel drone {ppg_id}: {e}")
        finally:
            del self.active_drones[ppg_id]


def pan_mono_to_stereo(mono_data, pan, enable_panning=False):
    """
    Convert mono PCM to stereo with constant-power panning.

    Uses constant-power pan law to maintain equal perceived loudness
    across the stereo field. Pan position controls the balance between
    left and right channels using trigonometric weighting.

    Args:
        mono_data: 1D numpy array (mono samples), dtype float32
        pan: -1.0 (hard left) to 1.0 (hard right), 0.0 = center
        enable_panning: If False, always pan to center (for development)

    Returns:
        2D numpy array shape (samples, 2) for stereo, dtype float32

    Raises:
        TypeError: If mono_data is not a numpy array
        ValueError: If mono_data is not 1D, is empty, or pan is out of range

    Examples:
        >>> mono = np.array([0.5, 0.3, 0.1], dtype=np.float32)
        >>> stereo = pan_mono_to_stereo(mono, -1.0)  # Hard left
        >>> stereo.shape
        (3, 2)
        >>> stereo[0, 0] > stereo[0, 1]  # Left channel louder
        True
    """
    # Validate inputs
    if not isinstance(mono_data, np.ndarray):
        raise TypeError(f"mono_data must be numpy array, got {type(mono_data)}")

    if mono_data.ndim != 1:
        raise ValueError(f"mono_data must be 1D array, got shape {mono_data.shape}")

    if len(mono_data) == 0:
        raise ValueError("mono_data is empty")

    if not -1.0 <= pan <= 1.0:
        raise ValueError(f"pan must be in [-1.0, 1.0], got {pan}")

    # Map pan from [-1, 1] to angle [0, π/2]
    if enable_panning:
        angle = (pan + 1.0) * np.pi / 4.0
    else:
        angle = np.pi / 4  # Center (development mode)

    # Cast to float32 to avoid precision loss when multiplying with float32 arrays
    left_gain = np.float32(np.cos(angle))
    right_gain = np.float32(np.sin(angle))

    # Create stereo array
    stereo = np.zeros((len(mono_data), 2), dtype=np.float32)
    stereo[:, 0] = mono_data * left_gain   # Left channel
    stereo[:, 1] = mono_data * right_gain  # Right channel

    return stereo


class AudioEngine:
    """OSC server for beat event audio playback using rtmixer.

    Manages beat reception, timestamp validation, and concurrent audio playback
    with stereo panning. Uses rtmixer for true concurrent mixing of overlapping
    samples.

    Architecture:
        - OSC server on port (default 8001) listening for /beat/{0-3} messages
        - Four mono WAV samples loaded at startup (44.1kHz or 48kHz, 16-bit)
        - Single rtmixer.Mixer instance for stereo output
        - Mono → stereo panning on-the-fly per beat
        - Concurrent playback of overlapping samples

    Attributes:
        port (int): UDP port for beat input (default: 8001)
        sounds_dir (str): Directory containing WAV files
        samples (dict): 4 loaded mono WAV samples indexed 0-3
        sample_rate (float): Sample rate from WAV files (typically 44100 or 48000)
        mixer (rtmixer.Mixer): Stereo audio mixer for concurrent playback
        stats (MessageStatistics): Message counters
    """

    # Timestamp age threshold in milliseconds
    TIMESTAMP_THRESHOLD_MS = 500

    def __init__(self, port=osc.PORT_BEATS, control_port=osc.PORT_CONTROL, sounds_dir="sounds", enable_panning=False, enable_intensity_scaling=False, config_path="amor/config/samples.yaml", device=None):
        """Initialize audio engine and load WAV samples.

        Args:
            port (int): OSC port for beat input (default: osc.PORT_BEATS)
            control_port (int): OSC port for control messages (default: osc.PORT_CONTROL)
            sounds_dir (str): Path to directory containing WAV files (deprecated, use config)
            enable_panning (bool): Enable stereo panning (default False for development)
            enable_intensity_scaling (bool): Enable intensity-based volume scaling (default False for development)
            config_path (str): Path to YAML config file (default: amor/config/samples.yaml)
            device (int or None): Audio device index or None for default (default: None)

        Raises:
            FileNotFoundError: If config file not found
            RuntimeError: If config loading or rtmixer initialization fails
        """
        self.port = port
        self.control_port = control_port
        self.sounds_dir = sounds_dir
        self.enable_panning = enable_panning
        self.enable_intensity_scaling = enable_intensity_scaling
        self.device = device

        # Load YAML config
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

        # Store config for later use (e.g., by handle_load_bank_message)
        self.config = config

        # Validate config structure
        if 'ppg_samples' not in config:
            raise RuntimeError("Config missing 'ppg_samples' section")
        if not isinstance(config['ppg_samples'], dict):
            raise RuntimeError("'ppg_samples' must be a dict, not list")
        if 'ambient_loops' not in config:
            raise RuntimeError("Config missing 'ambient_loops' section")
        if not isinstance(config.get('ambient_loops', {}), dict):
            raise RuntimeError("'ambient_loops' must be a dict")
        if 'latching' not in config['ambient_loops'] or 'momentary' not in config['ambient_loops']:
            raise RuntimeError("'ambient_loops' must contain 'latching' and 'momentary' keys")

        # Extract voice limit (used by PPG voice manager for sample playback limiting)
        self.voice_limit = config.get('voice_limit', 4)

        # Load PPG samples (32 files: 4 PPGs × 8 samples each)
        self.samples = {}
        self.sample_rate = None

        # Load global acquire acknowledgement sample
        self.acquire_sample = None
        acquire_path = config.get('acquire_sample')
        if acquire_path:
            self._load_acquire_sample(acquire_path)

        for ppg_id in range(4):
            self.samples[ppg_id] = {}
            # Load default bank for each PPG (new multi-bank structure)
            ppg_banks = config.get('ppg_samples', {}).get(ppg_id, {})

            # Handle both old format (list) and new format (dict of banks)
            if isinstance(ppg_banks, list):
                # Old format: direct list of samples
                sample_paths = ppg_banks
            elif isinstance(ppg_banks, dict):
                # New format: dict of named banks, use 'default' bank
                sample_paths = ppg_banks.get('default', [])
            else:
                logger.warning(f"Invalid ppg_samples format for PPG {ppg_id}, skipping")
                sample_paths = []

            for sample_id, filepath in enumerate(sample_paths):
                if sample_id >= 8:
                    break  # Only load first 8 samples per PPG

                self._load_sample(filepath, ppg_id, sample_id)

        # Load ambient loops (32 files: 16 latching + 16 momentary)
        self.loops = {}
        loop_id = 0

        # Load latching loops (0-15)
        for filepath in config.get('ambient_loops', {}).get('latching', []):
            if loop_id >= 16:
                break
            self._load_loop(filepath, loop_id)
            loop_id += 1

        # Load momentary loops (16-31)
        for filepath in config.get('ambient_loops', {}).get('momentary', []):
            if loop_id >= 32:
                break
            self._load_loop(filepath, loop_id)
            loop_id += 1

        # Load drone samples for continuous synthesis
        self.drone_samples = {}
        drone_configs = config.get('drone_samples', [])
        for sample_id, drone_config in enumerate(drone_configs):
            if isinstance(drone_config, dict):
                # New format: {path: ..., base_freq_hz: ...}
                self._load_drone_sample(drone_config, sample_id)
            elif isinstance(drone_config, str):
                # Old format: just a path, require base_freq_hz to be specified
                logger.warning(f"Drone sample {sample_id} missing base_freq_hz, skipping: {drone_config}")

        # Validate that at least one audio file loaded successfully
        if self.sample_rate is None:
            raise RuntimeError(
                "No valid audio files found. At least one sample or loop "
                "must load successfully to determine sample rate."
            )

        # Print loading summary
        loaded_samples = sum(len(samples) for samples in self.samples.values())
        loaded_loops = len(self.loops)
        loaded_drones = len(self.drone_samples)
        logger.info(f"Loaded {loaded_samples}/32 PPG samples, {loaded_loops}/32 ambient loops, {loaded_drones} drone samples")

        # Initialize routing table (PPG ID → mode config)
        # 8 channels: 0-3 (real sensors), 4-7 (virtual channels)
        # Modulo-4 bank mapping: channel N uses sample bank (N % 4)
        # Load from config or use defaults
        routing_config = config.get('ppg_routing', {})
        self.routing = {}
        for ppg_id in range(8):
            if ppg_id in routing_config:
                self.routing[ppg_id] = routing_config[ppg_id]
            else:
                # Default to percussive mode with sample 0
                self.routing[ppg_id] = {'mode': 'percussive', 'sample_id': 0}

        # BPM multiplier for tempo scaling (default: 1.0, no scaling)
        self.bpm_multiplier = 1.0

        # Initialize rtmixer for stereo output
        # Note: rtmixer (via PortAudio) will handle sample rate conversion if
        # the system audio hardware uses a different rate than the WAV files
        try:
            self.mixer = rtmixer.Mixer(
                device=self.device,
                channels=2,
                samplerate=int(self.sample_rate),
                blocksize=512  # ~11.6ms at 44.1kHz or ~10.7ms at 48kHz, balances latency vs CPU
            )
            self.mixer.start()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize rtmixer: {e}")

        # Initialize loop manager
        self.loop_manager = LoopManager(self.mixer, self.loops)

        # Initialize PPG voice manager (voice limiting for beat sample playback)
        self.ppg_voice_manager = PPGVoiceManager(self.mixer, voice_limit=self.voice_limit)

        # Initialize drone manager
        self.drone_manager = DroneManager(self.mixer, self.drone_samples, self.sample_rate)

        # Initialize effects processor
        self.effects_processor = None
        if EFFECTS_AVAILABLE:
            effects_config = config.get('audio_effects', {})
            if effects_config.get('enable', False):
                try:
                    self.effects_processor = EffectsProcessor(effects_config, self.sample_rate)
                    logger.info("Audio effects processor initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize effects processor: {e}")
            else:
                logger.info("Audio effects disabled in config (set audio_effects.enable: true to enable)")
        else:
            logger.info("Audio effects unavailable (install pedalboard: pip install pedalboard)")

        # Threading lock for shared state (routing table, loop manager)
        self.state_lock = threading.Lock()

        # Statistics
        self.stats = osc.MessageStatistics()

    def _load_sample(self, filepath, ppg_id, sample_id):
        """Load a single PPG sample WAV file.

        Args:
            filepath (str): Path to WAV file
            ppg_id (int): PPG sensor ID (0-3)
            sample_id (int): Sample ID within PPG bank (0-7)

        Side effects:
            - Stores audio data in self.samples[ppg_id][sample_id] if successful
            - Sets self.sample_rate if not yet set
            - Prints warning if file missing or invalid (no-op)
        """
        filepath = Path(filepath)

        if not filepath.exists():
            logger.warning(f"PPG sample not found, skipping: {filepath} (PPG {ppg_id}, sample {sample_id})")
            return

        try:
            # Load WAV file (soundfile returns data and sample_rate)
            data, sr = sf.read(str(filepath), dtype='float32')

            # Ensure mono with robust shape validation
            if data.ndim == 1:
                # Already mono
                pass
            elif data.ndim == 2:
                # Multichannel - take first channel
                data = data[:, 0]
            else:
                logger.warning(f"Unexpected audio shape {data.shape}, skipping: {filepath}")
                return

            # Validate non-empty
            if len(data) == 0:
                logger.warning(f"Empty audio file, skipping: {filepath}")
                return

            # Verify consistent sample rate across all files
            if self.sample_rate is None:
                self.sample_rate = sr
            elif self.sample_rate != sr:
                logger.warning(f"Sample rate mismatch ({sr}Hz vs {self.sample_rate}Hz), skipping: {filepath}")
                return

            # Store sample
            self.samples[ppg_id][sample_id] = data

        except Exception as e:
            logger.warning(f"Failed to load sample, skipping: {filepath} ({e})")

    def _load_loop(self, filepath, loop_id):
        """Load a single loop WAV file.

        Args:
            filepath (str): Path to WAV file
            loop_id (int): Loop ID (0-31)

        Side effects:
            - Stores audio data in self.loops[loop_id] if successful
            - Sets self.sample_rate if not yet set
            - Prints warning if file missing or invalid (no-op)
        """
        filepath = Path(filepath)

        if not filepath.exists():
            logger.warning(f"Loop not found, skipping: {filepath} (loop {loop_id})")
            return

        try:
            # Load WAV file
            data, sr = sf.read(str(filepath), dtype='float32')

            # Ensure mono
            if data.ndim == 1:
                pass
            elif data.ndim == 2:
                data = data[:, 0]
            else:
                logger.warning(f"Unexpected audio shape {data.shape}, skipping: {filepath}")
                return

            # Validate non-empty
            if len(data) == 0:
                logger.warning(f"Empty audio file, skipping: {filepath}")
                return

            # Verify consistent sample rate
            if self.sample_rate is None:
                self.sample_rate = sr
            elif self.sample_rate != sr:
                logger.warning(f"Sample rate mismatch ({sr}Hz vs {self.sample_rate}Hz), skipping: {filepath}")
                return

            # Store loop
            self.loops[loop_id] = data

        except Exception as e:
            logger.warning(f"Failed to load loop, skipping: {filepath} ({e})")

    def _load_acquire_sample(self, filepath):
        """Load the global acquire acknowledgement sample.

        Args:
            filepath (str): Path to WAV file

        Side effects:
            - Stores audio data in self.acquire_sample if successful
            - Sets self.sample_rate if not yet set
            - Prints warning if file missing or invalid (no-op)
        """
        filepath = Path(filepath)

        if not filepath.exists():
            logger.warning(f"Acquire sample not found, skipping: {filepath}")
            return

        try:
            # Load WAV file
            data, sr = sf.read(str(filepath), dtype='float32')

            # Ensure mono
            if data.ndim == 1:
                pass
            elif data.ndim == 2:
                data = data[:, 0]
            else:
                logger.warning(f"Unexpected audio shape {data.shape}, skipping: {filepath}")
                return

            # Validate non-empty
            if len(data) == 0:
                logger.warning(f"Empty audio file, skipping: {filepath}")
                return

            # Verify consistent sample rate
            if self.sample_rate is None:
                self.sample_rate = sr
            elif self.sample_rate != sr:
                logger.warning(f"Sample rate mismatch ({sr}Hz vs {self.sample_rate}Hz), skipping: {filepath}")
                return

            # Store acquire sample
            self.acquire_sample = data
            logger.info(f"Loaded acquire sample: {filepath}")

        except Exception as e:
            logger.warning(f"Failed to load acquire sample, skipping: {filepath} ({e})")

    def _load_drone_sample(self, drone_config, sample_id):
        """Load a single drone sample WAV file with base frequency.

        Args:
            drone_config (dict): Config with 'path' and 'base_freq_hz' keys
            sample_id (int): Drone sample ID

        Side effects:
            - Stores audio data and base frequency in self.drone_samples[sample_id] if successful
            - Sets self.sample_rate if not yet set
            - Prints warning if file missing or invalid (no-op)
        """
        filepath = Path(drone_config.get('path', ''))
        base_freq_hz = drone_config.get('base_freq_hz')

        if not filepath:
            logger.warning(f"Drone sample {sample_id} missing 'path', skipping")
            return

        if base_freq_hz is None:
            logger.warning(f"Drone sample {sample_id} missing 'base_freq_hz', skipping: {filepath}")
            return

        if not filepath.exists():
            logger.warning(f"Drone sample not found, skipping: {filepath} (sample {sample_id})")
            return

        try:
            # Load WAV file
            data, sr = sf.read(str(filepath), dtype='float32')

            # Ensure mono
            if data.ndim == 1:
                pass
            elif data.ndim == 2:
                data = data[:, 0]
            else:
                logger.warning(f"Unexpected audio shape {data.shape}, skipping: {filepath}")
                return

            # Validate non-empty
            if len(data) == 0:
                logger.warning(f"Empty audio file, skipping: {filepath}")
                return

            # Verify consistent sample rate
            if self.sample_rate is None:
                self.sample_rate = sr
            elif self.sample_rate != sr:
                logger.warning(f"Sample rate mismatch ({sr}Hz vs {self.sample_rate}Hz), skipping: {filepath}")
                return

            # Store drone sample with metadata
            self.drone_samples[sample_id] = {
                'audio': data,
                'base_freq_hz': float(base_freq_hz)
            }
            logger.info(f"Loaded drone sample {sample_id}: {filepath} (base freq: {base_freq_hz} Hz)")

        except Exception as e:
            logger.warning(f"Failed to load drone sample, skipping: {filepath} ({e})")

    def validate_timestamp(self, timestamp):
        """Validate beat timestamp age.

        Calculates timestamp age and determines if beat should be played or dropped.
        Per TRD: play if < 500ms old, drop if >= 500ms old.

        Args:
            timestamp (float): Unix time (seconds) of beat detection

        Returns:
            tuple: (is_valid, age_ms)
                - is_valid (bool): True if timestamp < 500ms old
                - age_ms (float): Age of timestamp in milliseconds
        """
        now = time.time()
        age_ms = (now - timestamp) * 1000.0

        is_valid = age_ms < self.TIMESTAMP_THRESHOLD_MS
        return is_valid, age_ms

    def validate_message(self, address, args):
        """Validate OSC message format and content.

        Checks address pattern, argument count/types, and timestamp age.

        Expected format:
            Address: /beat/{ppg_id}  where ppg_id is 0-7 (0-3: real, 4-7: virtual)
            Arguments: [timestamp, bpm, intensity]

        Validation steps:
            1. Address matches /beat/[0-7] pattern
            2. Exactly 3 arguments provided
            3. All arguments are floats (or int that can convert to float)
            4. Timestamp is non-negative

        Args:
            address (str): OSC message address (e.g., "/beat/0", "/beat/5")
            args (list): Message arguments

        Returns:
            tuple: (is_valid, ppg_id, timestamp, bpm, intensity, error_message)
                - is_valid (bool): True if message passes all validation
                - ppg_id (int): Channel ID 0-7 (None if address invalid)
                - timestamp (float): Beat timestamp (None if invalid)
                - bpm (float): BPM value (None if invalid)
                - intensity (float): Intensity value (None if invalid)
                - error_message (str): Human-readable error if invalid (None if valid)
        """
        # Validate address pattern: /beat/[0-7]
        is_valid, ppg_id, error_msg = osc.validate_beat_address(address)
        if not is_valid:
            return False, None, None, None, None, error_msg

        # Validate argument count (should be 3: timestamp, bpm, intensity)
        if len(args) != 3:
            return False, ppg_id, None, None, None, (
                f"Expected 3 arguments, got {len(args)} (PPG {ppg_id})"
            )

        # Extract and validate arguments
        try:
            # Timestamp comes as integer milliseconds (OSC float32 can't handle Unix seconds)
            timestamp_ms = float(args[0])
            timestamp = timestamp_ms / 1000.0  # Convert to seconds
            bpm = float(args[1])
            intensity = float(args[2])
        except (TypeError, ValueError) as e:
            return False, ppg_id, None, None, None, (
                f"Invalid argument types: {e} (PPG {ppg_id})"
            )

        # Timestamp should be non-negative
        if timestamp < 0:
            return False, ppg_id, timestamp, bpm, intensity, (
                f"Invalid timestamp: {timestamp} (PPG {ppg_id})"
            )

        return True, ppg_id, timestamp, bpm, intensity, None

    def handle_beat_message(self, ppg_id, timestamp, bpm, intensity):
        """Process a beat message and play corresponding audio.

        Called after validation. Checks timestamp age, pans mono → stereo,
        and queues audio to rtmixer for playback.

        Args:
            ppg_id (int): PPG channel ID (0-7: 0-3 real sensors, 4-7 virtual channels)
            timestamp (float): Unix time (seconds) of beat
            bpm (float): Heart rate in beats per minute
            intensity (float): Signal strength 0.0-1.0

        Side effects:
            - Increments appropriate statistics
            - Pans mono sample to stereo and queues to rtmixer if beat is valid and recent
            - Prints to console
        """
        self.stats.increment('total_messages')

        # Note: ppg_id is guaranteed to be in [0-7] by regex validation in validate_message()
        # No need for redundant range check here

        # Validate timestamp age
        is_valid, age_ms = self.validate_timestamp(timestamp)

        if not is_valid:
            self.stats.increment('dropped_messages')
            return

        # Valid beat: check mode and dispatch accordingly
        self.stats.increment('valid_messages')

        try:
            # Get routing config (thread-safe read)
            with self.state_lock:
                route_config = self.routing.get(ppg_id, {'mode': 'percussive', 'sample_id': 0})
                mode = route_config.get('mode', 'percussive')
                scaled_bpm = bpm * self.bpm_multiplier

            if mode == 'pitched_sample':
                # Drone mode: update drone frequency and volume
                sample_id = route_config.get('sample_id', 0)
                octave_shift = route_config.get('octave_shift', 3)
                pan = osc.PPG_PANS[ppg_id]

                # Clamp intensity to valid range [0.0, 1.0]
                intensity_clamped = max(0.0, min(1.0, intensity))

                # Check if drone is already active
                with self.drone_manager.lock:
                    drone_active = ppg_id in self.drone_manager.active_drones

                if drone_active:
                    # Update existing drone
                    self.drone_manager.update_drone(ppg_id, scaled_bpm, intensity_clamped, octave_shift)
                else:
                    # Start new drone
                    self.drone_manager.start_drone(ppg_id, scaled_bpm, sample_id, octave_shift, pan, intensity_clamped)

                self.stats.increment('played_messages')

            elif mode == 'additive':
                # Additive synthesis mode: generate waveform on-the-fly
                harmonics = route_config.get('harmonics', 4)
                rolloff = route_config.get('rolloff', 1.5)
                base_octave = route_config.get('octave_shift', 5)
                sample_id = route_config.get('sample_id', 0)

                # Map column (sample_id) to octave: column 0 = base-3, column 7 = base+4
                # This gives a 7-octave range centered around column 3
                octave_shift = base_octave + sample_id - 3
                pan = osc.PPG_PANS[ppg_id]

                # Clamp intensity to valid range [0.0, 1.0]
                intensity_clamped = max(0.0, min(1.0, intensity))

                # Check if drone is already active
                with self.drone_manager.lock:
                    drone_active = ppg_id in self.drone_manager.active_drones

                if drone_active:
                    # Update existing drone
                    self.drone_manager.update_drone(ppg_id, scaled_bpm, intensity_clamped, octave_shift)
                else:
                    # Start new additive drone
                    self.drone_manager.start_additive_drone(ppg_id, scaled_bpm, octave_shift, harmonics, rolloff, pan, intensity_clamped)

                self.stats.increment('played_messages')

            else:
                # Percussive mode: existing behavior
                sample_id = route_config.get('sample_id', 0)
                bank_id = ppg_id % 4
                mono_sample = self.samples.get(bank_id, {}).get(sample_id)

                if mono_sample is None:
                    logger.warning(f"No sample loaded for PPG {ppg_id}, bank {bank_id}, sample {sample_id} - skipping beat")
                    return

                # Apply effects if enabled (use scaled BPM)
                if self.effects_processor:
                    mono_sample = self.effects_processor.process(
                        mono_sample,
                        ppg_id=ppg_id,
                        bpm=scaled_bpm,
                        intensity=intensity
                    )

                pan = osc.PPG_PANS[ppg_id]

                # Pan to stereo
                stereo_sample = pan_mono_to_stereo(mono_sample, pan, self.enable_panning)

                # Apply intensity scaling if enabled
                if self.enable_intensity_scaling:
                    # Clamp intensity to valid range [0.0, 1.0]
                    intensity_clamped = max(0.0, min(1.0, intensity))
                    stereo_sample = stereo_sample * intensity_clamped

                # Queue to rtmixer for concurrent playback
                action = self.mixer.play_buffer(stereo_sample, channels=2)

                # Increment stats immediately after successful queueing (before voice tracking)
                # This ensures stats reflect reality even if voice limiting fails
                self.stats.increment('played_messages')

                # Track sample for voice limiting (NO lock held here - safe to call mixer methods)
                self.ppg_voice_manager.track_sample(ppg_id, action)

                # Format pan info based on whether panning is enabled
                if self.enable_panning:
                    pan_info = f"Pan: {pan:+.2f}"
                else:
                    pan_info = "Pan: CENTER (disabled)"

                # Format intensity info based on whether intensity scaling is enabled
                if self.enable_intensity_scaling:
                    intensity_info = f"Intensity: {intensity:.2f}"
                else:
                    intensity_info = "Intensity: DISABLED"

                logger.info(
                    f"BEAT PLAYED: PPG {ppg_id}, BPM: {bpm:.1f}, {pan_info}, {intensity_info}, "
                    f"Timestamp: {timestamp:.3f}s (age: {age_ms:.1f}ms)"
                )
        except Exception as e:
            logger.warning(f"Failed to play audio for PPG {ppg_id}: {e}")

    def handle_acquire_message(self, ppg_id, timestamp, bpm):
        """Process an acquire message and play corresponding audio.

        Called after validation. Plays the global acquire acknowledgement sample
        when predictor initially acquires rhythm (INITIALIZATION → LOCKED).
        Uses spatial panning to indicate which PPG acquired.

        Args:
            ppg_id (int): PPG sensor ID (0-3)
            timestamp (float): Unix time (seconds) of acquire event
            bpm (float): Heart rate in beats per minute at acquisition

        Side effects:
            - Increments appropriate statistics
            - Pans mono sample to stereo and queues to rtmixer
            - Prints to console
        """
        self.stats.increment('total_messages')

        # Validate timestamp age
        is_valid, age_ms = self.validate_timestamp(timestamp)

        if not is_valid:
            self.stats.increment('dropped_messages')
            return

        # Valid acquire: play global acquire acknowledgement sample
        self.stats.increment('valid_messages')

        try:
            # Check if acquire sample is loaded (thread-safe read)
            with self.state_lock:
                acquire_sample = self.acquire_sample

            if acquire_sample is None:
                logger.warning(f"No acquire sample loaded - skipping acquire for PPG {ppg_id}")
                return

            # Use global acquire sample (no routing table)
            mono_sample = acquire_sample
            pan = osc.PPG_PANS[ppg_id]

            # Pan to stereo (spatial position indicates which PPG acquired)
            stereo_sample = pan_mono_to_stereo(mono_sample, pan, self.enable_panning)

            # Queue to rtmixer for concurrent playback
            self.mixer.play_buffer(stereo_sample, channels=2)

            # Increment played_messages after successful playback
            self.stats.increment('played_messages')

            # Format pan info based on whether panning is enabled
            if self.enable_panning:
                pan_info = f"Pan: {pan:+.2f}"
            else:
                pan_info = "Pan: CENTER (disabled)"

            logger.info(
                f"ACQUIRE PLAYED: PPG {ppg_id}, BPM: {bpm:.1f}, {pan_info}, "
                f"Timestamp: {timestamp:.3f}s (age: {age_ms:.1f}ms)"
            )
        except Exception as e:
            logger.warning(f"Failed to play acquire audio for PPG {ppg_id}: {e}")

    def handle_release_message(self, ppg_id, timestamp):
        """Process a release message.

        Called after validation. Currently does nothing (silent release).
        Future enhancement could play a "lock lost" sound.

        Args:
            ppg_id (int): PPG sensor ID (0-3)
            timestamp (float): Unix time (seconds) of release event

        Side effects:
            - Increments statistics
            - Prints to console
        """
        self.stats.increment('total_messages')

        # Validate timestamp age
        is_valid, age_ms = self.validate_timestamp(timestamp)

        if not is_valid:
            self.stats.increment('dropped_messages')
            return

        # Valid release: currently silent (no audio playback)
        self.stats.increment('valid_messages')

        logger.info(
            f"RELEASE: PPG {ppg_id}, Timestamp: {timestamp:.3f}s (age: {age_ms:.1f}ms)"
        )

    def handle_osc_beat_message(self, address, *args):
        """Handle incoming beat OSC message.

        Called by OSC dispatcher when /beat/{0-3} message arrives.
        Validates message and processes through beat handler.

        Args:
            address (str): OSC address (e.g., "/beat/0")
            *args: Variable arguments from OSC message

        Side effects:
            - Validates message format and content
            - Calls handle_beat_message if validation passes
            - Prints warnings for invalid messages
        """
        # Validate message
        is_valid, ppg_id, timestamp, bpm, intensity, error_msg = self.validate_message(
            address, args
        )

        if not is_valid:
            # Still count as a message even if invalid (validation error)
            self.stats.increment('total_messages')
            self.stats.increment('dropped_messages')
            if error_msg:
                logger.warning(f"AudioEngine: {error_msg}")
            return

        # Process valid beat (handle_beat_message will increment total_messages)
        self.handle_beat_message(ppg_id, timestamp, bpm, intensity)

    def handle_osc_acquire_message(self, address, *args):
        """Handle incoming acquire OSC message.

        Called by OSC dispatcher when /acquire/{0-3} message arrives.
        Validates message and processes through acquire handler.

        Args:
            address (str): OSC address (e.g., "/acquire/0")
            *args: Variable arguments from OSC message

        Side effects:
            - Validates message format and content
            - Calls handle_acquire_message if validation passes
            - Prints warnings for invalid messages
        """
        # Validate message
        is_valid, ppg_id, timestamp, bpm, error_msg = self.validate_acquire_message(
            address, args
        )

        if not is_valid:
            # Still count as a message even if invalid (validation error)
            self.stats.increment('total_messages')
            self.stats.increment('dropped_messages')
            if error_msg:
                logger.warning(f"AudioEngine: {error_msg}")
            return

        # Process valid acquire (handle_acquire_message will increment total_messages)
        self.handle_acquire_message(ppg_id, timestamp, bpm)

    def handle_osc_release_message(self, address, *args):
        """Handle incoming release OSC message.

        Called by OSC dispatcher when /release/{0-3} message arrives.
        Validates message and processes through release handler.

        Args:
            address (str): OSC address (e.g., "/release/0")
            *args: Variable arguments from OSC message

        Side effects:
            - Validates message format and content
            - Calls handle_release_message if validation passes
            - Prints warnings for invalid messages
        """
        # Validate message
        is_valid, ppg_id, timestamp, error_msg = self.validate_release_message(
            address, args
        )

        if not is_valid:
            # Still count as a message even if invalid (validation error)
            self.stats.increment('total_messages')
            self.stats.increment('dropped_messages')
            if error_msg:
                logger.warning(f"AudioEngine: {error_msg}")
            return

        # Process valid release (handle_release_message will increment total_messages)
        self.handle_release_message(ppg_id, timestamp)

    def validate_acquire_message(self, address, args):
        """Validate acquire OSC message format and content.

        Checks address pattern, argument count/types, and timestamp validity.

        Expected format:
            Address: /acquire/{ppg_id}  where ppg_id is 0-3
            Arguments: [timestamp_ms, bpm]

        Validation steps:
            1. Address matches /acquire/[0-3] pattern
            2. Exactly 2 arguments provided
            3. All arguments are floats (or int that can convert to float)
            4. Timestamp is non-negative

        Args:
            address (str): OSC message address (e.g., "/acquire/0")
            args (list): Message arguments

        Returns:
            tuple: (is_valid, ppg_id, timestamp, bpm, error_message)
                - is_valid (bool): True if message passes all validation
                - ppg_id (int): Sensor ID 0-3 (None if address invalid)
                - timestamp (float): Acquire timestamp (None if invalid)
                - bpm (float): BPM value (None if invalid)
                - error_message (str): Human-readable error if invalid (None if valid)
        """
        # Validate address pattern: /acquire/[0-3]
        is_valid, ppg_id, error_msg = osc.validate_acquire_address(address)
        if not is_valid:
            return False, None, None, None, error_msg

        # Validate argument count (should be 2: timestamp, bpm)
        if len(args) != 2:
            return False, ppg_id, None, None, (
                f"Expected 2 arguments, got {len(args)} (PPG {ppg_id})"
            )

        # Extract and validate arguments
        try:
            timestamp_ms = float(args[0])
            timestamp = timestamp_ms / 1000.0  # Convert to seconds
            bpm = float(args[1])
        except (TypeError, ValueError) as e:
            return False, ppg_id, None, None, (
                f"Invalid argument types: {e} (PPG {ppg_id})"
            )

        # Timestamp should be non-negative
        if timestamp < 0:
            return False, ppg_id, timestamp, bpm, (
                f"Invalid timestamp: {timestamp} (PPG {ppg_id})"
            )

        return True, ppg_id, timestamp, bpm, None

    def validate_release_message(self, address, args):
        """Validate release OSC message format and content.

        Checks address pattern, argument count/types, and timestamp validity.

        Expected format:
            Address: /release/{ppg_id}  where ppg_id is 0-3
            Arguments: [timestamp_ms]

        Validation steps:
            1. Address matches /release/[0-3] pattern
            2. Exactly 1 argument provided
            3. Argument is float (or int that can convert to float)
            4. Timestamp is non-negative

        Args:
            address (str): OSC message address (e.g., "/release/0")
            args (list): Message arguments

        Returns:
            tuple: (is_valid, ppg_id, timestamp, error_message)
                - is_valid (bool): True if message passes all validation
                - ppg_id (int): Sensor ID 0-3 (None if address invalid)
                - timestamp (float): Release timestamp (None if invalid)
                - error_message (str): Human-readable error if invalid (None if valid)
        """
        # Validate address pattern: /release/[0-3]
        is_valid, ppg_id, error_msg = osc.validate_release_address(address)
        if not is_valid:
            return False, None, None, error_msg

        # Validate argument count (should be 1: timestamp)
        if len(args) != 1:
            return False, ppg_id, None, (
                f"Expected 1 argument, got {len(args)} (PPG {ppg_id})"
            )

        # Extract and validate argument
        try:
            timestamp_ms = float(args[0])
            timestamp = timestamp_ms / 1000.0  # Convert to seconds
        except (TypeError, ValueError) as e:
            return False, ppg_id, None, (
                f"Invalid argument type: {e} (PPG {ppg_id})"
            )

        # Timestamp should be non-negative
        if timestamp < 0:
            return False, ppg_id, timestamp, (
                f"Invalid timestamp: {timestamp} (PPG {ppg_id})"
            )

        return True, ppg_id, timestamp, None

    def handle_route_message(self, address, *args):
        """Handle /route/{ppg_id} message to update sample routing.

        Args:
            address: OSC address (e.g., "/route/0", "/route/5")
            *args: [sample_id] - sample ID to route to (0-7)

        Note:
            Uses modulo-4 bank mapping: channel N uses samples from bank (N % 4).
            For example, channel 5 routes to samples in bank 1.
        """
        logger.debug(f"handle_route_message called: address={address}, args={args}")
        # Parse PPG ID from address
        parts = address.split('/')
        if len(parts) != 3 or parts[1] != 'route':
            logger.warning(f"Invalid route address format: {address}")
            return

        try:
            ppg_id = int(parts[2])
        except (ValueError, IndexError):
            logger.warning(f"Invalid PPG ID in route address: {address}")
            return

        # Validate PPG ID range (0-7: 0-3 real sensors, 4-7 virtual channels)
        if not 0 <= ppg_id <= 7:
            logger.warning(f"PPG ID out of range [0, 7]: {ppg_id}")
            return

        # Parse sample ID from args
        if len(args) != 1:
            logger.warning(f"Expected 1 argument for /route, got {len(args)}")
            return

        try:
            sample_id = int(args[0])
        except (ValueError, TypeError):
            logger.warning(f"Invalid sample ID type: {args[0]}")
            return

        # Validate sample ID range
        if not 0 <= sample_id <= 7:
            logger.warning(f"Sample ID out of range [0, 7]: {sample_id}")
            return

        # Update routing table (thread-safe write)
        # Note: We update routing even if sample isn't loaded yet, since beat handler
        # will check for sample existence before playback
        bank_id = ppg_id % 4

        # Preserve mode and other config, just update sample_id
        with self.state_lock:
            if ppg_id in self.routing:
                self.routing[ppg_id]['sample_id'] = sample_id
            else:
                self.routing[ppg_id] = {'mode': 'percussive', 'sample_id': sample_id}

        # Warn if sample isn't loaded, but routing is still updated
        if bank_id not in self.samples or sample_id not in self.samples[bank_id]:
            logger.warning(f"ROUTING: PPG {ppg_id} (bank {bank_id}) → sample {sample_id} (sample not loaded)")
        else:
            logger.info(f"ROUTING: PPG {ppg_id} (bank {bank_id}) → sample {sample_id}")

    def handle_load_bank_message(self, address, *args):
        """Handle /load_bank message to reload a PPG's samples from a different bank.

        Args:
            address: OSC address ("/load_bank")
            *args: [ppg_id, bank_name] - PPG ID (0-3) and bank name to load
        """
        logger.debug(f"handle_load_bank_message called: address={address}, args={args}")
        if len(args) != 2:
            logger.warning(f"Expected 2 arguments for /load_bank, got {len(args)}")
            return

        try:
            ppg_id = int(args[0])
        except (ValueError, TypeError):
            logger.warning(f"Invalid PPG ID type: {args[0]}")
            return

        if not 0 <= ppg_id <= 3:
            logger.warning(f"PPG ID out of range [0, 3]: {ppg_id}")
            return

        bank_name = str(args[1])

        # Get banks for this PPG from config
        ppg_banks = self.config.get('ppg_samples', {}).get(ppg_id, {})

        if not isinstance(ppg_banks, dict):
            logger.warning(f"PPG {ppg_id} config is not multi-bank format")
            return

        if bank_name not in ppg_banks:
            available = ', '.join(ppg_banks.keys())
            logger.warning(f"Bank '{bank_name}' not found for PPG {ppg_id}. Available: {available}")
            return

        # Clear existing samples and load new bank (thread-safe)
        with self.state_lock:
            self.samples[ppg_id] = {}

            # Load new bank
            sample_paths = ppg_banks[bank_name]
            for sample_id, filepath in enumerate(sample_paths):
                if sample_id >= 8:
                    break

                self._load_sample(filepath, ppg_id, sample_id)

            loaded_count = len(self.samples[ppg_id])

        logger.info(f"LOAD_BANK: PPG {ppg_id} → bank '{bank_name}' ({loaded_count}/8 samples loaded)")

    def handle_loop_start_message(self, address, *args):
        """Handle /loop/start message to start a loop.

        Args:
            address: OSC address ("/loop/start")
            *args: [loop_id] - loop ID to start (0-31)
        """
        logger.debug(f"handle_loop_start_message called: address={address}, args={args}")
        if len(args) != 1:
            logger.warning(f"Expected 1 argument for /loop/start, got {len(args)}")
            return

        try:
            loop_id = int(args[0])
        except (ValueError, TypeError):
            logger.warning(f"Invalid loop ID type: {args[0]}")
            return

        try:
            # Call loop manager start WITHOUT holding state_lock
            # (LoopManager.start internally calls mixer.play_buffer which must not be called with locks held)
            ejected = self.loop_manager.start(loop_id)
            # Print after operation completes
            if ejected is not None:
                logger.info(f"LOOP START: Loop {loop_id} started, ejected loop {ejected}")
            else:
                logger.info(f"LOOP START: Loop {loop_id} started")
        except ValueError as e:
            logger.warning(f"Failed to start loop: {e}")

    def handle_loop_stop_message(self, address, *args):
        """Handle /loop/stop message to stop a loop.

        Args:
            address: OSC address ("/loop/stop")
            *args: [loop_id] - loop ID to stop (0-31)
        """
        logger.debug(f"handle_loop_stop_message called: address={address}, args={args}")
        if len(args) != 1:
            logger.warning(f"Expected 1 argument for /loop/stop, got {len(args)}")
            return

        try:
            loop_id = int(args[0])
        except (ValueError, TypeError):
            logger.warning(f"Invalid loop ID type: {args[0]}")
            return

        try:
            # Call loop manager stop WITHOUT holding state_lock
            # (LoopManager.stop internally calls mixer.cancel which must not be called with locks held)
            self.loop_manager.stop(loop_id)
            logger.info(f"LOOP STOP: Loop {loop_id} stopped")
        except ValueError as e:
            logger.warning(f"Failed to stop loop: {e}")

    def handle_effect_toggle_message(self, address, *args):
        """Handle /ppg/effect/toggle message to toggle an effect for a PPG.

        Args:
            address: OSC address ("/ppg/effect/toggle")
            *args: [ppg_id, effect_name] - PPG ID (0-7) and effect name (string)
        """
        logger.debug(f"handle_effect_toggle_message called: address={address}, args={args}")
        if len(args) != 2:
            logger.warning(f"Expected 2 arguments for /ppg/effect/toggle, got {len(args)}")
            return

        try:
            ppg_id = int(args[0])
            effect_name = str(args[1])
        except (ValueError, TypeError):
            logger.warning(f"Invalid argument types for /ppg/effect/toggle: {args}")
            return

        # Validate PPG ID (0-7 for physical and virtual PPGs)
        if not 0 <= ppg_id <= 7:
            logger.warning(f"PPG ID must be 0-7, got {ppg_id}")
            return

        # Check if effects processor exists
        if not self.effects_processor:
            logger.warning(f"Effects processor not available, cannot toggle effect")
            return

        # Toggle effect (thread-safe)
        try:
            with self.state_lock:
                self.effects_processor.toggle_effect(ppg_id, effect_name)
            logger.info(f"EFFECT TOGGLE: PPG {ppg_id}, effect '{effect_name}' toggled")
        except Exception as e:
            logger.warning(f"Failed to toggle effect for PPG {ppg_id}: {e}")

    def handle_effect_clear_message(self, address, *args):
        """Handle /ppg/effect/clear message to clear all effects for a PPG.

        Args:
            address: OSC address ("/ppg/effect/clear")
            *args: [ppg_id] - PPG ID (0-7)
        """
        logger.debug(f"handle_effect_clear_message called: address={address}, args={args}")
        if len(args) != 1:
            logger.warning(f"Expected 1 argument for /ppg/effect/clear, got {len(args)}")
            return

        try:
            ppg_id = int(args[0])
        except (ValueError, TypeError):
            logger.warning(f"Invalid PPG ID type: {args[0]}")
            return

        # Validate PPG ID (0-7 for physical and virtual PPGs)
        if not 0 <= ppg_id <= 7:
            logger.warning(f"PPG ID must be 0-7, got {ppg_id}")
            return

        # Check if effects processor exists
        if not self.effects_processor:
            logger.warning(f"Effects processor not available, cannot clear effects")
            return

        # Clear all effects (thread-safe)
        try:
            with self.state_lock:
                self.effects_processor.clear_effects(ppg_id)
            logger.info(f"EFFECT CLEAR: PPG {ppg_id}, all effects cleared")
        except Exception as e:
            logger.warning(f"Failed to clear effects for PPG {ppg_id}: {e}")

    def handle_bpm_multiplier_message(self, address, *args):
        """Handle /bpm/multiplier message to set tempo scaling.

        Args:
            address: OSC address ("/bpm/multiplier")
            *args: [multiplier] - BPM multiplier (validation: 0.1-10.0, UI provides: 0.25-3.0)
        """
        logger.debug(f"handle_bpm_multiplier_message called: address={address}, args={args}")
        if len(args) != 1:
            logger.warning(f"Expected 1 argument for /bpm/multiplier, got {len(args)}")
            return

        try:
            multiplier = float(args[0])
        except (ValueError, TypeError):
            logger.warning(f"Invalid multiplier type: {args[0]}")
            return

        # Validate multiplier range
        if not 0.1 <= multiplier <= 10.0:
            logger.warning(f"BPM multiplier {multiplier} out of range (0.1-10.0)")
            return

        # Update multiplier (thread-safe)
        with self.state_lock:
            old_multiplier = self.bpm_multiplier
            self.bpm_multiplier = multiplier

        logger.info(f"BPM MULTIPLIER: {old_multiplier}x → {self.bpm_multiplier}x")

    def cleanup(self):
        """Close rtmixer and effects gracefully.

        Called when the audio engine is shutting down.
        Stops the mixer and cleans up effects.
        """
        # Stop all active loops before cleanup (thread-safe copy)
        logger.info("Stopping all active loops...")
        with self.loop_manager.lock:
            active_loop_ids = list(self.loop_manager.active_loops.keys())
        for loop_id in active_loop_ids:
            try:
                self.loop_manager.stop(loop_id)
            except Exception as e:
                logger.warning(f"Failed to stop loop {loop_id}: {e}")

        # Cleanup effects
        if self.effects_processor:
            try:
                self.effects_processor.cleanup()
            except Exception as e:
                logger.warning(f"Failed to cleanup effects: {e}")

        # Stop mixer
        try:
            self.mixer.stop()
        except Exception as e:
            logger.warning(f"Failed to stop mixer: {e}")

    def run(self):
        """Start dual OSC servers for beat and control messages.

        Runs two OSC servers concurrently:
        - Beat port (osc.PORT_BEATS): /beat/{0-3}, /acquire/{0-3}, /release/{0-3} from processor
        - Control port (osc.PORT_CONTROL): /route/{ppg_id} and /loop/* messages from sequencer

        Blocks indefinitely until Ctrl+C. Handles shutdown gracefully.

        Side effects:
            - Prints startup information to console
            - Prints beat/acquire/release/routing/loop messages during operation
            - Handles KeyboardInterrupt
            - Prints final statistics on shutdown
            - Stops mixer on shutdown
        """
        # Create beat dispatcher (osc.PORT_BEATS)
        beat_disp = dispatcher.Dispatcher()
        beat_disp.map("/beat/*", self.handle_osc_beat_message)
        beat_disp.map("/acquire/*", self.handle_osc_acquire_message)
        beat_disp.map("/release/*", self.handle_osc_release_message)
        beat_server = osc.ReusePortBlockingOSCUDPServer(("0.0.0.0", self.port), beat_disp)

        # Create control dispatcher (osc.PORT_CONTROL)
        control_disp = dispatcher.Dispatcher()
        control_disp.map("/route/*", self.handle_route_message)
        control_disp.map("/load_bank", self.handle_load_bank_message)
        control_disp.map("/loop/start", self.handle_loop_start_message)
        control_disp.map("/loop/stop", self.handle_loop_stop_message)
        control_disp.map("/ppg/effect/toggle", self.handle_effect_toggle_message)
        control_disp.map("/ppg/effect/clear", self.handle_effect_clear_message)
        control_disp.map("/bpm/multiplier", self.handle_bpm_multiplier_message)
        logger.debug(f"Creating control server on port {self.control_port}")
        control_server = osc.ReusePortBlockingOSCUDPServer(("0.0.0.0", self.control_port), control_disp)
        logger.debug(f"Control server created successfully, bound to {control_server.server_address}")

        logger.info(f"Audio Engine (rtmixer) with dual-port OSC")
        logger.info(f"  Beat port: {self.port} (listening for /beat/{{0-3}}, /acquire/{{0-3}}, /release/{{0-3}})")
        logger.info(f"  Control port: {self.control_port} (listening for /route/* and /loop/*)")
        logger.info(f"Sample rate: {self.sample_rate}Hz")
        logger.info(f"Mixer: stereo output, true concurrent playback")

        # Display panning status clearly
        panning_status = "ENABLED" if self.enable_panning else "DISABLED (center only)"
        logger.info(f"Stereo panning: {panning_status}")
        if self.enable_panning:
            logger.info(f"  PPG 0={osc.PPG_PANS[0]:+.2f}, PPG 1={osc.PPG_PANS[1]:+.2f}, "
                  f"PPG 2={osc.PPG_PANS[2]:+.2f}, PPG 3={osc.PPG_PANS[3]:+.2f}")

        # Display intensity scaling status
        intensity_status = "ENABLED" if self.enable_intensity_scaling else "DISABLED (original amplitude)"
        logger.info(f"Intensity scaling: {intensity_status}")

        logger.info(f"Timestamp validation: drop if >= 500ms old")
        logger.info(f"Waiting for messages... (Ctrl+C to stop)")
        logger.info("")

        # Start control server in background thread
        control_thread = threading.Thread(target=control_server.serve_forever, daemon=True)
        control_thread.start()
        logger.debug(f"Control server thread started (daemon={control_thread.daemon})")

        # Run beat server in main thread (blocks here)
        try:
            beat_server.serve_forever()
        except KeyboardInterrupt:
            logger.info("\n\nShutting down...")
        except Exception as e:
            logger.error(f"\nServer crashed: {e}")
        finally:
            beat_server.shutdown()
            control_server.shutdown()
            # Wait for control thread to finish
            control_thread.join(timeout=2.0)
            if control_thread.is_alive():
                logger.warning("Control server thread did not terminate cleanly")
            self.cleanup()
            self.stats.print_stats("AUDIO ENGINE STATISTICS")


def main():
    """Main entry point with command-line argument parsing.

    Parses arguments for port and sounds directory configuration,
    creates AudioEngine instance, and handles runtime errors.

    Command-line arguments:
        --port N            UDP port to listen for beat input (default: 8001)
        --sounds-dir PATH   Directory containing WAV files (default: sounds)

    Example usage:
        python3 -m amor.audio
        python3 -m amor.audio --port 8001 --sounds-dir ./sounds
        python3 -m amor.audio --port 9001 --sounds-dir /path/to/sounds

    Validation:
        - Port must be in range 1-65535
        - Config file must exist and be valid YAML with required structure
        - Exits with error code 1 if validation fails or port is already in use
    """
    parser = argparse.ArgumentParser(description="Audio Engine - Beat audio playback (rtmixer)")
    parser.add_argument(
        "--port",
        type=int,
        default=osc.PORT_BEATS,
        help=f"UDP port to listen for beat input (default: {osc.PORT_BEATS})",
    )
    parser.add_argument(
        "--control-port",
        type=int,
        default=osc.PORT_CONTROL,
        help=f"UDP port to listen for control messages (default: {osc.PORT_CONTROL})",
    )
    parser.add_argument(
        "--sounds-dir",
        type=str,
        default="sounds",
        help="Directory containing WAV files (default: sounds)",
    )
    parser.add_argument(
        "--enable-panning",
        action="store_true",
        help="Enable stereo panning (default: disabled for development, all signals centered)",
    )
    parser.add_argument(
        "--enable-intensity-scaling",
        action="store_true",
        help="Enable intensity-based volume scaling (default: disabled for development)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="amor/config/samples.yaml",
        help="Path to YAML config file (default: amor/config/samples.yaml)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Audio device substring to match (e.g., 'pulse', 'MobilePre'). First matching device will be used. Use 'python3 -c \"import sounddevice; print(sounddevice.query_devices())\"' to list devices.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("AMOR_LOG_LEVEL", "INFO"),
        help="Logging verbosity (default: INFO)",
    )

    args = parser.parse_args()

    # Set log level
    logger.setLevel(args.log_level)

    # Validate ports
    try:
        osc.validate_port(args.port)
    except ValueError as e:
        logger.error(f"{e}")
        sys.exit(1)

    try:
        osc.validate_port(args.control_port)
    except ValueError as e:
        logger.error(f"Control port validation failed: {e}")
        sys.exit(1)

    # Validate ports are different
    if args.port == args.control_port:
        logger.error(f"Beat port and control port cannot be the same ({args.port})")
        sys.exit(1)

    # Find audio device if specified
    device = None
    if args.device:
        device = find_audio_device(args.device)

    # Create and run engine
    try:
        engine = AudioEngine(
            port=args.port,
            control_port=args.control_port,
            sounds_dir=args.sounds_dir,
            enable_panning=args.enable_panning,
            enable_intensity_scaling=args.enable_intensity_scaling,
            config_path=args.config,
            device=device
        )
        logger.info(f"Audio engine started successfully on port {args.port}")
        engine.run()
    except FileNotFoundError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {args.port} already in use")
        else:
            logger.error(f"{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
