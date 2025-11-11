#!/usr/bin/env python3
"""
Audio Engine - Amor Phase 2 Audio Playback (rtmixer version)

Receives beat events from sensor processor, plays overlapping sound samples with stereo panning.

ARCHITECTURE:
- OSC server listening on port 8001 for beat input (/beat/{0-3} messages)
- Loads 4 mono WAV samples (one per PPG sensor) at startup
- Validates beat timestamps: plays if <500ms old, drops if older
- Uses rtmixer for true concurrent playback with low-latency mixing
- Per-sensor stereo panning for spatial audio separation
- Statistics tracking for beat events

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

Configurable via PPG_PANS constant.

USAGE:
    # Start with default settings (port 8001, sounds/ directory)
    python3 audio/audio_engine.py

    # Custom port and sounds directory
    python3 audio/audio_engine.py --port 8001 --sounds-dir /path/to/sounds

INPUT OSC MESSAGES:

Input (port 8001):
    Address: /beat/{ppg_id}  where ppg_id is 0-3
    Arguments: [timestamp, bpm, intensity]
    - Timestamp: float, Unix time (seconds) when beat detected
    - BPM: float, heart rate in beats per minute
    - Intensity: float, signal strength 0.0-1.0 (reserved for future use)

BEAT HANDLING:

1. Timestamp validation:
   - Calculate age: age_ms = (time.time() - timestamp) * 1000
   - Play if age < 500ms
   - Drop if age >= 500ms

2. Audio playback:
   - Load mono sound samples at startup (WAV format: 44.1kHz or 48kHz, 16-bit, mono)
   - Pan mono → stereo based on PPG_PANS constant
   - Use rtmixer.play_buffer() for non-blocking concurrent playback
   - Multiple beats from same or different PPGs overlap properly

3. Statistics:
   - Total messages received
   - Valid messages (timestamp < 500ms old)
   - Dropped messages (timestamp >= 500ms old)
   - Successfully played messages

BEAT MESSAGE VALIDATION:

Validation steps:
1. Address matches /beat/[0-3] pattern
2. Exactly 3 arguments (timestamp, bpm, intensity)
3. PPG ID (from address) in range 0-3
4. Timestamp is non-negative
5. Timestamp is < 500ms old (age validation)

Edge cases:
- Missing WAV files: raises FileNotFoundError at startup
- Invalid ppg_id: message rejected
- Stale timestamp: message dropped (not played)
- Future timestamp: accepted and played (per protocol contract)

DEBUGGING TIPS:

1. Enable verbose output:
   - Check console for "BEAT PLAYED:" messages
   - Watch "DROPPED:" messages for stale timestamps

2. Check statistics on shutdown (Ctrl+C):
   - Total messages, valid, dropped, played
   - Ratio should show how many timestamps are stale

3. Audio verification:
   - Use test_inject_beats.py to send test beats
   - Listen for 4 spatially separated sounds across stereo field

Reference: docs/audio/rtmixer-architecture.md
"""

import argparse
import re
import sys
import time
from pathlib import Path
from pythonosc import dispatcher
from pythonosc import osc_server
import soundfile as sf
import numpy as np
import rtmixer


# Stereo panning positions for each PPG sensor
# -1.0 = hard left, 0.0 = center, 1.0 = hard right
PPG_PANS = {
    0: -1.0,   # Person 1: Hard left
    1: -0.33,  # Person 2: Center-left
    2: 0.33,   # Person 3: Center-right
    3: 1.0     # Person 4: Hard right
}


def pan_mono_to_stereo(mono_data, pan):
    """
    Convert mono PCM to stereo with constant-power panning.

    Uses constant-power pan law to maintain equal perceived loudness
    across the stereo field. Pan position controls the balance between
    left and right channels using trigonometric weighting.

    Args:
        mono_data: 1D numpy array (mono samples), dtype float32
        pan: -1.0 (hard left) to 1.0 (hard right), 0.0 = center

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
    angle = (pan + 1.0) * np.pi / 4.0
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
        total_messages (int): Count of all received messages
        valid_messages (int): Count of valid messages (timestamp < 500ms old)
        dropped_messages (int): Count of dropped messages (timestamp >= 500ms old)
        played_messages (int): Count of successfully played messages
    """

    # Timestamp age threshold in milliseconds
    TIMESTAMP_THRESHOLD_MS = 500

    def __init__(self, port=8001, sounds_dir="sounds"):
        """Initialize audio engine and load WAV samples.

        Args:
            port (int): OSC port to listen on (default 8001)
            sounds_dir (str): Path to directory containing ppg_0.wav through ppg_3.wav

        Raises:
            FileNotFoundError: If any required WAV file is missing
            ValueError: If WAV files have mismatched sample rates
            RuntimeError: If rtmixer initialization fails
        """
        self.port = port
        self.sounds_dir = sounds_dir

        # Load WAV samples (mono)
        self.samples = {}
        self.sample_rate = None

        for ppg_id in range(4):
            filepath = Path(sounds_dir) / f"ppg_{ppg_id}.wav"

            if not filepath.exists():
                raise FileNotFoundError(f"Missing WAV file: {filepath}")

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
                    raise ValueError(
                        f"Unexpected audio data shape: {data.shape} for {filepath}. "
                        f"Expected 1D (mono) or 2D (multichannel)."
                    )

                # Validate non-empty
                if len(data) == 0:
                    raise ValueError(f"Empty audio file: {filepath}")

                self.samples[ppg_id] = data

                # Verify consistent sample rate across all files
                if self.sample_rate is None:
                    self.sample_rate = sr
                elif self.sample_rate != sr:
                    raise ValueError(
                        f"Sample rate mismatch: ppg_{ppg_id} has {sr}Hz, "
                        f"expected {self.sample_rate}Hz"
                    )
            except Exception as e:
                raise RuntimeError(f"Failed to load {filepath}: {e}")

        # Initialize rtmixer for stereo output
        # Note: rtmixer (via PortAudio) will handle sample rate conversion if
        # the system audio hardware uses a different rate than the WAV files
        try:
            self.mixer = rtmixer.Mixer(
                channels=2,
                samplerate=int(self.sample_rate),
                blocksize=512  # ~11.6ms at 44.1kHz or ~10.7ms at 48kHz, balances latency vs CPU
            )
            self.mixer.start()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize rtmixer: {e}")

        # Precompile regex for address pattern
        self.address_pattern = re.compile(r"^/beat/([0-3])$")

        # Statistics
        self.total_messages = 0
        self.valid_messages = 0
        self.dropped_messages = 0
        self.played_messages = 0

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
            Address: /beat/{ppg_id}  where ppg_id is 0-3
            Arguments: [timestamp, bpm, intensity]

        Validation steps:
            1. Address matches /beat/[0-3] pattern
            2. Exactly 3 arguments provided
            3. All arguments are floats (or int that can convert to float)
            4. Timestamp is non-negative
            5. Timestamp is < 500ms old

        Args:
            address (str): OSC message address (e.g., "/beat/0")
            args (list): Message arguments

        Returns:
            tuple: (is_valid, ppg_id, timestamp, bpm, intensity, error_message)
                - is_valid (bool): True if message passes all validation
                - ppg_id (int): Sensor ID 0-3 (None if address invalid)
                - timestamp (float): Beat timestamp (None if invalid)
                - bpm (float): BPM value (None if invalid)
                - intensity (float): Intensity value (None if invalid)
                - error_message (str): Human-readable error if invalid (None if valid)
        """
        # Validate address pattern: /beat/[0-3]
        match = self.address_pattern.match(address)
        if not match:
            return False, None, None, None, None, f"Invalid address pattern: {address}"

        ppg_id = int(match.group(1))

        # Validate argument count (should be 3: timestamp, bpm, intensity)
        if len(args) != 3:
            return False, ppg_id, None, None, None, (
                f"Expected 3 arguments, got {len(args)} (PPG {ppg_id})"
            )

        # Extract and validate arguments
        try:
            timestamp = float(args[0])
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
            ppg_id (int): PPG sensor ID (0-3)
            timestamp (float): Unix time (seconds) of beat
            bpm (float): Heart rate in beats per minute
            intensity (float): Signal strength 0.0-1.0

        Side effects:
            - Increments appropriate statistics
            - Pans mono sample to stereo and queues to rtmixer if beat is valid and recent
            - Prints to console
        """
        self.total_messages += 1

        # Note: ppg_id is guaranteed to be in [0-3] by regex validation in validate_message()
        # No need for redundant range check here

        # Validate timestamp age
        is_valid, age_ms = self.validate_timestamp(timestamp)

        if not is_valid:
            self.dropped_messages += 1
            return

        # Valid beat: pan mono → stereo and play
        self.valid_messages += 1

        try:
            # Get mono sample and pan position
            mono_sample = self.samples[ppg_id]
            pan = PPG_PANS[ppg_id]

            # Pan to stereo
            stereo_sample = pan_mono_to_stereo(mono_sample, pan)

            # Queue to rtmixer for concurrent playback
            self.mixer.play_buffer(stereo_sample, channels=2)

            # Only increment played_messages after successful playback
            self.played_messages += 1

            print(
                f"BEAT PLAYED: PPG {ppg_id}, BPM: {bpm:.1f}, Pan: {pan:+.2f}, "
                f"Timestamp: {timestamp:.3f}s (age: {age_ms:.1f}ms)"
            )
        except Exception as e:
            print(f"WARNING: Failed to play audio for PPG {ppg_id}: {e}")

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
            self.total_messages += 1
            self.dropped_messages += 1
            if error_msg:
                print(f"WARNING: AudioEngine: {error_msg}")
            return

        # Process valid beat (handle_beat_message will increment total_messages)
        self.handle_beat_message(ppg_id, timestamp, bpm, intensity)

    def cleanup(self):
        """Close rtmixer gracefully.

        Called when the audio engine is shutting down.
        Stops the mixer.
        """
        try:
            self.mixer.stop()
        except Exception as e:
            print(f"WARNING: Failed to stop mixer: {e}")

    def run(self):
        """Start the OSC server and process beat messages.

        Blocks indefinitely, listening for /beat/{0-3} messages on the port.
        Handles Ctrl+C gracefully with clean shutdown and statistics.

        Message flow:
            1. Listen on port (default 8001) for OSC messages
            2. Route /beat/* messages to handle_osc_beat_message
            3. Call dispatcher for message handling
            4. On Ctrl+C, shutdown gracefully and print statistics

        Side effects:
            - Prints startup information to console
            - Prints beat playback messages during operation
            - Handles KeyboardInterrupt
            - Prints final statistics on shutdown
            - Stops mixer on shutdown
        """
        # Create dispatcher and bind handler
        disp = dispatcher.Dispatcher()
        disp.map("/beat/*", self.handle_osc_beat_message)

        # Create OSC server
        server = osc_server.BlockingOSCUDPServer(("0.0.0.0", self.port), disp)

        print(f"Audio Engine (rtmixer) listening on port {self.port}")
        print(f"Sounds directory: {self.sounds_dir}")
        print(f"Sample rate: {self.sample_rate}Hz")
        print(f"Mixer: stereo output, true concurrent playback")
        print(f"Stereo panning: PPG 0={PPG_PANS[0]:+.2f}, PPG 1={PPG_PANS[1]:+.2f}, "
              f"PPG 2={PPG_PANS[2]:+.2f}, PPG 3={PPG_PANS[3]:+.2f}")
        print(f"Expecting /beat/{{0-3}} messages with [timestamp, bpm, intensity]")
        print(f"Timestamp validation: drop if >= 500ms old")
        print(f"Waiting for messages... (Ctrl+C to stop)")
        print()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        except Exception as e:
            print(f"\nERROR: Server crashed: {e}", file=sys.stderr)
        finally:
            server.shutdown()
            self.cleanup()
            self._print_statistics()

    def _print_statistics(self):
        """Print final statistics on shutdown.

        Shows message counts: total received, valid passed, dropped rejected, played.
        Useful for evaluating timestamp freshness and playback performance.

        Output format:
            Total messages: N (all OSC messages received)
            Valid: N (messages with timestamp < 500ms old)
            Dropped: N (messages with stale timestamp or invalid)
            Played: N (successfully played beats)

        Interpretation:
            - dropped_messages shows how many beats were stale
            - played_messages should equal valid_messages
            - Ratio played:total indicates timestamp freshness
        """
        print("\n" + "=" * 60)
        print("AUDIO ENGINE STATISTICS")
        print("=" * 60)
        print(f"Total messages: {self.total_messages}")
        print(f"Valid: {self.valid_messages}")
        print(f"Dropped: {self.dropped_messages}")
        print(f"Played: {self.played_messages}")
        print("=" * 60)


def main():
    """Main entry point with command-line argument parsing.

    Parses arguments for port and sounds directory configuration,
    creates AudioEngine instance, and handles runtime errors.

    Command-line arguments:
        --port N            UDP port to listen for beat input (default: 8001)
        --sounds-dir PATH   Directory containing WAV files (default: sounds)

    Example usage:
        python3 audio/audio_engine.py
        python3 audio/audio_engine.py --port 8001 --sounds-dir ./sounds
        python3 audio/audio_engine.py --port 9001 --sounds-dir /path/to/sounds

    Validation:
        - Port must be in range 1-65535
        - Sounds directory must exist and contain ppg_0.wav through ppg_3.wav
        - Exits with error code 1 if validation fails or port is already in use
    """
    parser = argparse.ArgumentParser(description="Audio Engine - Beat audio playback (rtmixer)")
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="UDP port to listen for beat input (default: 8001)",
    )
    parser.add_argument(
        "--sounds-dir",
        type=str,
        default="sounds",
        help="Directory containing WAV files (default: sounds)",
    )

    args = parser.parse_args()

    # Validate port
    if args.port < 1 or args.port > 65535:
        print(f"ERROR: Port must be in range 1-65535", file=sys.stderr)
        sys.exit(1)

    # Validate sounds directory
    sounds_path = Path(args.sounds_dir)
    if not sounds_path.exists():
        print(f"ERROR: Sounds directory not found: {args.sounds_dir}", file=sys.stderr)
        sys.exit(1)

    # Create and run engine
    try:
        engine = AudioEngine(port=args.port, sounds_dir=args.sounds_dir)
        engine.run()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Port {args.port} already in use", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
