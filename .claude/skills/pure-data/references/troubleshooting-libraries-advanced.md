# Pure Data Troubleshooting: Libraries & Advanced

External library issues and array/table configuration.

**Related guides**: [Patch Creation](troubleshooting-patch-creation.md), [Audio Troubleshooting](troubleshooting-audio.md)

## External Library Issues

### Library not found

**Symptoms**:
- "can't load library" in console
- Objects from library won't create

**Check installed**:
```bash
find /usr/lib -name "*.pd_linux" | grep mrpeach
```

**Install**:
- Help → Find Externals → Search "mrpeach" → Install
- Or package manager: `sudo apt install pd-mrpeach`

### Wrong library version

**Symptom**: Object has different behavior than expected.

**Check version**:
```
pd -version
# Pd-0.52-1 or newer
```

**Update if old**:
```bash
sudo apt update
sudo apt install puredata
```

## Array / Table Issues

### Array not found

**Symptoms**:
- `[tabread~ tablename]` creates but no output
- Console: "tablename: no such array"

**Cause**: Array not created or different name.

**Fix**:
1. Put → Array
2. Name must match exactly (case-sensitive)
3. Set size (will resize on `[soundfiler]` with `-resize`)
4. Check "Save contents" if you want table data saved with patch

### Wrong array size

**Symptom**: Sample plays too fast or too slow.

**Cause**: Array size doesn't match sample length.

**Fix**: Use `-resize` flag:
```
[read -resize filename.wav tablename(
|
[soundfiler]
```

This automatically resizes table to fit sample.
