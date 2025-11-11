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
an initial IBI estimate. During this phase, the model emits beats at detected
crossings with ramping confidence (0.2, 0.4, 0.6, 0.8, 1.0 over the first five
beats). After five observations, the model transitions to locked mode.

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

Beat messages are emitted when phase crosses 1.0. The message format matches the
current protocol: `[timestamp, bpm, intensity]` where timestamp is the current time
(not future-predicted), bpm is derived from the IBI estimate, and intensity equals
confidence.

## Observation Integration

Threshold crossings are treated as noisy observations that update the model state.
Two types of corrections occur: IBI correction and phase correction.

### IBI Correction

When a threshold crossing is observed, the time since the last crossing provides an
observed IBI. This is blended with the current IBI estimate using a low weight on
the new observation (approximately 10%). This slow adaptation smooths out sensor
noise and physiological variance while allowing the model to track gradual tempo
changes over multiple beats.

The blending formula is:

```
new_ibi_estimate = (0.9 × current_estimate) + (0.1 × observed_ibi)
```

This means the model takes roughly 10 beats to fully adapt to a tempo change.

### Phase Correction

When a crossing occurs at an unexpected phase, it indicates the model's timing has
drifted from reality. Rather than jumping phase immediately, the error is
accumulated and applied gradually over the next 2-3 beats. This prevents artifacts
in the beat stream while ensuring the model stays locked to the actual heartbeat.

If a crossing happens early (phase < 0.8), the model is running slow. If it happens
late (phase > 1.2 after wrapping), the model is running fast. The phase error is
stored and used to adjust the phase increment slightly over subsequent cycles until
the error is corrected.

## Confidence System

### Initialization Ramp

During the first five beats, confidence ramps linearly:
- Beat 1: 0.2
- Beat 2: 0.4
- Beat 3: 0.6
- Beat 4: 0.8
- Beat 5 and beyond: 1.0

This creates a natural fade-in as the participant's heartbeat enters the mix.

### Coasting Decay

When threshold crossings stop arriving, confidence decays linearly over 10 seconds.
At a typical heartbeat of 60-80 BPM, this corresponds to 10-13 beats fading out. The
decay rate per millisecond is:

```
decay_rate = 1.0 / 10000  # 0.0001 per millisecond
```

### Recovery Ramp

If observations resume during coasting (before confidence reaches 0.0), confidence
ramps back up linearly at the same rate it would during initialization. There are no
jumps - the participant fades back in smoothly. If coasting reaches confidence 0.0,
the model stops and the next observation triggers a full re-initialization.

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

### IBI Bounds

Minimum IBI: 400ms (150 BPM maximum)
Maximum IBI: 10000ms (6 BPM minimum)

These bounds are carried over from the current implementation and provide reasonable
limits for human heart rates across various activity levels.

### Coasting Duration

10 seconds from confidence 1.0 to 0.0

### Initialization Length

5 beats to reach full confidence

### Adaptation Rates

IBI blending weight: 0.1 (10% new observation, 90% current estimate)
Phase correction horizon: 2-3 beats

### Emission Threshold

Stop emitting at confidence 0.0

## Multi-Sensor Operation

The system processes four independent PPG sensors (ppg_id 0-3), each corresponding
to a different participant. Each sensor maintains its own model state with
independent phase, IBI, and confidence. There is no cross-sensor synchronization or
blending. This allows each participant's rhythm to evolve and fade independently in
the audio-visual mix.
