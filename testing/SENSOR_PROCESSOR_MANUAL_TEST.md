# Sensor Processor Manual Testing Guide

## Overview
This guide provides manual testing steps for validating sensor_processor.py

## Prerequisites
- Python 3 with pythonosc and numpy installed
- Three terminal windows

## Test 1: Basic Functionality

### Setup
Terminal 1 - Start sensor processor:
```bash
cd /home/user/corazonn
python3 testing/sensor_processor.py
```

Terminal 2 - Start beat sink (audio output):
```bash
cd /home/user/corazonn
python3 testing/ppg_test_sink.py --port 8001
```

Terminal 3 - Start beat sink (lighting output):
```bash
cd /home/user/corazonn
python3 testing/ppg_test_sink.py --port 8002
```

### Run Test
In a fourth terminal, run:
```bash
cd /home/user/corazonn
python3 testing/test_sensor_processor.py
```

### Expected Results
1. Sensor processor should start and listen on port 8000
2. Both sinks should receive beat messages
3. No error messages about invalid input
4. Beat messages should show reasonable BPM values (30-150 range)
5. State transitions visible in processor output

## Test 2: Input Validation

### Test Invalid PPG ID
```bash
python3 -c "
from pythonosc.udp_client import SimpleUDPClient
client = SimpleUDPClient('127.0.0.1', 8000)
client.send_message('/ppg/5', [2048, 2048, 2048, 2048, 2048, 1000])
"
```

**Expected:** Processor shows WARNING about invalid address pattern

### Test Out of Range ADC
```bash
python3 -c "
from pythonosc.udp_client import SimpleUDPClient
client = SimpleUDPClient('127.0.0.1', 8000)
client.send_message('/ppg/0', [5000, 2048, 2048, 2048, 2048, 1000])
"
```

**Expected:** Processor shows WARNING about sample out of range

### Test Wrong Argument Count
```bash
python3 -c "
from pythonosc.udp_client import SimpleUDPClient
client = SimpleUDPClient('127.0.0.1', 8000)
client.send_message('/ppg/0', [2048, 2048, 2048, 1000])
"
```

**Expected:** Processor shows WARNING about wrong argument count

## Test 3: State Machine

### Verify Warmup Period
Send 250 samples and verify no beats are detected until after warmup:

```bash
python3 << 'EOF'
from pythonosc.udp_client import SimpleUDPClient
import time
import numpy as np

client = SimpleUDPClient('127.0.0.1', 8000)

# Generate heartbeat signal
for i in range(300):
    t = i / 50.0  # 50Hz sample rate
    value = int(2048 + 300 * np.sin(2 * np.pi * 1.0 * t))  # 60 BPM
    value = max(0, min(4095, value))

    # Send as bundle of 5 samples
    if i % 5 == 0:
        bundle = [value] * 5
        client.send_message('/ppg/0', bundle + [i * 20])
        time.sleep(0.1)  # 100ms between bundles

        if i == 245:
            print(f"Sent {i+5} samples - should still be in warmup, no beats yet")
        elif i == 255:
            print(f"Sent {i+5} samples - now active, beats should start appearing")
EOF
```

**Expected:**
- No beat messages before sample 250
- Beat messages appear after sample 250

### Verify Noise Rejection
Watch processor output as noise test runs - should see state transitions

## Test 4: Beat Detection Accuracy

Send known BPM signal and verify detected BPM matches:

```bash
python3 << 'EOF'
from pythonosc.udp_client import SimpleUDPClient
import time
import numpy as np

client = SimpleUDPClient('127.0.0.1', 8000)

BPM = 75  # Test with 75 BPM
heart_rate_hz = BPM / 60.0

print(f"Sending signal at {BPM} BPM for 20 seconds...")

for i in range(1000):  # 20 seconds at 50Hz
    t = i / 50.0
    value = int(2048 + 400 * np.sin(2 * np.pi * heart_rate_hz * t))
    value = max(0, min(4095, value))

    if i % 5 == 0:
        bundle = [value] * 5
        client.send_message('/ppg/1', bundle + [i * 20])
        time.sleep(0.1)

print("Done. Check sinks for detected BPM - should be around 75")
EOF
```

**Expected:** Detected BPM should be 75 ± 5

## Test 5: Multiple Sensors

Test all 4 sensors simultaneously:

```bash
python3 << 'EOF'
from pythonosc.udp_client import SimpleUDPClient
import time
import numpy as np

client = SimpleUDPClient('127.0.0.1', 8000)

print("Sending data to all 4 sensors with different BPMs...")

for i in range(500):  # 10 seconds
    t = i / 50.0

    # Different BPM for each sensor
    for ppg_id, bpm in enumerate([60, 75, 90, 105]):
        heart_rate_hz = bpm / 60.0
        value = int(2048 + 400 * np.sin(2 * np.pi * heart_rate_hz * t))
        value = max(0, min(4095, value))

        if i % 5 == 0:
            bundle = [value] * 5
            client.send_message(f'/ppg/{ppg_id}', bundle + [i * 20])

    time.sleep(0.1)

print("Done. Check sinks for beats from all 4 sensors")
EOF
```

**Expected:**
- Beat messages from all 4 PPG IDs (0, 1, 2, 3)
- Different BPM values: ~60, ~75, ~90, ~105

## Test 6: Statistics and Shutdown

Press Ctrl+C in the sensor processor terminal

**Expected:**
- Clean shutdown message
- Statistics printed showing:
  - Total messages
  - Valid/invalid counts
  - Beat messages sent

## Validation Checklist

- [ ] Syntax check passes (`python3 -m py_compile`)
- [ ] Basic instantiation works
- [ ] State machine: warmup → active transition at 250 samples
- [ ] State machine: active → paused on high noise (stddev > mean)
- [ ] State machine: paused → active after 2s of stable signal
- [ ] Beat detection: threshold crossing works
- [ ] Beat detection: first beat doesn't generate message (no IBI yet)
- [ ] Beat detection: second+ beats generate messages
- [ ] Debouncing: beats < 400ms apart are rejected
- [ ] IBI validation: only 400-2000ms IBIs accepted
- [ ] BPM calculation: uses median of last 5 IBIs
- [ ] Input validation: invalid PPG ID rejected
- [ ] Input validation: wrong arg count rejected
- [ ] Input validation: out of range ADC rejected
- [ ] Input validation: negative timestamp rejected
- [ ] Dual output: messages sent to both ports (8001 and 8002)
- [ ] CLI: help text displays correctly
- [ ] CLI: port arguments work
- [ ] Shutdown: Ctrl+C handled cleanly with statistics

## Success Criteria

✓ All automated tests pass
✓ Manual tests show expected behavior
✓ No runtime errors
✓ Clean shutdown
✓ Reasonable BPM detection (within ±10% of known signal)
