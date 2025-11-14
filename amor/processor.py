#!/usr/bin/env python3
"""
Sensor Processor - Amor Phase 1 Beat Detection

Receives raw PPG (Photoplethysmography) samples from ESP32 units, detects heartbeats,
and sends beat events to audio and lighting subsystems via OSC.

ARCHITECTURE:
- OSC server listening on port 8000 for PPG input (/ppg/{0-7} messages)
  - Uses SO_REUSEPORT socket option to allow port sharing across processes
- Eight independent PPGSensor instances (0-3: real ESP32 units, 4-7: virtual channels)
- Each sensor runs a state machine: WARMUP → ACTIVE → PAUSED (with recovery)
- Threshold-based beat detection with upward-crossing algorithm
- Broadcasts beat messages to port 8001 (all listeners receive via SO_REUSEPORT)

USAGE:
    # Start processor with default ports
    python3 -m amor.processor

    # Custom ports
    python3 -m amor.processor --input-port 8000 --beats-port 8001

QUICK START (Testing):
    Terminal 1: python3 -m amor.processor
    Terminal 2: python3 testing/ppg_test_sink.py --port 8001  # Receiver (SO_REUSEPORT)
    Terminal 3: python3 testing/ppg_test_sink.py --port 8001  # Another receiver (SO_REUSEPORT)
    Terminal 4: # Send test PPG data via OSC to port 8000

INPUT/OUTPUT OSC MESSAGES:

Input (port 8000):
    Address: /ppg/{ppg_id}  where ppg_id is 0-7 (0-3: real sensors, 4-7: virtual channels)
    Arguments: [sample0, sample1, sample2, sample3, sample4, timestamp_ms]
    - Samples: 5 int32 values, each 0-4095 (12-bit ADC from ESP32)
    - Timestamp: int32, milliseconds on ESP32 (used for gap detection)
    - Samples represent 100ms of data at 50Hz (5 samples * 20ms apart)

Output (broadcast to port 8001):
    Address: /beat/{ppg_id}  where ppg_id is 0-7
    Arguments: [timestamp_ms, bpm, intensity]
    - Timestamp_ms: int, Unix time (milliseconds) when beat detected
    - BPM: float, heart rate from phase-based predictor model
    - Intensity: float, confidence level (0.0-1.0) from predictor model
    - All listeners with SO_REUSEPORT receive the message

    Address: /acquire/{ppg_id}  where ppg_id is 0-7
    Arguments: [timestamp_ms, bpm]
    - Timestamp_ms: int, Unix time (milliseconds) when rhythm acquired
    - BPM: float, heart rate at acquisition (INITIALIZATION → LOCKED only)
    - Sent once per initial rhythm acquisition (not on coasting recovery)
    - All listeners with SO_REUSEPORT receive the message

    Address: /release/{ppg_id}  where ppg_id is 0-7
    Arguments: [timestamp_ms]
    - Timestamp_ms: int, Unix time (milliseconds) when rhythm released
    - Sent when predictor loses confidence (LOCKED → COASTING)
    - All listeners with SO_REUSEPORT receive the message

BEAT DETECTION ALGORITHM:

Algorithm parameters are defined as class constants in PPGSensor for easy tuning.

1. Signal processing:
   - Maintains rolling buffer (PPGSensor.BUFFER_SIZE samples, 6s at 50Hz)
   - Monitors recent samples (PPGSensor.THRESHOLD_WINDOW) for threshold calculation
   - MAD-based threshold: median(samples) + PPGSensor.MAD_THRESHOLD_K * MAD(samples)
   - MAD (Median Absolute Deviation) is robust to outliers (50% breakdown point)

2. Detection logic:
   - Upward crossing: previous_sample < threshold AND current_sample >= threshold
   - Detects transitions where signal crosses adaptive threshold upward
   - Debouncing: minimum PPGSensor.IBI_MIN_MS between consecutive beats

3. IBI validation (Inter-Beat Interval):
   - Stores last PPGSensor.IBI_HISTORY_SIZE IBIs in milliseconds
   - Minimum validation: IBIs < IBI_MIN_MS rejected (prevents double-detection)
   - No maximum validation: allows missed beats, median BPM provides outlier robustness
   - Calculates BPM from median IBI: 60000 / median_ibi

4. First beat handling:
   - First beat only records timestamp, doesn't send message (no IBI yet)
   - Second and subsequent beats send output messages

STATE MACHINE:

WARMUP (initial state):
  - Accumulates samples (PPGSensor.WARMUP_SAMPLES at 50Hz)
  - No beat detection during warmup
  - Transitions to ACTIVE once sufficient data accumulated

ACTIVE (normal operation):
  - Performs beat detection with MAD-based adaptive threshold
  - Monitors signal quality using MAD (Median Absolute Deviation)
  - Transitions to PAUSED if MAD < PPGSensor.MAD_MIN_QUALITY (signal too flat/noisy)

PAUSED (noise recovery):
  - Suspends beat detection
  - Waits for valid signal: MAD >= PPGSensor.MAD_MIN_QUALITY
  - Measures stable data (PPGSensor.RECOVERY_TIME_S) before resuming
  - Transitions back to ACTIVE after recovery timer expires

Out-of-order/gap handling:
  - Detects timestamps that go backwards (drops sample, warns)
  - Detects message gaps > PPGSensor.MESSAGE_GAP_THRESHOLD_S (resets sensor to WARMUP)
  - Prevents stale beat detection from corrupted data streams

DEBUGGING TIPS:

1. Enable verbose output: processor prints all warnings and beat detections
   - Check for "WARNING: Out-of-order sample dropped" or "Message gap detected"
   - Watch "BEAT:" messages to verify detection is working

2. State transitions visible in processor output:
   - Check console for state changes (WARMUP → ACTIVE → PAUSED → ACTIVE)
   - Each sensor transitions independently

3. Beat accuracy:
   - Detected BPM should match known signal within ±10%
   - Use test_sensor_processor.py for verification with known signals

4. Performance:
   - Statistics printed on shutdown (Ctrl+C)
   - Track total_messages, valid_messages, beat_messages
   - Healthy operation: invalid_messages should be < 1%

Reference: Groucho's architectural proposal
"""

import argparse
import os
import sys
import time
from pythonosc import dispatcher
from pythonosc.udp_client import SimpleUDPClient

from amor import osc
from amor.detector import ThresholdDetector, ThresholdCrossing
from amor.predictor import HeartbeatPredictor
from amor.log import get_logger

logger = get_logger(__name__)


class PPGSensor:
    """Per-sensor coordinator integrating detection and prediction.

    Manages a single PPG sensor by coordinating threshold detection (ThresholdDetector)
    and rhythm prediction (HeartbeatPredictor). Each of the 4 sensors runs independently.

    Architecture (Phase 2):
        - ThresholdDetector: Handles state machine, signal quality, crossing detection
        - HeartbeatPredictor: Phase-based rhythm model, confidence tracking, beat emission
        - PPGSensor: Coordinates detector → predictor pipeline, manages OSC output

    Flow:
        Detector finds crossings → Predictor records observations → Predictor emits beats

    Attributes:
        ppg_id (int): Sensor ID (0-3)
        detector (ThresholdDetector): Threshold crossing detector
        predictor (HeartbeatPredictor): Phase-based beat predictor
        last_detector_state (str): Previous detector state for transition detection
    """

    def __init__(self, ppg_id, beats_port, verbose=False):
        self.ppg_id = ppg_id

        # Threshold detector (signal quality and crossing detection)
        self.detector = ThresholdDetector(ppg_id, verbose=verbose)

        # Heartbeat predictor (autonomous rhythm model with beat emission thread)
        self.predictor = HeartbeatPredictor(ppg_id, beats_port=beats_port, verbose=verbose)

        # Start autonomous beat emission thread
        self.predictor.start()

        # State tracking for detector transitions
        self.last_detector_state = self.detector.get_state()

        # State tracking for predictor mode transitions
        self.last_predictor_mode = self.predictor.get_mode()

    def add_sample(self, value, timestamp_ms):
        """Process a single PPG sample through detector → predictor pipeline.

        Coordinates threshold detection and rhythm prediction:
        1. Checks for detector resets (ESP32 reboot, message gaps)
        2. Monitors detector state transitions (ACTIVE → PAUSED triggers coasting)
        3. Monitors predictor mode transitions:
           - INITIALIZATION → LOCKED triggers acquire event
           - LOCKED → COASTING triggers release event
        4. Processes sample through detector to detect crossings
        5. Routes crossing observations to predictor
        6. Updates predictor state (50Hz) - beat emission handled autonomously by thread

        Args:
            value (int): PPG ADC sample (0-4095 from ESP32)
            timestamp_ms (int): Sample timestamp in milliseconds (ESP32 time)

        Returns:
            dict or None: Event if acquire/release emitted, None otherwise
                Acquire format: {'type': 'acquire', 'timestamp': float, 'bpm': float}
                Release format: {'type': 'release', 'timestamp': float}
                - timestamp: Unix time (seconds) when event occurred
                - bpm: Detected heart rate in beats per minute

                Note: Beat events are emitted autonomously by predictor's background thread,
                not returned by this method.

        Architecture:
            Detector finds crossings → Predictor observes crossings
            Predictor emits beats autonomously via background thread (not returned here)
            Predictor mode transitions → Acquire/Release events (returned here)
        """
        timestamp_s = timestamp_ms / 1000.0

        # Check if detector was reset (ESP32 reboot or message gap)
        # Immediately coast predictor to prevent ghost beats during WARMUP period
        if self.detector.was_reset():
            self.predictor.enter_coasting()
            self.detector.clear_reset_flag()

        # Process sample through detector
        observation = self.detector.process_sample(value, timestamp_ms)

        # Check for detector state transitions
        current_detector_state = self.detector.get_state()
        if current_detector_state != self.last_detector_state:
            # Handle ACTIVE → PAUSED transition (signal quality degraded)
            if self.last_detector_state == "active" and current_detector_state == "paused":
                # Notify predictor to enter coasting mode
                self.predictor.enter_coasting()

            self.last_detector_state = current_detector_state

        # Check for predictor mode transitions
        current_predictor_mode = self.predictor.get_mode()
        rhythm_event = None
        if current_predictor_mode != self.last_predictor_mode:
            # Detect INITIALIZATION → LOCKED (acquire)
            if (self.last_predictor_mode == "initialization" and
                current_predictor_mode == "locked"):
                # Create acquire event
                # Defensive check: IBI estimate should always be set during lock transition
                if self.predictor.ibi_estimate_ms is None or self.predictor.ibi_estimate_ms <= 0:
                    logger.warning(f"PPG {self.ppg_id} acquire event with invalid IBI estimate: {self.predictor.ibi_estimate_ms}")
                else:
                    rhythm_event = {
                        'type': 'acquire',
                        'timestamp': timestamp_s,
                        'bpm': 60000.0 / self.predictor.ibi_estimate_ms
                    }
            # Detect LOCKED → COASTING (release - confidence lost)
            elif (self.last_predictor_mode == "locked" and
                  current_predictor_mode == "coasting"):
                # Create release event
                rhythm_event = {
                    'type': 'release',
                    'timestamp': timestamp_s
                }

            self.last_predictor_mode = current_predictor_mode

        # If crossing detected, route to predictor
        if observation is not None:
            self.predictor.observe_crossing(timestamp_s)

        # Update predictor state (runs at 50Hz regardless of observations)
        # Note: Beats are now emitted autonomously by predictor's background thread
        self.predictor.update(timestamp_s)

        # Return rhythm event (acquire/release) if it occurred
        # Beat emission is handled autonomously by predictor, not returned here
        return rhythm_event


class SensorProcessor:
    """OSC server for processing PPG sensors and routing beat detection output.

    Manages 8 independent PPGSensor instances and routes their beat detections to
    audio and lighting subsystems. Validates input messages, tracks statistics,
    and handles clean shutdown.

    Architecture:
        - OSC server on input_port (default 8000) listening for /ppg/{0-7} messages
        - Eight PPGSensor instances for parallel, independent beat detection
          (0-3: real ESP32 sensors, 4-7: virtual channels from sampler)
        - UDP clients for output to audio_port and lighting_port (both get same messages)
        - Input validation: address pattern, argument count/types, ADC range, timestamps

    Message flow:
        /ppg/N (port 8000) -> validate -> PPGSensor.add_sample -> detect beat
        -> _send_beat_message -> /beat/N (port 8001 broadcast)

    Attributes:
        input_port (int): UDP port for PPG input (default: 8000)
        beats_port (int): UDP port for beat broadcast output (default: 8001)
        sensors (dict): 8 PPGSensor instances indexed 0-7
        stats (MessageStatistics): Message counters
    """

    def __init__(self, input_port=osc.PORT_PPG, beats_port=osc.PORT_BEATS, verbose=False):
        self.input_port = input_port
        self.beats_port = beats_port
        self.verbose = verbose

        # Create broadcast output client (255.255.255.255 allows multiple SO_REUSEPORT receivers)
        self.beats_client = osc.BroadcastUDPClient("255.255.255.255", beats_port)

        # Create 8 PPGSensor instances (0-3: real sensors, 4-7: virtual channels)
        # Pass beats_port so each predictor can emit beats autonomously
        self.sensors = {i: PPGSensor(i, beats_port=beats_port, verbose=verbose) for i in range(8)}

        # Statistics
        self.stats = osc.MessageStatistics()

    def validate_message(self, address, args):
        """Validate OSC message format and content.

        Checks address pattern, argument count/types, ADC range, and timestamp validity.

        Expected format:
            Address: /ppg/{ppg_id}  where ppg_id is 0-7 (0-3: real sensors, 4-7: virtual channels)
            Arguments: [sample0, sample1, sample2, sample3, sample4, timestamp_ms]

        Validation steps:
            1. Address matches /ppg/[0-7] pattern
            2. Exactly 6 arguments provided
            3. All arguments are integers
            4. All samples in range 0-4095 (12-bit ADC)
            5. Timestamp is non-negative

        Args:
            address (str): OSC message address (e.g., "/ppg/0")
            args (list): Message arguments

        Returns:
            tuple: (is_valid, ppg_id, samples, timestamp_ms, error_message)
                - is_valid (bool): True if message passes all validation
                - ppg_id (int): Sensor ID 0-3 (None if address invalid)
                - samples (list): 5 sample values (None if invalid)
                - timestamp_ms (int): Timestamp in milliseconds (None if invalid)
                - error_message (str): Human-readable error if invalid (None if valid)
        """
        # Validate address pattern: /ppg/[0-3]
        is_valid, ppg_id, error_msg = osc.validate_ppg_address(address)
        if not is_valid:
            return False, None, None, None, error_msg

        # Validate argument count (should be 6: 5 samples + timestamp)
        if len(args) != 6:
            return False, ppg_id, None, None, f"Expected 6 arguments, got {len(args)} (PPG {ppg_id})"

        # Validate all arguments are integers
        for i, arg in enumerate(args):
            if not isinstance(arg, int):
                return False, ppg_id, None, None, f"Argument {i} is not integer: {type(arg).__name__} (PPG {ppg_id})"

        samples = args[0:5]
        timestamp_ms = args[5]

        # Validate ADC range (0-4095 for 12-bit)
        for i, sample in enumerate(samples):
            if sample < osc.ADC_MIN or sample > osc.ADC_MAX:
                return False, ppg_id, None, None, f"Sample {i} out of range: {sample} (PPG {ppg_id})"

        # Timestamp should be positive
        if timestamp_ms < 0:
            return False, ppg_id, None, None, f"Invalid timestamp: {timestamp_ms} (PPG {ppg_id})"

        return True, ppg_id, samples, timestamp_ms, None

    def handle_ppg_message(self, address, *args):
        """Handle incoming PPG OSC message.

        Called by OSC dispatcher when /ppg/{0-3} message arrives.
        Validates message, extracts samples, and processes through sensor state machine.

        Each PPG message contains 5 samples at 20ms intervals (100ms total).
        Samples are processed individually through the PPGSensor.add_sample() method,
        with synthetic timestamps accounting for the inter-sample timing.

        Args:
            address (str): OSC address (e.g., "/ppg/0")
            *args: Variable arguments from OSC message

        Side effects:
            - Increments total_messages counter
            - Increments valid_messages or invalid_messages
            - Prints warnings for invalid messages
            - Calls _send_beat_message if beat detected
        """
        self.stats.increment('total_messages')

        # Validate message
        is_valid, ppg_id, samples, timestamp_ms, error_msg = self.validate_message(address, args)

        if not is_valid:
            self.stats.increment('invalid_messages')
            logger.warning(f"Processor: {error_msg}")
            return

        self.stats.increment('valid_messages')

        # Process each sample through the sensor's state machine
        # Each sample arrives 20ms apart (50Hz = 1 sample per 20ms)
        for i, sample in enumerate(samples):
            # Calculate individual timestamp for each sample in the bundle
            sample_timestamp_ms = timestamp_ms + (i * 20)
            event = self.sensors[ppg_id].add_sample(sample, sample_timestamp_ms)

            # Handle rhythm events (acquire/release)
            # Note: Beat events are now emitted autonomously by predictor threads
            if event is not None:
                event_type = event.get('type')
                if event_type == 'acquire':
                    self._send_acquire_message(ppg_id, event)
                elif event_type == 'release':
                    self._send_release_message(ppg_id, event)
                # Beat events no longer returned by add_sample() - handled by predictor thread

    def _send_beat_message(self, ppg_id, beat_message):
        """Broadcast beat detection message to all listeners.

        Broadcasts message once to PORT_BEATS. All listeners (audio, lighting, viewer)
        with SO_REUSEPORT receive the same message.

        Args:
            ppg_id (int): Sensor ID (0-3)
            beat_message (dict): Beat data
                {'timestamp': float, 'bpm': float, 'intensity': float}

        Message format:
            Address: /beat/{ppg_id}
            Arguments: [timestamp_ms, bpm, intensity]
            - timestamp_ms: Unix time (int, milliseconds) to avoid float32 precision issues
            - bpm: Heart rate (float, beats per minute)
            - intensity: Confidence level (float, 0.0-1.0) from predictor model

        Side effects:
            - Broadcasts UDP message to beats_port (all SO_REUSEPORT listeners receive)
            - Increments beat_messages counter
            - Prints "BEAT:" message to console
        """
        self.stats.increment('beat_messages')

        # Beat message format: /beat/{ppg_id} with [timestamp (int ms), bpm (float), intensity (float)]
        timestamp = beat_message['timestamp']
        bpm = beat_message['bpm']
        intensity = beat_message['intensity']

        # Broadcast once to PORT_BEATS (all listeners with SO_REUSEPORT receive)
        # Send timestamp as integer milliseconds to avoid float32 precision issues with large Unix timestamps
        timestamp_ms = int(timestamp * 1000)
        msg_data = [timestamp_ms, float(bpm), float(intensity)]
        self.beats_client.send_message(f"/beat/{ppg_id}", msg_data)

        logger.info(f"BEAT: PPG {ppg_id}, BPM: {bpm:.1f}, Timestamp: {timestamp:.3f}s")

    def _send_acquire_message(self, ppg_id, acquire_event):
        """Broadcast predictor acquire message to all listeners.

        Broadcasts message once to PORT_BEATS when predictor transitions from
        INITIALIZATION to LOCKED (initial rhythm acquisition only, not recovery).

        Args:
            ppg_id (int): Sensor ID (0-3)
            acquire_event (dict): Acquire data
                {'timestamp': float, 'bpm': float}

        Message format:
            Address: /acquire/{ppg_id}
            Arguments: [timestamp_ms, bpm]
            - timestamp_ms: Unix time (int, milliseconds) when rhythm acquired
            - bpm: Heart rate (float, beats per minute) at acquisition

        Side effects:
            - Broadcasts UDP message to beats_port (all SO_REUSEPORT listeners receive)
            - Increments acquire_messages counter
            - Prints "ACQUIRE:" message to console
        """
        self.stats.increment('acquire_messages')

        timestamp = acquire_event['timestamp']
        bpm = acquire_event['bpm']

        timestamp_ms = int(timestamp * 1000)
        msg_data = [timestamp_ms, float(bpm)]
        self.beats_client.send_message(f"/acquire/{ppg_id}", msg_data)

        logger.info(f"ACQUIRE: PPG {ppg_id}, BPM: {bpm:.1f}, Timestamp: {timestamp:.3f}s")

    def _send_release_message(self, ppg_id, release_event):
        """Broadcast predictor release message to all listeners.

        Broadcasts message once to PORT_BEATS when predictor transitions from
        LOCKED to COASTING (rhythm confidence lost).

        Args:
            ppg_id (int): Sensor ID (0-3)
            release_event (dict): Release data
                {'timestamp': float}

        Message format:
            Address: /release/{ppg_id}
            Arguments: [timestamp_ms]
            - timestamp_ms: Unix time (int, milliseconds) when rhythm released

        Side effects:
            - Broadcasts UDP message to beats_port (all SO_REUSEPORT listeners receive)
            - Increments release_messages counter
            - Prints "RELEASE:" message to console
        """
        self.stats.increment('release_messages')

        timestamp = release_event['timestamp']

        timestamp_ms = int(timestamp * 1000)
        msg_data = [timestamp_ms]
        self.beats_client.send_message(f"/release/{ppg_id}", msg_data)

        logger.info(f"RELEASE: PPG {ppg_id}, Timestamp: {timestamp:.3f}s")

    def run(self):
        """Start the OSC server and process PPG messages.

        Blocks indefinitely, listening for /ppg/{0-3} messages on input_port.
        Handles Ctrl+C gracefully with clean shutdown and statistics.

        Message flow:
            1. Listen on input_port (default 8000) for OSC messages
            2. Route /ppg/* messages to handle_ppg_message
            3. Call dispatcher for message handling
            4. On Ctrl+C, shutdown gracefully and print statistics

        Side effects:
            - Prints startup information to console
            - Prints warnings/beats during operation
            - Handles KeyboardInterrupt
            - Prints final statistics on shutdown
        """
        # Create dispatcher and bind handler
        disp = dispatcher.Dispatcher()
        disp.map("/ppg/*", self.handle_ppg_message)

        # Create OSC server
        server = osc.ReusePortBlockingOSCUDPServer(
            ("0.0.0.0", self.input_port),
            disp
        )

        logger.info(f"Sensor Processor listening on port {self.input_port}")
        logger.info(f"Beat broadcast: 255.255.255.255:{self.beats_port}")
        logger.info(f"Expecting /ppg/{{0-7}} messages with 5 samples + timestamp (0-3: real, 4-7: virtual)")
        if self.verbose:
            logger.info("Verbose mode: Per-sample debug logging ENABLED")
        logger.info(f"Waiting for messages... (Ctrl+C to stop)")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            server.shutdown()
            self.stats.print_stats("SENSOR PROCESSOR STATISTICS")


def main():
    """Main entry point with command-line argument parsing.

    Parses arguments for input and output port configuration, validates port ranges,
    creates SensorProcessor instance, and handles runtime errors.

    Command-line arguments:
        --input-port N      UDP port to listen for PPG input (default: osc.PORT_PPG = 8000)
        --beats-port N      UDP port for beat broadcast (default: osc.PORT_BEATS = 8001)
        --verbose           Enable per-sample debug logging

    Example usage:
        python3 -m amor.processor
        python3 -m amor.processor --input-port 9000 --beats-port 9001
        python3 -u -m amor.processor --verbose | tee processor_dump.log

    Validation:
        - All ports must be in range 1-65535
        - Exits with error code 1 if validation fails or port is already in use

    Error handling:
        - "Address already in use": Port is bound by another process
        - Other OSError: Network-related errors
    """
    parser = argparse.ArgumentParser(
        description="Sensor Processor - Beat detection and OSC messaging"
    )
    parser.add_argument(
        "--input-port",
        type=int,
        default=osc.PORT_PPG,
        help=f"UDP port to listen for PPG input (default: {osc.PORT_PPG})"
    )
    parser.add_argument(
        "--beats-port",
        type=int,
        default=osc.PORT_BEATS,
        help=f"UDP port for beat broadcast output (default: {osc.PORT_BEATS})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable per-sample debug logging (shows MAD, threshold, state for every sample)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("AMOR_LOG_LEVEL", "INFO"),
        help="Logging verbosity (default: INFO)"
    )

    args = parser.parse_args()

    # Handle --verbose flag for backward compatibility
    if args.verbose:
        args.log_level = "DEBUG"
    logger.setLevel(args.log_level)

    # Validate arguments
    for port_name, port_value in [
        ("input", args.input_port),
        ("beats", args.beats_port)
    ]:
        try:
            osc.validate_port(port_value)
        except ValueError as e:
            logger.error(f"{port_name} port: {e}")
            sys.exit(1)

    # Create and run processor
    processor = SensorProcessor(
        input_port=args.input_port,
        beats_port=args.beats_port,
        verbose=args.verbose
    )

    try:
        processor.run()
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {args.input_port} already in use")
        else:
            logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
