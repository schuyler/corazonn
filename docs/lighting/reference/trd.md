# Heartbeat Installation - Lighting Bridge MVP TRD v1.3
## Python OSC → Wyze Smart Bulb Control

**Version:** 1.3
**Date:** 2025-11-09
**Purpose:** Define MVP lighting bridge requirements for heartbeat-synchronized ambient lighting
**Audience:** Coding agent implementing Python bridge
**Hardware:** 4-6 Wyze Color Bulbs A19
**Dependencies:** Pure Data audio system (sends lighting OSC messages)

**Estimated Implementation Time:** 3-4 hours

**Related Documents:**
- `/docs/lighting/reference/design.md` - Complete lighting system vision (all features)
- This TRD implements MVP (Phase 1) only - individual heartbeat pulses

**Deferred Features:** See design.md for group breathing mode, convergence detection, zone waves, Launchpad controls, and multi-mode effects.

---

## 1. Objective

Implement Python bridge that receives OSC lighting commands from Pure Data and controls Wyze smart bulbs to create heartbeat-synchronized ambient lighting effects.

**MVP Scope:**
- Single lighting mode: individual heartbeat pulses per zone
- 4 bulbs (one per sensor/participant)
- BPM-to-color mapping
- Brightness pulse effect (baseline → peak → baseline fade)
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

**CRITICAL LIMITATION - Pulse Serialization:**
The `time.sleep()` call during pulse effects (200ms hold) blocks the OSC server thread. Multiple simultaneous zone pulses will be serialized - if 2+ zones pulse within 200ms of each other, the second will wait. At typical heart rates (60-80 BPM = 750-1000ms IBI), concurrent pulses are unlikely but possible. During the 200ms sleep, incoming OSC messages may be dropped by the OS UDP stack. Acceptable for MVP ambient effect.

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
  baseline_brightness: 40    # Percent (resting brightness)
  pulse_min: 20              # Percent (minimum brightness, for future use)
  pulse_max: 70              # Percent (peak brightness)
  baseline_saturation: 75    # Percent (constant, vibrant but not harsh)
  baseline_hue: 120          # Degrees (0-360, default green)
  fade_time_ms: 900          # Total pulse duration
  attack_time_ms: 200        # Rise to peak
  sustain_time_ms: 100       # Hold at peak

logging:
  console_level: INFO   # Console output level
  file_level: DEBUG     # Log file level
  file: "logs/lighting.log"
  max_bytes: 10485760   # 10MB
```

**Config validation rules:**
- **R1:** Port: 1-65535
- **R1a:** Brightness/Saturation: 0-100
- **R1b:** Hue: 0-360
- **R1c:** Time values: > 0
- **R1d:** Bulb zones: 0-3, unique
- **R1e:** Bulb IDs: non-empty
- **R1f:** All required config sections exist before access
- **R2:** Exit with specific error if validation fails

**Example config:** `lighting/config.yaml.example` (copy of above with placeholder values)

**Security Note:**
- Credentials stored in plain text in config.yaml
- **MUST** set file permissions: `chmod 600 config.yaml` to prevent unauthorized access
- Alternative approaches (environment variables, keyring) out of MVP scope
- **WARNING:** Never commit config.yaml to version control

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
- **R4a:** Bind to 0.0.0.0 (all interfaces) for compatibility
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

### 4.3 Network Binding

**Rationale for 0.0.0.0:**
- Binds to all network interfaces, not just 127.0.0.1 (localhost)
- Pure Data may send OSC from different localhost interfaces depending on configuration
- Ensures maximum compatibility with various Pd network object configurations
- UDP protocol has no message queue - packets dropped if server busy processing (acceptable for real-time heartbeat pulses)
- **Security consideration:** Binding to 0.0.0.0 allows connections from other machines on the network. For production use in multi-user environments, bind to 127.0.0.1 instead.

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

### 5.2 Brightness Pulse Effect

**Design:** Two API calls create brightness increase then fade back to baseline

**Timing:**
```
Baseline (40%) → Peak (70%) → Baseline (40%)
├─── 200ms rise ──┤── 100ms hold ──┤──── 600ms fade ────┤
Total duration: 900ms (matches natural heartbeat pulse)
```

**Implementation:**
```python
def execute_pulse(bulb_id: str, hue: int, config: dict, wyze_client):
    """Execute two-call brightness pulse effect."""
    baseline_bri = config['effects']['baseline_brightness']
    pulse_max = config['effects']['pulse_max']
    baseline_sat = config['effects']['baseline_saturation']

    # Call 1: Rise to peak brightness
    # Note: wyze-sdk doesn't expose transition_ms, bulb uses default ~300ms fade
    wyze_client.set_color(bulb_id, hue, baseline_sat, pulse_max)

    # Hold at peak (attack 200ms + sustain 100ms)
    time.sleep((config['effects']['attack_time_ms'] + config['effects']['sustain_time_ms']) / 1000)

    # Call 2: Fade back to baseline
    # Bulb automatically fades over ~300-600ms
    wyze_client.set_color(bulb_id, hue, baseline_sat, baseline_bri)
```

**Requirements:**
- **R11:** MUST use two API calls per pulse
- **R11a:** First: set brightness to pulse_max (70%) (bulb fades automatically ~300ms)
- **R11b:** Delay 300ms (attack + sustain time)
- **R11c:** Second: set brightness to baseline (40%) (bulb fades automatically ~300-600ms)
- **R12:** Keep saturation constant at 75%
- **R13:** Keep hue constant during pulse (changes between pulses based on BPM)

**Note:** wyze-sdk does not expose transition_ms parameter. Both calls execute with bulb's default hardware transition (~300ms fade). The exponential decay curve from design.md is simplified to linear decay due to this limitation. The config parameter `fade_time_ms` defines the intended total duration but actual timing is controlled by bulb firmware.

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

**Failure Handling:**
- **R16a:** If Wyze API unreachable, log error and continue (individual pulse fails, bridge keeps running)
- **R16b:** Offline bulbs log "Device not found" error, processing continues
- **R16c:** No timeout configuration in MVP (uses wyze-sdk defaults, typically 30s)
- **R16d:** Auth token expiration (~24 hours) requires manual bridge restart

**Requirements:**
- **R14:** Use wyze-sdk official library
- **R15:** Authenticate on startup
- **R16:** Handle auth failure (print error, exit code 1)
- **R17:** Set color using HSB values
- **R18:** Disable color_temp for RGB mode
- **R19:** Accept wyze-sdk transition limitation

### 6.3 Rate Limiting

**Wyze API limit:** ~1 request/second per bulb (empirical)

**Impact at 2 calls/pulse:**

Each pulse makes 2 API calls. To stay within 1 req/sec limit, the rate limiter enforces a minimum of 2 seconds between pulses (allowing 2 calls over 2 seconds = 1 call/sec average).

| BPM | Pulse Rate | Pulses Allowed | Drop Rate |
|-----|------------|----------------|-----------|
| 40  | 0.67 Hz    | 0.50 Hz        | ~25% |
| 60  | 1.0 Hz     | 0.50 Hz        | ~50% |
| 80  | 1.33 Hz    | 0.50 Hz        | ~62% |
| 120 | 2.0 Hz     | 0.50 Hz        | ~75% |

**At typical resting heart rate (60-80 BPM), expect 50-62% drop rate (every other pulse). Acceptable for MVP ambient effect.**

**Note:** Drop rates are theoretical calculations based on estimated API rate limits. Actual performance should be validated during live testing with real bulbs.

**Implementation:**
```python
class RateLimiter:
    def __init__(self, min_interval_sec: float = 2.0):  # 2 sec for 2 API calls
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
- **R20:** Rate limit to 1 pulse per 2 seconds per bulb (0.5 Hz, checked before first API call)
- **R21:** If exceeded, drop ENTIRE pulse (skip both API calls)
- **R21a:** Log drops at WARNING (max 1 log/sec aggregate)
- **R22:** Track drop statistics per bulb

**Rate Limiting Strategy: Drop-Based (Real-Time Priority)**

**Why drop-based instead of sleep-based?**
- **Real-time sync:** Lighting must stay synchronized with audio and actual heartbeats
- **Sleep-based would cause drift:** Delaying commands to respect rate limits causes lighting to lag behind the music
- **Better to drop than lag:** Dropping some pulses maintains sync with current heartbeats rather than showing delayed/stale pulses
- **Ambient effect tolerates drops:** At 50-62% drop rate, enough pulses still show through for ambient effect

**Alternative (sleep-based) rejected:** Would preserve all commands but cause cumulative latency, breaking sync with real-time heartbeat/audio experience.

**Rate Limiting Behavior:**
The rate limiter checks timestamps at the START of `pulse()`. If a pulse is allowed, the timestamp is updated immediately, and both API calls proceed without additional checks. This ensures:
1. Both calls are treated as a single atomic operation
2. If rate limit is exceeded, neither call executes (no partial pulse)
3. The 200ms sleep between calls does NOT count toward rate limiting
4. Minimum 2 seconds between pulses allows 2 API calls while staying within 1 req/sec limit per bulb
5. Effective API call rate: ~1 request per second per bulb (2 calls over 2 seconds)

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
"""Heartbeat Lighting Bridge - MVP v1.3"""

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
    """R1-R1f: Validate all config parameters."""
    # R1f: Check top-level sections exist
    required_sections = ['wyze', 'osc', 'bulbs', 'effects', 'logging']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    # R1: Port validation
    if 'listen_port' not in config['osc']:
        raise ValueError("Missing osc.listen_port")
    port = config['osc']['listen_port']
    if not (1 <= port <= 65535):
        raise ValueError(f"Invalid port: {port} (must be 1-65535)")

    # R1a: Brightness/Saturation validation
    required_effects = ['baseline_brightness', 'pulse_min', 'pulse_max',
                        'baseline_saturation', 'fade_time_ms', 'attack_time_ms', 'sustain_time_ms']
    for key in required_effects:
        if key not in config['effects']:
            raise ValueError(f"Missing effects.{key}")

    for key in ['baseline_brightness', 'pulse_min', 'pulse_max', 'baseline_saturation']:
        val = config['effects'][key]
        if not (0 <= val <= 100):
            raise ValueError(f"Invalid {key}: {val} (must be 0-100)")

    # R1b: Hue validation (optional)
    if 'baseline_hue' in config['effects']:
        hue = config['effects']['baseline_hue']
        if not (0 <= hue <= 360):
            raise ValueError(f"Invalid baseline_hue: {hue} (must be 0-360)")

    # R1c: Time values
    for key in ['fade_time_ms', 'attack_time_ms', 'sustain_time_ms']:
        val = config['effects'][key]
        if val <= 0:
            raise ValueError(f"Invalid {key}: {val} (must be > 0)")

    # R1d: Bulb zones
    if not config['bulbs']:
        raise ValueError("No bulbs configured")
    zones = [b['zone'] for b in config['bulbs']]
    if len(zones) != len(set(zones)):
        raise ValueError("Duplicate bulb zones")
    if any(z not in range(4) for z in zones):
        raise ValueError("Bulb zones must be 0-3")

    # R1e: Bulb IDs
    if any(not b.get('id') for b in config['bulbs']):
        raise ValueError("Bulb ID cannot be empty")

def setup_logging(config: dict):
    """R48-R51: Configure logging with per-handler levels."""
    from logging.handlers import RotatingFileHandler

    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # R50: File handler with DEBUG level
    file_handler = RotatingFileHandler(
        config['logging']['file'],
        maxBytes=config['logging']['max_bytes'],
        backupCount=3
    )
    file_level = config['logging'].get('file_level', 'DEBUG')
    file_handler.setLevel(getattr(logging, file_level))

    # R49: Console handler with INFO level
    console_handler = logging.StreamHandler()
    console_level = config['logging'].get('console_level', 'INFO')
    console_handler.setLevel(getattr(logging, console_level))

    # Set format on both handlers
    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # R51: Root logger at DEBUG to allow all messages through
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler]
    )

def main():
    try:
        config = load_config('config.yaml')
        setup_logging(config)
        logger = logging.getLogger('main')

        # R23: Startup banner
        logger.info("=" * 60)
        logger.info("Heartbeat Lighting Bridge MVP v1.3")
        logger.info("=" * 60)

        # R24: Print bulb configuration
        for bulb in config['bulbs']:
            logger.info(f"Zone {bulb['zone']} → {bulb['name']} ({bulb['id']})")

        # R15, R16: Authenticate
        wyze = WyzeClient(config)
        wyze.authenticate()

        # R25: Initialize bulbs to baseline
        wyze.set_all_baseline()

        # R4: Start OSC server (blocks)
        try:
            start_osc_server(config, wyze)
        except OSError as e:
            # R47: Helpful error for "Address already in use"
            # Handle both macOS (errno 48) and Linux (errno 98)
            import errno as errno_module
            if ('Address already in use' in str(e) or
                getattr(e, 'errno', None) in (48, 98, errno_module.EADDRINUSE)):
                logger.error("Address already in use")
                logger.error(f"Port {config['osc']['listen_port']} is in use. "
                           "Kill other process or change config.")
                return 1
            raise

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    except ValueError as e:
        print(f"ERROR: Invalid config: {e}")
        return 1
    except KeyboardInterrupt:
        logger = logging.getLogger('main')
        logger.info("Shutting down...")
        # R52: Print stats
        wyze.print_stats()
        return 0
    except Exception as e:
        logger = logging.getLogger('main')
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())
```

**Requirements:**
- **R23:** Print startup banner
- **R24:** Print bulb→zone mappings
- **R25:** Initialize all bulbs to baseline on startup
- **R47:** Catch OSError for "Address already in use" with helpful message
- **R52:** Print drop statistics on clean shutdown

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
        
        # R27: Validate zone has configured bulb
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
        # R26: Don't crash on individual bulb errors
        logger.error(f"Error handling pulse: {e}", exc_info=True)

def start_osc_server(config: dict, wyze_client):
    """Start blocking OSC server."""
    dispatcher = Dispatcher()
    
    from functools import partial
    handler = partial(handle_pulse, 
                      wyze_client=wyze_client, 
                      config=config)
    dispatcher.map("/light/*/pulse", handler)
    
    # R29: Bind to 0.0.0.0 (all interfaces)
    server = BlockingOSCUDPServer(
        ("0.0.0.0", config['osc']['listen_port']),
        dispatcher
    )
    
    logger.info(f"OSC server listening on port {config['osc']['listen_port']}")
    
    # R28: Graceful shutdown (handled by main)
    server.serve_forever()
```

**Requirements:**
- **R26:** Don't crash on individual bulb errors
- **R27:** Validate zone has configured bulb
- **R28:** Use BlockingOSCUDPServer
- **R29:** Bind to 0.0.0.0 (per R4a)
- **R30:** Graceful KeyboardInterrupt (handled in main)

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
        """R25: Set all bulbs to baseline."""
        baseline_bri = self.config['effects']['baseline_brightness']
        baseline_sat = self.config['effects']['baseline_saturation']
        baseline_hue = self.config['effects'].get('baseline_hue', 120)  # Default green

        for bulb in self.config['bulbs']:
            try:
                self.client.bulbs.set_color(
                    device_mac=bulb['id'],
                    color_temp=None,
                    color={'hue': baseline_hue, 'saturation': baseline_sat,
                           'brightness': baseline_bri}
                )
                logger.info(f"Initialized {bulb['name']} to baseline")
            except Exception as e:
                logger.error(f"Failed to init {bulb['name']}: {e}")
    
    def pulse(self, bulb_id: str, hue: int, zone: int):
        """R11-R13: Execute two-call brightness pulse effect."""
        # R21: Check rate limit BEFORE calls
        if self.rate_limiter.should_drop(bulb_id):
            self._record_drop(bulb_id, zone)
            return

        try:
            baseline_bri = self.config['effects']['baseline_brightness']
            pulse_max = self.config['effects']['pulse_max']
            baseline_sat = self.config['effects']['baseline_saturation']

            # R11a: Call 1 - rise to peak brightness
            self._set_color(bulb_id, hue, baseline_sat, pulse_max)

            # R11b: Hold at peak (attack + sustain)
            attack_sustain = (self.config['effects']['attack_time_ms'] +
                            self.config['effects']['sustain_time_ms']) / 1000
            time.sleep(attack_sustain)

            # R11c: Call 2 - fade back to baseline
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
    def __init__(self, min_interval_sec: float = 2.0):  # 2 sec for 2 API calls
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
from pathlib import Path

# R53: Use absolute path from test file location
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

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
- **R31:** Standalone test provided
- **R32:** Tests all 4 zones independently
- **R33:** Runs 30 seconds minimum
- **R53:** Test imports use Path-based absolute paths

### 8.3 Live Testing

**Manual procedure:**

1. Discover bulbs: `python tools/bulb-discovery.py --email ... --password ...`
2. Configure config.yaml with real bulb IDs
3. Start bridge: `python src/main.py`
4. Run standalone test: `python tests/test_standalone.py`
5. Verify zone→bulb mappings and colors

**Requirements:**
- **R34:** Manual test with all 4 bulbs successful
- **R35:** Each zone pulses at expected rate (±20% due to drops)
- **R36:** Colors match BPM specification
- **R37:** No crashes over 30 minutes

---

## 9. Error Handling

### 9.1 Startup Errors

**Requirements:**
- **R42:** Print specific, actionable error messages
- **R43:** Test Wyze auth before starting OSC server
- **R44:** Exit code 1 on startup errors

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
- **R45:** Don't crash on single bulb failure
- **R46:** Log all errors to file
- **R47a:** Continue processing other bulbs

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
- **R48:** Log to file AND console
- **R49:** Console: INFO+ (configurable via console_level)
- **R50:** File: DEBUG+ (configurable via file_level)
- **R51:** Rotate at 10MB (configurable), keep 3 backups (hardcoded)

### 10.2 Format

```
2025-11-09 14:32:15.123 INFO [main] Heartbeat Lighting Bridge MVP v1.2
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
# Edit config.yaml with your Wyze credentials and bulb IDs
chmod 600 config.yaml  # Security: restrict file permissions
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
- ✅ Pulses visible (brightness fade)
- ✅ No crashes over 30 minutes
- ✅ Rate limiting prevents API errors
- ✅ Drop statistics logged
- ✅ Handles offline bulbs gracefully
- ✅ Standalone test works (no Pd dependency)

**Known Limitations:**
- 50-75% pulse drop rate at typical BPM (theoretical, requires empirical testing)
- Exponential decay curve simplified to linear decay (wyze-sdk transition limitations)
- Cannot configure transition timing (wyze-sdk limitation, bulbs use ~300ms default fade)
- 300-500ms cloud API latency
- Single effect mode only
- 300ms blocking sleep serializes concurrent zone pulses (rare at typical heart rates)
- Plain text credentials in config file (file permissions user's responsibility)
- No API timeout configuration (uses wyze-sdk defaults ~30s)
- Auth token expiration (~24 hours) requires manual bridge restart
- No automatic retry on temporary API failures

---

## 13. Future Enhancements

- Async/threaded implementation to eliminate pulse serialization blocking
- Multiple lighting modes (group breathing, convergence detection, zone waves)
- Baseline brightness enforcement and drift correction
- Latency compensation for cloud API delays
- Raw HTTP API for precise transition timing control
- Local bulb control (WiFi direct) to reduce latency and drop rate
- Launchpad integration for mode switching
- Secure credential storage (keyring, environment variables)
- API timeout and retry configuration
- Automatic auth token refresh
- Message queue with configurable max size

---

*End of Technical Reference Document*

**Document Version:** 1.3
**Last Updated:** 2025-11-09
**Status:** Ready for MVP implementation
**Estimated Effort:** 3-4 hours implementation + 1 hour testing

---

## Revision History

**v1.2 → v1.3 (2025-11-09):**

**CRITICAL FIX - Effect Implementation:**
- Changed from saturation pulse to brightness pulse effect (Section 1, 5.2, 12)
- Saturation pulse (sat: 100%→40%→100%) was incorrect
- Corrected to brightness pulse (brightness: 40%→70%→40%, saturation constant at 75%)
- Matches design.md Effect 1 specification for natural heartbeat feel

**Configuration Changes:**
- Updated config.yaml effects section (Section 3.1)
- Removed: `pulse_saturation`, old `baseline_saturation` value
- Added: `pulse_min: 20`, `pulse_max: 70`, `attack_time_ms: 200`, `sustain_time_ms: 100`
- Changed `baseline_brightness` from 50% to 40% (consistent with design.md)
- Changed `baseline_saturation` to 75% (constant during pulse)
- Updated validation rules (Section 7.2)

**Code Updates:**
- Updated `wyze_client.py` `pulse()` method to vary brightness instead of saturation (Section 7.4)
- Updated `set_all_baseline()` to use correct baseline brightness
- Updated requirements R11-R13 to describe brightness pulse
- Updated all code examples and pseudo-code

**Documentation Improvements:**
- Added cross-references between trd.md and design.md (header)
- Documented rate limiting strategy rationale (Section 6.3)
  - Explains why drop-based is correct for real-time sync
  - Documents why sleep-based was rejected (causes drift/lag)
- Updated known limitations (Section 12)
  - Added note about exponential decay simplification
  - Corrected blocking sleep duration (300ms not 200ms)
- Updated acceptance criteria (brightness fade not desaturated flash)

**Version Bumps:**
- Header, main.py docstring, footer all updated to v1.3

**v1.1 → v1.2 (2025-11-09):**

**Critical Fixes:**
- Fixed rate limiting logic documentation - clarified both API calls are atomic operation (Section 6.3)
- Documented blocking sleep limitation and pulse serialization (Section 2.2)
- Fixed logging configuration to use per-handler levels (Section 7.2)
- Removed unused config parameters (api.timeout_seconds, api.retry_attempts, osc.pd_ip)
- Fixed config validation to check section existence before access (Section 7.2)
- Made baseline_hue configurable instead of hardcoded (Section 3.1, 7.4)
- Fixed duplicate requirement numbers (renumbered R23-R53)
- Removed transition_ms from code examples (SDK doesn't support it)
- Fixed test path fragility with Path(__file__) (Section 8.1)
- Added OSError handling for "Address already in use" (Section 7.2)
- Added security note about file permissions (Section 3.1)

**Documentation Improvements:**
- Added network binding rationale (Section 4.3)
- Added failure handling documentation (Section 6.2)
- Clarified drop rates are theoretical/untested (Section 6.3)
- Expanded known limitations with all MVP constraints (Section 12)
- Expanded future enhancements list (Section 13)
- Added chmod 600 to installation instructions (Section 11.1)

**Requirement Updates:**
- R1f: Validate config sections exist
- R4a: Bind to 0.0.0.0 for compatibility
- R14: Use wyze-sdk (was missing)
- R16a-d: Failure handling requirements
- R20: Updated to 1 pulse per 2 seconds (0.5 Hz)
- R42-R44: Startup error requirements (renumbered from R45-R47)
- R45-R47a: Runtime error requirements (renumbered from R39-R41)
- R48-R51: Logging requirements
- R53: Test import path requirement

**v1.2a (2025-11-09) - Post-Chico Review:**
- **CRITICAL FIX:** Corrected rate limiting from 1.0 sec to 2.0 sec interval to respect 1 req/sec API limit
- Fixed section ordering (4.2/4.3 were reversed)
- Fixed all version strings to v1.2 (were inconsistent)
- Fixed cross-platform errno handling (added Linux errno 98)
- Fixed duplicate R25 reference (changed to R26)
- Fixed R25a reference (changed to R27)
- Added missing R14 requirement
- Renumbered requirements to eliminate gaps (R42-R47a)
- Updated drop rate table to reflect 0.5 Hz pulse limit
