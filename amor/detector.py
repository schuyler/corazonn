#!/usr/bin/env python3
"""
Threshold Detector - Signal Quality and Crossing Detection for PPG Sensors

Manages state machine for signal quality monitoring, detects threshold crossings,
and returns observations when valid crossings occur in ACTIVE state. Does NOT emit
beats—only signals when threshold crossings are detected.

ARCHITECTURE:
- State machine: WARMUP → ACTIVE → PAUSED (with recovery)
- MAD-based adaptive threshold calculation
- Upward crossing detection (previous < threshold AND current >= threshold)
- Observation debouncing (minimum 400ms between observations)
- Self-contained ESP32 reset and message gap handling

USAGE:
    detector = ThresholdDetector(ppg_id=0)
    observation = detector.process_sample(value=2000, timestamp_ms=1000)
    if observation is not None:
        # Threshold crossing detected in ACTIVE state
        print(f"Crossing at {observation.timestamp_ms}ms")

Reference: Design document at docs/amor-heartbeat-prediction-design.md
"""

from dataclasses import dataclass
from collections import deque
from typing import Optional
import numpy as np


# Configuration parameters
MAD_THRESHOLD_K = 4.5          # Threshold multiplier: median + k*MAD
MAD_MIN_QUALITY = 40           # Minimum MAD for valid signal (reject noise floor)
MAD_MAX_QUALITY = None         # Maximum MAD for valid signal (None = disabled, allows clipping)
SATURATION_THRESHOLD = 0.8     # Reject if >80% samples at one rail (stuck sensor)
SATURATION_BOTTOM_RAIL = 10    # ADC values ≤ this count as bottom saturation
SATURATION_TOP_RAIL = 4085     # ADC values ≥ this count as top saturation
WARMUP_SAMPLES = 100           # Samples before ACTIVE (2s at 50Hz)
THRESHOLD_WINDOW = 100         # Number of recent samples for threshold calculation
RECOVERY_TIME_S = 2.0          # Seconds of good signal to exit PAUSED
OBSERVATION_MIN_INTERVAL_MS = 400  # Minimum time between observations (debouncing)
MESSAGE_GAP_THRESHOLD_S = 1.0  # Message gap that triggers WARMUP reset
REBOOT_DETECTION_THRESHOLD_S = 3.0  # Backward jump > this indicates ESP32 reboot


@dataclass
class ThresholdCrossing:
    """Observation of a threshold crossing event.

    Returned by ThresholdDetector when upward crossing detected in ACTIVE state.
    Provides all information needed for downstream beat detection and debugging.

    Attributes:
        timestamp_ms (int): ESP32 timestamp when crossing occurred
        sample_value (int): PPG sample value at crossing (0-4095)
        threshold (float): Calculated threshold that was crossed
        mad (float): Signal quality metric (Median Absolute Deviation)
    """
    timestamp_ms: int
    sample_value: int
    threshold: float
    mad: float


class ThresholdDetector:
    """Threshold-based signal quality detector for PPG sensors.

    Manages state machine for signal quality monitoring, detects threshold
    crossings, and returns observations when valid crossings occur in ACTIVE state.
    Does NOT emit beats—only signals when threshold crossings are detected.

    Handles ESP32 resets and message gaps internally - processor doesn't need to
    coordinate state resets.

    State Transitions:
        WARMUP -> ACTIVE: After WARMUP_SAMPLES samples
        ACTIVE -> PAUSED: When MAD < MAD_MIN_QUALITY (noise floor) or saturation > SATURATION_THRESHOLD (stuck sensor)
        PAUSED -> ACTIVE: After RECOVERY_TIME_S of valid signal (MAD >= MAD_MIN_QUALITY and saturation OK)
        Any state -> WARMUP: When message gap > MESSAGE_GAP_THRESHOLD_S or ESP32 reboot

    Attributes:
        ppg_id (int): Sensor ID (0-3)
        state (str): Current state (STATE_WARMUP, STATE_ACTIVE, STATE_PAUSED)
        samples (deque): Rolling buffer of last THRESHOLD_WINDOW samples
        previous_sample (float): Previous sample for crossing detection
        last_message_timestamp (float): Timestamp of last received sample (seconds)
        last_observation_timestamp_ms (int): Timestamp of last observation (for debouncing)
        noise_start_time (float): When sensor entered PAUSED state
        resume_threshold_met_time (float): When recovery condition first met
    """

    # States
    STATE_WARMUP = "warmup"
    STATE_ACTIVE = "active"
    STATE_PAUSED = "paused"

    def __init__(self, ppg_id: int, verbose: bool = False) -> None:
        """Initialize detector for a specific PPG sensor.

        Args:
            ppg_id: Sensor ID (0-3)
            verbose: Enable per-sample debug logging
        """
        self.ppg_id = ppg_id
        self.state = self.STATE_WARMUP
        self.verbose = verbose

        # Sample buffer: only keep THRESHOLD_WINDOW samples for MAD calculation
        self.samples: deque = deque(maxlen=THRESHOLD_WINDOW)

        # Crossing detection state
        self.previous_sample: Optional[float] = None

        # Timestamp tracking
        self.last_message_timestamp: Optional[float] = None  # For gap/reboot detection
        self.last_observation_timestamp_ms: Optional[int] = None  # For debouncing

        # State machine timing
        self.noise_start_time: Optional[float] = None  # When entered PAUSED
        self.resume_threshold_met_time: Optional[float] = None  # When recovery started

        # Reset notification flag for processor coordination
        self._was_reset: bool = False

    def process_sample(self, value: int, timestamp_ms: int) -> Optional[ThresholdCrossing]:
        """Process a single PPG sample through the state machine.

        Manages state transitions, monitors signal quality, and detects threshold
        crossings. Handles out-of-order samples, ESP32 resets, and connection gaps
        internally.

        Args:
            value: PPG ADC sample (0-4095 from ESP32)
            timestamp_ms: Sample timestamp in milliseconds (ESP32 time)

        Returns:
            ThresholdCrossing: If upward crossing detected in ACTIVE state
            None: If no crossing detected OR not in ACTIVE state

        Note: Caller should call this for every sample regardless of return value,
        as detector needs all samples for state management.
        """
        timestamp_s = timestamp_ms / 1000.0

        # Handle timestamp discontinuities (ESP32 reset, gaps, out-of-order)
        if self.last_message_timestamp is not None:
            # Backward jump detection
            if timestamp_s < self.last_message_timestamp:
                backward_jump = self.last_message_timestamp - timestamp_s
                if backward_jump > REBOOT_DETECTION_THRESHOLD_S:
                    # Large backward jump = ESP32 rebooted
                    print(f"WARNING: ESP32 reboot detected (PPG {self.ppg_id}): "
                          f"timestamp jumped backward {backward_jump:.1f}s, resetting to warmup")
                    self._reset_internal()
                    # Continue processing this sample as new session
                else:
                    # Small backward jump = out-of-order packet, drop it
                    print(f"WARNING: Out-of-order sample dropped (PPG {self.ppg_id}): "
                          f"{timestamp_s:.3f}s < {self.last_message_timestamp:.3f}s")
                    # Reset debouncing to prevent negative intervals on next valid sample
                    self.last_observation_timestamp_ms = None
                    return None

            # Forward gap detection
            gap_s = timestamp_s - self.last_message_timestamp
            if gap_s > MESSAGE_GAP_THRESHOLD_S:
                print(f"WARNING: Message gap detected (PPG {self.ppg_id}): {gap_s:.3f}s, "
                      f"resetting to warmup")
                self._reset_internal()

        # Update timestamp and add sample to buffer
        self.last_message_timestamp = timestamp_s
        self.samples.append(value)

        # Verbose logging: show per-sample stats
        if self.verbose:
            self._log_sample_debug(value, timestamp_ms)

        # State machine and crossing detection
        return self._update_state_and_detect(value, timestamp_ms, timestamp_s)

    def _update_state_and_detect(self, value: int, timestamp_ms: int,
                                   timestamp_s: float) -> Optional[ThresholdCrossing]:
        """Update state machine and detect crossings.

        Args:
            value: Current sample value
            timestamp_ms: Timestamp in milliseconds
            timestamp_s: Timestamp in seconds

        Returns:
            ThresholdCrossing if detected in ACTIVE state, None otherwise
        """
        # State machine handling
        if self.state == self.STATE_WARMUP:
            if len(self.samples) >= WARMUP_SAMPLES:
                print(f"PPG {self.ppg_id}: State transition WARMUP → ACTIVE")
                self.state = self.STATE_ACTIVE

        elif self.state == self.STATE_ACTIVE:
            # Check signal quality - pause if MAD too low or sensor saturated
            if len(self.samples) >= THRESHOLD_WINDOW:
                median, mad, _ = self._calculate_mad_threshold()

                if mad < MAD_MIN_QUALITY:
                    # Signal too flat (noise floor)
                    print(f"PPG {self.ppg_id}: State transition ACTIVE → PAUSED "
                          f"(MAD {mad:.1f} < {MAD_MIN_QUALITY})")
                    self.state = self.STATE_PAUSED
                    self.noise_start_time = timestamp_s
                    return None
                elif MAD_MAX_QUALITY is not None and mad > MAD_MAX_QUALITY:
                    # Signal too noisy (only if MAD_MAX_QUALITY enabled)
                    print(f"PPG {self.ppg_id}: State transition ACTIVE → PAUSED "
                          f"(MAD {mad:.1f} > {MAD_MAX_QUALITY})")
                    self.state = self.STATE_PAUSED
                    self.noise_start_time = timestamp_s
                    return None

                # Check for sensor saturation (stuck at one rail)
                saturation_ratio = self._check_saturation()
                if saturation_ratio > SATURATION_THRESHOLD:
                    print(f"PPG {self.ppg_id}: State transition ACTIVE → PAUSED "
                          f"(saturation {saturation_ratio:.1%} > {SATURATION_THRESHOLD:.1%})")
                    self.state = self.STATE_PAUSED
                    self.noise_start_time = timestamp_s
                    return None

            # Detect crossing in ACTIVE state
            return self._detect_crossing(value, timestamp_ms)

        elif self.state == self.STATE_PAUSED:
            # Check for resume condition - MAD must be valid and sensor not saturated
            if len(self.samples) >= THRESHOLD_WINDOW:
                median, mad, _ = self._calculate_mad_threshold()
                saturation_ratio = self._check_saturation()

                # Check MAD bounds
                mad_ok = mad >= MAD_MIN_QUALITY
                if MAD_MAX_QUALITY is not None:
                    mad_ok = mad_ok and mad <= MAD_MAX_QUALITY

                # Check saturation
                saturation_ok = saturation_ratio <= SATURATION_THRESHOLD

                if mad_ok and saturation_ok:
                    # Resume condition met - signal quality in valid range
                    if self.resume_threshold_met_time is None:
                        self.resume_threshold_met_time = timestamp_s
                    elif timestamp_s - self.resume_threshold_met_time >= RECOVERY_TIME_S:
                        # Recovery period complete
                        print(f"PPG {self.ppg_id}: State transition PAUSED → ACTIVE "
                              f"(2s of valid signal, MAD={mad:.1f})")
                        self.state = self.STATE_ACTIVE
                        self.resume_threshold_met_time = None
                else:
                    # Condition not met, reset timer
                    self.resume_threshold_met_time = None

        return None

    def _detect_crossing(self, value: int, timestamp_ms: int) -> Optional[ThresholdCrossing]:
        """Detect upward threshold crossing.

        Uses MAD-based threshold with upward crossing detection:
        previous < threshold AND current >= threshold

        Applies debouncing to prevent multiple observations per cardiac cycle.

        Args:
            value: Current sample value
            timestamp_ms: Timestamp in milliseconds

        Returns:
            ThresholdCrossing if upward crossing detected and debouncing passed, None otherwise
        """
        if len(self.samples) < THRESHOLD_WINDOW:
            return None

        # Calculate MAD-based threshold
        median, mad, threshold = self._calculate_mad_threshold()

        # Check for upward crossing
        crossing_detected = False
        if self.previous_sample is not None:
            if self.previous_sample < threshold and value >= threshold:
                crossing_detected = True
                print(f"PPG {self.ppg_id}: Threshold crossing detected - "
                      f"sample={value:.0f}, threshold={threshold:.0f}, "
                      f"median={median:.0f}, MAD={mad:.1f}")

        self.previous_sample = value

        if not crossing_detected:
            return None

        # Apply debouncing
        if self.last_observation_timestamp_ms is not None:
            time_since_last = timestamp_ms - self.last_observation_timestamp_ms
            if time_since_last < OBSERVATION_MIN_INTERVAL_MS:
                print(f"PPG {self.ppg_id}: Crossing debounced - "
                      f"only {time_since_last:.0f}ms since last observation")
                return None

        # Record observation
        self.last_observation_timestamp_ms = timestamp_ms

        # Return observation
        return ThresholdCrossing(
            timestamp_ms=timestamp_ms,
            sample_value=value,
            threshold=threshold,
            mad=mad
        )

    def _log_sample_debug(self, value: int, timestamp_ms: int) -> None:
        """Log per-sample debug information.

        Shows sample value, state, MAD, threshold, and detection status.
        Called only when verbose=True.

        Args:
            value: Current sample value
            timestamp_ms: Sample timestamp in milliseconds
        """
        # Build debug output
        state_str = self.state.upper()

        # Calculate MAD/threshold if we have enough samples
        if len(self.samples) >= THRESHOLD_WINDOW:
            median, mad, threshold = self._calculate_mad_threshold()

            # Check if this sample would cross threshold
            crossing = ""
            if self.previous_sample is not None:
                if self.previous_sample < threshold and value >= threshold:
                    crossing = "[CROSSING]"
                else:
                    crossing = "[no crossing]"

            # Check MAD quality bounds and saturation
            quality = ""
            if mad < MAD_MIN_QUALITY:
                quality = f" (MAD too low < {MAD_MIN_QUALITY})"
            elif MAD_MAX_QUALITY is not None and mad > MAD_MAX_QUALITY:
                quality = f" (MAD too high > {MAD_MAX_QUALITY})"

            saturation_ratio = self._check_saturation()
            if saturation_ratio > SATURATION_THRESHOLD:
                quality += f" (saturated {saturation_ratio:.1%} > {SATURATION_THRESHOLD:.1%})"
            elif saturation_ratio > 0.5:  # Show high saturation even if below threshold
                quality += f" (saturation {saturation_ratio:.1%})"

            print(f"PPG {self.ppg_id}: sample={value:4d}, median={median:6.1f}, "
                  f"MAD={mad:5.1f}, threshold={threshold:6.1f}, "
                  f"state={state_str:6s} {crossing}{quality}")
        else:
            # Not enough samples yet
            samples_needed = THRESHOLD_WINDOW - len(self.samples)
            print(f"PPG {self.ppg_id}: sample={value:4d}, state={state_str:6s} "
                  f"(need {samples_needed} more samples for MAD)")

    def _calculate_mad_threshold(self) -> tuple[float, float, float]:
        """Calculate MAD-based threshold from recent samples.

        MAD (Median Absolute Deviation) is robust to outliers (50% breakdown point),
        making it immune to transient spikes and sensor saturation.

        Returns:
            Tuple of (median, mad, threshold) where:
                median: Median of recent samples
                mad: Median Absolute Deviation
                threshold: median + MAD_THRESHOLD_K * mad
        """
        # samples deque has maxlen=THRESHOLD_WINDOW, so no need to slice
        sample_array = np.array(list(self.samples))
        median = np.median(sample_array)
        mad = np.median(np.abs(sample_array - median))
        threshold = median + MAD_THRESHOLD_K * mad
        return median, mad, threshold

    def _check_saturation(self) -> float:
        """Check if sensor is saturated (stuck at one rail).

        Detects sensors stuck at min (≤SATURATION_BOTTOM_RAIL) or max
        (≥SATURATION_TOP_RAIL) values. Rhythmic clipping (alternating between
        rails) is OK, but stuck sensors indicate disconnection or malfunction.

        Returns:
            Saturation ratio (0.0-1.0): Fraction of samples at min OR max rail
            (whichever is higher). Returns 0.0 if not enough samples.

        Examples:
            - All samples at 4095: returns 1.0
            - All samples at 0: returns 1.0
            - 40% at 4095, 40% at 0, 20% middle: returns 0.4 (max of the two)
            - Evenly distributed: returns ~0.0
        """
        if len(self.samples) < THRESHOLD_WINDOW:
            return 0.0

        sample_array = np.array(list(self.samples))

        # Count samples stuck at each rail
        bottom_saturated = np.sum(sample_array <= SATURATION_BOTTOM_RAIL)
        top_saturated = np.sum(sample_array >= SATURATION_TOP_RAIL)

        # Return the worse of the two (stuck at one rail)
        bottom_ratio = bottom_saturated / len(self.samples)
        top_ratio = top_saturated / len(self.samples)

        return max(bottom_ratio, top_ratio)

    def _reset_internal(self) -> None:
        """Reset detector to initial WARMUP state.

        Called internally when ESP32 reboot or message gap detected.
        Clears all accumulated state and starts fresh warmup cycle.
        Sets reset flag so processor can coordinate its beat state.
        """
        self.state = self.STATE_WARMUP
        self.samples.clear()
        self.previous_sample = None
        self.last_observation_timestamp_ms = None
        self.noise_start_time = None
        self.resume_threshold_met_time = None
        self._was_reset = True  # Signal reset to processor
        # Keep last_message_timestamp to detect next discontinuity

    def was_reset(self) -> bool:
        """Check if detector was reset since last check.

        Returns:
            True if detector was reset (ESP32 reboot or message gap), False otherwise

        Note: This is a one-shot flag that clears after being read.
        Call clear_reset_flag() explicitly if you want to preserve it.
        """
        return self._was_reset

    def clear_reset_flag(self) -> None:
        """Clear the reset notification flag.

        Call after handling the reset event in processor to prevent
        repeated reset handling.
        """
        self._was_reset = False

    def get_state(self) -> str:
        """Get current detector state for monitoring/debugging.

        Returns:
            Current state: "warmup", "active", or "paused"

        Note: For observability only. Caller should not make control-flow
        decisions based on state.
        """
        return self.state
