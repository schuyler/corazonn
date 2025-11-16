#!/usr/bin/env python3
"""
MIDI Engine - External FluidSynth synthesis via MIDI output

Receives beat and control events from sensor processor/sequencer, outputs MIDI
notes to external FluidSynth daemon for synthesis.

ARCHITECTURE:
- OSC server listening on port 8001 for beat input (/beat/{0-3} messages)
- OSC server listening on port 8003 for control messages (/synth/note/{ppg_id})
- Uses SO_REUSEPORT socket option to allow port sharing across processes
- Outputs MIDI to external FluidSynth daemon via ALSA MIDI
- Runs independently of amor.audio (can run simultaneously)

MIDI OUTPUT:
- Sends note_on with velocity from intensity
- Schedules note_off after short delay (50ms default)
- FluidSynth's ADSR envelope controls actual sound duration
- Separate MIDI channel per PPG (0-3)

INSTRUMENT SELECTION:
- Per-PPG instrument banks configured in samples.yaml
- Sends program_change before each note
- Uses same ppg_instruments config as embedded synth

USAGE:
    # Start with default settings
    python3 -m amor.midi

    # Custom ports and config
    python3 -m amor.midi --port 8001 --control-port 8003 --config amor/config/samples.yaml

INPUT OSC MESSAGES:

Input (port 8001):
    Address: /beat/{ppg_id}  where ppg_id is 0-3
    Arguments: [timestamp_ms, bpm, intensity]
    - Timestamp: int, Unix time (milliseconds) when beat detected
    - BPM: float, heart rate in beats per minute
    - Intensity: float, signal strength 0.0-1.0 (maps to MIDI velocity)

Input (port 8003):
    Address: /synth/note/{ppg_id}  where ppg_id is 0-7
    Arguments: [instrument_idx, scale_degree]
    - instrument_idx: int, index into ppg_instruments list (0-7)
    - scale_degree: int, scale degree in Natural Major (0-7)

MESSAGE HANDLING:
1. Timestamp validation (same as audio.py):
   - Calculate age: age_ms = (time.time() - timestamp) * 1000
   - Play if age < 500ms
   - Drop if age >= 500ms

2. MIDI output:
   - Send program_change to select instrument
   - Send note_on with calculated pitch and velocity
   - Schedule note_off after configurable delay
   - FluidSynth daemon mixes and outputs to audio device

3. Statistics:
   - Total messages received
   - Valid messages (timestamp < 500ms old)
   - Dropped messages (timestamp >= 500ms old)
   - Notes sent

EXTERNAL FLUIDSYNTH SETUP:
    # Start FluidSynth daemon with ALSA MIDI and audio output
    fluidsynth -a alsa -m alsa_seq -o audio.alsa.device=hw:1,0 soundfont.sf2

    # List available MIDI ports
    python3 -c "import mido; print(mido.get_output_names())"

Reference: docs/audio/midi-architecture.md (to be created)
"""

import argparse
import os
import sys
import threading
import time
from pathlib import Path
from pythonosc import dispatcher
import yaml
import mido

from amor import osc
from amor.log import get_logger

logger = get_logger("midi")

# Natural Major scale intervals (semitones from root)
# Column 0-6: C D E F G A B (root, major 2nd, major 3rd, perfect 4th, perfect 5th, major 6th, major 7th)
# Column 7: Octave (root + 12 semitones)
NATURAL_MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11, 12]


class MIDIEngine:
    """OSC to MIDI bridge for external FluidSynth daemon.

    Receives beat and control events via OSC, outputs MIDI notes to
    external synthesizer daemon.

    Attributes:
        port (int): OSC port for beat input (default: osc.PORT_BEATS)
        control_port (int): OSC port for control messages (default: osc.PORT_CONTROL)
        midi_port_name (str): ALSA MIDI port name (e.g., "FluidSynth:0")
        midi_out (mido.ports.BaseOutput): MIDI output port
        config (dict): Configuration from samples.yaml
        synth_routing (dict): PPG ID → (instrument_idx, scale_degree) mapping
        midi_channels (dict): PPG ID → MIDI channel mapping
        note_off_delay (float): Note off delay in seconds
        state_lock (threading.Lock): Protects shared state
        stats (osc.MessageStatistics): Message counters
    """

    # Timestamp age threshold in milliseconds
    TIMESTAMP_THRESHOLD_MS = 500

    def __init__(self, port=osc.PORT_BEATS, control_port=osc.PORT_CONTROL,
                 config_path="amor/config/samples.yaml", midi_port_name=None):
        """Initialize MIDI engine and connect to external FluidSynth.

        Args:
            port (int): OSC port for beat input (default: osc.PORT_BEATS)
            control_port (int): OSC port for control messages (default: osc.PORT_CONTROL)
            config_path (str): Path to samples.yaml configuration
            midi_port_name (str): ALSA MIDI port name (default: from config or "FluidSynth:0")

        Raises:
            FileNotFoundError: If config file not found
            RuntimeError: If MIDI port cannot be opened
        """
        self.port = port
        self.control_port = control_port
        self.config_path = config_path

        # Load configuration
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

        # Extract MIDI configuration
        midi_config = self.config.get('midi', {})
        self.midi_port_name = midi_port_name or midi_config.get('port_name', 'FluidSynth:0')
        self.note_off_delay = midi_config.get('note_off_delay_ms', 50) / 1000.0  # Convert to seconds

        # MIDI channel mapping (PPG → MIDI channel)
        channel_config = midi_config.get('channels', {})
        self.midi_channels = {
            0: channel_config.get(0, 0),
            1: channel_config.get(1, 1),
            2: channel_config.get(2, 2),
            3: channel_config.get(3, 3),
        }

        # Load PPG instrument configuration (reuse synthesis section)
        synth_config = self.config.get('synthesis', {})
        ppg_instruments_config = synth_config.get('ppg_instruments', {})
        self.ppg_instruments = {}
        for ppg_id in range(4):
            instrument = ppg_instruments_config.get(ppg_id, {})
            self.ppg_instruments[ppg_id] = instrument if instrument else {
                'midi_bank': 0,
                'root_note': 60,
                'instruments': [0]
            }

        # Open MIDI output port
        try:
            available_ports = mido.get_output_names()
            logger.info(f"Available MIDI ports: {available_ports}")

            if self.midi_port_name not in available_ports:
                raise RuntimeError(
                    f"MIDI port '{self.midi_port_name}' not found. "
                    f"Available ports: {available_ports}. "
                    f"Make sure FluidSynth is running with: "
                    f"fluidsynth -a alsa -m alsa_seq soundfont.sf2"
                )

            self.midi_out = mido.open_output(self.midi_port_name)
            logger.info(f"MIDI output opened: {self.midi_port_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to open MIDI port '{self.midi_port_name}': {e}")

        # Synth routing: stores (instrument_idx, scale_degree) for each PPG
        # Updated via /synth/note/{ppg_id} messages from sequencer
        self.synth_routing = {}  # ppg_id → (instrument_idx, scale_degree)

        # Thread safety
        self.state_lock = threading.Lock()

        # Statistics
        self.stats = osc.MessageStatistics()

        # Track pending timers for cleanup
        self.pending_timers = []
        self.pending_timers_lock = threading.Lock()

        logger.info(f"MIDI Engine initialized:")
        logger.info(f"  MIDI port: {self.midi_port_name}")
        logger.info(f"  Note off delay: {self.note_off_delay * 1000:.0f}ms")
        logger.info(f"  PPG instruments:")
        for ppg_id in range(4):
            ppg_config = self.ppg_instruments[ppg_id]
            if 'instruments' in ppg_config:
                instruments = ppg_config['instruments']
                midi_bank = ppg_config.get('midi_bank', 0)
                root_note = ppg_config.get('root_note', 60)
                channel = self.midi_channels[ppg_id]
                logger.info(
                    f"    PPG {ppg_id}: Bank {midi_bank}, Root {root_note}, "
                    f"Instruments {instruments}, Channel {channel}"
                )

    def validate_timestamp(self, timestamp):
        """Validate beat timestamp age.

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

    def send_note(self, ppg_id: int, instrument_idx: int, note: int, intensity: float):
        """Send MIDI note with envelope-controlled duration.

        Sends note_on immediately, schedules note_off after short delay.
        The soundfont's ADSR envelope determines actual sound duration.

        Args:
            ppg_id: PPG channel ID (0-3, determines MIDI channel)
            instrument_idx: Index into ppg_instruments[ppg_id]['instruments'] list
            note: MIDI note number (0-127)
            intensity: Signal strength 0.0-1.0 (maps to velocity)

        Side effects:
            - Sends MIDI bank_select + program_change
            - Sends MIDI note_on
            - Schedules note_off after configured delay
        """
        # Get PPG instrument config
        ppg_config = self.ppg_instruments[ppg_id]

        # Extract instrument and bank (handle both old and new config formats)
        if 'instruments' in ppg_config:
            # New format: list of instruments
            instruments_list = ppg_config['instruments']
            if instrument_idx >= len(instruments_list):
                logger.warning(
                    f"instrument_idx {instrument_idx} out of range for PPG {ppg_id}, "
                    f"max {len(instruments_list) - 1}"
                )
                return
            program = instruments_list[instrument_idx]
            midi_bank = ppg_config.get('midi_bank', 0)
        else:
            # Old format: single program
            program = ppg_config.get('program', 0)
            midi_bank = ppg_config.get('bank', 0)

        # Get MIDI channel for this PPG
        channel = self.midi_channels[ppg_id]

        # Convert intensity to MIDI velocity
        velocity = int(intensity * 127)
        velocity = max(1, min(127, velocity))  # MIDI velocity range 1-127 (0 = note off)

        # Send bank select (CC #0)
        self.midi_out.send(mido.Message('control_change',
                                        control=0,
                                        value=midi_bank,
                                        channel=channel))

        # Send program change
        self.midi_out.send(mido.Message('program_change',
                                        program=program,
                                        channel=channel))

        # Send note on
        self.midi_out.send(mido.Message('note_on',
                                        note=note,
                                        velocity=velocity,
                                        channel=channel))

        logger.debug(
            f"MIDI NOTE ON: PPG {ppg_id}, channel {channel}, "
            f"program {program}, note {note}, velocity {velocity}"
        )

        # Schedule note off
        def send_note_off():
            self.midi_out.send(mido.Message('note_off',
                                           note=note,
                                           channel=channel))
            logger.debug(f"MIDI NOTE OFF: PPG {ppg_id}, channel {channel}, note {note}")

            # Remove from pending timers
            with self.pending_timers_lock:
                if timer in self.pending_timers:
                    self.pending_timers.remove(timer)

        timer = threading.Timer(self.note_off_delay, send_note_off)
        timer.daemon = True

        # Track timer for cleanup
        with self.pending_timers_lock:
            self.pending_timers.append(timer)

        timer.start()

    def handle_beat_message(self, ppg_id, timestamp, bpm, intensity):
        """Process a beat message and send MIDI note.

        Called after validation. Checks timestamp age, calculates MIDI note,
        and sends to external FluidSynth.

        Args:
            ppg_id (int): PPG channel ID (0-7: 0-3 real sensors, 4-7 virtual channels)
            timestamp (float): Unix time (seconds) of beat
            bpm (float): Heart rate in beats per minute
            intensity (float): Signal strength 0.0-1.0

        Side effects:
            - Increments appropriate statistics
            - Sends MIDI messages if beat is valid and recent
        """
        self.stats.increment('total_messages')

        # Validate timestamp age
        is_valid, age_ms = self.validate_timestamp(timestamp)

        if not is_valid:
            self.stats.increment('dropped_messages')
            logger.debug(f"Dropped stale beat: PPG {ppg_id}, age {age_ms:.1f}ms")
            return

        self.stats.increment('valid_messages')

        # Get synth routing (thread-safe read)
        with self.state_lock:
            routing = self.synth_routing.get(ppg_id)

        if routing is None:
            logger.debug(f"No synth routing set for PPG {ppg_id} - skipping beat")
            return

        instrument_idx, scale_degree = routing

        # Map virtual PPGs (4-7) to physical PPG banks (0-3) for instrument selection
        physical_ppg_id = ppg_id % 4

        # Get root note from config
        ppg_config = self.ppg_instruments[physical_ppg_id]
        root_note = ppg_config.get('root_note', 60)  # Default to middle C

        # Validate scale_degree range
        if not isinstance(scale_degree, int) or scale_degree < 0 or scale_degree > 7:
            logger.error(
                f"Invalid scale_degree {scale_degree} in synth_routing for PPG {ppg_id} "
                f"- skipping beat"
            )
            return

        # Calculate MIDI note from root + scale degree
        scale_offset = NATURAL_MAJOR_SCALE[scale_degree]
        midi_note = root_note + scale_offset

        # Clamp to MIDI range
        midi_note = max(0, min(127, midi_note))

        try:
            # Send MIDI note
            self.send_note(
                ppg_id=physical_ppg_id,
                instrument_idx=instrument_idx,
                note=midi_note,
                intensity=intensity
            )

            # Increment stats
            self.stats.increment('played_messages')

            logger.info(
                f"MIDI SENT: PPG {ppg_id}, note {midi_note}, "
                f"velocity {int(intensity * 127)}, age {age_ms:.1f}ms"
            )

        except Exception as e:
            logger.warning(f"Failed to send MIDI note for PPG {ppg_id}: {e}")

    def handle_synth_note_message(self, address, *args):
        """Handle /synth/note/{ppg_id} message to store synth routing.

        Stores instrument index and scale degree for the specified PPG.
        Used to determine which note to play on the next beat.

        Args:
            address: OSC address ("/synth/note/{ppg_id}")
            *args: [instrument_idx, scale_degree]
        """
        logger.debug(f"handle_synth_note_message: address={address}, args={args}")

        # Parse PPG ID from address
        parts = address.split('/')
        if len(parts) != 4 or parts[1] != 'synth' or parts[2] != 'note':
            logger.warning(f"Invalid /synth/note address format: {address}")
            return

        try:
            ppg_id = int(parts[3])
        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid PPG ID in address {address}: {e}")
            return

        # Validate arguments
        if len(args) != 2:
            logger.warning(f"Expected 2 arguments for /synth/note, got {len(args)}")
            return

        try:
            instrument_idx = int(args[0])
            scale_degree = int(args[1])
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid instrument_idx or scale_degree: {args} ({e})")
            return

        # Validate values
        if instrument_idx < 0 or instrument_idx > 7:
            logger.warning(f"instrument_idx must be 0-7, got {instrument_idx}")
            return

        if scale_degree < 0 or scale_degree > 7:
            logger.warning(f"scale_degree must be 0-7, got {scale_degree}")
            return

        # Store routing (thread-safe)
        with self.state_lock:
            self.synth_routing[ppg_id] = (instrument_idx, scale_degree)

        logger.info(
            f"SYNTH ROUTING: PPG {ppg_id} → instrument {instrument_idx}, "
            f"scale degree {scale_degree}"
        )

    def handle_osc_beat_message(self, address, *args):
        """Handle incoming beat OSC message.

        Called by OSC dispatcher when /beat/{0-7} message arrives.
        Validates message and processes through beat handler.

        Args:
            address (str): OSC address (e.g., "/beat/0")
            *args: Variable arguments from OSC message
        """
        # Validate address pattern: /beat/[0-7]
        is_valid, ppg_id, error_msg = osc.validate_beat_address(address)
        if not is_valid:
            self.stats.increment('total_messages')
            self.stats.increment('dropped_messages')
            logger.warning(f"MIDIEngine: {error_msg}")
            return

        # Validate argument count (should be 3: timestamp, bpm, intensity)
        if len(args) != 3:
            self.stats.increment('total_messages')
            self.stats.increment('dropped_messages')
            logger.warning(
                f"Expected 3 arguments, got {len(args)} (PPG {ppg_id})"
            )
            return

        # Extract and validate arguments
        try:
            timestamp_ms = float(args[0])
            timestamp = timestamp_ms / 1000.0  # Convert to seconds
            bpm = float(args[1])
            intensity = float(args[2])
        except (TypeError, ValueError) as e:
            self.stats.increment('total_messages')
            self.stats.increment('dropped_messages')
            logger.warning(f"Invalid argument types: {e} (PPG {ppg_id})")
            return

        # Timestamp should be non-negative
        if timestamp < 0:
            self.stats.increment('total_messages')
            self.stats.increment('dropped_messages')
            logger.warning(f"Invalid timestamp: {timestamp} (PPG {ppg_id})")
            return

        # Process valid beat
        self.handle_beat_message(ppg_id, timestamp, bpm, intensity)

    def cleanup(self):
        """Close MIDI output and clean up resources.

        Called on shutdown to prevent resource leaks.
        """
        try:
            # Cancel pending timers
            with self.pending_timers_lock:
                for timer in self.pending_timers:
                    timer.cancel()
                self.pending_timers.clear()

            # Send all notes off on all channels
            if hasattr(self, 'midi_out') and self.midi_out:
                for channel in range(4):
                    # CC #123 = All Notes Off
                    self.midi_out.send(mido.Message('control_change',
                                                    control=123,
                                                    value=0,
                                                    channel=channel))
                self.midi_out.close()
                logger.info("MIDI output closed")
        except Exception as e:
            logger.warning(f"Failed to cleanup MIDI engine: {e}")

    def run(self):
        """Start dual OSC servers for beat and control messages.

        Runs two OSC servers concurrently:
        - Beat port (osc.PORT_BEATS): /beat/{0-7} from processor
        - Control port (osc.PORT_CONTROL): /synth/note/{ppg_id} from sequencer

        Blocks indefinitely until Ctrl+C. Handles shutdown gracefully.
        """
        # Create beat dispatcher (osc.PORT_BEATS)
        beat_disp = dispatcher.Dispatcher()
        beat_disp.map("/beat/*", self.handle_osc_beat_message)
        beat_server = osc.ReusePortBlockingOSCUDPServer(("0.0.0.0", self.port), beat_disp)

        # Create control dispatcher (osc.PORT_CONTROL)
        control_disp = dispatcher.Dispatcher()
        control_disp.map("/synth/note/*", self.handle_synth_note_message)
        control_server = osc.ReusePortBlockingOSCUDPServer(
            ("0.0.0.0", self.control_port), control_disp
        )

        logger.info(f"MIDI Engine with dual-port OSC")
        logger.info(f"  Beat port: {self.port} (listening for /beat/{{0-7}})")
        logger.info(f"  Control port: {self.control_port} (listening for /synth/note/*)")
        logger.info(f"  MIDI output: {self.midi_port_name}")
        logger.info(f"Timestamp validation: drop if >= 500ms old")
        logger.info(f"Waiting for messages... (Ctrl+C to stop)")
        logger.info("")

        # Start control server in background thread
        control_thread = threading.Thread(target=control_server.serve_forever, daemon=True)
        control_thread.start()

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
            self.stats.print_stats("MIDI ENGINE STATISTICS")


def main():
    """Main entry point with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="MIDI Engine - External FluidSynth synthesis via MIDI"
    )
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
        "--config",
        type=str,
        default="amor/config/samples.yaml",
        help="Path to YAML config file (default: amor/config/samples.yaml)",
    )
    parser.add_argument(
        "--midi-port",
        type=str,
        default=None,
        help="ALSA MIDI port name (default: from config or 'FluidSynth:0')",
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
        osc.validate_port(args.control_port)
    except ValueError as e:
        logger.error(f"{e}")
        sys.exit(1)

    # Validate ports are different
    if args.port == args.control_port:
        logger.error(f"Beat port and control port cannot be the same ({args.port})")
        sys.exit(1)

    # Create and run engine
    try:
        engine = MIDIEngine(
            port=args.port,
            control_port=args.control_port,
            config_path=args.config,
            midi_port_name=args.midi_port
        )
        logger.info(f"MIDI engine started successfully")
        engine.run()
    except FileNotFoundError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(
                f"Port already in use. This is expected if running alongside amor.audio. "
                f"Both processes use SO_REUSEPORT to share ports."
            )
        else:
            logger.error(f"{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
