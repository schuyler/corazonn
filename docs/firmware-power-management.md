# Firmware Power Management Design

This document describes the actual power management approach implemented in the firmware.

## Architecture Overview

**Important:** Power state management (IDLE/ACTIVE) is NOT implemented in the firmware. The ESP32 runs a simple, stateless design:
- Continuously samples at 50Hz
- Continuously transmits samples via WiFi when connected
- No dynamic power scaling in firmware

**Signal quality filtering happens in the processor (detector.py),** not the firmware. The firmware sends raw data; the processor decides what to do with it.

## Why This Simple Approach?

1. **Reduced complexity:** No state machine bugs, no state transitions to debug
2. **Predictable power:** Users either have WiFi connected (80-120mA) or WiFi off (minimal, but firmware continues sampling)
3. **Separation of concerns:** Firmware does sampling, processor does signal intelligence
4. **Robustness:** Simple code has fewer failure modes

The cost: higher power consumption when WiFi is active. The benefit: simpler, more reliable system.

## Firmware Behavior

### Sampling

- **Rate:** Constant 50Hz (20ms intervals)
- **Samples per bundle:** 5 samples = 100ms transmission interval
- **Behavior:** Samples continuously regardless of signal quality
- **Transmission:** OSC bundles sent every 100ms (after collecting 5 samples over 100ms interval)

**Serial output example:**
```
[INFO] Bundle 1234: samples=[2048, 2050, 2049, 2051, 2048]
[INFO] WiFi connected, transmitted bundle
```

### WiFi Management

- **Connection check:** Every 3 seconds
- **Retry on disconnect:** Every 3 seconds, indefinitely
- **No disconnect timeout:** Device will keep trying to reconnect forever
- **Non-blocking:** WiFi.begin() returns immediately, doesn't block sampling
- **Transmission conditional:** OSC bundles are only sent when WiFi is connected. Samples continue to be collected during disconnection but are not buffered for later transmission.

**Serial output example:**
```
[WARN] WiFi disconnected (status=1)
[INFO] Attempting reconnection...
[INFO] Connected! IP: 192.168.1.50
```

### Optional Features

- **LED status:** Visual feedback for connection state (if `ENABLE_LED`)
- **OSC admin listener:** Remote restart commands on port 8006 (if `ENABLE_OSC_ADMIN`)
- **Hardware watchdog:** Auto-reset on hang (if `ENABLE_WATCHDOG`, experimental)

## What the Firmware Does NOT Do

To understand the architecture, it's important to know what the firmware deliberately avoids:

- **No signal quality measurement:** Doesn't calculate MAD or signal statistics for decision-making
- **No power states:** No IDLE/ACTIVE modes; no dynamic behavior changes
- **No filtering:** Sends raw sensor data without preprocessing
- **No buffering:** Doesn't save samples from disconnections for later transmission
- **No beat detection:** Doesn't attempt to identify heartbeats
- **No sleep modes:** Doesn't use light sleep, deep sleep, or power-down features

All of these intelligence tasks are delegated to the processor layer.

## What the Processor Does

While firmware handles raw sampling, processor (`detector.py`) implements actual power-relevant logic:

```python
# From detector.py - the real decision-making
class ThresholdDetector:
    WARMUP -> ACTIVE:  signal quality (MAD) >= 40 for 100 samples
    ACTIVE -> PAUSED:  signal quality (MAD) < 40
    PAUSED -> ACTIVE:  signal quality (MAD) >= 40

    Recovery time: 0.2 seconds (very fast)
```

The processor:
1. Validates signal quality using MAD threshold (40)
2. Manages beat detection state (WARMUP/ACTIVE/PAUSED)
3. Decides whether to render visuals/audio based on detected beats
4. Can disable downstream processing for poor signals (no UI rendering)

## Power Consumption

- **WiFi connected, transmitting:** 80-120mA (radio dominates)
- **WiFi disconnected:** Firmware idles (~1mA), still sampling (CPU minimal load)
- **Theoretical low-power mode:** Not implemented (would require state machine)

**In practice:** Most power consumption comes from WiFi transmission. Firmware sampling cost is negligible (~5mA).

## Serial Diagnostics

The firmware outputs useful information for debugging:

```
[INFO] Samples sent: 1234 bundles
[INFO] WiFi status: connected
[INFO] Received: /admin/restart command -> rebooting
[WARN] WiFi disconnected, retrying...
```

Monitor these to understand:
- If bundles are transmitting consistently
- WiFi stability
- Connection churn (rapid disconnect/reconnect cycles)

## Configuration

See `docs/guide/firmware.md` for:
- WiFi credentials and server IP
- GPIO pin selection (ADC1 only)
- Optional feature flags
- Build and flash instructions

## Migration Note

An earlier design document (`firmware-power-management.md`) proposed a complex IDLE/ACTIVE state machine with:
- Light sleep in IDLE (0.8mA)
- Fast sampling in ACTIVE (80-120mA)
- 10-second grace periods
- 3-minute sustain timeouts
- Signal quality filtering in firmware

**This was never implemented.** The current firmware is intentionally simpler, delegating signal intelligence to the processor. If future power optimization is needed, this design could be revisited, but it would require significant firmware changes.
