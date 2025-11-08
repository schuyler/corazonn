# Phase 1 Testing Infrastructure

OSC protocol simulation and validation environment for heartbeat installation project.

## Overview

This testing infrastructure validates the OSC messaging protocol before ESP32 hardware arrives. All code runs on a development machine (Linux/Mac/Windows).

**Components:**
- `esp32_simulator.py` - Simulates 1-4 ESP32 sensor units sending heartbeat messages
- `osc_receiver.py` - Validates OSC message format and tracks statistics
- `test_osc_protocol.py` - Unit tests for protocol correctness
- `test_integration.py` - End-to-end integration test

## Prerequisites

**Python:** Version 3.8 or higher

**Check Python version:**
```bash
python3 --version
```

## Installation

```bash
# Install dependencies
pip3 install -r requirements.txt

# Verify installation
python3 -c "from pythonosc import udp_client; print('OK')"
# Expected output: OK
```

**Optional: Use virtual environment (recommended)**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

pip3 install -r requirements.txt
```

## Quick Start

### 1. Run Unit Tests
```bash
python3 test_osc_protocol.py
```
Expected: All tests pass

### 2. Test Receiver + Simulator

**Terminal 1 - Start receiver:**
```bash
python3 osc_receiver.py --port 8000
```

**Terminal 2 - Start single sensor simulator:**
```bash
python3 esp32_simulator.py --sensors 1 --bpm 60
```

Expected: Receiver shows ~1 message/second from sensor 0

Stop both with Ctrl+C to see final statistics.

### 3. Multi-Sensor Test

**Terminal 1:**
```bash
python3 osc_receiver.py --port 8000
```

**Terminal 2 - Four sensors at different BPM:**
```bash
python3 esp32_simulator.py --sensors 4 --bpm 60,72,58,80
```

Expected: Receiver shows ~4 messages/second from sensors 0-3

### 4. Run Integration Test
```bash
python3 test_integration.py
```

Expected: Test completes successfully, all checks pass

## Usage

### OSC Receiver

```bash
python3 osc_receiver.py [OPTIONS]
```

**Options:**
- `--port N` - UDP port to listen on (default: 8000)
- `--stats-interval N` - Seconds between statistics output (default: 10)

**Example:**
```bash
python3 osc_receiver.py --port 9000 --stats-interval 5
```

**Output:**
- Each received message: `[/heartbeat/N] IBI: VALUE ms, BPM: VALUE`
- Statistics every 10 seconds
- Final statistics on Ctrl+C

### ESP32 Simulator

```bash
python3 esp32_simulator.py [OPTIONS]
```

**Options:**
- `--sensors N` - Number of sensors to simulate (1-4, default: 1)
- `--bpm CSV` - Comma-separated BPM values, one per sensor (default: 60)
- `--server IP` - Destination IP address (default: 127.0.0.1)
- `--port N` - Destination UDP port (default: 8000)

**Examples:**
```bash
# Single sensor at 60 BPM
python3 esp32_simulator.py --sensors 1 --bpm 60

# Four sensors at different rates
python3 esp32_simulator.py --sensors 4 --bpm 60,72,58,80

# Send to remote server
python3 esp32_simulator.py --sensors 4 --bpm 65,70,75,80 --server 192.168.1.100
```

**Output:**
- Each sent message: `[Sensor N] Sent /heartbeat/N IBI_VALUE (#COUNT)`
- Final statistics on Ctrl+C

## OSC Protocol Specification

**Address Pattern:** `/heartbeat/N` where N is sensor ID (0-3)

**Argument:** Single int32 value representing inter-beat interval (IBI) in milliseconds

**Valid Range:** 300-3000 ms

**Example Message:** `/heartbeat/0 847` (sensor 0, 847ms since last beat)

**Transport:** UDP over IPv4, port 8000 (configurable)

## Troubleshooting

### "Module not found: pythonosc"
```bash
pip3 install python-osc
python3 -c "from pythonosc import udp_client; print('OK')"
```

### "Address already in use"
Port 8000 is already bound. Either:
- Use different port: `--port 8001`
- Kill process using port (Linux/Mac): `lsof -ti:8000 | xargs kill`

### "No messages received"
1. Check firewall isn't blocking UDP port 8000
2. Verify both simulator and receiver use same port
3. For localhost testing, use `--server 127.0.0.1`

### Network debugging (Linux/Mac)
```bash
# Capture OSC traffic
sudo tcpdump -i lo port 8000 -A -c 10
```

## Success Criteria

Phase 1 testing infrastructure complete when:
- ✅ Unit tests pass (all 8+ tests)
- ✅ Simulator sends valid OSC messages for 1-4 sensors
- ✅ Receiver validates messages and tracks statistics
- ✅ Integration test passes
- ✅ 60-second stability test passes
- ✅ Message loss < 1% over 60 seconds
- ✅ BPM accuracy within ±2 BPM

## Reference

See `../docs/p1-tst-trd.md` for complete technical specification.

## Next Steps

After Phase 1 testing infrastructure is validated:
1. Proceed to Phase 1 firmware implementation (`../docs/p1-fw-trd.md`)
2. Implement ESP32 firmware with WiFi + OSC (no sensors yet)
3. Test firmware against this testing infrastructure
