# Pure Data Troubleshooting: Audio

Audio configuration, signal flow, and connection issues.

**Related guides**: [Patch Creation](troubleshooting-patch-creation.md), [Timing & Performance](troubleshooting-timing-performance.md)

## No Audio Output

### DSP is off

**Check**: Pd window → DSP toggle (top right)

**Fix**:
- Click toggle to turn on
- Or: Media → Audio ON
- Or: Add to patch: `[loadbang] → [; pd dsp 1(`

### No signal reaching DAC

**Debug**:
```
[osc~ 440]  # Test tone
|
[*~ 0.1]    # Reduce volume
|
[print~ DEBUG]  # Check if signal exists
|
[dac~ 1 2]
```

**Check**:
- `[print~]` shows non-zero values when DSP on
- All connections are signal (not message)
- No breaks in signal chain

### Audio device not configured

**Symptoms**:
- "audio I/O stuck" in console
- No sound from speakers

**Fix**:
1. Media → Audio Settings
2. Select correct device
3. Set sample rate: 48000
4. Set channels: 2
5. Click OK
6. Toggle DSP off and on

**Command line**:
```bash
pd -audiodev 4 -channels 2 -r 48000 -audiobuf 64
```

### Samples not loaded

**Symptoms**:
- Pd console: "couldn't open 'filename.wav'"
- `[soundfiler]` outputs 0

**Check**:
1. File path correct (case-sensitive on Linux)
2. `[declare -path]` points to sample directory
3. File format is WAV, 48kHz, mono or stereo

**Fix**:
```
[declare -path ../samples/percussion/starter]
```
Must be relative to patch location.

## Audio Glitches / Crackling

### Buffer underruns

**Symptoms**:
- Crackling, popping
- Pd console: "audio I/O stuck"

**Cause**: Audio buffer too small for system load.

**Fix**: Increase buffer size:
```bash
pd -audiobuf 128  # Try 128 or 256
```

**Trade-off**: Larger buffer = more latency, more stable.

### CPU overload

**Check**:
```bash
top -p $(pgrep pd)
```

**Target**: < 50% on single core

**If too high**:
1. Simplify patch (remove unnecessary objects)
2. Use `[block~ 128]` to increase DSP block size
3. Close other programs
4. Use table-based sample playback (not `[readsf~]`)

### Disk I/O bottleneck

**Symptoms**:
- Glitches when `[readsf~]` starts playback
- High `%iowait` in `top`

**Cause**: Reading samples from disk during performance.

**Fix**: Use table-based playback for short samples:
```
[loadbang] → [read -resize file.wav table( → [soundfiler]
[trigger] → [tabread4~ table]
```

## Signal Connections Not Working

### Message vs signal mismatch

**Common error**: Using message object where signal needed (or vice versa).

**Signal objects** have `~` suffix:
- `[*~]` not `[*]`
- `[+~]` not `[+]`
- `[osc~]` not `[osc]`

**Visual**: Signal connections are thicker lines.

### No connection made

**Cause**: Clicking outlet then clicking inlet doesn't connect.

**Fix**: Click and **drag** from outlet to inlet.

**Delete connection**: Click connection line, press Delete or Backspace.

### Wrong inlet/outlet

**Inlets**: Top of object box
**Outlets**: Bottom of object box

**Numbering**: Left to right, starting at 0.

**Check help**: Right-click object → Help shows inlet/outlet functions.
