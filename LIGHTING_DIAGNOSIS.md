# Lighting Event Loop Diagnosis

## Problem
`amor.lighting` fails to initialize bulbs to baseline with "Event loop is closed" errors:
```
[W 19:54:34.318 lighting ] Failed to init 192.168.8.227: Failed to set color for 192.168.8.227: Event loop is closed
```

## Evidence of Code Mismatch

**Log shows:**
1. "Lighting Engine initialized" appears BEFORE "Authenticating Kasa backend..."
2. Error message: "Failed to set color for X" (from `set_color()` method)

**Current code should:**
1. Print "Initializing Kasa backend..." (not "Authenticating")
2. Block at `backend.initialize()` before printing "Lighting Engine initialized"
3. Call `await light.set_hsv()` directly (line 178), not `set_color()`

**Conclusion:** You're running OLD CODE, not the current `amor/lighting.py`

## Root Cause Analysis

The "Event loop is closed" error occurs when:
1. `Discover.discover()` creates device objects bound to one event loop
2. Those devices are later used from a different async context
3. The original event loop context has been closed/destroyed

## The Fix That's Already in Current Code

The current code (lines 113-198) runs ALL initialization in a single `initialize_async()` coroutine:
- Discovery
- Device updates
- Baseline setting

This ensures all device operations happen in the same event loop context.

## What the Old Code Probably Does Wrong

Old code likely:
1. Discovers devices in one async context
2. Stores device objects
3. Tries to use them from a DIFFERENT async context (new coroutine)
4. Fails because original event loop is closed

## Action Required

**You were running CACHED BYTECODE (.pyc file) from old code.**

I've cleared the cache:
```bash
rm -rf amor/__pycache__/lighting.cpython-311.pyc
```

**Now restart `amor.lighting`:**
```bash
python -m amor.lighting
```

## Expected Behavior After Fix

Logs should show:
```
[I] Loaded config from amor/config/lighting.yaml
[I] Initializing Kasa backend...           <-- Not "Authenticating"
[I] Discovering Kasa bulbs on network...
[I] Connecting to Corazon 0 (192.168.8.227)...
[I]   Zone 0 → Corazon 0 (192.168.8.227) - OK
[I] Connected to 4 bulbs successfully
[I] Setting all bulbs to baseline...
[I]   Initialized Corazon 0 (zone 0) to baseline: hue=0°
[I] Lighting Engine initialized            <-- AFTER bulb init
```

No "Event loop is closed" errors.
