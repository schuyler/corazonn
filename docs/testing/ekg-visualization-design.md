# EKG Visualization Tool - Design

## Overview

Simple development tool for visualizing live heartbeat IBI data from a single ESP32 sensor. Uses matplotlib animation to plot incoming OSC messages in real-time.

## Requirements

**Functional**
- Receive OSC messages from `/heartbeat/[0-3]` address pattern
- Plot IBI values (ms) over time as a scrolling waveform
- Display last 30 seconds of data
- Support selection of which sensor ID to monitor (0-3)
- Cross-platform (macOS, Linux, Windows)

**Non-functional**
- Simple implementation (~100-150 lines)
- Responsive UI (30 FPS animation)
- Thread-safe data handling

## Architecture

```
┌─────────────┐          ┌──────────────────┐          ┌─────────────┐
│  ESP32      │          │  EKG Viewer      │          │  matplotlib │
│  Firmware   │  ─OSC─>  │  (Python)        │  ─plot─> │  Window     │
│             │  UDP     │                  │          │             │
└─────────────┘          └──────────────────┘          └─────────────┘
                                  │
                                  ├─ OSC Thread (ThreadingOSCUDPServer)
                                  │  └─ Receives messages, appends to buffer
                                  │
                                  └─ Main Thread (matplotlib)
                                     └─ Animation loop reads buffer, updates plot
```

## Components

### 1. Data Buffer (thread-safe)
- `collections.deque` with maxlen for automatic size limiting
- Stores tuples: `(timestamp, ibi_value)`
- Protected by `threading.Lock`
- Size: ~30 seconds of data at 1 Hz = 30 samples

### 2. OSC Handler
- Uses `pythonosc.osc_server.ThreadingOSCUDPServer`
- Handler function validates and appends to buffer
- Validates:
  - Address pattern matches `/heartbeat/{sensor_id}`
  - IBI value in range [300, 3000] ms

### 3. Plot Manager
- matplotlib FuncAnimation for real-time updates
- Updates at 30 FPS
- X-axis: time (seconds relative to start)
- Y-axis: IBI (milliseconds)
- Auto-scaling Y-axis to data range

### 4. CLI Interface
- `--port` (default: 8000)
- `--sensor-id` (required: 0-3)
- `--window` (default: 30 seconds)

## Data Flow

1. **OSC Message Arrives** (OSC thread)
   - ThreadingOSCUDPServer receives UDP packet
   - Dispatcher routes to handler based on address pattern
   - Handler validates message format and IBI range
   - Acquires lock, appends `(time.time(), ibi_value)` to deque
   - Releases lock

2. **Animation Update** (main thread, ~30 FPS)
   - FuncAnimation callback triggered
   - Acquires lock, copies buffer data
   - Releases lock
   - Computes relative timestamps (t - start_time)
   - Updates plot line data
   - matplotlib redraws

3. **Buffer Management**
   - deque automatically evicts old samples when full
   - No manual cleanup needed

## Implementation Notes

### Threading Model
- **OSC thread**: Handles incoming messages via ThreadingOSCUDPServer
- **Main thread**: Runs matplotlib event loop and animation
- **Synchronization**: Single `threading.Lock` protects deque

### matplotlib Backend
- Cross-platform: Uses default backend (TkAgg, MacOSX, etc.)
- If issues on macOS, can force: `matplotlib.use('MacOSX')`

### Performance
- deque operations: O(1) append/pop
- Lock contention minimal (1 Hz message rate)
- Animation interval: 33ms (30 FPS) sufficient for 1 Hz data

### Example Usage
```bash
# Monitor sensor 0 on port 8000
python ekg_viewer.py --sensor-id 0

# Monitor sensor 2 on custom port, 60 second window
python ekg_viewer.py --sensor-id 2 --port 9000 --window 60
```

## Code Structure (~120 lines)

```
ekg_viewer.py
├─ Imports (10 lines)
├─ EKGViewer class (80 lines)
│  ├─ __init__(port, sensor_id, window)
│  ├─ osc_handler(address, *args)  # Validate & append to buffer
│  ├─ animation_update(frame)      # Read buffer, update plot
│  └─ run()                        # Setup & start
└─ main() with argparse (30 lines)
```

## Testing Considerations

1. **Unit Testing** (optional for dev tool)
   - Validate IBI range checking
   - Test buffer overflow behavior

2. **Integration Testing**
   - Use existing `esp32_simulator.py` to send test data
   - Verify plot updates in real-time
   - Test with sensor IDs 0-3

3. **Manual Testing**
   - Connect to live ESP32
   - Verify smooth scrolling
   - Check responsiveness with window resize

## Future Enhancements (out of scope)

- Multi-sensor view (split panes or overlays)
- BPM calculation and display
- Data export (CSV, screenshots)
- Statistics overlay (avg IBI, BPM range)
- Color-coded BPM zones (calm/neutral/excited)

## References

- OSC message format: `docs/firmware/guides/phase1-04-osc-messaging.md`
- Existing receiver: `testing/osc_receiver.py`
- ESP32 firmware: `firmware/heartbeat_phase1/src/main.cpp`
- pythonosc docs: https://python-osc.readthedocs.io/
