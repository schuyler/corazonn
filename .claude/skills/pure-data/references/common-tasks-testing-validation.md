# Testing and Debugging

Quick reference for debugging and verifying Pure Data patches.

## Print Messages to Console

```
[r something]
|
[print LABEL]
```

**Shows in Pd console**: `LABEL: <value>`

## Monitor Audio Levels

```
[r~ audio]
|
[env~]  # Amplitude envelope follower
|
[print LEVEL]
```

**Or** connect to number box for visual display.

## Measure Timing

```
[r trigger1]     [r trigger2]
|                |
[timer]  # Outputs time difference in ms
|
[print TIME-DIFF]
```

## Verify Sample Loading

After `[soundfiler]`, check Pd console for:
```
read 48000 samples into table sample-0
```

**If error**: Check file path, `[declare -path]`, and file format.

## Test Without Hardware

Use `test-osc-sender.py` to simulate sensors:

```bash
cd audio/scripts
python3 test-osc-sender.py --port 8000 --sensors 4
```

**Verify**:
1. Pd console shows "VALID-IBI" messages
2. Audio triggers at ~1 beat per second per sensor
3. Stereo positioning audible (use headphones)

---

## Validation

### Check Patch Opens Without Errors

1. Open .pd file in Pure Data
2. Check Pd console for errors (red text)
3. Click on error → jumps to problem object
4. Common errors:
   - "couldn't create" = missing external or typo
   - "no such object" = wrong object name
   - DSP loop detected = feedback in signal graph

### Verify Externals Loaded

**Method 1**: Try creating objects:
- `[packOSC]` should create (not dashed border)
- `[unpackOSC]` should create
- `[udpsend]` should create

**Method 2**: Pd console shows on startup:
```
cyclone: version 0.X
```

### Test Signal Flow

Add `[print]` objects at key points:
```
[r ibi-0]
|
[print 1-RAW-IBI]
|
[moses 300]
|
[print 2-VALID-IBI]
|
[s ibi-valid-0]
```

Remove or comment out prints after debugging.

### Verify Audio Routing

1. Turn on DSP
2. Add test tone:
```
[loadbang]
|
[440(
|
[osc~]
|
[*~ 0.1]
|
[dac~ 1 2]
```
3. Should hear 440Hz sine wave
4. Remove test after verification

---

**Related documentation**:
- See common-tasks-message-routing.md for message routing patterns
- See common-tasks-osc-networking.md for OSC debugging techniques
- See common-tasks-sample-playback.md for sample loading verification
