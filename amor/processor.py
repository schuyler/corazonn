#!/usr/bin/env python3
"""
Sensor Processor - Amor Phase 1 Beat Detection

Receives raw PPG (Photoplethysmography) samples from ESP32 units, detects heartbeats,
and sends beat events to audio and lighting subsystems via OSC.

ARCHITECTURE:
- OSC server listening on port 8000 for PPG input (/ppg/{0-3} messages)
  - Uses SO_REUSEPORT socket option to allow port sharing across processes
- Four independent PPGSensor instances (one per ESP32 unit)
- Each sensor runs a state machine: WARMUP → ACTIVE → PAUSED (with recovery)
- Threshold-based beat detection with upward-crossing algorithm
- Outputs beat messages to ports 8001 (audio) and 8002 (lighting)

USAGE:
    # Start processor with default ports
    python3 -m amor.processor

    # Custom ports
    python3 -m amor.processor --input-port 8000 --audio-port 8001 --lighting-port 8002

QUICK START (Testing):
    Terminal 1: python3 -m amor.processor
    Terminal 2: python3 testing/ppg_test_sink.py --port 8001  # Audio receiver
    Terminal 3: python3 testing/ppg_test_sink.py --port 8002  # Lighting receiver
    Terminal 4: # Send test PPG data via OSC to port 8000

INPUT/OUTPUT OSC MESSAGES:

Input (port 8000):
    Address: /ppg/{ppg_id}  where ppg_id is 0-3
    Arguments: [sample0, sample1, sample2, sample3, sample4, timestamp_ms]
    - Samples: 5 int32 values, each 0-4095 (12-bit ADC from ESP32)
    - Timestamp: int32, milliseconds on ESP32 (used for gap detection)
    - Samples represent 100ms of data at 50Hz (5 samples * 20ms apart)

Output (ports 8001, 8002):
    Address: /beat/{ppg_id}  where ppg_id is 0-3
    Arguments: [timestamp, bpm, intensity]
    - Timestamp: float, Unix time (seconds) when beat detected
    - BPM: float, heart rate calculated from inter-beat intervals
    - Intensity: float, currently 0.0 (reserved for future use)

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
import sys
import time
from collections import deque
from pythonosc import dispatcher
from pythonosc.udp_client import SimpleUDPClient
import numpy as np

from amor import osc
from amor.detector import ThresholdDetector, ThresholdCrossing


class PPGSensor:
    """Per-sensor beat detection coordinator.

    Manages a single PPG sensor by coordinating threshold detection (via ThresholdDetector)
    and beat emission (IBI tracking and BPM calculation). Each of the 4 sensors runs independently.

    Architecture (Phase 1):
        - ThresholdDetector: Handles state machine, signal quality, crossing detection
        - PPGSensor: Handles beat emission, IBI validation, BPM calculation

    Note: In Phase 2, beat emission logic will move to HeartbeatPredictor.

    Attributes:
        ppg_id (int): Sensor ID (0-3)
        detector (ThresholdDetector): Threshold crossing detector
        last_beat_timestamp (float): ESP32 time of last detected beat (seconds)
        ibis (deque): Last 5 inter-beat intervals in milliseconds
    """

    # Beat emission parameters (temporary, will move to HeartbeatPredictor in Phase 2)
    IBI_MIN_MS = 400               # Minimum inter-beat interval (prevents double-detection)
    IBI_RESET_THRESHOLD_MS = 10000 # IBI above this triggers baseline reset (10s = clearly stuck)
    IBI_HISTORY_SIZE = 5           # Number of IBIs to keep for median BPM

    def __init__(self, ppg_id):
        self.ppg_id = ppg_id

        # Threshold detector (handles state machine and crossing detection)
        self.detector = ThresholdDetector(ppg_id)

        # Beat emission state (temporary, will move to predictor in Phase 2)
        self.last_beat_timestamp = None  # Timestamp of last detected beat (seconds, ESP32 time)
        self.ibis = deque(maxlen=self.IBI_HISTORY_SIZE)  # Keep last N IBIs for median BPM calculation

    def add_sample(self, value, timestamp_ms):
        """Process a single PPG sample and emit beat if detected.

        Delegates to ThresholdDetector for crossing detection, then processes
        observations for beat emission using IBI validation. Coordinates with
        detector to clear beat state when detector resets.

        Args:
            value (int): PPG ADC sample (0-4095 from ESP32)
            timestamp_ms (int): Sample timestamp in milliseconds (ESP32 time)

        Returns:
            dict or None: Beat message if beat detected, None otherwise
                Dict format: {'timestamp': float, 'bpm': float, 'intensity': float}
                - timestamp: Unix time (seconds) when beat was detected by processor
                - bpm: Detected heart rate in beats per minute
                - intensity: Reserved for future use (currently 0.0)

        Note: Detector handles state machine, signal quality, gap detection, ESP32 resets.
        This method only handles beat emission logic (IBI validation, BPM calculation).
        """
        # Check if detector was reset (ESP32 reboot or message gap)
        if self.detector.was_reset():
            # Clear stale beat state from previous session
            self.last_beat_timestamp = None
            self.ibis.clear()
            self.detector.clear_reset_flag()

        # Delegate to detector for crossing detection
        observation = self.detector.process_sample(value, timestamp_ms)

        # If crossing detected, process for beat emission
        if observation is not None:
            return self._process_observation(observation)

        return None

    def _process_observation(self, observation: ThresholdCrossing):
        """Process threshold crossing observation for beat emission.

        Takes observation from ThresholdDetector and applies IBI validation
        and beat message generation. This is temporary Phase 1 logic that will
        move to HeartbeatPredictor in Phase 2.

        Args:
            observation: ThresholdCrossing observation from detector

        Returns:
            dict or None: Beat message if IBI valid, None otherwise
                {'timestamp': float, 'bpm': float, 'intensity': float}

        Logic:
            - First beat: records timestamp only, returns None (establishes baseline)
            - Subsequent beats: calculates IBI and sends message if valid
            - Rejects too-short IBIs (< IBI_MIN_MS) to prevent double-detection
            - Resets on extremely large IBI (> IBI_RESET_THRESHOLD_MS)
        """
        timestamp_s = observation.timestamp_ms / 1000.0

        # Check if this is the first beat or subsequent beats
        if self.last_beat_timestamp is None:
            # First beat: store timestamp only, no message
            print(f"PPG {self.ppg_id}: First beat detected (establishing baseline)")
            self.last_beat_timestamp = timestamp_s
            return None

        # Second+ beat: calculate IBI
        ibi_ms = (timestamp_s - self.last_beat_timestamp) * 1000.0  # Convert to ms

        # IBI validation: reject if too short (likely double-detection of same beat)
        if ibi_ms < self.IBI_MIN_MS:
            print(f"PPG {self.ppg_id}: Beat rejected - IBI {ibi_ms:.0f}ms < {self.IBI_MIN_MS}ms (likely double-detection)")
            return None

        # Check for extremely large IBI indicating we're stuck/broken
        if ibi_ms > self.IBI_RESET_THRESHOLD_MS:
            # Extremely large gap: reset baseline to prevent stuck state
            print(f"PPG {self.ppg_id}: Extremely large IBI {ibi_ms:.0f}ms, resetting baseline")
            self.last_beat_timestamp = timestamp_s
            self.ibis.clear()  # Clear stale IBI history
            return None

        self.ibis.append(ibi_ms)
        print(f"PPG {self.ppg_id}: Valid IBI recorded: {ibi_ms:.0f}ms, total IBIs: {len(self.ibis)}")

        # BPM: median of available IBIs
        bpm = self._calculate_bpm()
        if bpm is None:
            print(f"PPG {self.ppg_id}: BPM calculation returned None (need at least 1 IBI)")
            self.last_beat_timestamp = timestamp_s
            return None

        print(f"PPG {self.ppg_id}: BPM calculated: {bpm:.1f}, sending beat message")

        # Update for next beat
        self.last_beat_timestamp = timestamp_s

        # Return beat message with Unix time timestamp
        return {
            'timestamp': time.time(),  # Unix time (seconds) when beat occurred
            'bpm': bpm,
            'intensity': 0.0
        }

    def _calculate_bpm(self):
        """Calculate heart rate in beats per minute from inter-beat intervals.

        Uses median of last 5 IBIs to reduce noise from individual beat variations.
        Formula: BPM = 60000 / IBI_ms

        Returns:
            float or None: Calculated BPM, or None if insufficient IBI data

        Note:
            - Requires at least 1 IBI to calculate
            - Uses median (not mean) to be robust to outliers
            - IBI range already validated in _detect_beat (400-2000ms)
            - Result range: 30-150 BPM (inverse of IBI range)
        """
        if len(self.ibis) == 0:
            return None

        # BPM = 60000 / IBI (where IBI is in milliseconds)
        median_ibi = np.median(list(self.ibis))
        bpm = 60000.0 / median_ibi
        return bpm

class SensorProcessor:
    """OSC server for processing PPG sensors and routing beat detection output.

    Manages 4 independent PPGSensor instances and routes their beat detections to
    audio and lighting subsystems. Validates input messages, tracks statistics,
    and handles clean shutdown.

    Architecture:
        - OSC server on input_port (default 8000) listening for /ppg/{0-3} messages
        - Four PPGSensor instances for parallel, independent beat detection
        - UDP clients for output to audio_port and lighting_port (both get same messages)
        - Input validation: address pattern, argument count/types, ADC range, timestamps

    Message flow:
        /ppg/N (port 8000) -> validate -> PPGSensor.add_sample -> detect beat
        -> _send_beat_message -> /beat/N (ports 8001, 8002)

    Attributes:
        input_port (int): UDP port for PPG input (default: 8000)
        audio_port (int): UDP port for audio beat output (default: 8001)
        lighting_port (int): UDP port for lighting beat output (default: 8002)
        sensors (dict): 4 PPGSensor instances indexed 0-3
        stats (MessageStatistics): Message counters
    """

    def __init__(self, input_port=8000, audio_port=8001, lighting_port=8002):
        self.input_port = input_port
        self.audio_port = audio_port
        self.lighting_port = lighting_port

        # Create output clients
        self.audio_client = SimpleUDPClient("127.0.0.1", audio_port)
        self.lighting_client = SimpleUDPClient("127.0.0.1", lighting_port)

        # Create 4 PPGSensor instances
        self.sensors = {i: PPGSensor(i) for i in range(4)}

        # Statistics
        self.stats = osc.MessageStatistics()

    def validate_message(self, address, args):
        """Validate OSC message format and content.

        Checks address pattern, argument count/types, ADC range, and timestamp validity.

        Expected format:
            Address: /ppg/{ppg_id}  where ppg_id is 0-3
            Arguments: [sample0, sample1, sample2, sample3, sample4, timestamp_ms]

        Validation steps:
            1. Address matches /ppg/[0-3] pattern
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
            print(f"WARNING: Processor: {error_msg}")
            return

        self.stats.increment('valid_messages')

        # Process each sample through the sensor's state machine
        # Each sample arrives 20ms apart (50Hz = 1 sample per 20ms)
        for i, sample in enumerate(samples):
            # Calculate individual timestamp for each sample in the bundle
            sample_timestamp_ms = timestamp_ms + (i * 20)
            beat_message = self.sensors[ppg_id].add_sample(sample, sample_timestamp_ms)

            if beat_message is not None:
                self._send_beat_message(ppg_id, beat_message)

    def _send_beat_message(self, ppg_id, beat_message):
        """Send beat detection message to audio and lighting subsystems.

        Sends identical message to both ports simultaneously via UDP.
        Logs beat to console for real-time monitoring.

        Args:
            ppg_id (int): Sensor ID (0-3)
            beat_message (dict): Beat data
                {'timestamp': float, 'bpm': float, 'intensity': float}

        Message format sent (both ports):
            Address: /beat/{ppg_id}
            Arguments: [timestamp, bpm, intensity]
            - timestamp: Unix time (float, seconds)
            - bpm: Heart rate (float, beats per minute)
            - intensity: Currently 0.0 (reserved for future use)

        Side effects:
            - Sends UDP messages to audio_port and lighting_port
            - Increments beat_messages counter
            - Prints "BEAT:" message to console
        """
        self.stats.increment('beat_messages')

        # Beat message format: /beat/{ppg_id} with [timestamp (int ms), bpm (float), intensity (float)]
        timestamp = beat_message['timestamp']
        bpm = beat_message['bpm']
        intensity = beat_message['intensity']

        # Send to both audio and lighting
        # Send timestamp as integer milliseconds to avoid float32 precision issues with large Unix timestamps
        timestamp_ms = int(timestamp * 1000)
        msg_data = [timestamp_ms, float(bpm), float(intensity)]
        self.audio_client.send_message(f"/beat/{ppg_id}", msg_data)
        self.lighting_client.send_message(f"/beat/{ppg_id}", msg_data)

        print(f"BEAT: PPG {ppg_id}, BPM: {bpm:.1f}, Timestamp: {timestamp:.3f}s")

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

        print(f"Sensor Processor listening on port {self.input_port}")
        print(f"Audio output: 127.0.0.1:{self.audio_port}")
        print(f"Lighting output: 127.0.0.1:{self.lighting_port}")
        print(f"Expecting /ppg/{{0-3}} messages with 5 samples + timestamp")
        print(f"Waiting for messages... (Ctrl+C to stop)")
        print()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            server.shutdown()
            self.stats.print_stats("SENSOR PROCESSOR STATISTICS")


def main():
    """Main entry point with command-line argument parsing.

    Parses arguments for input and output port configuration, validates port ranges,
    creates SensorProcessor instance, and handles runtime errors.

    Command-line arguments:
        --input-port N      UDP port to listen for PPG input (default: 8000)
        --audio-port N      UDP port for audio output (default: 8001)
        --lighting-port N   UDP port for lighting output (default: 8002)

    Example usage:
        python3 -m amor.processor
        python3 -m amor.processor --input-port 9000 --audio-port 9001 --lighting-port 9002

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
        default=8000,
        help="UDP port to listen for PPG input (default: 8000)"
    )
    parser.add_argument(
        "--audio-port",
        type=int,
        default=8001,
        help="UDP port for audio output (default: 8001)"
    )
    parser.add_argument(
        "--lighting-port",
        type=int,
        default=8002,
        help="UDP port for lighting output (default: 8002)"
    )

    args = parser.parse_args()

    # Validate arguments
    for port_name, port_value in [
        ("input", args.input_port),
        ("audio", args.audio_port),
        ("lighting", args.lighting_port)
    ]:
        try:
            osc.validate_port(port_value)
        except ValueError as e:
            print(f"ERROR: {port_name} port: {e}", file=sys.stderr)
            sys.exit(1)

    # Create and run processor
    processor = SensorProcessor(
        input_port=args.input_port,
        audio_port=args.audio_port,
        lighting_port=args.lighting_port
    )

    try:
        processor.run()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Port {args.input_port} already in use", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
