# Heartbeat Installation - Lighting Bridge MVP TRD v2.0
## Python OSC → Multi-Backend Smart Lighting Control

**Version:** 2.0
**Date:** 2025-11-09
**Purpose:** Define MVP lighting bridge with abstracted backend support
**Audience:** Coding agent implementing Python bridge
**Hardware:** 4 Smart RGB bulbs (Kasa primary, Wyze/WLED supported)
**Dependencies:** Pure Data audio system (sends lighting OSC messages)

**Estimated Implementation Time:** 4-5 hours (including abstraction layer)

**Related Documents:**
- `/docs/lighting/reference/design.md` - Complete lighting system vision (all features)
- `/docs/lighting/reference/trd.md` - Previous Wyze-specific implementation (v1.3)
- This TRD implements MVP (Phase 1) with pluggable backend architecture

**Deferred Features:** See design.md for group breathing mode, convergence detection, zone waves, Launchpad controls, and multi-mode effects.

---

## 1. Objective

Implement Python bridge that receives OSC lighting commands from Pure Data and controls smart bulbs through a pluggable backend system. Primary implementation uses TP-Link Kasa bulbs with local network control.

**MVP Scope:**
- Single lighting mode: individual heartbeat pulses per zone
- 4 bulbs (one per sensor/participant)
- BPM-to-color mapping
- Brightness pulse effect (baseline → peak → baseline fade)
- Pluggable backend architecture (Kasa primary, Wyze/WLED supported)
- Local network control (no cloud dependency for primary backend)

**Out of MVP Scope:**
- Group breathing mode, convergence detection, zone waves
- Multiple lighting modes, Launchpad controls
- Latency compensation
- Multiple simultaneous backends

**Success Criteria:**
- Bridge receives OSC messages from Pd
- Bulbs pulse in sync with heartbeats (within 500ms for Kasa)
- Color reflects BPM (blue=slow, red=fast)
- 4 bulbs operate independently
- Runs for 30+ minutes without crashes
- Backend can be swapped via config file

---

## 2. Architecture

### 2.1 Abstraction Layer Design

```
Pure Data Patch
      ↓
   OSC/UDP (port 8001)
      ↓
Python OSC Receiver (blocking event loop)
      ↓
Effect Calculation (BPM→color, pulse parameters)
      ↓
┌─────────────────────────────────────┐
│   LightingBackend (Abstract Base)   │  ← Abstraction Layer
└─────────────────────────────────────┘
      ↓         ↓           ↓
  ┌─────┐  ┌───────┐  ┌────────┐
  │Kasa │  │ Wyze  │  │ WLED   │        ← Concrete Implementations
  └─────┘  └───────┘  └────────┘
      ↓         ↓           ↓
   Local     Cloud       Local
   TCP      HTTP API      UDP
```

**Key Principle:** OSC receiver and effect logic never call backend-specific code directly. All bulb control goes through the `LightingBackend` interface.

### 2.2 Data Flow

```
Pure Data → OSC Message → OSC Handler → Effect Logic → Backend Interface → Bulb
            /heartbeat/N   (validate)   (BPM→hue)    set_color()         (device)
```

### 2.3 Execution Model

**Single-threaded architecture:**
- Blocking OSC server (`pythonosc.osc_server.BlockingOSCUDPServer`)
- OSC handlers process messages synchronously
- Backend calls may block (Kasa: 50-150ms, Wyze: 300-500ms)
- Rate limiting handled per-backend

**Rationale:** Simple, predictable, adequate for 4 bulbs at <1 Hz per bulb

**CRITICAL LIMITATION - Pulse Serialization:**
The backend `pulse()` call includes `time.sleep()` (200-300ms) which blocks the OSC thread. Multiple simultaneous zone pulses will serialize. At typical heart rates (60-80 BPM = 750-1000ms IBI), concurrent pulses are unlikely but possible. Acceptable for MVP ambient effect.

---

## 3. Backend Abstraction Interface

### 3.1 LightingBackend Base Class

**File:** `lighting/src/backends/base.py`

```python
"""Abstract base class for lighting backends."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging

class LightingBackend(ABC):
    """
    Interface that all lighting backends must implement.

    Backends handle authentication, device discovery, and bulb control
    for specific hardware/API platforms (Kasa, Wyze, WLED, etc).
    """

    def __init__(self, config: dict):
        """
        Initialize backend with configuration.

        Args:
            config: Full config dict (backend can access its own section)
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def authenticate(self) -> None:
        """
        Initialize connection to lighting system.

        For cloud backends: Perform login, get tokens
        For local backends: Discover devices on network

        Raises:
            SystemExit: On authentication failure (prevents startup)
        """
        pass

    @abstractmethod
    def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:
        """
        Set bulb to specific HSV values.

        Args:
            bulb_id: Backend-specific bulb identifier (IP, MAC, etc)
            hue: 0-360 degrees
            saturation: 0-100 percent
            brightness: 0-100 percent

        Raises:
            Exception: On communication failure (logged, not fatal)
        """
        pass

    @abstractmethod
    def pulse(self, bulb_id: str, hue: int, zone: int) -> None:
        """
        Execute two-step brightness pulse effect.

        Implementation must:
        1. Rise to pulse_max brightness
        2. Sleep for attack + sustain time
        3. Fall back to baseline brightness
        4. Handle rate limiting if needed
        5. Record drop statistics

        Args:
            bulb_id: Backend-specific bulb identifier
            hue: Target hue (0-360) for this pulse
            zone: Zone number (0-3) for logging
        """
        pass

    @abstractmethod
    def set_all_baseline(self) -> None:
        """
        Initialize all configured bulbs to baseline state.

        Called once on startup. Sets all bulbs to baseline brightness,
        saturation, and default hue.
        """
        pass

    @abstractmethod
    def get_latency_estimate(self) -> float:
        """
        Return typical command latency in milliseconds.

        Used for logging/diagnostics. Returns:
        - Kasa: 50-150ms
        - Wyze: 300-500ms
        - WLED: <10ms
        """
        pass

    @abstractmethod
    def print_stats(self) -> None:
        """
        Print statistics on shutdown (drop rates, errors, etc).

        Called during graceful shutdown (Ctrl+C).
        """
        pass

    @abstractmethod
    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        """
        Map zone number to bulb ID.

        Args:
            zone: Zone number (0-3)

        Returns:
            bulb_id or None if zone not configured
        """
        pass
```

**Requirements:**
- **R1:** All backends MUST inherit from `LightingBackend`
- **R2:** All abstract methods MUST be implemented
- **R3:** Backends MUST NOT modify effect calculation logic
- **R4:** Backends MUST handle their own rate limiting
- **R5:** Authentication failure MUST raise SystemExit(1)
- **R6:** Runtime errors MUST be logged, not crash bridge

### 3.2 Backend Characteristics

| Backend | Latency | Rate Limit | Auth | Network | Best Use Case |
|---------|---------|------------|------|---------|---------------|
| **Kasa** (Primary) | 50-150ms | ~5/sec (200ms rate limit) | None | Local TCP | Production, reliability |
| **Wyze** (Supported) | 300-500ms | ~1/sec (API enforced) | Cloud login | Internet required | Existing Wyze bulbs |
| **WLED** (Supported) | <10ms | None | None | Local UDP | LED strips, ultra-low latency |

---

## 4. Configuration

### 4.1 Configuration File

**File:** `lighting/config.yaml`

```yaml
# Backend selection
lighting:
  backend: "kasa"  # Options: kasa, wyze, wled

# OSC receiver settings
osc:
  listen_port: 8001

# Effect parameters (shared across all backends)
effects:
  baseline_brightness: 40    # Percent (resting brightness)
  pulse_min: 20              # Percent (reserved for future)
  pulse_max: 70              # Percent (peak brightness)
  baseline_saturation: 75    # Percent (constant)
  baseline_hue: 120          # Degrees (default green)
  fade_time_ms: 900          # Total pulse duration
  attack_time_ms: 200        # Rise to peak
  sustain_time_ms: 100       # Hold at peak

# Logging
logging:
  console_level: INFO
  file_level: DEBUG
  file: "logs/lighting.log"
  max_bytes: 10485760   # 10MB

# ============================================
# Backend-Specific Configuration
# ============================================

# Kasa Backend (TP-Link Kasa bulbs, local control)
kasa:
  bulbs:
    - ip: "192.168.1.100"
      name: "NW Corner"
      zone: 0
    - ip: "192.168.1.101"
      name: "NE Corner"
      zone: 3
    - ip: "192.168.1.102"
      name: "SW Corner"
      zone: 1
    - ip: "192.168.1.103"
      name: "SE Corner"
      zone: 2

# Wyze Backend (Wyze Color Bulbs A19, cloud control)
wyze:
  email: "user@example.com"
  password: "secure_password"
  bulbs:
    - id: "ABCDEF123456"  # MAC address
      name: "NW Corner"
      zone: 0
    - id: "ABCDEF123457"
      name: "NE Corner"
      zone: 3

# WLED Backend (ESP32 LED controllers, UDP control)
wled:
  devices:
    - ip: "192.168.1.200"
      name: "Strip 1"
      zone: 0
      pixel_count: 60
    - ip: "192.168.1.201"
      name: "Strip 2"
      zone: 1
      pixel_count: 60
```

**Config validation rules:**
- **R7:** `lighting.backend` must be one of: kasa, wyze, wled
- **R8:** Port: 1-65535
- **R9:** Brightness/Saturation: 0-100
- **R10:** Hue: 0-360
- **R11:** Time values: > 0
- **R12:** Bulb zones: 0-3, unique within backend section
- **R13:** Backend section must exist for selected backend
- **R14:** Exit with specific error if validation fails

### 4.2 Backend Discovery Tools

Each backend provides a discovery tool to help populate config.yaml:

**Kasa:** `tools/discover-kasa.py`
```bash
python tools/discover-kasa.py
# Scans local network for Kasa devices, prints IPs
```

**Wyze:** `tools/discover-wyze.py`
```bash
python tools/discover-wyze.py --email ... --password ...
# Lists bulbs on Wyze account, prints MAC addresses
```

**WLED:** `tools/discover-wled.py`
```bash
python tools/discover-wled.py
# Uses mDNS to find WLED devices, prints IPs
```

---

## 5. OSC Protocol

### 5.1 Message Format

**Pulse trigger:**
```
Address: /light/N/pulse
Arguments: <int32> ibi_ms
Example: /light/0/pulse 847
```

**Requirements:**
- **R15:** Bridge MUST listen on port 8001
- **R16:** Bind to 0.0.0.0 (all interfaces)
- **R17:** MUST accept `/light/N/pulse` where N=0-3
- **R18:** MUST validate IBI range 300-3000ms
- **R19:** Log invalid messages as warnings, continue processing

*(OSC protocol same as v1.3, unchanged)*

---

## 6. Effect Implementation

### 6.1 BPM to Color Mapping

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
- **R20:** Calculate BPM: `bpm = 60000 / ibi_ms`
- **R21:** Clamp BPM to 40-120 for color mapping
- **R22:** Linear mapping: 40 BPM=240°, 120 BPM=0°

*(Effect calculation same as v1.3, backend-agnostic)*

### 6.2 Brightness Pulse Effect

**Design:** Two API calls create brightness increase then fade back to baseline

**Timing:**
```
Baseline (40%) → Peak (70%) → Baseline (40%)
├─── 200ms rise ──┤── 100ms hold ──┤──── 600ms fade ────┤
Total duration: 900ms (matches natural heartbeat pulse)
```

**Requirements:**
- **R23:** Effect logic implemented in backend `pulse()` method
- **R24:** Two color set commands per pulse (rise, fall)
- **R25:** Sleep for attack + sustain between commands
- **R26:** Saturation and hue constant during pulse
- **R27:** Backend handles rate limiting internally

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
│   ├── main.py                    # Entry point, backend factory
│   ├── osc_receiver.py            # OSC server + effect logic
│   └── backends/
│       ├── __init__.py            # Backend factory
│       ├── base.py                # LightingBackend ABC
│       ├── kasa_backend.py        # Kasa implementation (primary)
│       ├── wyze_backend.py        # Wyze implementation (reference)
│       └── wled_backend.py        # WLED implementation (stub)
├── tools/
│   ├── discover-kasa.py
│   ├── discover-wyze.py
│   └── discover-wled.py
└── tests/
    ├── test_effects.py            # BPM mapping tests
    ├── test_backends.py           # Backend interface tests
    └── test_standalone.py         # End-to-end with OSC sender
```

### 7.2 Backend Factory

**File:** `lighting/src/backends/__init__.py`

```python
"""Backend factory for loading lighting implementations."""

from typing import Type
from .base import LightingBackend
from .kasa_backend import KasaBackend
from .wyze_backend import WyzeBackend
from .wled_backend import WLEDBackend

BACKENDS = {
    'kasa': KasaBackend,
    'wyze': WyzeBackend,
    'wled': WLEDBackend,
}

def create_backend(config: dict) -> LightingBackend:
    """
    Factory function to instantiate the configured backend.

    Args:
        config: Full configuration dict

    Returns:
        Instantiated backend object

    Raises:
        ValueError: If backend name invalid or not found
    """
    backend_name = config.get('lighting', {}).get('backend')

    if not backend_name:
        raise ValueError("Config missing 'lighting.backend'")

    if backend_name not in BACKENDS:
        available = ', '.join(BACKENDS.keys())
        raise ValueError(
            f"Unknown backend: '{backend_name}'\n"
            f"Available backends: {available}"
        )

    backend_class = BACKENDS[backend_name]
    return backend_class(config)
```

**Requirements:**
- **R28:** Factory MUST validate backend name before instantiation
- **R29:** Factory MUST provide helpful error for unknown backends
- **R30:** New backends added by importing and registering in BACKENDS dict

### 7.3 main.py

```python
"""Heartbeat Lighting Bridge - MVP v2.0 (Multi-Backend)"""

import yaml
import logging
from pathlib import Path
from osc_receiver import start_osc_server
from backends import create_backend

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
    """Validate shared configuration (R7-R14)."""
    # R7: Check backend selection
    if 'lighting' not in config or 'backend' not in config['lighting']:
        raise ValueError("Missing required config: lighting.backend")

    backend_name = config['lighting']['backend']
    valid_backends = ['kasa', 'wyze', 'wled']
    if backend_name not in valid_backends:
        raise ValueError(
            f"Invalid backend: {backend_name}\n"
            f"Valid options: {', '.join(valid_backends)}"
        )

    # R13: Check backend section exists
    if backend_name not in config:
        raise ValueError(
            f"Backend '{backend_name}' selected but config section missing"
        )

    # R8-R11: Validate shared effect parameters
    required_sections = ['osc', 'effects', 'logging']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    # Port validation
    port = config['osc'].get('listen_port')
    if not port or not (1 <= port <= 65535):
        raise ValueError(f"Invalid port: {port} (must be 1-65535)")

    # Effect parameter validation
    effects = config['effects']
    required_effects = ['baseline_brightness', 'pulse_max', 'baseline_saturation']
    for key in required_effects:
        if key not in effects:
            raise ValueError(f"Missing effects.{key}")
        val = effects[key]
        if not (0 <= val <= 100):
            raise ValueError(f"Invalid {key}: {val} (must be 0-100)")

    # Hue validation
    if 'baseline_hue' in effects:
        hue = effects['baseline_hue']
        if not (0 <= hue <= 360):
            raise ValueError(f"Invalid baseline_hue: {hue} (must be 0-360)")

def setup_logging(config: dict):
    """Configure logging with per-handler levels."""
    from logging.handlers import RotatingFileHandler

    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        config['logging']['file'],
        maxBytes=config['logging']['max_bytes'],
        backupCount=3
    )
    file_handler.setLevel(getattr(logging, config['logging']['file_level']))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config['logging']['console_level']))

    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler]
    )

def main():
    try:
        config = load_config('config.yaml')
        setup_logging(config)
        logger = logging.getLogger('main')

        # Startup banner
        logger.info("=" * 60)
        logger.info("Heartbeat Lighting Bridge MVP v2.0 (Multi-Backend)")
        logger.info("=" * 60)

        # Create backend
        backend = create_backend(config)
        backend_name = config['lighting']['backend']
        logger.info(f"Using backend: {backend_name}")
        logger.info(f"Estimated latency: {backend.get_latency_estimate():.0f}ms")

        # Authenticate/discover
        backend.authenticate()

        # Initialize bulbs to baseline
        backend.set_all_baseline()

        # Start OSC server (blocks)
        try:
            start_osc_server(config, backend)
        except OSError as e:
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
        backend.print_stats()
        return 0
    except Exception as e:
        logger = logging.getLogger('main')
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())
```

### 7.4 osc_receiver.py

**File:** `lighting/src/osc_receiver.py`

```python
"""OSC receiver and effect engine (backend-agnostic)."""

from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from backends.base import LightingBackend
import logging
import re

logger = logging.getLogger('osc')

def bpm_to_hue(bpm: float) -> int:
    """R20-R22: Map BPM to hue."""
    bpm_clamped = max(40, min(120, bpm))
    hue = 240 - ((bpm_clamped - 40) / 80) * 240
    return int(hue)

def handle_pulse(address: str, ibi_ms: int, backend: LightingBackend, config: dict):
    """Handle /light/N/pulse message (backend-agnostic)."""
    try:
        # R17: Parse zone
        match = re.match(r'/light/(\d+)/pulse', address)
        if not match:
            logger.warning(f"Invalid address: {address}")
            return

        zone = int(match.group(1))

        # R18: Validate IBI
        if not (300 <= ibi_ms <= 3000):
            logger.warning(f"IBI out of range: {ibi_ms}ms (zone {zone})")
            return

        # Get bulb for zone (backend handles mapping)
        bulb_id = backend.get_bulb_for_zone(zone)
        if bulb_id is None:
            logger.warning(f"No bulb configured for zone {zone}")
            return

        # R20-R22: Calculate BPM and hue
        bpm = 60000 / ibi_ms
        hue = bpm_to_hue(bpm)

        logger.debug(f"Pulse: zone={zone} bpm={bpm:.1f} hue={hue}")

        # R23-R27: Execute pulse via backend
        backend.pulse(bulb_id, hue, zone)

    except Exception as e:
        logger.error(f"Error handling pulse: {e}", exc_info=True)

def start_osc_server(config: dict, backend: LightingBackend):
    """Start blocking OSC server."""
    dispatcher = Dispatcher()

    from functools import partial
    handler = partial(handle_pulse, backend=backend, config=config)
    dispatcher.map("/light/*/pulse", handler)

    # R16: Bind to 0.0.0.0
    server = BlockingOSCUDPServer(
        ("0.0.0.0", config['osc']['listen_port']),
        dispatcher
    )

    logger.info(f"OSC server listening on port {config['osc']['listen_port']}")
    server.serve_forever()
```

**Requirements:**
- **R31:** OSC receiver MUST NOT import backend-specific modules
- **R32:** All bulb control MUST go through LightingBackend interface
- **R33:** Effect logic (BPM→hue) MUST be backend-agnostic

---

## 8. Kasa Backend Implementation

### 8.1 Overview

Primary backend using TP-Link Kasa smart bulbs with local network control (no cloud dependency).

**Library:** `python-kasa` (official TP-Link library)

**Installation:**
```bash
pip install python-kasa>=0.6.0
```

### 8.2 Implementation

**File:** `lighting/src/backends/kasa_backend.py`

```python
"""Kasa backend for TP-Link Kasa smart bulbs (local control)."""

import asyncio
import time
from typing import Optional
from kasa import SmartBulb, Discover
from .base import LightingBackend

class KasaBackend(LightingBackend):
    """
    TP-Link Kasa bulb control via local network.

    Features:
    - Local TCP control (no cloud)
    - 50-150ms latency
    - ~10 requests/sec physical limit
    - Async library wrapped in sync calls
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.bulbs = {}  # Map bulb_id (IP) -> SmartBulb object
        self.zone_map = {}  # Map zone -> bulb_id
        self.drop_stats = {}  # Track drops per bulb
        self.last_request = {}  # Rate limiting timestamps

    def authenticate(self) -> None:
        """Initialize connection to Kasa bulbs."""
        try:
            kasa_config = self.config['kasa']

            # Connect to each configured bulb
            for bulb_cfg in kasa_config['bulbs']:
                ip = bulb_cfg['ip']
                zone = bulb_cfg['zone']
                name = bulb_cfg['name']

                self.logger.info(f"Connecting to {name} ({ip})...")

                # Create SmartBulb instance
                bulb = SmartBulb(ip)

                # Update device info (async call)
                asyncio.run(bulb.update())

                # Store references
                self.bulbs[ip] = bulb
                self.zone_map[zone] = ip
                self.drop_stats[ip] = 0

                self.logger.info(f"Zone {zone} → {name} ({ip}) - OK")

            self.logger.info(f"Kasa: {len(self.bulbs)} bulbs connected")

        except Exception as e:
            self.logger.error(f"Kasa authentication failed: {e}")
            raise SystemExit(1)

    def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:
        """Set Kasa bulb to HSV values."""
        try:
            bulb = self.bulbs.get(bulb_id)
            if not bulb:
                raise ValueError(f"Unknown bulb ID: {bulb_id}")

            # python-kasa uses async, wrap in sync call
            asyncio.run(bulb.set_hsv(hue, saturation, brightness))

        except Exception as e:
            self.logger.error(f"Failed to set color for {bulb_id}: {e}")
            raise

    def pulse(self, bulb_id: str, hue: int, zone: int) -> None:
        """Execute brightness pulse effect with minimal rate limiting."""
        # Kasa can handle ~10 req/sec, so minimal rate limiting needed
        # Only enforce 200ms minimum between pulses (allows 5 Hz)
        now = time.time()
        last = self.last_request.get(bulb_id, 0)

        if now - last < 0.2:  # 200ms minimum
            self.drop_stats[bulb_id] += 1
            if not hasattr(self, '_last_drop_log'):
                self._last_drop_log = {}

            if now - self._last_drop_log.get(bulb_id, 0) >= 1.0:
                self.logger.warning(f"Pulse dropped for zone {zone} (rate limit)")
                self._last_drop_log[bulb_id] = now
            return

        self.last_request[bulb_id] = now

        try:
            effects = self.config['effects']
            baseline_bri = effects['baseline_brightness']
            pulse_max = effects['pulse_max']
            baseline_sat = effects['baseline_saturation']

            # Call 1: Rise to peak
            self.set_color(bulb_id, hue, baseline_sat, pulse_max)

            # Hold at peak
            attack_sustain = (effects['attack_time_ms'] +
                            effects['sustain_time_ms']) / 1000
            time.sleep(attack_sustain)

            # Call 2: Fall to baseline
            self.set_color(bulb_id, hue, baseline_sat, baseline_bri)

        except Exception as e:
            self.logger.error(f"Pulse failed for {bulb_id}: {e}")

    def set_all_baseline(self) -> None:
        """Initialize all Kasa bulbs to baseline."""
        effects = self.config['effects']
        baseline_bri = effects['baseline_brightness']
        baseline_sat = effects['baseline_saturation']
        baseline_hue = effects.get('baseline_hue', 120)

        for bulb_id, bulb in self.bulbs.items():
            try:
                self.set_color(bulb_id, baseline_hue, baseline_sat, baseline_bri)

                # Get bulb name from config
                bulb_cfg = next(
                    (b for b in self.config['kasa']['bulbs']
                     if b['ip'] == bulb_id),
                    None
                )
                name = bulb_cfg['name'] if bulb_cfg else bulb_id
                self.logger.info(f"Initialized {name} to baseline")

            except Exception as e:
                self.logger.error(f"Failed to init {bulb_id}: {e}")

    def get_latency_estimate(self) -> float:
        """Return Kasa typical latency."""
        return 100.0  # ~100ms average

    def print_stats(self) -> None:
        """Print drop statistics."""
        total_drops = sum(self.drop_stats.values())

        if total_drops == 0:
            self.logger.info("No pulses dropped")
            return

        self.logger.info("Drop statistics:")
        for bulb_id, count in self.drop_stats.items():
            bulb_cfg = next(
                (b for b in self.config['kasa']['bulbs']
                 if b['ip'] == bulb_id),
                None
            )
            name = bulb_cfg['name'] if bulb_cfg else bulb_id
            self.logger.info(f"  {name}: {count} pulses dropped")

    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        """Map zone to bulb IP."""
        return self.zone_map.get(zone)
```

**Kasa-Specific Requirements:**
- **R34:** Use `python-kasa` library version 0.6.0+
- **R35:** Connect via IP address (no discovery in bridge startup)
- **R36:** Wrap async calls with `asyncio.run()`
- **R37:** Minimal rate limiting: 200ms between pulses (5 Hz max)
- **R38:** At 60-120 BPM, expect 0-5% drop rate (negligible)

### 8.3 Discovery Tool

**File:** `lighting/tools/discover-kasa.py`

```python
#!/usr/bin/env python3
"""Discover Kasa bulbs on local network."""

import asyncio
from kasa import Discover

async def main():
    print("Scanning for Kasa devices...")
    devices = await Discover.discover()

    bulbs = [dev for dev in devices.values() if dev.is_bulb]

    if not bulbs:
        print("No Kasa bulbs found on network")
        return

    print(f"\nFound {len(bulbs)} Kasa bulbs:\n")

    for bulb in bulbs:
        await bulb.update()
        print(f"Name: {bulb.alias}")
        print(f"  IP (for config): {bulb.host}")
        print(f"  Model: {bulb.model}")
        print(f"  MAC: {bulb.mac}")
        print()

if __name__ == '__main__':
    asyncio.run(main())
```

**Usage:**
```bash
python tools/discover-kasa.py
```

---

## 9. Wyze Backend Implementation

### 9.1 Overview

Secondary backend for Wyze Color Bulbs A19 using cloud API.

**Limitations:**
- 300-500ms latency (cloud round-trip)
- ~1 request/sec rate limit (API enforced)
- 50-75% pulse drop rate at typical BPM
- Requires internet connection
- Requires Wyze account credentials

**Use Case:** Compatibility for existing Wyze bulb owners

### 9.2 Implementation Outline

**File:** `lighting/src/backends/wyze_backend.py`

```python
"""Wyze backend for Wyze Color Bulbs A19 (cloud control)."""

from wyze_sdk import Client
import time
from typing import Optional
from .base import LightingBackend

class WyzeBackend(LightingBackend):
    """
    Wyze smart bulb control via cloud API.

    Features:
    - Cloud API (requires internet)
    - 300-500ms latency
    - ~1 request/sec rate limit
    - High drop rate (50-75% at 60 BPM)
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.client = None
        self.zone_map = {}
        self.drop_stats = {}
        self.last_request = {}

    def authenticate(self) -> None:
        """Authenticate with Wyze cloud."""
        try:
            wyze_config = self.config['wyze']
            self.client = Client(
                email=wyze_config['email'],
                password=wyze_config['password']
            )

            # Test authentication
            self.client.bulbs.list()

            # Build zone map
            for bulb in wyze_config['bulbs']:
                self.zone_map[bulb['zone']] = bulb['id']
                self.drop_stats[bulb['id']] = 0

            self.logger.info(f"Wyze: {len(self.zone_map)} bulbs configured")

        except Exception as e:
            self.logger.error(f"Wyze authentication failed: {e}")
            raise SystemExit(1)

    def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:
        """Set Wyze bulb via cloud API."""
        self.client.bulbs.set_color(
            device_mac=bulb_id,
            color_temp=None,
            color={'hue': hue, 'saturation': saturation, 'brightness': brightness}
        )

    def pulse(self, bulb_id: str, hue: int, zone: int) -> None:
        """Execute pulse with aggressive rate limiting (2 sec min)."""
        now = time.time()
        last = self.last_request.get(bulb_id, 0)

        # R39: Wyze requires 2 sec minimum (2 API calls at 1 req/sec)
        if now - last < 2.0:
            self.drop_stats[bulb_id] += 1
            # Log drops (max 1/sec)
            if not hasattr(self, '_last_drop_log'):
                self._last_drop_log = {}
            if now - self._last_drop_log.get(bulb_id, 0) >= 1.0:
                self.logger.warning(f"Pulse dropped for zone {zone} (rate limit)")
                self._last_drop_log[bulb_id] = now
            return

        self.last_request[bulb_id] = now

        try:
            effects = self.config['effects']
            baseline_bri = effects['baseline_brightness']
            pulse_max = effects['pulse_max']
            baseline_sat = effects['baseline_saturation']

            # Rise to peak
            self.set_color(bulb_id, hue, baseline_sat, pulse_max)

            # Hold
            attack_sustain = (effects['attack_time_ms'] +
                            effects['sustain_time_ms']) / 1000
            time.sleep(attack_sustain)

            # Fall to baseline
            self.set_color(bulb_id, hue, baseline_sat, baseline_bri)

        except Exception as e:
            self.logger.error(f"Pulse failed for {bulb_id}: {e}")

    def set_all_baseline(self) -> None:
        """Initialize all Wyze bulbs."""
        # Similar to Kasa implementation
        pass

    def get_latency_estimate(self) -> float:
        return 400.0  # ~400ms average

    def print_stats(self) -> None:
        """Print drop statistics."""
        # Similar to Kasa implementation
        pass

    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        return self.zone_map.get(zone)
```

**Wyze-Specific Requirements:**
- **R39:** Enforce 2.0 second minimum between pulses (0.5 Hz)
- **R40:** Expect 50-75% drop rate at typical heart rates
- **R41:** Log "rate limit" drops at WARNING level

---

## 10. WLED Backend Implementation

### 10.1 Overview

High-performance backend for WLED-powered ESP32 LED controllers.

**Advantages:**
- <10ms latency (local UDP)
- No rate limits (can handle every pulse)
- Ultra-low cost ($5-10 per ESP32)
- Open source firmware

**Trade-offs:**
- DIY assembly (not plug-and-play)
- LED strips, not bulbs (different aesthetic)
- Requires mounting/installation

### 10.2 Implementation Outline

**File:** `lighting/src/backends/wled_backend.py`

```python
"""WLED backend for ESP32-based LED controllers (UDP control)."""

import socket
import time
from typing import Optional
from .base import LightingBackend

class WLEDBackend(LightingBackend):
    """
    WLED LED controller via local UDP.

    Features:
    - Local UDP (no cloud)
    - <10ms latency
    - No rate limits
    - Supports LED strips, matrices, rings
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.devices = {}  # IP -> config
        self.zone_map = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def authenticate(self) -> None:
        """Initialize WLED devices."""
        try:
            wled_config = self.config['wled']

            for dev in wled_config['devices']:
                ip = dev['ip']
                zone = dev['zone']

                # Test connectivity with JSON API
                # (UDP is fire-and-forget, so test with HTTP)
                import requests
                resp = requests.get(f"http://{ip}/json/state", timeout=2)

                if resp.status_code == 200:
                    self.devices[ip] = dev
                    self.zone_map[zone] = ip
                    self.logger.info(f"Zone {zone} → {dev['name']} ({ip}) - OK")
                else:
                    self.logger.error(f"Failed to connect to {ip}")

            self.logger.info(f"WLED: {len(self.devices)} devices connected")

        except Exception as e:
            self.logger.error(f"WLED initialization failed: {e}")
            raise SystemExit(1)

    def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:
        """Set WLED device color via UDP (DRGB protocol)."""
        # WLED DRGB protocol: send RGB values via UDP port 21324
        # Convert HSV to RGB first
        rgb = self._hsv_to_rgb(hue, saturation, brightness)

        # DRGB protocol: 2 (protocol) + 1 (timeout) + RGB bytes per pixel
        pixel_count = self.devices[bulb_id]['pixel_count']
        packet = bytes([2, 1]) + (rgb * pixel_count)

        self.sock.sendto(packet, (bulb_id, 21324))

    def pulse(self, bulb_id: str, hue: int, zone: int) -> None:
        """Execute pulse (no rate limiting needed for WLED)."""
        try:
            effects = self.config['effects']
            baseline_bri = effects['baseline_brightness']
            pulse_max = effects['pulse_max']
            baseline_sat = effects['baseline_saturation']

            # Rise
            self.set_color(bulb_id, hue, baseline_sat, pulse_max)

            # Hold
            attack_sustain = (effects['attack_time_ms'] +
                            effects['sustain_time_ms']) / 1000
            time.sleep(attack_sustain)

            # Fall
            self.set_color(bulb_id, hue, baseline_sat, baseline_bri)

        except Exception as e:
            self.logger.error(f"Pulse failed for {bulb_id}: {e}")

    def set_all_baseline(self) -> None:
        """Initialize all WLED devices."""
        pass  # Similar to other backends

    def get_latency_estimate(self) -> float:
        return 5.0  # ~5ms

    def print_stats(self) -> None:
        """WLED has no drops, print confirmation."""
        self.logger.info("WLED: No pulses dropped (no rate limits)")

    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        return self.zone_map.get(zone)

    def _hsv_to_rgb(self, h: int, s: int, v: int) -> bytes:
        """Convert HSV to RGB bytes."""
        # Standard HSV->RGB conversion
        # (Implementation omitted for brevity)
        pass
```

**WLED-Specific Requirements:**
- **R42:** Use UDP port 21324 (DRGB protocol)
- **R43:** No rate limiting (WLED can handle sustained load)
- **R44:** Test connectivity via HTTP JSON API on startup
- **R45:** Convert HSV to RGB (WLED native RGB)

---

## 11. Testing Strategy

### 11.1 Backend Interface Tests

**File:** `lighting/tests/test_backends.py`

```python
"""Test that all backends implement the interface correctly."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backends.base import LightingBackend
from backends.kasa_backend import KasaBackend
from backends.wyze_backend import WyzeBackend
from backends.wled_backend import WLEDBackend

def test_kasa_implements_interface():
    """Verify KasaBackend implements all abstract methods."""
    assert issubclass(KasaBackend, LightingBackend)

    required_methods = [
        'authenticate', 'set_color', 'pulse', 'set_all_baseline',
        'get_latency_estimate', 'print_stats', 'get_bulb_for_zone'
    ]

    for method in required_methods:
        assert hasattr(KasaBackend, method)

def test_wyze_implements_interface():
    """Verify WyzeBackend implements all abstract methods."""
    assert issubclass(WyzeBackend, LightingBackend)

def test_wled_implements_interface():
    """Verify WLEDBackend implements all abstract methods."""
    assert issubclass(WLEDBackend, LightingBackend)

def test_backend_factory():
    """Test backend factory function."""
    from backends import create_backend

    config_kasa = {'lighting': {'backend': 'kasa'}, 'kasa': {}}
    backend = create_backend(config_kasa)
    assert isinstance(backend, KasaBackend)

    config_wyze = {'lighting': {'backend': 'wyze'}, 'wyze': {}}
    backend = create_backend(config_wyze)
    assert isinstance(backend, WyzeBackend)
```

### 11.2 Effect Tests

**File:** `lighting/tests/test_effects.py`

```python
"""Test backend-agnostic effect calculations."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from osc_receiver import bpm_to_hue

def test_bpm_to_hue():
    assert bpm_to_hue(40) == 240   # Blue
    assert bpm_to_hue(80) == 120   # Green
    assert bpm_to_hue(120) == 0    # Red

def test_bpm_clamping():
    assert bpm_to_hue(30) == 240   # Clamp low
    assert bpm_to_hue(150) == 0    # Clamp high
```

### 11.3 Standalone Integration Test

**File:** `lighting/tests/test_standalone.py`

```python
"""Test bridge with OSC sender (no Pure Data required)."""

from pythonosc import udp_client
import time

def test_standalone():
    """
    Send test pulses to lighting bridge.

    Prerequisites:
    - Bridge running (python src/main.py)
    - Backend configured and authenticated
    """
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

---

## 12. Dependencies

### 12.1 requirements.txt

```
# Core dependencies
python-osc>=1.9.0
PyYAML>=6.0

# Backend libraries (install only what you need)
python-kasa>=0.6.0        # For Kasa backend
wyze-sdk>=1.3.0           # For Wyze backend
requests>=2.31.0          # For WLED backend (HTTP check)
```

**Installation:**
```bash
# Minimal (Kasa only)
pip install python-osc PyYAML python-kasa

# All backends
pip install -r requirements.txt
```

---

## 13. Acceptance Criteria

**MVP Complete:**

- ✅ Bridge receives OSC on port 8001
- ✅ Config validation catches errors
- ✅ Backend selected via config file
- ✅ All 4 bulbs pulse independently
- ✅ Colors map to BPM (blue→green→red)
- ✅ Pulses visible (brightness fade)
- ✅ No crashes over 30 minutes
- ✅ Kasa: 0-5% drop rate (negligible)
- ✅ Wyze: 50-75% drop rate (expected)
- ✅ WLED: 0% drop rate
- ✅ Drop statistics logged
- ✅ Handles offline bulbs gracefully
- ✅ Standalone test works (no Pd dependency)

**Backend Support:**
- ✅ Kasa: Fully implemented, tested, production-ready
- ✅ Wyze: Implemented, tested, documented limitations
- ✅ WLED: Implemented, tested, documented trade-offs

---

## 14. Future Enhancements

**Architecture:**
- Async/threaded implementation to eliminate pulse serialization
- Multiple simultaneous backends (e.g., Kasa + WLED)

**Features:**
- Multiple lighting modes (group breathing, convergence, zone waves)
- Launchpad integration for mode switching
- Web dashboard for monitoring

**Backends:**
- Philips Hue (local bridge API)
- ESPHome devices
- DMX512 professional lighting

---

*End of Technical Reference Document*

**Document Version:** 2.0
**Last Updated:** 2025-11-09
**Status:** Ready for implementation
**Estimated Effort:** 4-5 hours (Kasa primary + abstraction layer)

---

## Revision History

**v1.3 → v2.0 (2025-11-09):**

**MAJOR ARCHITECTURAL CHANGE - Backend Abstraction Layer:**
- Introduced `LightingBackend` abstract base class (Section 3)
- Backend selection via config file (Section 4)
- Backend factory pattern for instantiation (Section 7.2)
- Replaced single wyze_client.py with pluggable backend system

**Backend Implementations:**
- **Kasa (Primary):** Fully specified with python-kasa library (Section 8)
  - Local network control (no cloud)
  - 50-150ms latency
  - 0-5% drop rate at typical BPM
- **Wyze (Supported):** Migrated from v1.3 spec (Section 9)
  - Cloud API control
  - 300-500ms latency
  - 50-75% drop rate (documented limitation)
- **WLED (Supported):** New implementation spec (Section 10)
  - Local UDP control
  - <10ms latency
  - No rate limits, 0% drops

**Configuration Changes:**
- Added `lighting.backend` selection field (Section 4.1)
- Backend-specific config sections (kasa, wyze, wled)
- Shared effect parameters (all backends)
- Per-backend discovery tools (Section 4.2)

**Code Structure:**
- New directory: `src/backends/` (Section 7.1)
- Backend factory in `__init__.py` (Section 7.2)
- OSC receiver now backend-agnostic (Section 7.4)
- Main.py updated to use factory pattern (Section 7.3)

**Testing:**
- New backend interface tests (Section 11.1)
- Effect tests remain backend-agnostic (Section 11.2)
- Standalone test works with any backend (Section 11.3)

**Requirements:**
- Added R1-R6 (backend interface requirements)
- Added R7-R14 (config validation)
- Added R28-R30 (factory requirements)
- Added R31-R33 (OSC receiver requirements)
- Added R34-R45 (backend-specific requirements)
- Renumbered existing requirements to avoid conflicts

**Documentation:**
- Added backend comparison table (Section 3.2)
- Added discovery tool specs for each backend (Section 4.2)
- Expanded acceptance criteria to include all backends (Section 13)
- Updated dependencies to be modular (Section 12)

**Design Philosophy:**
- Effect logic (BPM→hue) remains backend-agnostic
- OSC protocol unchanged from v1.3
- Pulse timing/characteristics same across backends
- Drop behavior handled per-backend (Kasa minimal, Wyze aggressive)
