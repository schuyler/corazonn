# Pure Data Troubleshooting: Patch Creation

Common issues when creating patches and setting up basic objects.

**Related guides**: [Audio Troubleshooting](troubleshooting-audio.md), [Libraries & Advanced](troubleshooting-libraries-advanced.md)

## Patch Won't Open / Object Creation Failed

### Couldn't create object

**Symptoms**:
- Dashed border around object box
- Pd console: "couldn't create 'objectname'"

**Causes**:
1. Missing external library
2. Typo in object name (case-sensitive)
3. Missing abstraction file

**Solutions**:

**For externals**:
```
[declare -lib mrpeach -lib cyclone]
```
Add to top of main patch.

**Install missing externals**:
- Pd menu → Help → Find Externals
- Search for library name (e.g., "mrpeach")
- Click download

**For abstractions**:
- Verify .pd file exists in same directory or in search path
- Check spelling (case-sensitive)
- Add to search path: `[declare -path /path/to/abstractions]`

### DSP loop detected

**Symptoms**:
- Pd console: "DSP loop detected"
- Audio doesn't process

**Cause**: Feedback loop in signal graph (output connects back to input).

**Solution**: Use delay-based feedback:
```
[delwrite~ buffer 1000]  # 1000ms buffer
|
[delread~ buffer]
```

## OSC Messages Not Received

### Port not listening

**Check**:
```bash
sudo netstat -uln | grep 8000
```

**Should show**: `0.0.0.0:8000`

**If not**: `[udpreceive]` not created or wrong port number.

### Firewall blocking port

**Linux**:
```bash
sudo ufw allow 8000/udp
```

**Or disable** (for testing only):
```bash
sudo ufw disable
```

### Wrong IP address

**For local testing**: Use `127.0.0.1` (localhost)

**For network**: Use machine's LAN IP (e.g., `192.168.50.100`)

**Find IP**:
```bash
ip addr show
```

### Messages malformed

**Debug**:
```
[udpreceive 8000]
|
[print RAW-OSC]  # See what's received
|
[unpackOSC]
|
[print UNPACKED]  # See after parsing
```

**Check**: OSC address format `/path/to/destination`
