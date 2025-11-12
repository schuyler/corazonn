# Firmware Power Management Design

## Overview

The ESP32-S3 firmware implements adaptive power management to minimize battery drain while maintaining responsive beat detection. The system uses a two-state machine (IDLE/ACTIVE) with light sleep between operations and WiFi enabled only when good signal is detected.

**Key Goals:**
- Maximize battery life (target: multi-hour operation on portable power)
- Minimize false WiFi activations (wasted power transmitting noise)
- Maintain responsive user experience (<1 second activation)
- Align signal quality decisions with tuned beat detector

## Architecture

### State Machine

**IDLE State:**
- Light sleep for 500ms intervals
- WiFi radio OFF (radio is largest power consumer)
- Periodic signal quality checks (20 samples every 500ms)
- Monitors for valid PPG signal using MAD metric
- Transitions to ACTIVE when good signal detected

**ACTIVE State:**
- WiFi ON, streaming PPG data at 50Hz (5 samples per bundle)
- Light sleep between samples (20ms intervals)
- Continuous signal quality monitoring
- Transitions to IDLE after 5min + 10s grace period of poor signal
- Transitions to IDLE after 60s of WiFi connection failures

### Power Consumption Profile

Estimated current draw:
- IDLE state: ~0.8mA (light sleep with periodic wake)
- ACTIVE state: ~80-120mA (WiFi + sampling + processing)
- WiFi connection attempt: ~150-200mA peak

The 100x difference between IDLE and ACTIVE makes state management critical.

## Signal Quality Metric: MAD Alignment

**Critical Design Decision:** Firmware uses MAD (Median Absolute Deviation) instead of stddev to match the tuned beat detector (detector.py).

### Why MAD?

The processor.py beat detector uses `MAD >= 40` (MAD_MIN_QUALITY) to validate signal quality before detecting beats. If firmware used a different metric (stddev), they wouldn't correlate:

**Problem scenario with stddev:**
1. Firmware activates WiFi at stddev=50 (thinks signal is good)
2. Processor sees MAD=25 (signal is noise, enters PAUSED state)
3. No beats detected, but WiFi burns power for 5 minutes
4. Result: Wasted WiFi cycles → heating + battery drain

**Solution:** Firmware calculates MAD exactly as processor does:
1. Calculate median of PPG samples
2. Calculate absolute deviations from median
3. Return median of deviations

This ensures firmware and processor agree on "good signal" definition.

### MAD vs Stddev Properties

MAD is preferred because:
- **Robust to outliers:** 50% breakdown point vs stddev's 0%
- **Matches tuned detector:** Empirically validated threshold (MAD >= 40)
- **Efficient:** No square root calculation
- **Stable:** Less sensitive to transient spikes

## Power Saving Mechanisms

### 1. Light Sleep

ESP32 light sleep mode preserves RAM and peripheral state while reducing power:
- Configures timer wake source before sleep
- Validates actual sleep duration after wake
- Falls back to regular delay() if light sleep fails
- Sleep validation prevents undetected failures causing heating

### 2. WiFi Radio Control

WiFi is the largest power consumer (~100mA continuous):
- Radio OFF in IDLE state (WiFi.mode(WIFI_OFF))
- Radio ON only in ACTIVE state
- Power save mode enabled (WIFI_PS_MIN_MODEM) for light sleep compatibility
- Connection retry limit (20 attempts = 60s) prevents infinite WiFi churn

### 3. Efficient Computation

- No floating point in critical path (integer MAD calculation)
- Selection sort for median (optimal for N=20-50 samples)
- No dynamic allocation (stack-only data structures)
- LED fully disabled (not visible, wastes power)

## Thresholds and Decision Points

All thresholds align with detector.py for consistency:

```cpp
SIGNAL_QUALITY_THRESHOLD_TRIGGER = 40   // MAD > 40 activates (matches MAD_MIN_QUALITY)
SIGNAL_QUALITY_THRESHOLD_SUSTAIN = 40   // Same threshold (no hysteresis needed)
SIGNAL_QUALITY_THRESHOLD_VERY_STRONG = 80  // Bypass stability check for very strong signals
SIGNAL_STABILITY_THRESHOLD = 20         // MAD of MADs < 20 = stable signal
```

### Trigger Logic

**IDLE → ACTIVE transition:**
- MAD > 40 AND (stability < 20 OR MAD > 80)
- Stability check prevents false triggers from transient noise
- Very strong signals (MAD > 80) bypass stability for faster UX

**ACTIVE → IDLE transition:**
- MAD ≤ 40 for 5 minutes + 10 second grace period, OR
- WiFi fails for 60 seconds (20 attempts × 3s intervals)

## Trade-offs: Responsiveness vs Power

### Situations Where We Trade Responsiveness for Power

1. **IDLE check interval (500ms):**
   - Trade-off: Detection latency up to 500ms vs deeper/longer sleep
   - Impact: User touches sensor → device may take up to 500ms to notice
   - Rationale: 500ms is imperceptible to users, significant power savings

2. **Stability check (1.5 seconds for 3 measurements):**
   - Trade-off: 1.5s delay for weak signals vs false activation prevention
   - Impact: Marginal signals (MAD 40-80) require 3 checks before activation
   - Mitigation: Very strong signals (MAD > 80) bypass this check
   - Rationale: Prevents WiFi churn from hand movement artifacts

3. **Poor signal grace period (10 seconds):**
   - Trade-off: 10s delayed response to signal loss vs preventing momentary disconnects
   - Impact: If sensor loses contact, WiFi stays on for extra 10s
   - Rationale: Users frequently adjust sensor position, avoid rapid on/off cycles

4. **Sustain timeout (5 minutes):**
   - Trade-off: 5 minutes of WiFi for marginal signals vs missing weak beats
   - Impact: Weak signals (MAD 40-80) stream for full 5 minutes before giving up
   - Rationale: Captures data from poor sensor placement/contact that may still produce beats

5. **WiFi retry limit (60 seconds):**
   - Trade-off: 60s of connection attempts vs immediate fallback
   - Impact: If WiFi fails to connect, device spends 60s trying before returning to IDLE
   - Rationale: Networks take time to associate, prevents giving up too soon

### Situations Where We Favor Responsiveness

1. **Single check threshold (ACTIVE_TRIGGER_COUNT = 1):**
   - Strong signals activate immediately on first valid check
   - Very strong signals bypass stability requirement entirely

2. **Short sample intervals (20ms = 50Hz):**
   - Maintains real-time beat detection quality
   - No decimation or batching that would add latency

3. **Immediate ACTIVE transition:**
   - No gradual ramp-up or warm-up period
   - WiFi connects and streaming begins immediately

## Implementation Details

### State Contamination Prevention

When transitioning IDLE → ACTIVE or ACTIVE → IDLE:
- Reset MAD history buffer (prevents old signal quality from affecting decisions)
- Reset ADC ring buffer (ensures fresh samples)
- Reset WiFi retry counter

### Light Sleep Validation

Both IDLE and ACTIVE states validate sleep operation:
- Check return value from esp_light_sleep_start()
- Measure actual sleep duration with millis()
- Warn if sleep is shorter than requested (indicates failure)
- Fall back to regular delay() if light sleep fails

This prevents "silent failure" scenario where light sleep returns immediately, causing tight loop and heating.

### WiFi State Management

WiFi connection attempts are non-blocking but require careful management:
- Track connection state (WL_IDLE_STATUS = in progress)
- Only interrupt failed connections (WL_DISCONNECTED, WL_CONNECT_FAILED)
- Count in-progress attempts to prevent infinite waiting
- Increment retry counter even for WL_IDLE_STATUS

### Signal Statistics

Stats output includes both power-relevant and debugging metrics:
- MAD (signal quality for power decisions)
- Mean and median (for debugging sensor issues)
- Min/max (detect clipping or stuck sensor)
- Transition counters (detect thrashing between states)

## Validation and Tuning

### Expected Behavior

**Good sensor contact:**
- IDLE → ACTIVE within 500ms-2s
- MAD typically 60-200 range
- Stays ACTIVE as long as contact maintained
- Immediate beats detected by processor.py

**Poor/no contact:**
- Remains in IDLE
- MAD typically < 30 range
- No WiFi activation
- Battery lasts for hours/days

**Marginal contact:**
- IDLE → ACTIVE (MAD 40-80 range)
- Streams for 5 minutes attempting to capture beats
- Processor may detect intermittent beats
- Returns to IDLE if no improvement

### Monitoring Power Issues

Serial output provides power management diagnostics:
- "IDLE: MAD=X stability=Y" - signal quality checks
- "WARNING: Sleep short, only Xms" - light sleep failure
- "WiFi connection failed (status=X, retry Y/20)" - connection issues
- "Transitions: I=X A=Y" - detect rapid state thrashing

Heating indicates power management failure (likely WiFi staying on unnecessarily).
