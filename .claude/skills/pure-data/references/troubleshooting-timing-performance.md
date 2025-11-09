# Pure Data Troubleshooting: Timing & Performance

Message ordering, latency, and system performance issues.

**Related guides**: [Audio Troubleshooting](troubleshooting-audio.md), [Debugging Methodology](troubleshooting-debugging-methodology.md)

## Timing Issues

### Messages arrive in wrong order

**Cause**: Pure Data executes depth-first, right-to-left outlets.

**Example problem**:
```
[trigger]
|       |
[A]     [B]
```
B executes before A.

**Solution**: Use `[trigger]` (or `[t]`) to control order:
```
[t b b]  # or [trigger bang bang]
|    |
|    [B]  # Executes first (right outlet)
|
[A]       # Executes second (left outlet)
```

### Delay not working

**Check**:
- `[delay]` takes time in **milliseconds**
- Must receive bang or number to start
- One-shot (doesn't repeat)

**For repeating**: Use `[metro]`
```
[metro 1000]  # Bangs every 1000ms
```

## Performance Issues

### High latency

**Measure**: Time from trigger to sound output.

**Causes**:
1. Large audio buffer
2. Network latency (OSC)
3. Disk I/O (`[readsf~]`)

**Reduce**:
```bash
pd -audiobuf 32  # Smaller buffer = lower latency
```

**Warning**: Too small = glitches.

### Dropouts

**Symptom**: Intermittent silence or missing beats.

**Causes**:
1. CPU spikes
2. Wireless interference (if using OSC over WiFi)
3. Buffer underruns

**Fix**:
1. Increase priority (Linux): `sudo renice -10 $(pgrep pd)`
2. Use wired network for OSC
3. Increase audio buffer
