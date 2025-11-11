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

**IBI blending**:
```
new_ibi_estimate = (0.9 × current_estimate) + (0.1 × observed_ibi)
```

**Phase correction** (prevents drift):
```
phase_error = (observed_time - last_beat_time) / current_ibi - current_phase
current_phase += 0.15 × phase_error
```

IBI blending tracks tempo changes over ~10 beats. Phase correction prevents beats
drifting early/late even when IBI is accurate.

### Observation Debouncing

To filter noise and prevent multiple crossings per cardiac cycle from corrupting the
IBI estimate, observations are debounced. A crossing is only accepted if it occurs at
least 0.7 × current_ibi_estimate after the last accepted observation. This threshold
scales with tempo and may require tuning based on signal characteristics.

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
# Detector parameters (amor/detector.py)
MAD_THRESHOLD_K = 4.5          # Threshold multiplier: median + k*MAD
MAD_MIN_QUALITY = 10           # Minimum MAD for valid signal (ACTIVE state)
WARMUP_SAMPLES = 100           # Samples before ACTIVE (2s at 50Hz)
RECOVERY_TIME_S = 2.0          # Seconds of good signal to exit PAUSED

# Predictor IBI parameters (amor/predictor.py)
IBI_MIN_MS = 400               # Minimum IBI (150 BPM max)
IBI_MAX_MS = 10000             # Maximum IBI (6 BPM min)
IBI_BLEND_WEIGHT = 0.1         # Weight for new observation (0.1 = 10%)

# Predictor phase parameters
PHASE_CORRECTION_WEIGHT = 0.15 # Weight for phase error correction (0.15 = 15%)

# Predictor observation filtering
OBSERVATION_DEBOUNCE = 0.7     # Accept crossings ≥ 0.7 × IBI apart

# Predictor confidence parameters
CONFIDENCE_RAMP_PER_BEAT = 0.2 # Confidence increase per observation
COASTING_DURATION_MS = 10000   # Time from confidence 1.0 → 0.0 (10 seconds)
INIT_OBSERVATIONS = 5          # Observations needed for full confidence
CONFIDENCE_EMISSION_MIN = 0.0  # Minimum confidence to emit beats (0 = always emit if >0)

# Update frequency
UPDATE_RATE_HZ = 50            # Predictor update() calls per second
```

These parameters balance sensitivity, stability, and artistic experience. Adjust based
on testing with actual participants and signal quality observed in deployment.

## Multi-Sensor Operation

The system processes four independent PPG sensors (ppg_id 0-3), each corresponding
to a different participant. Each sensor maintains its own model state with
independent phase, IBI, and confidence. There is no cross-sensor synchronization or
blending. This allows each participant's rhythm to evolve and fade independently in
the audio-visual mix.
