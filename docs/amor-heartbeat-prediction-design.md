# Heartbeat Prediction Model Design

## Overview

This document specifies the design of a model-based heartbeat predictor for the Amor
PPG sensor processor. The predictor maintains an internal rhythmic model for each
participant's heartbeat, using sensor threshold crossings as noisy observations to
keep the model synchronized.

## Motivation

The current threshold-crossing detector drops beats when sensor signal amplitude
varies. A model-based approach solves this by maintaining an internal metronome that
represents the participant's cardiac rhythm. The sensor observations nudge this
metronome to stay locked, but the metronome continues emitting beats even when
observations are missed.

From an artistic standpoint, the system presents an idealized rhythm to downstream
modules (audio, lighting) rather than raw sensor events. Participants naturally fade
into and out of the sonic mix as their signal quality varies.

## Architecture

Three-module design with clean separation of concerns:

**`amor/detector.py`** - Signal quality and threshold detection
- `ThresholdDetector` class: MAD-based state machine (WARMUP/ACTIVE/PAUSED)
- Monitors signal quality, detects threshold crossings
- Returns observations when crossings detected in ACTIVE state
- No beat emission—only signals when valid crossings occur

**`amor/predictor.py`** - Rhythm modeling and beat emission
- `HeartbeatPredictor` class: Phase/IBI/confidence tracking
- `observe_crossing(timestamp)`: Record threshold crossing observation
- `update(timestamp) -> Optional[beat_message]`: Advance phase, emit beats at phase ≥ 1.0
- Runs at 50Hz regardless of detector state
- Emits beats only when confidence > 0

**`amor/processor.py`** - Integration and OSC routing
- Instantiates `ThresholdDetector` and `HeartbeatPredictor` for each PPG sensor
- Routes detector observations to predictor during ACTIVE state
- Calls predictor `update()` every sample
- Sends beat messages to audio/lighting ports

Flow: Detector finds crossings → Processor gates observations → Predictor models rhythm → Processor emits beats

## Core Concepts

### Phase

The model tracks where it is within the current cardiac cycle as a value from 0.0 to
1.0, where 0.0 represents the moment immediately after a beat and 1.0 represents the
moment just before the next beat. Phase advances continuously based on the IBI
estimate. When phase reaches 1.0, the model emits a beat message and resets to 0.0.

### Inter-Beat Interval (IBI)

The IBI estimate is the expected number of milliseconds between consecutive beats.
This represents the model's current belief about the participant's tempo. The IBI is
derived from sensor observations but heavily smoothed to avoid jitter.

### Confidence

Confidence is a value from 0.0 to 1.0 that represents how much the model trusts its
rhythm estimate. High confidence means frequent observations confirm the model. Low
confidence means the model is coasting without recent observations or is still
initializing. Confidence maps directly to the intensity field in output messages,
creating natural fade-in and fade-out effects.

## Signal Quality Challenges

### Noise Floor Locking

PPG sensors at idle (no finger contact) produce stable noise around ADC mid-range with
small variations (MAD 17-28). This can trigger threshold crossings and cause the
predictor to lock on random noise, emitting phantom beats at ~60 BPM indefinitely.

**Solution**: Raise `MAD_MIN_QUALITY` to 40, rejecting signals with insufficient
variation. Real heartbeats have MAD ≥ 40 due to cardiac pulse amplitude. Idle sensors
transition to PAUSED state, preventing observation flow to predictor.

### Clipped Signals

PPG sensors can clip at 0 or 4095 (12-bit ADC rails) when contact pressure is high or
skin tone affects light absorption. Clipping produces high MAD values (300-600) but
represents valid heartbeats with rhythmic amplitude swings.

**Solution**: Disable `MAD_MAX_QUALITY` (set to None) to allow high MAD signals. Use
saturation detection instead to identify truly stuck sensors.

### Stuck Sensors

When sensors disconnect or fail, all samples may saturate at one rail (>80% at 0 or
4095). This differs from rhythmic clipping where peaks alternate with valleys.

**Solution**: `_check_saturation()` calculates the fraction of samples stuck at bottom
(≤10) or top (≥4085) rails. If either exceeds `SATURATION_THRESHOLD` (0.8), detector
transitions to PAUSED. Rhythmic clipping (e.g., 40% at top, 40% at bottom) yields
max(0.4, 0.4) = 0.4 < 0.8 → remains ACTIVE.

## Observation Outlier Rejection

### Death Spiral from Missed Beats

When detector misses several beats (user repositions finger, signal degrades), the next
observation arrives after a long interval. Predictor measures IBI from last observation
to current, producing values like 3860ms (5 missed beats). Exponential smoothing blends
this outlier into the estimate:

```
new_ibi = 0.9 × 740ms + 0.1 × 3860ms = 1052ms
```

This creates positive feedback: longer IBI → longer wait → even longer measured IBI →
BPM crashes (81 → 53 → 41 → 33 → 25).

**Solutions**:

1. **Hard limit**: `IBI_MAX_MS = 1333` (45 BPM minimum) prevents acceptance of extremely
   long intervals. Values >1333ms are rejected as out-of-range.

2. **Outlier factor**: `IBI_OUTLIER_FACTOR = 1.5` rejects observations where
   `observed_ibi > current_estimate × 1.5` or `< current_estimate / 1.5`. This prevents
   large jumps even within the hard limit range.

### Harmonic Locking

Without a realistic lower BPM bound, predictor can lock at harmonics of true rate
(e.g., 30 BPM = half of 60 BPM, 45 BPM = half of 90 BPM) when beats are missed. The
hard limit at 45 BPM prevents this by rejecting sub-harmonic intervals.

## Operational Modes

### Initialization

The model starts in initialization mode, collecting threshold crossings to establish
an initial IBI estimate. The first five observations provide four IBI measurements.
The initial IBI estimate is the median of these four values. During this phase, the
model emits beats when phase reaches 1.0, with confidence ramping by 0.2 per
observation (0.2, 0.4, 0.6, 0.8, 1.0). After five observations, the model transitions
to locked mode.

If processor enters PAUSED during initialization, predictor continues with partial
confidence and coasts. Recovery follows normal coasting rules (+0.2 per observation).

### Locked

In locked mode, the model emits beats based on phase progression while observations
keep it synchronized. Confidence remains at 1.0 as long as observations arrive
regularly. This is the normal operating state.

### Coasting

When observations stop arriving (no threshold crossings), the model enters coasting
mode. It continues emitting beats based on its last IBI estimate while confidence
decays linearly from 1.0 to 0.0 over 10 seconds. This allows the rhythm to fade out
gracefully when sensor signal is lost.

The processor also forces coasting when the detector resets (ESP32 reboot or message
gap detected), immediately beginning confidence decay instead of continuing with a
stale IBI estimate. This prevents ghost beats during detector WARMUP periods.

### Stopped

When confidence reaches 0.0, the model stops emitting beats and returns to
initialization mode. The next threshold crossing will begin a new initialization
sequence.

## Model Dynamics

### Autonomous Progression

The model advances phase continuously based on elapsed time and the current IBI
estimate. On each sample processed:

```
time_delta = current_time - last_update_time
phase_increment = time_delta / ibi_estimate
phase = phase + phase_increment
```

When phase exceeds 1.0, the model emits a beat message and decrements phase by 1.0
(carrying over any excess into the next cycle).

### Beat Emission

Predictor `update()` runs at 50Hz (every sample). When phase crosses 1.0 and
confidence > 0, a beat message is emitted. Timestamp is set to current time when
crossing detected (no interpolation). Message format: `[timestamp, bpm, intensity]`
where bpm = 60000 / ibi_estimate and intensity = confidence.

## Observation Integration

Threshold crossings from the processor are treated as noisy observations that update
the IBI estimate. Observations do not directly produce beat messages; only the model
emits beats when phase reaches 1.0. This keeps the model as the authoritative source
of rhythm.

### IBI and Phase Correction

When a threshold crossing is observed, two corrections occur:

**IBI measurement**: Time since last *observation* (not last beat emission):
```
observed_ibi = current_observation_time - last_observation_time
```

This prevents drift when model phase leads or lags actual sensor events. Using
`last_beat_time` would introduce positive feedback as phase error accumulates.

**IBI blending** (exponential smoothing):
```
new_ibi_estimate = (0.9 × current_estimate) + (0.1 × observed_ibi)
```

**Phase correction** (prevents drift even when IBI is accurate):
```
expected_phase = observed_ibi / current_ibi
phase_error = expected_phase - current_phase
clamped_phase_error = clamp(phase_error, -0.2, +0.2)  # Prevent large jumps
current_phase += 0.10 × clamped_phase_error
```

IBI blending tracks tempo changes over ~10 beats. Phase correction prevents beats
drifting early/late by nudging phase toward expected position based on observation
timing. Reduced weight (0.10) provides smooth synchronization without visible snapping.
Clamping to ±0.2 prevents large phase jumps from outlier observations.

### Observation Debouncing

To filter noise and prevent multiple crossings per cardiac cycle from corrupting the
IBI estimate, observations are debounced. A crossing is only accepted if it occurs at
least 0.7 × current_ibi_estimate after the last accepted observation. This threshold
scales with tempo and filters double-detections during signal transitions.

## Confidence System

### Initialization Ramp

Confidence increases by 0.2 per observation during initialization:
- Observation 1: 0.2
- Observation 2: 0.4
- Observation 3: 0.6
- Observation 4: 0.8
- Observation 5 and beyond: 1.0

This creates a natural fade-in as the participant's heartbeat enters the mix.

### Coasting Decay

When threshold crossings stop arriving, confidence decays linearly over 10 seconds.
At a typical heartbeat of 60-80 BPM, this corresponds to 10-13 beats fading out. The
decay rate per millisecond is:

```
decay_rate = 1.0 / 10000  # 0.0001 per millisecond
```

### Recovery Ramp

When processor transitions PAUSED → ACTIVE, observations resume. Confidence increases
by 0.2 per observation received while coasting (before reaching 0.0). The participant
fades back in smoothly. If confidence reaches 0.0, predictor stops emitting beats and
resets to initialization mode. Next observation begins new 5-beat initialization.

Beats emit only when confidence > 0. No minimum threshold—even 0.01 produces output
with very low intensity.

### Observation Frequency

No explicit variance checking is performed. Irregular rhythms are handled implicitly
through observation frequency. If crossings are erratic, confidence will fluctuate
naturally as the model enters and exits coasting mode repeatedly.

## Output Specification

### Message Format

Beat messages use the existing protocol:
- Address: `/beat/{ppg_id}` where ppg_id is 0-3
- Arguments: `[timestamp, bpm, intensity]`
  - timestamp: Unix time in seconds (float)
  - bpm: Beats per minute, derived as 60000 / ibi_estimate
  - intensity: Current confidence (0.0-1.0)

### Destination Ports

Beat messages are sent to:
- Port 8001: Audio engine and viewer
- Port 8002: Lighting controller

### Emission Timing

Beats are emitted with timestamp equal to current time. No lead time or future
prediction is implemented. Downstream modules receive beats as they occur according
to the model, and can choose to react immediately or schedule based on the timestamp.

## Configuration Parameters

All tunable parameters consolidated for easy adjustment:

```python
# Detector signal quality (amor/detector.py)
MAD_THRESHOLD_K = 4.5          # Threshold multiplier: median + k*MAD
MAD_MIN_QUALITY = 40           # Minimum MAD for valid signal (reject noise floor)
MAD_MAX_QUALITY = None         # Maximum MAD (None = disabled, allows clipping)
SATURATION_THRESHOLD = 0.8     # Reject if >80% samples at one rail (stuck sensor)
SATURATION_BOTTOM_RAIL = 10    # ADC values ≤ this count as bottom saturation
SATURATION_TOP_RAIL = 4085     # ADC values ≥ this count as top saturation
WARMUP_SAMPLES = 100           # Samples before ACTIVE (2s at 50Hz)
RECOVERY_TIME_S = 2.0          # Seconds of good signal to exit PAUSED

# Predictor IBI parameters (amor/predictor.py)
IBI_MIN_MS = 400               # Minimum IBI (150 BPM max)
IBI_MAX_MS = 1333              # Maximum IBI (45 BPM min, prevents harmonics)
IBI_BLEND_WEIGHT = 0.1         # Weight for new observation (0.1 = 10%)
IBI_OUTLIER_FACTOR = 1.5       # Reject if observed_ibi > factor × current

# Predictor phase parameters
PHASE_CORRECTION_WEIGHT = 0.10 # Weight for phase error correction (0.10 = 10%)
                               # Reduced from 0.15 to 0.10 to prevent visible beat snapping
PHASE_CORRECTION_MAX = 0.2     # Maximum phase correction per observation (prevents jumps)

# Predictor observation filtering
OBSERVATION_DEBOUNCE = 0.7     # Accept crossings ≥ 0.7 × IBI apart

# Predictor confidence parameters
CONFIDENCE_RAMP_PER_BEAT = 0.2 # Confidence increase per observation
COASTING_DURATION_MS = 10000   # Time from confidence 1.0 → 0.0 (10 seconds)
INIT_OBSERVATIONS = 5          # Observations needed for full confidence
CONFIDENCE_EMISSION_MIN = 0.0  # Minimum confidence to emit beats (0 = always if >0)

# Update frequency
UPDATE_RATE_HZ = 50            # Predictor update() calls per second
```

These parameters balance sensitivity, stability, and artistic experience. Key tuning
considerations:

- `MAD_MIN_QUALITY`: Must exceed idle sensor MAD (~26) but not reject weak heartbeats
- `SATURATION_THRESHOLD`: Must allow rhythmic clipping (e.g., 40% top + 40% bottom)
  but reject stuck sensors (90%+ at one rail)
- `IBI_OUTLIER_FACTOR`: 1.5 allows ±50% tempo variation between beats while rejecting
  missed-beat artifacts
- `PHASE_CORRECTION_WEIGHT`: Lower values (0.05-0.10) prevent visible beat snapping,
  higher values (0.15-0.20) provide tighter lock at cost of jitter

## Multi-Sensor Operation

The system processes four independent PPG sensors (ppg_id 0-3), each corresponding
to a different participant. Each sensor maintains its own model state with
independent phase, IBI, and confidence. There is no cross-sensor synchronization or
blending. This allows each participant's rhythm to evolve and fade independently in
the audio-visual mix.

## Testing and Validation

Key scenarios for validation:

1. **Idle sensor**: Should reject (MAD < 40), no ghost beats
2. **Clipped signal**: Should accept rhythmic clipping (MAD 300-600, saturation <80%)
3. **Stuck sensor**: Should reject (saturation >80%)
4. **Missed beats**: Should reject outlier IBIs, maintain stable BPM
5. **Finger removal**: Should coast to stop (confidence 1.0 → 0.0 over 10s)
6. **Initialization**: Should lock within 5 beats, fade in smoothly
