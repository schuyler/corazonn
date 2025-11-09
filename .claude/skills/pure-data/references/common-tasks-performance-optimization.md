# Performance

Quick reference for monitoring and optimizing Pure Data patch performance.

## Monitor CPU Usage

**On Pi**:
```bash
top -p $(pgrep pd)
```

**Target**: < 30% CPU usage.

**If high**:
- Increase audio buffer: `pd -audiobuf 128`
- Simplify patch (remove unnecessary objects)
- Use table-based sample playback (not `[readsf~]`)

## Check for Audio Glitches

**Symptoms**:
- Crackling or popping sounds
- Dropouts (silence)
- Distortion

**Causes**:
- CPU overload
- Audio buffer too small
- Disk I/O bottleneck (if using `[readsf~]`)

**Fixes**:
- Increase buffer size
- Close unnecessary programs
- Use table-based playback for short samples

## Optimize Patch

**Reduce DSP load**:
- Combine multiple multiplies: `[*~ A] → [*~ B]` instead of parallel
- Use `[clip~]` instead of `[expr~]` for simple operations
- Avoid feedback loops (use `[delwrite~]`/`[delread~]` if needed)

**Reduce message load**:
- Use wireless sends (`[s]`/`[r]`) instead of many connections
- Don't send control messages at audio rate

---

**Related documentation**:
- See common-tasks-sample-playback.md for choosing between table-based and streaming playback
- See common-tasks-testing-validation.md for verifying audio routing under load
