#!/usr/bin/env python3
"""
Heartbeat Predictor - Model-Based Rhythm Tracking for PPG Sensors

Maintains an internal rhythmic model for each participant's heartbeat, using sensor
threshold crossings as noisy observations to keep the model synchronized. Emits beats
based on phase progression rather than raw sensor events, providing smooth fade-in
and fade-out as signal quality varies.

ARCHITECTURE:
- Phase-based rhythm model (0.0 to 1.0 within cardiac cycle)
- IBI estimation with exponential smoothing (0.9 × old + 0.1 × observed)
- Phase correction to prevent drift (0.15 × phase_error)
- Confidence system: initialization → locked → coasting → stopped
- Adaptive observation debouncing (≥ 0.7 × IBI)
- Beat emission when phase ≥ 1.0 and confidence > 0

USAGE:
    predictor = HeartbeatPredictor(ppg_id=0)

    # When threshold crossing detected:
    predictor.observe_crossing(timestamp_s=1.234)

    # Every sample (50Hz):
    beat = predictor.update(timestamp_s=1.254)
    if beat is not None:
        # Send beat message with timestamp, bpm, intensity (confidence)
        send_osc(beat)

Reference: Design document at docs/amor-heartbeat-prediction-design.md
"""

from dataclasses import dataclass
from typing import Optional
import time


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
COASTING_DURATION_MS = 10000   # Time from confidence 1.0 → 0.0 (10 seconds)
INIT_OBSERVATIONS = 5          # Observations needed for full confidence
CONFIDENCE_EMISSION_MIN = 0.0  # Minimum confidence to emit beats (0 = always emit if >0)

# Update frequency
UPDATE_RATE_HZ = 50            # Predictor update() calls per second

# Beat prediction timing
BEAT_PREDICTION_LOOKAHEAD_MS = 100  # Minimum lookahead for device compensation


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
        Locked: Regular observations maintain confidence at 1.0
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

    def __init__(self, ppg_id: int, verbose: bool = False) -> None:
        """Initialize predictor for a specific PPG sensor.

        Args:
            ppg_id: Sensor ID (0-3)
            verbose: Enable detailed logging
        """
        self.ppg_id = ppg_id
        self.verbose = verbose
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

        # Initialization state
        self.init_observations: list[float] = []

        # Beat emission tracking (prevent duplicates during prediction window)
        self.beat_emitted_this_cycle: bool = False

        # Observation rejection metrics (for debugging)
        self.debounced_count: int = 0
        self.out_of_range_count: int = 0
        self.outlier_count: int = 0

    def observe_crossing(self, timestamp_s: float) -> None:
        """Record threshold crossing observation from detector.

        Updates IBI estimate and phase based on observation timing. Applies
        debouncing to filter noise and prevent multiple observations per cycle.

        Args:
            timestamp_s: Observation timestamp in seconds (ESP32 time)

        Behavior by mode:
            Stopped: Begins initialization, records first observation
            Initialization: Accumulates observations until INIT_OBSERVATIONS reached
            Locked/Coasting: Updates IBI and phase, resets coasting decay
        """
        # Debounce observations using current IBI estimate
        if self.ibi_estimate_ms is not None and self.last_observation_time is not None:
            time_since_last = (timestamp_s - self.last_observation_time) * 1000.0  # ms
            min_interval = OBSERVATION_DEBOUNCE * self.ibi_estimate_ms

            if time_since_last < min_interval:
                self.debounced_count += 1
                if self.verbose:
                    print(f"PPG {self.ppg_id}: Observation debounced - "
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

    def update(self, timestamp_s: float) -> Optional[BeatMessage]:
        """Advance phase and emit beat if phase crosses 1.0.

        Called at 50Hz regardless of observations. Advances phase based on
        elapsed time and IBI estimate. Emits beat when phase ≥ 1.0 and
        confidence > 0. Updates confidence decay during coasting.

        Args:
            timestamp_s: Current timestamp in seconds (ESP32 time)

        Returns:
            BeatMessage if beat emitted, None otherwise
        """
        # First update - just record timestamp
        if self.last_update_time is None:
            self.last_update_time = timestamp_s
            return None

        # Calculate time delta
        time_delta_s = timestamp_s - self.last_update_time
        self.last_update_time = timestamp_s

        # Only advance phase if we have an IBI estimate
        if self.ibi_estimate_ms is None:
            return None

        # Advance phase
        time_delta_ms = time_delta_s * 1000.0
        phase_increment = time_delta_ms / self.ibi_estimate_ms
        self.phase += phase_increment

        # Update confidence decay if coasting
        if self.mode == self.MODE_COASTING:
            self._update_coasting_decay(time_delta_ms)

        # Check for beat emission - predict future beat with dynamic threshold
        beat_message = None

        # Calculate dynamic threshold for constant lookahead time
        lookahead_threshold = 1.0 - (BEAT_PREDICTION_LOOKAHEAD_MS / self.ibi_estimate_ms)
        lookahead_threshold = max(0.0, lookahead_threshold)  # Clamp to prevent negative

        # Emit beat when phase crosses threshold (before reaching 1.0)
        if (self.phase >= lookahead_threshold and
            not self.beat_emitted_this_cycle and
            self.confidence > CONFIDENCE_EMISSION_MIN):

            # Calculate future timestamp when phase will reach 1.0
            phase_remaining = max(0.0, 1.0 - self.phase)
            time_until_beat_ms = phase_remaining * self.ibi_estimate_ms
            future_timestamp = timestamp_s + (time_until_beat_ms / 1000.0)

            beat_message = self._emit_beat(future_timestamp)
            self.beat_emitted_this_cycle = True

        # Reset duplicate flag when phase wraps past 1.0
        if self.phase >= 1.0:
            self.phase -= 1.0
            self.last_beat_time = timestamp_s
            self.beat_emitted_this_cycle = False

        return beat_message

    def _begin_initialization(self, timestamp_s: float) -> None:
        """Begin initialization mode with first observation.

        Args:
            timestamp_s: First observation timestamp (seconds)
        """
        self.mode = self.MODE_INITIALIZATION
        self.init_observations = [timestamp_s]
        self.confidence = CONFIDENCE_RAMP_PER_BEAT  # 0.2 after first observation
        self.phase = 0.0

        print(f"PPG {self.ppg_id}: Predictor initialization started")

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
            self.last_beat_time = timestamp_s

            # Transition to locked mode
            self.mode = self.MODE_LOCKED
            self.confidence = 1.0

            print(f"PPG {self.ppg_id}: Predictor locked - IBI={self.ibi_estimate_ms:.0f}ms, "
                  f"BPM={60000.0 / self.ibi_estimate_ms:.1f}")

        else:
            if self.verbose:
                print(f"PPG {self.ppg_id}: Init observation {len(self.init_observations)}/{INIT_OBSERVATIONS}, "
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
            print(f"PPG {self.ppg_id}: Observation received but no IBI/observation baseline, ignoring")
            return

        # Calculate observed IBI (time since last observation)
        observed_ibi_ms = (timestamp_s - self.last_observation_time) * 1000.0

        # Validate observed IBI - basic range check
        if observed_ibi_ms < IBI_MIN_MS or observed_ibi_ms > IBI_MAX_MS:
            self.out_of_range_count += 1
            if self.verbose:
                print(f"PPG {self.ppg_id}: Observation rejected - "
                      f"IBI {observed_ibi_ms:.0f}ms out of range [{IBI_MIN_MS}, {IBI_MAX_MS}]")
            return

        # Outlier rejection - prevent death spiral from missed beats
        ibi_min_bound = self.ibi_estimate_ms / IBI_OUTLIER_FACTOR
        ibi_max_bound = self.ibi_estimate_ms * IBI_OUTLIER_FACTOR
        if observed_ibi_ms < ibi_min_bound or observed_ibi_ms > ibi_max_bound:
            self.outlier_count += 1
            if self.verbose:
                print(f"PPG {self.ppg_id}: Observation rejected - "
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

        if self.verbose:
            print(f"PPG {self.ppg_id}: Observation processed - "
                  f"IBI {old_ibi:.0f}→{self.ibi_estimate_ms:.0f}ms, "
                  f"phase correction {clamped_phase_error:+.3f}" +
                  (f" (clamped from {phase_error:+.3f})" if abs(phase_error) > PHASE_CORRECTION_MAX else ""))

        # Update confidence and mode
        if self.mode == self.MODE_COASTING:
            # Transition back to locked
            self.mode = self.MODE_LOCKED
            # Ramp confidence back up (0.2 per observation while recovering)
            self.confidence = min(1.0, self.confidence + CONFIDENCE_RAMP_PER_BEAT)
            print(f"PPG {self.ppg_id}: Coasting → Locked, confidence={self.confidence:.1f}")
        else:
            # Maintain full confidence in locked mode
            self.confidence = 1.0

    def _update_coasting_decay(self, time_delta_ms: float) -> None:
        """Update confidence decay during coasting mode.

        Decays confidence linearly over COASTING_DURATION_MS (10 seconds).
        Transitions to stopped mode when confidence reaches 0.

        Args:
            time_delta_ms: Elapsed time since last update (milliseconds)
        """
        decay_rate = 1.0 / COASTING_DURATION_MS  # Per millisecond
        decay_amount = decay_rate * time_delta_ms

        self.confidence = max(0.0, self.confidence - decay_amount)

        if self.confidence <= 0.0:
            # Transition to stopped mode
            self._print_rejection_metrics(reset=True)
            self.mode = self.MODE_STOPPED
            self.ibi_estimate_ms = None
            self.phase = 0.0
            self.init_observations = []

            print(f"PPG {self.ppg_id}: Coasting → Stopped (confidence depleted)")

    def _emit_beat(self, timestamp_s: float) -> BeatMessage:
        """Emit beat message with predicted timestamp.

        Args:
            timestamp_s: Predicted Unix timestamp (seconds) when beat will occur

        Returns:
            BeatMessage with future timestamp, BPM, and intensity (confidence)
        """
        if self.ibi_estimate_ms is None:
            # Shouldn't happen, but handle gracefully
            raise ValueError("Cannot emit beat without IBI estimate")

        bpm = 60000.0 / self.ibi_estimate_ms

        print(f"PPG {self.ppg_id}: BEAT emitted - BPM={bpm:.1f}, intensity={self.confidence:.2f}")

        return BeatMessage(
            timestamp=timestamp_s,  # Use provided future timestamp
            bpm=bpm,
            intensity=self.confidence
        )

    def enter_coasting(self) -> None:
        """Manually enter coasting mode.

        Called by processor when detector enters PAUSED state (signal quality too low).
        Begins confidence decay countdown.

        Can transition from LOCKED or INITIALIZATION modes:
        - LOCKED → COASTING: Normal signal loss during steady operation
        - INITIALIZATION → COASTING: Signal lost during startup (partial confidence continues)
        """
        if self.mode == self.MODE_LOCKED:
            self.mode = self.MODE_COASTING
            print(f"PPG {self.ppg_id}: Predictor Locked → Coasting")
            self._print_rejection_metrics(reset=True)
        elif self.mode == self.MODE_INITIALIZATION and self.ibi_estimate_ms is not None:
            # During initialization, if we have partial IBI estimate, enter coasting
            # This allows partial confidence beats to fade out gracefully
            self.mode = self.MODE_COASTING
            print(f"PPG {self.ppg_id}: Predictor Initialization → Coasting (partial confidence)")
            self._print_rejection_metrics(reset=True)

    def _print_rejection_metrics(self, reset: bool = False) -> None:
        """Print observation rejection metrics for debugging.

        Args:
            reset: If True, reset counters to zero after printing
        """
        total = self.debounced_count + self.out_of_range_count + self.outlier_count
        if total > 0:
            print(f"PPG {self.ppg_id}: Rejections - "
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
