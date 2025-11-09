# Working with Samples

Quick reference for loading and playing samples in Pure Data.

## Load Sample into Table

```
[loadbang]
|
[read -resize filename.wav tablename(
|
[soundfiler]
|
[s tablename-length]
```

**File location**: Use `[declare -path ../samples/percussion/starter]` in main patch.

**Table creation**: Put → Array, name it `tablename`, set initial size (will resize on load).

**Verify**: Pd console prints "read N samples into table tablename".

## Play Sample from Table (One-Shot)

```
[r trigger]
|
[t b b]
|    |
|    [r sample-length]
|    |
|    [/ 48000]          # Samples to seconds
|    |
|    [* 1000]           # Seconds to milliseconds
|    |
|    [0, 1 $1(          # line~ message format
|    |
|    [line~]
|    |
|    [*~ ] ← [r sample-length] → [sig~]
|    |
|    [tabread4~ tablename]
|
[vline~]  ← [envelope-message(
|
[*~]  # Apply envelope
```

**Envelope message format** for `[vline~]`:
- `[1 5, 0 5 40(` = ramp to 1 in 5ms, then after 40ms, ramp to 0 in 5ms
- Total duration: 5ms attack + 40ms sustain + 5ms release = 50ms

## Play Sample from Disk (Streaming)

```
[r trigger]
|
[open filename.wav, 1(  # "1" starts playback immediately
|
[readsf~ 1]  # 1 channel (mono)
|
[outlet~]
```

**When to use**:
- Samples > 10 seconds (saves RAM)
- Long ambient loops

**When not to use**:
- Short percussion (table-based is better)
- Disk I/O can cause glitches on Pi

---

**Related documentation**:
- See common-tasks-audio-processing.md for envelope and crossfading techniques
- See common-tasks-testing-validation.md for verifying sample loading
- See common-tasks-integration-setup.md for declaring sample paths
