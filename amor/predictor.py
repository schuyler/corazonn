#!/usr/bin/env python3
"""
Heartbeat Predictor - Autonomous Model-Based Rhythm Tracking for PPG Sensors

Maintains an internal rhythmic model for each participant's heartbeat, using sensor
threshold crossings as noisy observations to keep the model synchronized. Emits beats
autonomously via background thread at precise intervals based on the phase model,
eliminating quantization jitter from polling.

ARCHITECTURE:
- Phase-based rhythm model (0.0 to 1.0 within cardiac cycle)
- IBI estimation with exponential smoothing (0.9 × old + 0.1 × observed)
- Phase correction to prevent drift (0.10 × phase_error)
- Confidence system: initialization → locked → coasting → stopped
- Adaptive observation debouncing (≥ 0.7 × IBI)
- Autonomous beat emission via background thread with configurable lead time

THREADING:
- Background thread emits beats at precise intervals (not polled)
- Thread-safe state access with locks (phase, IBI, confidence)
- update() advances phase/confidence, thread reads state and emits beats
- No quantization jitter - beats emitted 200ms before predicted time

USAGE:
    predictor = HeartbeatPredictor(ppg_id=0, beats_port=8001)
    predictor.start()  # Start autonomous beat emission thread

    # When threshold crossing detected:
    predictor.observe_crossing(timestamp_s=1.234)

    # Every sample (50Hz) - updates state only, does NOT emit beats:
    predictor.update(timestamp_s=1.254)

    predictor.stop()  # Stop emission thread

Reference: Design document at docs/amor-heartbeat-prediction-design.md
"""

from dataclasses import dataclass
from typing import Optional
import time
import threading

from amor import osc
from amor.log import get_logger
import logging


# Configuration parameters - IBI constraints
IBI_MIN_MS = 400               # Minimum IBI (150 BPM max)
IBI_MAX_MS = 1333              # Maximum IBI (45 BPM min)
IBI_BLEND_WEIGHT = 0.1         # Weight for new observation (0.1 = 10%)
IBI_OUTLIER_FACTOR = 1.5       # Reject observations if IBI > factor × current (prevents death spiral)

# Phase correction
PHASE_CORRECTION_WEIGHT = 0.10 # Weight for phase error correction (0.10 = 10%)
PHASE_CORRECTION_MAX = 0.2     # Maximum phase correction per observation (prevents jumps)

# Observation filtering
OBSERVATION_DEBOUNCE = 0.7     # Accept crossings ≥ 0.7 × IBI apart

# Confidence parameters
CONFIDENCE_RAMP_PER_BEAT = 0.2 # Confidence increase per observation (0.2 = 20%)
FADEIN_DURATION_MS = 5000      # Time from confidence 0.0 → 1.0 (5 seconds)
COASTING_DURATION_MS = 10000   # Time from confidence 1.0 → 0.0 (10 seconds)
INIT_OBSERVATIONS = 5          # Observations needed for full confidence
CONFIDENCE_EMISSION_MIN = 0.0  # Minimum confidence to emit beats (0 = always emit if >0)

# Update frequency
UPDATE_RATE_HZ = 50            # Predictor update() calls per second

# Autonomous beat emission
BEAT_LEAD_TIME_S = 0.2         # Emit beats 200ms before predicted beat time


@dataclass
class BeatMessage:
    """Beat event emitted by predictor.

    Attributes:
        timestamp (float): Unix time (seconds) when beat occurred
        bpm (float): Beats per minute derived from IBI estimate
        intensity (float): Confidence level (0.0-1.0) indicating model certainty
    """
    timestamp: float
    bpm: float
    intensity: float


class HeartbeatPredictor:
    """Phase-based heartbeat predictor with confidence tracking.

    Maintains an internal rhythm model that emits beats based on phase progression.
    Sensor observations update the IBI estimate and phase, but the model is the
    authoritative source of beat timing. Confidence maps to output intensity,
    creating natural fade-in/fade-out effects.

    Operational Modes:
        Initialization: Collecting first 5 observations to establish IBI
        Locked: Regular observations maintain confidence at 1.0, with 5-second fade-in after init
        Coasting: No observations, confidence decays over 10 seconds
        Stopped: Confidence = 0, no beat emission until new observations

    Attributes:
        ppg_id (int): Sensor ID (0-3)
        mode (str): Current mode (initialization, locked, coasting, stopped)
        phase (float): Position within cardiac cycle (0.0-1.0)
        ibi_estimate_ms (float): Current IBI estimate in milliseconds
        confidence (float): Model confidence (0.0-1.0)
        last_update_time (float): Timestamp of last update() call (seconds)
        last_beat_time (float): Timestamp when phase last crossed 1.0 (seconds)
        last_observation_time (float): Timestamp of last accepted observation (seconds)
        init_observations (list): Collected observations during initialization
    """

    # Modes
    MODE_INITIALIZATION = "initialization"
    MODE_LOCKED = "locked"
    MODE_COASTING = "coasting"
    MODE_STOPPED = "stopped"

    def __init__(self, ppg_id: int, beats_port: int = osc.PORT_BEATS,
                 lead_time_s: float = BEAT_LEAD_TIME_S, verbose: bool = False) -> None:
        """Initialize predictor for a specific PPG sensor.

        Args:
            ppg_id: Sensor ID (0-3)
            beats_port: OSC port for beat output (default: osc.PORT_BEATS)
            lead_time_s: Seconds before beat to emit message (default: 0.2)
            verbose: Enable detailed logging
        """
        self.ppg_id = ppg_id
        self.beats_port = beats_port
        self.lead_time_s = lead_time_s
        self.verbose = verbose
        self.logger = get_logger("predictor")
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        self.mode = self.MODE_STOPPED

        # Phase and rhythm state
        self.phase: float = 0.0
        self.ibi_estimate_ms: Optional[float] = None

        # Confidence state
        self.confidence: float = 0.0

        # Timing state
        self.last_update_time: Optional[float] = None
        self.last_beat_time: Optional[float] = None
        self.last_observation_time: Optional[float] = None
        self.fadein_start_time: Optional[float] = None  # For time-based fade-in

        # Initialization state
        self.init_observations: list[float] = []

        # Observation rejection metrics (for debugging)
        self.debounced_count: int = 0
        self.out_of_range_count: int = 0
        self.outlier_count: int = 0

        # Autonomous beat emission (threading)
        self.beats_client: Optional[osc.BroadcastUDPClient] = None
        self.emission_thread: Optional[threading.Thread] = None
        self.running: bool = False
        self.emission_lock = threading.Lock()  # Protects running flag
        self.state_lock = threading.Lock()  # Protects phase, IBI, confidence

    def observe_crossing(self, timestamp_s: float) -> None:
        """Record threshold crossing observation from detector (thread-safe).

        Updates IBI estimate and phase based on observation timing. Applies
        debouncing to filter noise and prevent multiple observations per cycle.

        Args:
            timestamp_s: Observation timestamp in seconds (ESP32 time)

        Behavior by mode:
            Stopped: Begins initialization, records first observation
            Initialization: Accumulates observations until INIT_OBSERVATIONS reached
            Locked/Coasting: Updates IBI and phase, resets coasting decay
        """
        with self.state_lock:
            # Debounce observations using current IBI estimate
            if self.ibi_estimate_ms is not None and self.last_observation_time is not None:
                time_since_last = (timestamp_s - self.last_observation_time) * 1000.0  # ms
                min_interval = OBSERVATION_DEBOUNCE * self.ibi_estimate_ms

                if time_since_last < min_interval:
                    self.debounced_count += 1
                    self.logger.debug(f"PPG {self.ppg_id}: Observation debounced - "
                                      f"only {time_since_last:.0f}ms since last (min {min_interval:.0f}ms)")
                    return

            # Process observation based on current mode
            if self.mode == self.MODE_STOPPED:
                self._begin_initialization(timestamp_s)

            elif self.mode == self.MODE_INITIALIZATION:
                self._process_init_observation(timestamp_s)

            elif self.mode in (self.MODE_LOCKED, self.MODE_COASTING):
                self._process_observation(timestamp_s)

            self.last_observation_time = timestamp_s

    def update(self, timestamp_s: float) -> None:
        """Update phase and confidence from elapsed time (thread-safe).

        Called at 50Hz by processor regardless of observations. Advances phase
        based on elapsed time and IBI estimate. Updates confidence decay during
        coasting. Does NOT emit beats - emission handled by autonomous thread.

        Args:
            timestamp_s: Current timestamp in seconds (ESP32 time)

        Side effects:
            - Updates phase, confidence, last_update_time (with state_lock)
            - May transition coasting → stopped when confidence depletes
        """
        with self.state_lock:
            # First update - just record timestamp
            if self.last_update_time is None:
                self.last_update_time = timestamp_s
                return

            # Calculate time delta
            time_delta_s = timestamp_s - self.last_update_time
            self.last_update_time = timestamp_s

            # Only advance phase if we have an IBI estimate
            if self.ibi_estimate_ms is None:
                return

            # Advance phase
            time_delta_ms = time_delta_s * 1000.0
            phase_increment = time_delta_ms / self.ibi_estimate_ms
            self.phase += phase_increment

            # Wrap phase when it exceeds 1.0
            while self.phase >= 1.0:
                self.phase -= 1.0

            # Update confidence fade-in if active
            if self.fadein_start_time is not None:
                self._update_fadein(timestamp_s)

            # Update confidence decay if coasting
            if self.mode == self.MODE_COASTING:
                self._update_coasting_decay(time_delta_ms)

    def _begin_initialization(self, timestamp_s: float) -> None:
        """Begin initialization mode with first observation.

        Args:
            timestamp_s: First observation timestamp (seconds)
        """
        self.mode = self.MODE_INITIALIZATION
        self.init_observations = [timestamp_s]
        self.confidence = CONFIDENCE_RAMP_PER_BEAT  # 0.2 after first observation
        self.phase = 0.0

        self.logger.info(f"PPG {self.ppg_id}: Predictor initialization started")

    def _process_init_observation(self, timestamp_s: float) -> None:
        """Process observation during initialization mode.

        Accumulates observations and calculates initial IBI estimate from
        median of intervals. Transitions to locked mode after INIT_OBSERVATIONS.

        Args:
            timestamp_s: Observation timestamp (seconds)
        """
        self.init_observations.append(timestamp_s)

        # Calculate intervals between consecutive observations
        intervals = []
        for i in range(1, len(self.init_observations)):
            interval_ms = (self.init_observations[i] - self.init_observations[i-1]) * 1000.0
            # Validate interval is within reasonable bounds
            if IBI_MIN_MS <= interval_ms <= IBI_MAX_MS:
                intervals.append(interval_ms)

        # Update confidence (ramp by 0.2 per observation)
        self.confidence = min(1.0, len(self.init_observations) * CONFIDENCE_RAMP_PER_BEAT)

        # If we have enough observations, establish initial IBI and transition
        if len(self.init_observations) >= INIT_OBSERVATIONS and len(intervals) > 0:
            # Use median of intervals as initial IBI estimate
            intervals.sort()
            median_idx = len(intervals) // 2
            self.ibi_estimate_ms = intervals[median_idx]

            # Initialize phase to 0.0 - treat this observation as beat reference point
            self.phase = 0.0
            # Use system time for beat timing (emission thread uses time.time())
            self.last_beat_time = time.time()

            # Transition to locked mode with time-based fade-in
            self.mode = self.MODE_LOCKED
            self.confidence = 0.0
            self.fadein_start_time = timestamp_s

            self.logger.info(f"PPG {self.ppg_id}: Predictor locked - IBI={self.ibi_estimate_ms:.0f}ms, "
                             f"BPM={60000.0 / self.ibi_estimate_ms:.1f}, fading in over {FADEIN_DURATION_MS/1000.0:.1f}s")

        else:
            self.logger.debug(f"PPG {self.ppg_id}: Init observation {len(self.init_observations)}/{INIT_OBSERVATIONS}, "
                              f"confidence={self.confidence:.1f}")

    def _process_observation(self, timestamp_s: float) -> None:
        """Process observation in locked or coasting mode.

        Updates IBI estimate using exponential smoothing and corrects phase
        drift. Transitions from coasting back to locked if applicable.

        Args:
            timestamp_s: Observation timestamp (seconds)
        """
        if self.ibi_estimate_ms is None or self.last_observation_time is None:
            # Shouldn't happen, but handle gracefully
            self.logger.warning(f"PPG {self.ppg_id}: Observation received but no IBI/observation baseline, ignoring")
            return

        # Calculate observed IBI (time since last observation)
        observed_ibi_ms = (timestamp_s - self.last_observation_time) * 1000.0

        # Validate observed IBI - basic range check
        if observed_ibi_ms < IBI_MIN_MS or observed_ibi_ms > IBI_MAX_MS:
            self.out_of_range_count += 1
            self.logger.debug(f"PPG {self.ppg_id}: Observation rejected - "
                              f"IBI {observed_ibi_ms:.0f}ms out of range [{IBI_MIN_MS}, {IBI_MAX_MS}]")
            return

        # Outlier rejection - prevent death spiral from missed beats
        ibi_min_bound = self.ibi_estimate_ms / IBI_OUTLIER_FACTOR
        ibi_max_bound = self.ibi_estimate_ms * IBI_OUTLIER_FACTOR
        if observed_ibi_ms < ibi_min_bound or observed_ibi_ms > ibi_max_bound:
            self.outlier_count += 1
            self.logger.debug(f"PPG {self.ppg_id}: Observation rejected - "
                              f"IBI {observed_ibi_ms:.0f}ms is outlier (current {self.ibi_estimate_ms:.0f}ms, "
                              f"bounds [{ibi_min_bound:.0f}, {ibi_max_bound:.0f}]ms)")
            return

        # Update IBI estimate with exponential smoothing
        old_ibi = self.ibi_estimate_ms
        self.ibi_estimate_ms = (1.0 - IBI_BLEND_WEIGHT) * old_ibi + IBI_BLEND_WEIGHT * observed_ibi_ms

        # Phase correction: prevent drift even when IBI is accurate
        # expected_phase = (observed_time - last_observation_time) / current_ibi
        # phase_error = expected_phase - current_phase
        expected_phase = observed_ibi_ms / old_ibi  # Where phase should be based on observation
        phase_error = expected_phase - self.phase
        # Clamp phase error to prevent large jumps
        clamped_phase_error = max(-PHASE_CORRECTION_MAX, min(PHASE_CORRECTION_MAX, phase_error))
        self.phase += PHASE_CORRECTION_WEIGHT * clamped_phase_error

        self.logger.debug(f"PPG {self.ppg_id}: Observation processed - "
                          f"IBI {old_ibi:.0f}→{self.ibi_estimate_ms:.0f}ms, "
                          f"phase correction {clamped_phase_error:+.3f}" +
                          (f" (clamped from {phase_error:+.3f})" if abs(phase_error) > PHASE_CORRECTION_MAX else ""))

        # Update confidence and mode
        if self.mode == self.MODE_COASTING:
            # Transition back to locked with time-based fade-in
            self.mode = self.MODE_LOCKED
            # Start fade-in from current confidence level
            self.fadein_start_time = timestamp_s
            self.logger.info(f"PPG {self.ppg_id}: Coasting → Locked, fading in from confidence={self.confidence:.2f}")
        elif self.fadein_start_time is None:
            # Maintain full confidence in locked mode (only if not already fading in)
            self.confidence = 1.0

    def _update_fadein(self, timestamp_s: float) -> None:
        """Update confidence increase during fade-in.

        Increases confidence linearly over FADEIN_DURATION_MS (5 seconds).
        Clears fadein_start_time when confidence reaches 1.0.

        Args:
            timestamp_s: Current timestamp (seconds)
        """
        if self.fadein_start_time is None:
            return

        # Calculate elapsed time since fade-in started
        elapsed_ms = (timestamp_s - self.fadein_start_time) * 1000.0

        # Guard against negative elapsed time (ESP32 reboot causing backward time jump)
        if elapsed_ms < 0:
            self.logger.warning(f"PPG {self.ppg_id}: Negative elapsed time in fade-in: {elapsed_ms:.0f}ms, "
                                f"clearing fade-in state")
            self.fadein_start_time = None
            if hasattr(self, '_fadein_start_confidence'):
                delattr(self, '_fadein_start_confidence')
            return

        # Calculate target confidence based on elapsed time
        # Start from current confidence (for coasting recovery) or 0.0 (for initialization)
        fadein_progress = min(1.0, elapsed_ms / FADEIN_DURATION_MS)

        # When recovering from coasting, we want to ramp from current confidence to 1.0
        # When starting fresh (initialization), we ramp from 0.0 to 1.0
        # Store the starting confidence when fade-in begins
        if not hasattr(self, '_fadein_start_confidence'):
            self._fadein_start_confidence = self.confidence

        target_confidence = self._fadein_start_confidence + (1.0 - self._fadein_start_confidence) * fadein_progress
        # Clamp confidence to [0.0, 1.0] range
        self.confidence = max(0.0, min(1.0, target_confidence))

        # Complete fade-in when we reach full confidence
        if self.confidence >= 1.0:
            self.confidence = 1.0
            self.fadein_start_time = None
            if hasattr(self, '_fadein_start_confidence'):
                delattr(self, '_fadein_start_confidence')
            self.logger.debug(f"PPG {self.ppg_id}: Fade-in complete, confidence=1.0")

    def _update_coasting_decay(self, time_delta_ms: float) -> None:
        """Update confidence decay during coasting mode.

        Decays confidence linearly over COASTING_DURATION_MS (10 seconds).
        Transitions to stopped mode when confidence reaches 0.

        Args:
            time_delta_ms: Elapsed time since last update (milliseconds)
        """
        # Guard against negative time deltas (ESP32 reboot causing backward time jump)
        if time_delta_ms < 0:
            self.logger.warning(f"PPG {self.ppg_id}: Negative time delta in coasting decay: {time_delta_ms:.0f}ms, ignoring")
            return

        decay_rate = 1.0 / COASTING_DURATION_MS  # Per millisecond
        decay_amount = decay_rate * time_delta_ms

        # Clamp confidence to [0.0, 1.0] range
        self.confidence = max(0.0, min(1.0, self.confidence - decay_amount))

        if self.confidence <= 0.0:
            # Transition to stopped mode
            self._print_rejection_metrics(reset=True)
            self.mode = self.MODE_STOPPED
            self.ibi_estimate_ms = None
            self.phase = 0.0
            self.init_observations = []
            self.fadein_start_time = None
            if hasattr(self, '_fadein_start_confidence'):
                delattr(self, '_fadein_start_confidence')

            self.logger.info(f"PPG {self.ppg_id}: Coasting → Stopped (confidence depleted)")

    def enter_coasting(self) -> None:
        """Manually enter coasting mode (thread-safe).

        Called by processor when detector enters PAUSED state (signal quality too low)
        or when detector resets (ESP32 reboot, message gap). Begins confidence decay.

        Can transition from LOCKED or INITIALIZATION modes:
        - LOCKED → COASTING: Normal signal loss during steady operation
        - INITIALIZATION → COASTING: Signal lost during startup (partial confidence continues)
        """
        with self.state_lock:
            if self.mode == self.MODE_LOCKED:
                self.mode = self.MODE_COASTING
                # Clear any active fade-in
                self.fadein_start_time = None
                if hasattr(self, '_fadein_start_confidence'):
                    delattr(self, '_fadein_start_confidence')
                self.logger.info(f"PPG {self.ppg_id}: Predictor Locked → Coasting")
                self._print_rejection_metrics(reset=True)
            elif self.mode == self.MODE_INITIALIZATION and self.ibi_estimate_ms is not None:
                # During initialization, if we have partial IBI estimate, enter coasting
                # This allows partial confidence beats to fade out gracefully
                self.mode = self.MODE_COASTING
                # Clear any active fade-in
                self.fadein_start_time = None
                if hasattr(self, '_fadein_start_confidence'):
                    delattr(self, '_fadein_start_confidence')
                self.logger.info(f"PPG {self.ppg_id}: Predictor Initialization → Coasting (partial confidence)")
                self._print_rejection_metrics(reset=True)

    def _print_rejection_metrics(self, reset: bool = False) -> None:
        """Print observation rejection metrics for debugging.

        Args:
            reset: If True, reset counters to zero after printing
        """
        total = self.debounced_count + self.out_of_range_count + self.outlier_count
        if total > 0:
            self.logger.info(f"PPG {self.ppg_id}: Rejections - "
                             f"debounced={self.debounced_count}, "
                             f"out_of_range={self.out_of_range_count}, "
                             f"outlier={self.outlier_count}, "
                             f"total={total}")
            if reset:
                self.debounced_count = 0
                self.out_of_range_count = 0
                self.outlier_count = 0

    def get_mode(self) -> str:
        """Get current predictor mode for monitoring/debugging.

        Returns:
            Current mode: "initialization", "locked", "coasting", or "stopped"
        """
        return self.mode

    def get_confidence(self) -> float:
        """Get current confidence level.

        Returns:
            Confidence (0.0-1.0)
        """
        return self.confidence

    def start(self) -> None:
        """Start autonomous beat emission thread.

        Creates OSC client and launches background thread that emits beats
        at precise intervals based on the phase model. Thread calculates
        next beat time and sleeps until lead_time before emission.

        Side effects:
            - Creates self.beats_client (BroadcastUDPClient)
            - Starts self.emission_thread (daemon thread)
            - Sets self.running = True
        """
        with self.emission_lock:
            if self.running:
                return
            self.running = True
            self.beats_client = osc.BroadcastUDPClient("255.255.255.255", self.beats_port)
            self.emission_thread = threading.Thread(
                target=self._emission_loop,
                name=f"Predictor-PPG{self.ppg_id}",
                daemon=True
            )
            self.emission_thread.start()

        self.logger.info(f"PPG {self.ppg_id}: Autonomous beat emission started")

    def stop(self) -> None:
        """Stop emission thread.

        Signals thread to exit and waits up to 2 seconds for thread to join.
        Safe to call multiple times.

        Side effects:
            - Sets self.running = False
            - Joins emission_thread with 2s timeout
        """
        with self.emission_lock:
            if not self.running:
                return
            self.running = False
            thread_to_join = self.emission_thread

        if thread_to_join:
            thread_to_join.join(timeout=2.0)
            if thread_to_join.is_alive():
                self.logger.warning(f"PPG {self.ppg_id}: Emission thread did not stop within 2s")

        self.logger.info(f"PPG {self.ppg_id}: Autonomous beat emission stopped")

    def _emission_loop(self) -> None:
        """Background thread: emit beats autonomously at precise intervals.

        Continuously calculates next beat time based on current IBI estimate,
        sleeps until lead_time before beat, then sends OSC message. Reads
        phase/IBI/confidence with thread-safe locks.

        Thread exits when self.running becomes False.
        """
        while True:
            # Check if we should exit
            with self.emission_lock:
                if not self.running:
                    break

            # Read state and calculate next beat time atomically
            with self.state_lock:
                confidence = self.confidence
                ibi_ms = self.ibi_estimate_ms
                last_beat = self.last_beat_time

                # If no IBI estimate or no confidence, sleep briefly and retry
                # IMPORTANT: Sleep OUTSIDE the lock to avoid blocking main thread
                if confidence <= CONFIDENCE_EMISSION_MIN or ibi_ms is None:
                    should_wait = True
                    wait_duration = 0.05  # 50ms
                else:
                    should_wait = False
                    # Calculate next beat time with current state (prevents TOCTOU race)
                    now = time.time()
                    if last_beat is None:
                        # First beat - start from current time
                        next_beat_time = now + (ibi_ms / 1000.0)
                    else:
                        next_beat_time = last_beat + (ibi_ms / 1000.0)
                        # If next beat is in the past (recovery from stopped/coasting),
                        # reset to current time to avoid burst of historical beats
                        if next_beat_time < now:
                            next_beat_time = now + (ibi_ms / 1000.0)

                    # Update last_beat_time NOW (before releasing lock)
                    # This ensures timing calculations stay consistent
                    self.last_beat_time = next_beat_time

                    # Calculate BPM and intensity from captured state
                    # These values must match the IBI used for timing calculation
                    beat_bpm = 60000.0 / ibi_ms
                    beat_intensity = confidence

                    # Calculate sleep duration
                    sleep_until = next_beat_time - self.lead_time_s
                    wait_duration = sleep_until - time.time()

            # Sleep outside lock (doesn't block main thread)
            if should_wait or wait_duration > 0:
                time.sleep(max(wait_duration, 0))
                if should_wait:
                    continue

            # Send beat message with values that match the timing calculation
            # We still check current confidence to handle mode transitions during sleep
            with self.state_lock:
                if self.confidence > CONFIDENCE_EMISSION_MIN and self.ibi_estimate_ms is not None:
                    self._send_beat(next_beat_time, beat_bpm, beat_intensity)

    def _send_beat(self, beat_timestamp: float, bpm: float, intensity: float) -> None:
        """Send beat OSC message.

        Args:
            beat_timestamp: Unix timestamp (seconds) when beat will occur
            bpm: Beats per minute to emit (calculated from captured IBI)
            intensity: Confidence/intensity to emit (captured confidence)

        Side effects:
            - Sends OSC message to beats_client
            - Prints to console

        Note: Must be called with self.state_lock held.
        """
        # Format message: [timestamp_ms, bpm, intensity]
        timestamp_ms = int(beat_timestamp * 1000.0)
        msg_data = [timestamp_ms, bpm, intensity]

        # Send OSC message
        self.beats_client.send_message(f"/beat/{self.ppg_id}", msg_data)

        # Calculate lead time for logging
        lead_time_ms = (beat_timestamp - time.time()) * 1000.0

        self.logger.info(f"PPG {self.ppg_id}: BEAT emitted - BPM={bpm:.1f}, intensity={intensity:.2f}, "
                         f"lead_time={lead_time_ms:.1f}ms")
