# Working with OSC

Quick reference for sending and receiving OSC messages in Pure Data.

## Receive OSC Messages

```
[udpreceive PORT]
|
[unpackOSC]
|
[routeOSC /address/pattern]
|
[process value]
```

**Requirements**:
- mrpeach library: `[declare -lib mrpeach]`
- Firewall allows UDP on PORT

**Debug**: Add `[print OSC-DEBUG]` after `[unpackOSC]` to see all messages.

## Send OSC Messages

```
[r trigger-source]
|
[prepend /address/pattern]
|
[packOSC]
|
[udpsend]
|
[connect IP PORT(
```

**For lighting bridge** (localhost:8001):
```
[connect 127.0.0.1 8001(
```

**Key points**:
- `[connect]` only needs to happen once (use `[loadbang]`)
- Fire-and-forget (no confirmation that message was received)

---

**Related documentation**:
- See common-tasks-testing-validation.md for testing OSC with test-osc-sender.py
- See common-tasks-integration-setup.md for declaring mrpeach library
