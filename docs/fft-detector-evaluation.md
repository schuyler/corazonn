# FFT-Based Beat Detection Evaluation

## Executive Summary

**Recommendation: Do not replace the current MAD-based threshold detector with FFT.**

The current time-domain approach is better suited to corazonn's requirements for real-time beat detection with low latency, computational efficiency, and robust handling of signal quality variations. FFT-based methods offer no significant advantages for this use case and introduce substantial disadvantages.

---

## Current Detector Architecture

The existing `amor/detector.py` implements a **Median Absolute Deviation (MAD) based adaptive threshold** detector with upward crossing detection.

### Key Characteristics:
- **Algorithm**: Time-domain threshold crossing with MAD-based adaptive threshold
- **Latency**: Near-zero (processes each sample as it arrives at 50Hz)
- **Computational Cost**: O(1) per sample (after 2-second warmup)
- **Memory**: 100-sample rolling buffer (~400 bytes per sensor)
- **State Machine**: WARMUP → ACTIVE → PAUSED with automatic quality monitoring
- **Output**: Timestamp-precise threshold crossings (no interpolation needed)

### Strengths:
1. **Robustness**: MAD provides 50% breakdown point against outliers and sensor saturation
2. **Real-time**: Each sample processed independently with no windowing delay
3. **Minimal Resources**: Single-pass algorithm suitable for embedded systems
4. **Beat Timing Precision**: Exact timestamps at threshold crossing (±20ms at 50Hz sampling)
5. **Signal Quality Awareness**: Automatic PAUSED state when MAD < 10

---

## FFT-Based Approach

FFT methods estimate heart rate by transforming PPG signals into the frequency domain and identifying the dominant frequency peak in the cardiac range (0.5-4 Hz, or 30-240 BPM).

### Typical Implementation:
```
1. Collect N samples (window)
2. Apply bandpass filter (0.5-4 Hz)
3. Apply window function (Hann/Hamming) to reduce spectral leakage
4. Compute FFT
5. Find peak frequency in cardiac range
6. Convert to BPM: peak_freq × 60
```

### FFT Requirements:
- **Window Size**: Minimum 256-512 samples for acceptable frequency resolution
  - At 50Hz: 5.1-10.2 second windows
  - Frequency resolution: 50Hz/256 ≈ 0.195 Hz (11.7 BPM bins)
- **Overlap**: Typically 50% overlap for smoother tracking
  - Effective update rate: every 2.5-5 seconds
- **Computation**: O(N log N) per window
  - 256-point FFT: ~2048 operations
  - 512-point FFT: ~4608 operations
- **Latency**: Window duration + computation time (5-10+ seconds total)

---

## Comparative Analysis

| Aspect | Current MAD Detector | FFT-Based Detection |
|--------|---------------------|---------------------|
| **Latency** | ~20ms (1 sample) | 5-10+ seconds (window + overlap) |
| **Beat Timing** | Precise (threshold crossing timestamp) | Averaged over window (no individual beat timestamps) |
| **Computational Cost** | O(1) per sample | O(N log N) every window |
| **Memory Usage** | 400 bytes per sensor | 2-4KB+ per sensor (FFT buffers) |
| **Frequency Resolution** | N/A | ~12 BPM bins (insufficient for variability) |
| **Signal Quality Response** | Immediate (MAD < 10 → PAUSED) | Delayed by window duration |
| **Arrhythmia Handling** | Good (temporal beat-by-beat) | Poor (averaged over window) |
| **Motion Artifacts** | MAD-resistant, explicit PAUSED state | Frequency overlap (3.5-7.8 Hz) corrupts HR estimation |
| **Real-time Suitability** | Excellent | Poor |
| **Integration with Predictor** | Direct observation timestamps | Requires rate-to-beat conversion heuristics |

---

## Detailed Evaluation

### 1. Latency and Real-Time Performance

**Current System:**
- Processes samples as they arrive (50Hz)
- Threshold crossing detected within 20ms
- Predictor receives immediate observation for phase correction

**FFT System:**
- Requires 5-10 second windows for frequency resolution
- Beat rate estimate lags actual rhythm by window duration
- Predictor would receive delayed, averaged rate estimates instead of precise observations

**Impact:** FFT latency fundamentally conflicts with the predictor's phase-locked loop design, which relies on timely observations to maintain synchronization.

### 2. Beat Timing Precision

**Current System:**
- Outputs exact timestamp of threshold crossing
- Predictor uses observation timestamps for phase correction: `phase_error = (observed_time - last_beat_time) / current_ibi - current_phase`
- Enables tight phase locking (correction weight: 0.15)

**FFT System:**
- Outputs average heart rate over window (e.g., "73.5 BPM over last 5 seconds")
- No individual beat timestamps available
- Would require synthetic beat generation or heuristic timestamp assignment

**Impact:** Loss of precise beat timing would severely degrade predictor accuracy, causing drift and jitter in beat emission timing.

### 3. Signal Quality and Robustness

**Current System (Research-backed):**
> "MAD provides 50% breakdown point against outliers and sensor saturation" (amor-heartbeat-prediction-design.md:26-28)

- Adaptive threshold automatically adjusts to signal amplitude variations
- Explicit PAUSED state when MAD < 10 (flat/noisy signal)
- Recovers gracefully when signal quality improves

**FFT System (Research findings):**
> "In a corrupted signal the dominant frequency can shift due to noise and lead to wrong heart rate detection" (Web search results)

> "Motion artifacts occupy 3.5–7.8 Hz frequency band, overlapping normal cardiac frequencies (0.5–4 Hz), making spectral separation problematic" (PMC8869811)

- No inherent signal quality metric
- Motion artifacts in overlapping frequency bands cannot be distinguished from true heart rate
- Requires additional preprocessing and quality assessment algorithms

**Impact:** FFT is fundamentally less robust to the signal quality challenges present in PPG data.

### 4. Arrhythmia and Heart Rate Variability

**Current System:**
- Detects each beat independently
- Predictor's IBI blending (0.1 weight) naturally tracks tempo changes over ~10 beats
- Observation debouncing (0.7 × IBI) prevents double-detection while allowing variability

**FFT System:**
- Averages over entire window, masking beat-to-beat variability
- Cannot distinguish regular rhythm from arrhythmia
- Research specifically notes time-domain methods are essential for arrhythmia detection:

> "The Poincaré plot analysis—examining beat-to-beat interval relationships—requires temporal sequence information fundamentally unavailable from frequency-domain decomposition alone" (PMC8869811)

**Impact:** Participants with heart rate variability would experience averaged, smoothed beat patterns that don't reflect actual cardiac rhythm.

### 5. Computational Efficiency

**Current System:**
- Single median calculation per sample: O(1) amortized with sliding window
- MAD calculation: O(1) using cached median
- Total: ~10-20 operations per sample
- 4 sensors × 50Hz = 200 samples/sec = 2,000-4,000 ops/sec

**FFT System:**
- 256-point FFT: 2048 operations
- 4 sensors × 0.2 Hz update rate (5-second windows) = 1638 ops/sec FFT alone
- Plus filtering, windowing, peak finding: ~3,000-5,000 ops/sec total

**Resource Comparison (from research):**
- Time-domain (TDHR): ~152,000 ops/sec with 4KB memory
- CNN ensemble: 60M ops/sec with 240M parameters

**Impact:** While FFT is computationally feasible, it offers no efficiency advantage over the current approach and increases memory requirements by 5-10×.

### 6. Integration with HeartbeatPredictor

**Current Architecture:**
```
ThresholdDetector → ThresholdCrossing[timestamp, value, threshold, mad]
                  ↓
HeartbeatPredictor.observe_crossing(timestamp)
                  ↓
Phase correction + IBI blending
```

The predictor design explicitly expects threshold crossing observations with precise timestamps for phase-locked loop operation.

**FFT Integration Would Require:**
1. Converting windowed rate estimates to synthetic beat timestamps
2. Modifying predictor to accept rate estimates instead of observations
3. Redesigning phase correction algorithm (no precise observation timestamps)
4. Adding logic to handle delayed/averaged rate updates

**Impact:** FFT would require substantial architectural changes to the predictor, undermining the clean separation of concerns between detector and predictor.

---

## Use Cases Where FFT Would Be Appropriate

FFT-based heart rate estimation excels in different scenarios:

1. **Offline/batch analysis**: Where latency is not a concern and windowed averaging is acceptable
2. **Heart rate variability (HRV) frequency analysis**: Analyzing power in different frequency bands (LF/HF ratio, etc.)
3. **Average rate over time**: When you need mean heart rate over longer periods (minutes)
4. **Motion-prone environments**: When combined with accelerometer-based motion artifact rejection *before* FFT

None of these apply to corazonn's real-time beat emission use case.

---

## Recommendation

**Do not replace the detector with FFT-based detection.**

### Reasons:
1. **Latency**: 5-10 second FFT windows are incompatible with real-time beat emission and predictor phase locking
2. **Beat Precision**: Loss of individual beat timestamps would degrade predictor accuracy
3. **Signal Quality**: MAD-based approach is more robust to PPG-specific challenges (saturation, amplitude variation)
4. **Computational**: No efficiency advantage; FFT increases memory requirements
5. **Architectural**: Would require substantial redesign of predictor integration
6. **Artistic Intent**: System design emphasizes "idealized rhythm" presentation with natural fade-in/out based on signal quality—FFT averaging would conflict with this goal

### Current System Strengths:
- Beat timing precision suitable for musical/lighting synchronization
- Low latency enables responsive predictor phase correction
- MAD-based robustness proven in literature (>98% sensitivity)
- Minimal computational/memory footprint
- Clean integration with predictor design

---

## Alternative Improvements

If the current detector has shortcomings, consider these time-domain enhancements instead:

### 1. Envelope-Based Peak Detection
Research shows envelope methods eliminate dicrotic notch false positives:
> "Envelope-based peak detection using Hilbert transform to eliminate dicrotic notches" (PMC8869811)

Could augment MAD threshold with envelope filtering if double-detection occurs.

### 2. Adaptive Threshold Parameters
Current system uses fixed MAD_THRESHOLD_K = 4.5. Consider dynamic adjustment based on signal characteristics:
- Lower threshold during stable signal (MAD consistently high)
- Higher threshold during marginal signal (MAD near minimum)

### 3. Multi-Scale Analysis
Research mentions "Automatic Multiscale-based Peak Detection (AMPD)" for robust peak finding:
> "Modified AMPD method reduces computational demands using 1-bit binary values" (PMC7146569)

Could provide more robust peak detection than single-threshold approach.

### 4. Signal Quality Metrics
Add additional quality metrics beyond MAD:
- Pulse amplitude variation
- Signal regularity (successive IBI variance)
- Baseline drift rate

These could improve ACTIVE/PAUSED state transitions without changing detection algorithm.

---

## Conclusion

The current MAD-based threshold detector is well-suited to corazonn's requirements. FFT-based detection offers no advantages for real-time beat detection and introduces substantial latency, precision loss, and integration complexity. Any improvements should focus on time-domain enhancements that preserve the low-latency, beat-precise characteristics essential for the predictor's phase-locked loop operation.

---

## References

1. PMC8869811: "A Real-Time PPG Peak Detection Method for Accurate Determination of Heart Rate during Sinus Rhythm and Cardiac Arrhythmia"
2. PMC7146569: "Photoplethysmographic Time-Domain Heart Rate Measurement Algorithm for Resource-Constrained Wearable Devices"
3. PMC10926197: "Photoplethysmogram beat detection using Symmetric Projection Attractor Reconstruction"
4. Web search results on FFT computational complexity and latency characteristics
5. `/home/user/corazonn/amor/detector.py` - Current implementation
6. `/home/user/corazonn/docs/amor-heartbeat-prediction-design.md` - System architecture
