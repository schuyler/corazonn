# Firmware Power Management Design Rationale

This document explains design choices that might look wrong at first glance. Read this before assuming we made mistakes.

## Critical: MAD Alignment with Beat Detector

**Decision:** Firmware uses MAD (Median Absolute Deviation) with threshold 40, matching detector.py exactly.

**Why this matters:** The processor beat detector (detector.py line 34) uses `MAD >= 40` to validate signal quality before detecting beats. Firmware must use the same metric and threshold.

**What would break if we used stddev:**
1. Firmware activates WiFi at stddev=50 (thinks signal is good)
2. Processor sees MAD=25 (signal is noise, enters PAUSED)
3. No beats detected, WiFi burns 100mA for 5 minutes transmitting useless data
4. Result: Battery drain + heating from wasted WiFi cycles

**Key insight:** Stddev and MAD don't correlate predictably for PPG signals. You cannot convert between them reliably.

## Power/Responsiveness Trade-offs

Power consumption profile:
- IDLE: ~0.8mA (100x less than ACTIVE)
- ACTIVE: ~80-120mA (WiFi radio dominates)

The 100x difference makes state management critical. We chose to favor battery life over instant response where imperceptible to users.

### 1. IDLE Check Interval = 500ms

**Trade-off:** User touches sensor → up to 500ms before device notices

**Why 500ms:** Imperceptible to humans, but allows longer/deeper sleep between checks. Going to 100ms would only improve response by 400ms but require 5x more wake cycles.

**Power impact:** Significant - determines how often we wake from light sleep

### 2. Stability Check = 1.5 seconds (3 measurements)

**Trade-off:** Weak signals (MAD 40-80) require 3 checks before activation

**Why this exists:** Prevents false activation from transient noise (hand movement, sensor adjustment). Without it, rapid IDLE→ACTIVE→IDLE cycles waste more power than waiting.

**Mitigation:** Very strong signals (MAD > 80) bypass this check entirely, activating in 500ms.

**Why 3 measurements:** Minimum for meaningful stability calculation (MAD of MADs). Less = more false positives.

### 3. Grace Period = 10 seconds

**Trade-off:** Signal lost → WiFi stays on for extra 10s

**Why 10s:** Users frequently adjust sensor position. Without grace period, each adjustment causes rapid IDLE→ACTIVE→IDLE cycle, wasting power on WiFi reconnection (expensive).

**Empirical observation:** Sensor adjustments take 2-5 seconds. 10s covers 95% of cases.

### 4. Sustain Timeout = 5 minutes

**Decision that looks wrong:** Weak signals (MAD 40-80) stream for full 5 minutes even if processor isn't detecting beats.

**Why 5 minutes:** Gives processor multiple chances to lock onto rhythm from poor sensor placement. Some users will have marginal contact but still get useful beats. Cost of trying: minimal (already in ACTIVE). Cost of giving up too soon: missed beats.

**This is intentional:** We chose to be optimistic about marginal signals. User adjusts sensor → MAD improves → beats detected → good UX. If we timeout after 30s, user never gets that chance.

### 5. WiFi Retry Limit = 60 seconds

**Trade-off:** WiFi down → device tries for 60s before returning to IDLE

**Why 60s:** WiFi association can take 10-20 seconds in good conditions. Networks occasionally take 30-40s. 60s is the empirical cutoff where "temporary" becomes "broken."

**Alternative rejected:** Immediate fallback means transient WiFi issues cause lost data.

## Thresholds Explained

```cpp
SIGNAL_QUALITY_THRESHOLD_TRIGGER = 40    // Matches detector.py MAD_MIN_QUALITY
SIGNAL_QUALITY_THRESHOLD_SUSTAIN = 40    // Same (no hysteresis needed)
SIGNAL_QUALITY_THRESHOLD_VERY_STRONG = 80  // 2x threshold for stability bypass
SIGNAL_STABILITY_THRESHOLD = 20          // Half of trigger threshold
```

**Why no hysteresis (40/40):** With 5-minute timeout + 10s grace, we already have massive hysteresis. Adding different thresholds would create confusing behavior where marginal signals cause rapid cycling.

**Why 80 for "very strong":** Empirically, MAD > 80 is reliably good contact. False positive rate is acceptable (user wants responsiveness). 2x the base threshold is conservative.

## Implementation Details Worth Noting

### Light Sleep Validation

Both IDLE and ACTIVE states validate sleep actually worked:
- Check return value from `esp_light_sleep_start()`
- Measure actual sleep duration
- Fall back to `delay()` if sleep fails

**Why this matters:** ESP32 light sleep can fail silently, returning immediately. Without validation, this causes tight loop → heating. This is our safety net against the exact problem we're trying to solve.

### WiFi State Management

WiFi connection is non-blocking (`WiFi.begin()` returns immediately). We carefully track:
- `WL_IDLE_STATUS` = connection in progress (don't interrupt)
- `WL_DISCONNECTED` / `WL_CONNECT_FAILED` = retry now
- Count even in-progress attempts to prevent infinite waiting

**Why this is subtle:** Interrupting in-progress connection prevents WiFi from ever connecting. Previous implementation had this bug.

### State Contamination Prevention

When transitioning between states:
- Reset MAD history (old signal quality from other state)
- Reset ADC ring buffer (fresh samples only)
- Reset WiFi retry counter

**Why:** IDLE uses 20 samples at 500ms intervals. ACTIVE uses 50 samples at 20ms intervals. Mixing them produces garbage statistics.

## What We Monitor for Power Issues

Serial output shows power-relevant diagnostics:
- `IDLE: MAD=X stability=Y` - signal quality decisions
- `WARNING: Sleep short, only Xms` - light sleep failure (heating indicator)
- `WiFi connection failed (status=X, retry Y/20)` - WiFi churn
- `Transitions: I=X A=Y` - detect rapid state thrashing

**If board is heating:** Check for `WARNING: Sleep short` messages. Indicates light sleep failing, device stuck in tight loop.

## Common Review Questions

**"Why not use stddev? It's more standard."**
→ Detector.py uses MAD. Firmware must match. Stddev doesn't correlate.

**"5 minutes is way too long for poor signal!"**
→ Marginal signals can produce beats. This gives processor time to lock on. Already in ACTIVE anyway, cost is minimal.

**"Why not deeper sleep in IDLE?"**
→ Light sleep preserves RAM and wakes fast. Deep sleep requires full reboot. Would add seconds to response time.

**"The stability check delays activation!"**
→ Only for weak signals (MAD 40-80). Strong signals (>80) bypass it. This prevents false triggers that waste more power.

**"WiFi retry limit should be lower!"**
→ WiFi association takes time. 60s is empirical threshold where "slow" becomes "broken." Lower limit = missing data from transient issues.

**"Why not use processor's actual signal quality from ACTIVE state?"**
→ That creates a feedback loop: firmware → processor → firmware. Also adds latency. Firmware must make autonomous decisions for power management.

## Design Philosophy

**User experience > perfect power optimization.** We accept false activations and longer timeouts to ensure we don't miss beats from marginal sensor contact. Battery life matters, but not at the cost of functionality.

**Processor.py is source of truth.** All signal quality thresholds derive from its empirically-tuned parameters. Firmware aligns with processor, never the reverse.

**Fail safe, not silent.** Light sleep validation, WiFi retry limits, and diagnostic output ensure problems are visible, not hidden.
