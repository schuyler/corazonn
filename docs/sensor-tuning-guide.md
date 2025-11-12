# PPG Sensor Tuning Guide

Quick reference for tuning detector parameters based on observed behavior.

## Diagnostic Tools

```bash
# Verbose mode shows per-sample MAD, threshold, crossings
python3 -m amor.processor --verbose

# Capture sensor data for analysis
python3 testing/log_ppg_samples.py --ppg-id 0 --duration 10
```

## Common Issues and Fixes

### Ghost Beats on Idle Sensor

**Symptom**: Beat messages when no finger on sensor

**Diagnosis**: Check verbose output for MAD values during idle
- Low MAD (< 40): Detector locking on noise floor
- Solution: Increase `MAD_MIN_QUALITY` in `amor/detector.py`

```python
MAD_MIN_QUALITY = 40  # Raise to 60-100 for noisier sensors
```

### Missed Beats with Good Signal

**Symptom**: Irregular beats despite solid finger contact, high confidence

**Diagnosis**: Check verbose output during heartbeat
- Threshold too high: `sample < threshold` during peaks
- Solution: Lower `MAD_THRESHOLD_K`

```python
MAD_THRESHOLD_K = 4.5  # Lower to 3.5-4.0 for weaker signals
```

### Constant PAUSED State

**Symptom**: Detector stays PAUSED, never transitions to ACTIVE

**Diagnosis**: Check verbose output for MAD values with finger on sensor
- MAD below threshold: Signal too weak or noisy
- Solution A: Lower `MAD_MIN_QUALITY`
- Solution B: Improve sensor contact (reposition finger, adjust pressure)

```python
MAD_MIN_QUALITY = 40  # Lower to 30 if real heartbeats rejected
```

### Clipped Signal Rejected

**Symptom**: PAUSED state during strong signal that rails at 0 or 4095

**Diagnosis**: Check for saturation warnings in verbose output
- High saturation (> 80%): Rhythmic clipping mistaken for stuck sensor
- Solution: Increase `SATURATION_THRESHOLD` or adjust rail boundaries

```python
SATURATION_THRESHOLD = 0.8     # Raise to 0.9 for heavy clipping
SATURATION_BOTTOM_RAIL = 10    # Lower to 50 if clipping near bottom
SATURATION_TOP_RAIL = 4085     # Lower to 4000 if clipping near top
```

### BPM Crashes to Low Values

**Symptom**: BPM drops from 60 → 40 → 30 when beats missed

**Diagnosis**: Death spiral from missed-beat outliers
- Missed beats create long IBIs that corrupt estimate
- Solution: Already mitigated by `IBI_MAX_MS` and `IBI_OUTLIER_FACTOR`
- Check logs for "IBI rejected" messages

### Per-Sensor Tuning

Different sensors may have different noise characteristics. To configure per-sensor:

**Option 1**: Separate config files (cleanest for permanent differences)
```python
# In detector.py
SENSOR_CONFIGS = {
    0: {'k': 4.5, 'mad_min': 40, 'mad_max': None},
    1: {'k': 5.5, 'mad_min': 100, 'mad_max': 400},  # Noisier sensor
    # ...
}
```

**Option 2**: Runtime calibration (future work)
- Auto-measure idle MAD on startup
- Set thresholds based on observed baseline

## Parameter Interdependencies

- `MAD_MIN_QUALITY` ↑ → fewer false positives, more missed beats
- `MAD_THRESHOLD_K` ↓ → more sensitive detection, more false positives
- `SATURATION_THRESHOLD` ↑ → allows more clipping, risks accepting stuck sensors

## Verification Workflow

1. Test idle state (no finger):
   - Should stay WARMUP → PAUSED
   - No beat messages
   - MAD < `MAD_MIN_QUALITY`

2. Test normal contact:
   - Should reach ACTIVE within 2s
   - Regular beat messages
   - BPM stable (55-95 range)
   - MAD in valid range (40-400)

3. Test signal loss:
   - Remove finger during active state
   - Should transition ACTIVE → PAUSED
   - Confidence decays over 10s
   - Beat messages fade out

4. Test recovery:
   - Replace finger after PAUSED
   - Should transition PAUSED → ACTIVE after 2s
   - Confidence ramps back up
   - Beat messages resume
