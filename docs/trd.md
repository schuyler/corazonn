# Heartbeat Installation - Lighting Bridge MVP TRD v1.1
## Python OSC → Wyze Smart Bulb Control

**Version:** 1.1  
**Date:** 2025-11-09  
**Purpose:** Define MVP lighting bridge requirements for heartbeat-synchronized ambient lighting  
**Audience:** Coding agent implementing Python bridge  
**Hardware:** 4-6 Wyze Color Bulbs A19  
**Dependencies:** Pure Data audio system (sends lighting OSC messages)

**Estimated Implementation Time:** 3-4 hours

---

## 1. Objective

Implement Python bridge that receives OSC lighting commands from Pure Data and controls Wyze smart bulbs to create heartbeat-synchronized ambient lighting effects.

**MVP Scope:**
- Single lighting mode: individual heartbeat pulses per zone
- 4 bulbs (one per sensor/participant)
- BPM-to-color mapping
- Saturation pulse effect (desaturated → full color)
- Wyze Cloud API control

**Out of MVP Scope:**
- Group breathing mode, convergence detection, zone waves
- Multiple lighting modes, Launchpad controls
- Local bulb control (WiFi direct)
- Latency compensation

**Success Criteria:**
- Bridge receives OSC messages from Pd
- Bulbs pulse in sync with heartbeats (within 1 second)
- Color reflects BPM (blue=slow, red=fast)
- 4 bulbs operate independently
- Runs for 30+ minutes without crashes

---

## 2. Architecture

### 2.1 Data Flow

```
Pure Data Patch
      ↓
   OSC/UDP (port 8001)
      ↓
Python OSC Receiver (blocking event loop)
      ↓
Effect Calculation (BPM→color, pulse parameters)
      ↓
Wyze API Client (HTTP requests, rate limited)
      ↓
Wyze Cloud → Smart Bulbs
```

### 2.2 Execution Model

**Single-threaded architecture:**
- Blocking OSC server (`pythonosc.osc_server.BlockingOSCUDPServer`)
- OSC handlers process messages synchronously
- Wyze API calls block until response (no async/threading)
- Rate limiting via request timestamps

**Rationale:** Simple, predictable, adequate for 4 bulbs at <1 Hz per bulb

---

## 3. Configuration

### 3.1 Configuration File

**File:** `lighting/config.yaml`

```yaml
wyze:
  email: "user@example.com"
  password: "secure_password"

osc:
  listen_port: 8001
  pd_ip: "127.0.0.1"

bulbs:
  - id: "ABCDEF123456"  # MAC address from bulb-discovery.py
    name: "NW Corner"
    zone: 0
  - id: "ABCDEF123457"
    name: "NE Corner"
    zone: 3
  - id: "ABCDEF123458"
    name: "SW Corner"
    zone: 1
  - id: "ABCDEF123459"
    name: "SE Corner"
    zone: 2

effects:
  baseline_brightness: 50    # Percent (constant)
  baseline_saturation: 100   # Percent (full color)
  pulse_saturation: 40       # Percent (desaturated/white)
  fade_time_ms: 600          # Return to baseline
  pulse_delay_ms: 200        # Hold at pulse_saturation

api:
  timeout_seconds: 5
  retry_attempts: 2

logging:
  level: INFO
  file: "logs/lighting.log"
  max_bytes: 10485760  # 10MB
```

**Config validation rules:**
- **R1:** Port: 1-65535
- **R1a:** Brightness/Saturation: 0-100
- **R1b:** Time values: > 0
- **R1c:** Bulb zones: 0-3, unique
- **R1d:** Bulb IDs: non-empty
- **R2:** Exit with specific error if validation fails

**Example config:** `lighting/config.yaml.example` (copy of above with placeholder values)

### 3.2 Bulb Discovery Tool

**File:** `tools/bulb-discovery.py`

**Requirements:**
- **R3:** List all Wyze bulbs on account
- **R3a:** Print MAC address (for config.yaml `id` field)
- **R3b:** Print nickname, model, online status

```python
#!/usr/bin/env python3
"""Discover Wyze bulb MAC addresses for config.yaml"""
import argparse
from wyze_sdk import Client

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()
    
    client = Client(email=args.email, password=args.password)
    bulbs = client.bulbs.list()
    
    print(f"Found {len(bulbs)} bulbs:\n")
    for bulb in bulbs:
        print(f"Name: {bulb.nickname}")
        print(f"  ID (for config): {bulb.mac}")
        print(f"  Model: {bulb.product_model}")
        print(f"  Online: {bulb.device_params.get('online', False)}")
        print()

if __name__ == '__main__':
    main()
```

---

## 4. OSC Protocol

### 4.1 Message Format

**Pulse trigger:**
```
Address: /light/N/pulse
Arguments: <int32> ibi_ms
Example: /light/0/pulse 847
```

**Requirements:**
- **R4:** Bridge MUST listen on port 8001
- **R5:** MUST accept `/light/N/pulse` where N=0-3
- **R6:** MUST validate IBI range 300-3000ms
- **R7:** Log invalid messages as warnings, continue processing

### 4.2 Pure Data Integration

**Pd sends pulse on each heartbeat:**
```
[r beat-N]
|
[t b f]
|
[pack f N]
|
[prepend /light]
|
[prepend N]
|
[prepend /pulse]
|
[oscformat]
|
[udpsend 127.0.0.1 8001]
```

---

## 5. Effect Implementation

### 5.1 BPM to Color Mapping

**Algorithm:**
```python
def bpm_to_hue(bpm: float) -> int:
    """Map BPM to hue (0-360 degrees).
    
    40 BPM  → 240° (blue, calm)
    80 BPM  → 120° (green, neutral)  
    120 BPM → 0°   (red, excited)
    """
    bpm_clamped = max(40, min(120, bpm))
    hue = 240 - ((bpm_clamped - 40) / 80) * 240
    return int(hue)
```

**Requirements:**
- **R8:** Calculate BPM: `bpm = 60000 / ibi_ms`
- **R9:** Clamp BPM to 40-120 for color mapping
- **R10:** Linear mapping: 40 BPM=240°, 120 BPM=0°

### 5.2 Saturation Pulse Effect

**Design:** Two API calls create desaturated flash then fade back to full color

**Timing:**
```
Baseline (sat=100%) → Pulse (sat=40%, whitish) → Baseline (sat=100%)
├─── instant ────┤──── 200ms hold ──┤──── 600ms fade ────┤
```

**Implementation:**
```python
def execute_pulse(bulb_id: str, hue: int, config: dict, wyze_client):
    """Execute two-call pulse effect."""
    baseline_bri = config['effects']['baseline_brightness']
    pulse_sat = config['effects']['pulse_saturation']
    baseline_sat = config['effects']['baseline_saturation']
    fade_ms = config['effects']['fade_time_ms']
    
    # Call 1: Instant jump to desaturated (whitish)
    wyze_client.set_color(bulb_id, hue, pulse_sat, baseline_bri, 
                          transition_ms=0)
    
    # Hold
    time.sleep(config['effects']['pulse_delay_ms'] / 1000)
    
    # Call 2: Fade back to full color
    wyze_client.set_color(bulb_id, hue, baseline_sat, baseline_bri,
                          transition_ms=fade_ms)
```

**Requirements:**
- **R11:** MUST use two API calls per pulse
- **R11a:** First: set saturation=40% instantly (transition=0ms)
- **R11b:** Delay 200ms
- **R11c:** Second: set saturation=100% with 600ms fade
- **R12:** Keep brightness constant at 50%
- **R13:** Keep hue constant during pulse (changes between pulses)

---

## 6. Wyze API Client

### 6.1 Library Selection

**Library:** `wyze-sdk` (official Python SDK)

**Installation:**
```bash
pip install wyze-sdk
```

### 6.2 API Operations

**Authentication:**
```python
from wyze_sdk import Client

client = Client(email=config['wyze']['email'], 
                password=config['wyze']['password'])
client.refresh()  # Get tokens
```

**Control bulb:**
```python
client.bulbs.set_color(
    device_mac=bulb_id,
    color_temp=None,  # Disable white mode, use RGB
    color={
        'hue': hue,        # 0-360
        'saturation': sat, # 0-100
        'brightness': bri  # 1-100
    }
)
```

**Note:** wyze-sdk doesn't expose transition_ms parameter. Bulbs use default ~300ms transition. Acceptable for MVP, but less control than desired.

**Requirements:**
- **R15:** Authenticate on startup
- **R16:** Handle auth failure (print error, exit code 1)
- **R17:** Set color using HSB values
- **R18:** Disable color_temp for RGB mode
- **R19:** Accept wyze-sdk transition limitation

### 6.3 Rate Limiting

**Wyze API limit:** ~1 request/second per bulb (empirical)

**Impact at 2 calls/pulse:**

| BPM | Pulse Rate | Calls/sec | Drop Rate |
|-----|------------|-----------|-----------|
| 40  | 0.67 Hz    | 1.34/s    | ~25% |
| 60  | 1.0 Hz     | 2.0/s     | ~50% |
| 80  | 1.33 Hz    | 2.66/s    | ~60% |
| 120 | 2.0 Hz     | 4.0/s     | ~75% |

**At typical resting heart rate (60-80 BPM), expect 50-60% drop rate. Acceptable for MVP ambient effect.**

**Implementation:**
```python
class RateLimiter:
    def __init__(self, min_interval_sec: float = 1.0):
        self.min_interval = min_interval_sec
        self.last_request = {}
    
    def should_drop(self, bulb_id: str) -> bool:
        now = time.time()
        last = self.last_request.get(bulb_id, 0)
        
        if now - last >= self.min_interval:
            self.last_request[bulb_id] = now
            return False
        return True
```

**Requirements:**
- **R20:** Rate limit to 1 request/sec per bulb
- **R21:** If exceeded, drop ENTIRE pulse (both calls)
- **R21a:** Log drops at WARNING (max 1 log/sec aggregate)
- **R22:** Track drop statistics per bulb

---

## 7. Implementation Structure

### 7.1 File Organization

```
lighting/
├── config.yaml
├── config.yaml.example
├── requirements.txt
├── logs/
│   └── lighting.log
├── src/
│   ├── main.py              # Entry point, config loading
│   ├── osc_receiver.py      # OSC server + effect logic
│   └── wyze_client.py       # API wrapper + rate limiting
└── tests/
    ├── test_effects.py
    ├── test_integration.py
    └── test_standalone.py   # Test without Pure Data
```

### 7.2 main.py

```python
"""Heartbeat Lighting Bridge - MVP v1.1"""

import yaml
import logging
from pathlib import Path
from osc_receiver import start_osc_server
from wyze_client import WyzeClient

def load_config(path: str) -> dict:
    """Load and validate configuration."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found: {path}\n"
            f"Copy config.yaml.example to config.yaml and edit."
        )
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    validate_config(config)
    return config

def validate_config(config: dict):
    """R1a-d: Validate all config parameters."""
    port = config['osc']['listen_port']
    if not (1 <= port <= 65535):
        raise ValueError(f"Invalid port: {port}")
    
    for key in ['baseline_brightness', 'pulse_saturation', 'baseline_saturation']:
        val = config['effects'][key]
        if not (0 <= val <= 100):
            raise ValueError(f"Invalid {key}: {val} (must be 0-100)")
    
    for key in ['fade_time_ms', 'pulse_delay_ms']:
        val = config['effects'][key]
        if val <= 0:
            raise ValueError(f"Invalid {key}: {val} (must be > 0)")
    
    zones = [b['zone'] for b in config['bulbs']]
    if len(zones) != len(set(zones)):
        raise ValueError("Duplicate bulb zones")
    if any(z not in range(4) for z in zones):
        raise ValueError("Bulb zones must be 0-3")
    
    if any(not b['id'] for b in config['bulbs']):
        raise ValueError("Bulb ID cannot be empty")

def setup_logging(config: dict):
    """R39-R42: Configure logging."""
    from logging.handlers import RotatingFileHandler
    
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    handlers = [
        RotatingFileHandler(
            config['logging']['file'],
            maxBytes=config['logging']['max_bytes'],
            backupCount=3
        ),
        logging.StreamHandler()
    ]
    
    logging.basicConfig(
        level=getattr(logging, config['logging']['level']),
        format='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )

def main():
    try:
        config = load_config('config.yaml')
        setup_logging(config)
        logger = logging.getLogger('main')
        
        # R22: Startup banner
        logger.info("=" * 60)
        logger.info("Heartbeat Lighting Bridge MVP v1.1")
        logger.info("=" * 60)
        
        # R23: Print bulb configuration
        for bulb in config['bulbs']:
            logger.info(f"Zone {bulb['zone']} → {bulb['name']} ({bulb['id']})")
        
        # R15, R16: Authenticate
        wyze = WyzeClient(config)
        wyze.authenticate()
        
        # R24: Initialize bulbs to baseline
        wyze.set_all_baseline()
        
        # R4: Start OSC server (blocks)
        start_osc_server(config, wyze)
        
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    except ValueError as e:
        print(f"ERROR: Invalid config: {e}")
        return 1
    except KeyboardInterrupt:
        logger = logging.getLogger('main')
        logger.info("Shutting down...")
        # R43: Print stats
        wyze.print_stats()
        return 0
    except Exception as e:
        logger = logging.getLogger('main')
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())
```

**New requirements:**
- **R22:** Print startup banner
- **R23:** Print bulb→zone mappings
- **R24:** Initialize all bulbs to baseline on startup
- **R43:** Print drop statistics on clean shutdown

### 7.3 osc_receiver.py

```python
"""OSC receiver and effect engine."""

from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import logging
import re
import time

logger = logging.getLogger('osc')

def bpm_to_hue(bpm: float) -> int:
    """R8-R10: Map BPM to hue."""
    bpm_clamped = max(40, min(120, bpm))
    hue = 240 - ((bpm_clamped - 40) / 80) * 240
    return int(hue)

def get_bulb_for_zone(zone: int, config: dict) -> str:
    """Map zone to bulb ID."""
    for bulb in config['bulbs']:
        if bulb['zone'] == zone:
            return bulb['id']
    return None

def handle_pulse(address: str, ibi_ms: int, wyze_client, config: dict):
    """Handle /light/N/pulse message."""
    try:
        # R5: Parse zone
        match = re.match(r'/light/(\d+)/pulse', address)
        if not match:
            logger.warning(f"Invalid address: {address}")
            return
        
        zone = int(match.group(1))
        
        # R6: Validate IBI
        if not (300 <= ibi_ms <= 3000):
            logger.warning(f"IBI out of range: {ibi_ms}ms (zone {zone})")
            return
        
        # R25a: Validate zone has bulb
        bulb_id = get_bulb_for_zone(zone, config)
        if bulb_id is None:
            logger.warning(f"No bulb configured for zone {zone}")
            return
        
        # R8-R10: Calculate BPM and hue
        bpm = 60000 / ibi_ms
        hue = bpm_to_hue(bpm)
        
        logger.debug(f"Pulse: zone={zone} bpm={bpm:.1f} hue={hue}")
        
        # R11-R13, R20-R22: Execute pulse (rate-limited)
        wyze_client.pulse(bulb_id, hue, zone)
        
    except Exception as e:
        # R25: Log error but continue
        logger.error(f"Error handling pulse: {e}", exc_info=True)

def start_osc_server(config: dict, wyze_client):
    """Start blocking OSC server."""
    dispatcher = Dispatcher()
    
    from functools import partial
    handler = partial(handle_pulse, 
                      wyze_client=wyze_client, 
                      config=config)
    dispatcher.map("/light/*/pulse", handler)
    
    # R27: Bind to all interfaces
    server = BlockingOSCUDPServer(
        ("0.0.0.0", config['osc']['listen_port']),
        dispatcher
    )
    
    logger.info(f"OSC server listening on port {config['osc']['listen_port']}")
    
    # R28: Graceful shutdown (handled by main)
    server.serve_forever()
```

**New requirements:**
- **R25:** Don't crash on bulb error
- **R25a:** Validate zone has configured bulb
- **R26:** Use BlockingOSCUDPServer
- **R27:** Bind to 0.0.0.0
- **R28:** Graceful KeyboardInterrupt

### 7.4 wyze_client.py

```python
"""Wyze API client with rate limiting."""

from wyze_sdk import Client
import time
import logging

logger = logging.getLogger('wyze')

class WyzeClient:
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        self.rate_limiter = RateLimiter()
        self.drop_stats = {}
    
    def authenticate(self):
        """R15-R16: Authenticate with Wyze."""
        try:
            self.client = Client(
                email=self.config['wyze']['email'],
                password=self.config['wyze']['password']
            )
            self.client.bulbs.list()  # Test auth
            logger.info("Wyze authentication successful")
        except Exception as e:
            logger.error(f"Wyze authentication failed: {e}")
            raise SystemExit(1)
    
    def set_all_baseline(self):
        """R24: Set all bulbs to baseline."""
        baseline_bri = self.config['effects']['baseline_brightness']
        baseline_sat = self.config['effects']['baseline_saturation']
        
        for bulb in self.config['bulbs']:
            try:
                self.client.bulbs.set_color(
                    device_mac=bulb['id'],
                    color_temp=None,
                    color={'hue': 120, 'saturation': baseline_sat, 
                           'brightness': baseline_bri}
                )
                logger.info(f"Initialized {bulb['name']} to baseline")
            except Exception as e:
                logger.error(f"Failed to init {bulb['name']}: {e}")
    
    def pulse(self, bulb_id: str, hue: int, zone: int):
        """R11-R13: Execute two-call pulse effect."""
        # R21: Check rate limit BEFORE calls
        if self.rate_limiter.should_drop(bulb_id):
            self._record_drop(bulb_id, zone)
            return
        
        try:
            baseline_bri = self.config['effects']['baseline_brightness']
            pulse_sat = self.config['effects']['pulse_saturation']
            baseline_sat = self.config['effects']['baseline_saturation']
            
            # R11a: Call 1 - instant desaturation
            self._set_color(bulb_id, hue, pulse_sat, baseline_bri)
            
            # R11b: Hold
            time.sleep(self.config['effects']['pulse_delay_ms'] / 1000)
            
            # R11c: Call 2 - fade back
            self._set_color(bulb_id, hue, baseline_sat, baseline_bri)
            
        except Exception as e:
            logger.error(f"Pulse failed for bulb {bulb_id}: {e}")
    
    def _set_color(self, bulb_id: str, hue: int, sat: int, bri: int):
        """R17-R19: Wyze API call."""
        self.client.bulbs.set_color(
            device_mac=bulb_id,
            color_temp=None,
            color={'hue': hue, 'saturation': sat, 'brightness': bri}
        )
    
    def _record_drop(self, bulb_id: str, zone: int):
        """R21a: Record and log dropped pulse."""
        self.drop_stats[bulb_id] = self.drop_stats.get(bulb_id, 0) + 1
        
        if not hasattr(self, '_last_drop_log'):
            self._last_drop_log = 0
        
        if time.time() - self._last_drop_log >= 1.0:
            logger.warning(f"Pulse dropped for zone {zone} (rate limit)")
            self._last_drop_log = time.time()
    
    def print_stats(self):
        """R43: Print drop statistics."""
        if not self.drop_stats:
            logger.info("No pulses dropped")
            return
        
        logger.info("Drop statistics:")
        for bulb_id, count in self.drop_stats.items():
            bulb = next((b for b in self.config['bulbs'] 
                        if b['id'] == bulb_id), None)
            name = bulb['name'] if bulb else bulb_id
            logger.info(f"  {name}: {count} pulses dropped")

class RateLimiter:
    """R20: Per-bulb rate limiting."""
    def __init__(self, min_interval_sec: float = 1.0):
        self.min_interval = min_interval_sec
        self.last_request = {}
    
    def should_drop(self, bulb_id: str) -> bool:
        now = time.time()
        last = self.last_request.get(bulb_id, 0)
        
        if now - last >= self.min_interval:
            self.last_request[bulb_id] = now
            return False
        return True
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**File:** `lighting/tests/test_effects.py`

```python
import sys
sys.path.insert(0, 'src')
from osc_receiver import bpm_to_hue, get_bulb_for_zone

def test_bpm_to_hue():
    assert bpm_to_hue(40) == 240   # Blue
    assert bpm_to_hue(80) == 120   # Green
    assert bpm_to_hue(120) == 0    # Red

def test_bpm_clamping():
    assert bpm_to_hue(30) == 240
    assert bpm_to_hue(150) == 0

def test_get_bulb_for_zone():
    config = {
        'bulbs': [
            {'zone': 0, 'id': 'ABC123'},
            {'zone': 2, 'id': 'DEF456'}
        ]
    }
    assert get_bulb_for_zone(0, config) == 'ABC123'
    assert get_bulb_for_zone(2, config) == 'DEF456'
    assert get_bulb_for_zone(1, config) is None
```

### 8.2 Standalone Bridge Test

**File:** `lighting/tests/test_standalone.py`

```python
"""Test bridge without Pure Data."""

from pythonosc import udp_client
import time

def test_standalone():
    client = udp_client.SimpleUDPClient('127.0.0.1', 8001)
    
    test_data = [
        (0, 1000),  # 60 BPM
        (1, 833),   # 72 BPM
        (2, 1034),  # 58 BPM
        (3, 750),   # 80 BPM
    ]
    
    print("Sending test pulses for 30 seconds...")
    print("Watch bulbs for color-coded pulses")
    
    start = time.time()
    while time.time() - start < 30:
        for zone, ibi in test_data:
            client.send_message(f'/light/{zone}/pulse', ibi)
            time.sleep(ibi / 1000)

if __name__ == '__main__':
    test_standalone()
```

**Requirements:**
- **R29:** Standalone test provided
- **R30:** Tests all 4 zones independently
- **R31:** Runs 30 seconds minimum

### 8.3 Live Testing

**Manual procedure:**

1. Discover bulbs: `python tools/bulb-discovery.py --email ... --password ...`
2. Configure config.yaml with real bulb IDs
3. Start bridge: `python src/main.py`
4. Run standalone test: `python tests/test_standalone.py`
5. Verify zone→bulb mappings and colors

**Requirements:**
- **R32:** Manual test with all 4 bulbs successful
- **R33:** Each zone pulses at expected rate (±20% due to drops)
- **R34:** Colors match BPM specification
- **R35:** No crashes over 30 minutes

---

## 9. Error Handling

### 9.1 Startup Errors

**Requirements:**
- **R33:** Print specific, actionable error messages
- **R34:** Test Wyze auth before starting OSC server
- **R35:** Exit code 1 on startup errors

**Messages:**
```
ERROR: Config not found: config.yaml
Copy config.yaml.example to config.yaml and edit.

ERROR: Invalid config: Invalid port: 70000

ERROR: Wyze authentication failed: Invalid credentials

ERROR: [Errno 48] Address already in use
Port 8001 is in use. Kill other process or change config.
```

### 9.2 Runtime Errors

**Requirements:**
- **R36:** Don't crash on single bulb failure
- **R37:** Log all errors to file
- **R38:** Continue processing other bulbs

**Messages:**
```
WARNING: No bulb configured for zone 5
WARNING: IBI out of range: 5000ms (zone 2)
ERROR: Pulse failed for bulb ABC123: Timeout
ERROR: Pulse failed for bulb ABC123: Device not found (offline?)
```

---

## 10. Logging

### 10.1 Levels

**INFO:** Startup, config, auth, bulb init  
**DEBUG:** Each pulse (zone, BPM, hue)  
**WARNING:** Invalid messages, rate drops, zone not configured  
**ERROR:** API failures, auth issues

**Requirements:**
- **R39:** Log to file AND console
- **R40:** Console: INFO+
- **R41:** File: DEBUG+
- **R42:** Rotate at 10MB, keep 3 backups

### 10.2 Format

```
2025-11-09 14:32:15.123 INFO [main] Heartbeat Lighting Bridge MVP v1.1
2025-11-09 14:32:15.456 INFO [wyze] Wyze authentication successful
2025-11-09 14:32:16.789 INFO [osc] OSC server listening on port 8001
2025-11-09 14:32:17.012 DEBUG [osc] Pulse: zone=0 bpm=60.0 hue=120
2025-11-09 14:32:17.234 WARNING [wyze] Pulse dropped for zone 0 (rate limit)
```

---

## 11. Deployment

### 11.1 Installation

```bash
cd lighting
pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edit config.yaml
python src/main.py
```

### 11.2 Dependencies

**File:** `lighting/requirements.txt`

```
wyze-sdk>=1.3.0
python-osc>=1.9.0
PyYAML>=6.0
```

---

## 12. Acceptance Criteria

**MVP Complete:**

- ✅ Bridge receives OSC on port 8001
- ✅ Config validation catches errors
- ✅ All 4 bulbs pulse independently
- ✅ Colors map to BPM (blue→green→red)
- ✅ Pulses visible (desaturated flash)
- ✅ No crashes over 30 minutes
- ✅ Rate limiting prevents API errors
- ✅ Drop statistics logged
- ✅ Handles offline bulbs gracefully
- ✅ Standalone test works (no Pd dependency)

**Known Limitations:**
- 50-75% pulse drop rate at typical BPM
- Cannot control transition timing (wyze-sdk)
- 300-500ms cloud API latency
- Single effect mode only

---

## 13. Future Enhancements

- Multiple lighting modes
- Baseline brightness enforcement  
- Latency compensation
- Raw HTTP API for transition control
- Local bulb control (WiFi direct)
- Launchpad integration
- Drop rate optimization

---

*End of Technical Reference Document*

**Document Version:** 1.1  
**Last Updated:** 2025-11-09  
**Status:** Ready for MVP implementation  
**Estimated Effort:** 3-4 hours implementation + 1 hour testing
