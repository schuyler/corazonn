## Lighting Bridge Phase 1 - Python OSC → Multi-Backend Smart Lighting Control

Reference: `/home/user/corazonn/docs/lighting/reference/trd.md` (v2.0)

### Prerequisites

- [ ] **Task 0.1**: Verify Python 3.8+ installed
  - Run: `python3 --version`
  - Expected: Python 3.8.0 or higher
  - **Status**: Required for all Python components

- [ ] **Task 0.2**: Install core dependencies
  - Run: `pip3 install python-osc PyYAML`
  - Verify python-osc: `python3 -c "from pythonosc import osc_server; print('OK')"`
  - Verify PyYAML: `python3 -c "import yaml; print('OK')"`
  - Expected output: `OK` for both
  - **Status**: Core dependencies installed (backend libraries installed per-backend)

- [ ] **Task 0.3**: Install Kasa backend dependencies (primary backend)
  - Run: `pip3 install python-kasa>=0.6.0`
  - Verify: `python3 -c "from kasa import SmartBulb; print('OK')"`
  - Expected output: `OK`
  - **Status**: Kasa library installed (TRD R34)

- [ ] **Task 0.4**: Install Wyze backend dependencies (optional, for Wyze users)
  - Run: `pip3 install wyze-sdk>=1.3.0`
  - Verify: `python3 -c "from wyze_sdk import Client; print('OK')"`
  - Note: Skip if not using Wyze bulbs
  - **Status**: Wyze library installed if needed

- [ ] **Task 0.5**: Install WLED backend dependencies (optional, for WLED users)
  - Run: `pip3 install requests>=2.31.0`
  - Verify: `python3 -c "import requests; print('OK')"`
  - Note: Skip if not using WLED devices
  - **Status**: WLED dependencies installed if needed

- [ ] **Task 0.6**: Verify Pure Data audio pipeline running (TRD dependency)
  - Check: Pure Data patch from `/home/user/corazonn/audio/patches/heartbeat-main.pd` exists
  - Verify: Patch configured to send OSC to port 8001
  - Note: Lighting bridge receives from Pure Data, not ESP32s directly
  - **Status**: Audio pipeline available for integration testing

### Component 1: Project Structure

- [ ] **Task 1.1**: Create directory structure (TRD Section 7.1)
  - Create: `/home/user/corazonn/lighting/` (if not exists)
  - Create: `/home/user/corazonn/lighting/src/`
  - Create: `/home/user/corazonn/lighting/src/backends/`
  - Create: `/home/user/corazonn/lighting/tools/`
  - Create: `/home/user/corazonn/lighting/tests/`
  - Create: `/home/user/corazonn/lighting/logs/`
  - **Status**: Directory structure matches TRD Section 7.1

- [ ] **Task 1.2**: Create requirements.txt (TRD Section 12)
  - File: `/home/user/corazonn/lighting/requirements.txt`
  - Content from TRD Section 12.1:
    ```
    # Core dependencies
    python-osc>=1.9.0
    PyYAML>=6.0

    # Backend libraries (install only what you need)
    python-kasa>=0.6.0        # For Kasa backend
    wyze-sdk>=1.3.0           # For Wyze backend
    requests>=2.31.0          # For WLED backend (HTTP check)
    ```
  - **Status**: Dependencies documented for installation

- [ ] **Task 1.3**: Create config.yaml.example (TRD Section 4.1)
  - File: `/home/user/corazonn/lighting/config.yaml.example`
  - Copy entire YAML content from TRD Section 4.1
  - Include all three backend sections (kasa, wyze, wled)
  - Include comments explaining backend selection
  - **Status**: Example configuration ready for user customization

- [ ] **Task 1.4**: Create lighting README
  - File: `/home/user/corazonn/lighting/README.md`
  - Document: Quick start guide (copy config.yaml.example → config.yaml, edit)
  - Document: Backend selection (how to choose kasa/wyze/wled)
  - Document: How to discover bulbs (discovery tool usage)
  - Document: How to run bridge (python src/main.py)
  - Document: Integration with Pure Data audio pipeline
  - Include troubleshooting section (port conflicts, authentication failures)
  - **Status**: README complete with navigation

### Component 2: Backend Abstraction Layer

- [ ] **Task 2.1**: Create LightingBackend base class skeleton (TRD Section 3.1, R1-R2)
  - File: `/home/user/corazonn/lighting/src/backends/base.py`
  - Imports: `from abc import ABC, abstractmethod`, `from typing import Dict, List, Optional`, `import logging`
  - Class declaration: `class LightingBackend(ABC):`
  - **Status**: Base class structure created

- [ ] **Task 2.2**: Implement __init__ method (TRD Section 3.1)
  - Parameters: `config: dict`
  - Store config: `self.config = config`
  - Initialize logger: `self.logger = logging.getLogger(self.__class__.__name__)`
  - **Status**: Base initialization complete

- [ ] **Task 2.3**: Define authenticate() abstract method (TRD R5)
  - Decorator: `@abstractmethod`
  - Signature: `def authenticate(self) -> None:`
  - Docstring: From TRD Section 3.1 (cloud backends login, local backends discover)
  - Raises: `SystemExit` on authentication failure
  - **Status**: Authentication interface defined

- [ ] **Task 2.4**: Define set_color() abstract method (TRD R2)
  - Decorator: `@abstractmethod`
  - Signature: `def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:`
  - Parameters: hue 0-360, saturation/brightness 0-100
  - Raises: `Exception` on communication failure (logged, not fatal per R6)
  - **Status**: Color setting interface defined

- [ ] **Task 2.5**: Define pulse() abstract method (TRD R23-R27)
  - Decorator: `@abstractmethod`
  - Signature: `def pulse(self, bulb_id: str, hue: int, zone: int) -> None:`
  - Docstring: Two-step pulse effect (rise → hold → fall), handle rate limiting, record drops
  - Parameters: bulb_id (backend-specific), hue 0-360, zone 0-3
  - **Status**: Pulse effect interface defined

- [ ] **Task 2.6**: Define remaining abstract methods (TRD Section 3.1)
  - `set_all_baseline(self) -> None:` - Initialize all bulbs to baseline state
  - `get_latency_estimate(self) -> float:` - Return typical latency in ms
  - `print_stats(self) -> None:` - Print drop statistics on shutdown
  - `get_bulb_for_zone(self, zone: int) -> Optional[str]:` - Map zone to bulb ID
  - **Status**: All abstract methods defined (TRD R2)

- [ ] **Task 2.7**: Add complete docstrings (TRD Section 3.1)
  - Copy docstrings from TRD Section 3.1 for each method
  - Include Args, Returns, Raises sections
  - Include implementation notes (rate limiting, statistics, etc.)
  - **Status**: Base class fully documented

- [ ] **Task 2.8**: Test base class imports
  - Run: `python3 -c "from lighting.src.backends.base import LightingBackend; print('OK')"`
  - Expected: ImportError (ABC cannot be instantiated)
  - Verify: No syntax errors
  - **Status**: Base class importable, abstract methods enforced

### Component 3: Backend Factory

- [ ] **Task 3.1**: Create factory module skeleton (TRD Section 7.2, R28-R30)
  - File: `/home/user/corazonn/lighting/src/backends/__init__.py`
  - Imports: `from typing import Type`
  - Import base class: `from .base import LightingBackend`
  - **Status**: Factory module created

- [ ] **Task 3.2**: Add backend imports (TRD Section 7.2)
  - Add: `from .kasa_backend import KasaBackend` (will create in Task 4.x)
  - Add: `from .wyze_backend import WyzeBackend` (will create in Task 5.x)
  - Add: `from .wled_backend import WLEDBackend` (will create in Task 6.x)
  - Note: These imports will fail until backend files exist
  - **Status**: Backend imports prepared

- [ ] **Task 3.3**: Define BACKENDS registry (TRD Section 7.2, R30)
  - Dictionary: `BACKENDS = {'kasa': KasaBackend, 'wyze': WyzeBackend, 'wled': WLEDBackend}`
  - Maps backend name string to class
  - **Status**: Backend registry created

- [ ] **Task 3.4**: Implement create_backend() factory function (TRD Section 7.2, R28-R29)
  - Signature: `def create_backend(config: dict) -> LightingBackend:`
  - Extract backend name: `backend_name = config.get('lighting', {}).get('backend')`
  - Validate name exists: Raise ValueError if missing (R28)
  - **Status**: Factory function skeleton created

- [ ] **Task 3.5**: Implement factory validation (TRD Section 7.2, R29)
  - Check backend name in BACKENDS dict
  - If invalid: Raise ValueError with helpful message listing available backends
  - Format: `f"Unknown backend: '{backend_name}'\nAvailable backends: {', '.join(BACKENDS.keys())}"`
  - **Status**: Factory provides helpful errors

- [ ] **Task 3.6**: Implement backend instantiation (TRD Section 7.2)
  - Get backend class: `backend_class = BACKENDS[backend_name]`
  - Instantiate: `return backend_class(config)`
  - **Status**: Factory instantiates correct backend class

- [ ] **Task 3.7**: Add factory docstring
  - Copy docstring from TRD Section 7.2
  - Document Args, Returns, Raises
  - **Status**: Factory fully documented

### Component 4: Kasa Backend Implementation (Primary)

- [ ] **Task 4.1**: Create KasaBackend class skeleton (TRD Section 8.2, R1, R34)
  - File: `/home/user/corazonn/lighting/src/backends/kasa_backend.py`
  - Imports: `import asyncio`, `import time`, `from typing import Optional`, `from kasa import SmartBulb, Discover`
  - Import base: `from .base import LightingBackend`
  - Class declaration: `class KasaBackend(LightingBackend):`
  - **Status**: Kasa backend structure created

- [ ] **Task 4.2**: Implement __init__ method (TRD Section 8.2)
  - Call super: `super().__init__(config)`
  - Initialize: `self.bulbs = {}` (map bulb_id → SmartBulb object)
  - Initialize: `self.zone_map = {}` (map zone → bulb_id)
  - Initialize: `self.drop_stats = {}` (track drops per bulb)
  - **Status**: Kasa backend state initialized

- [ ] **Task 4.3**: Implement authenticate() method (TRD Section 8.2, R5, R35-R36)
  - Extract config: `kasa_config = self.config['kasa']`
  - Loop through bulbs: `for bulb_cfg in kasa_config['bulbs']:`
  - Extract: `ip = bulb_cfg['ip']`, `zone = bulb_cfg['zone']`, `name = bulb_cfg['name']`
  - Create bulb: `bulb = SmartBulb(ip)`
  - Update device (async): `asyncio.run(bulb.update())` (TRD R36)
  - **Status**: Kasa bulbs connected via IP

- [ ] **Task 4.4**: Store bulb references and log (TRD Section 8.2)
  - Store bulb: `self.bulbs[ip] = bulb`
  - Store zone mapping: `self.zone_map[zone] = ip`
  - Initialize drop stats: `self.drop_stats[ip] = 0`
  - Log success: `self.logger.info(f"Zone {zone} → {name} ({ip}) - OK")`
  - **Status**: Bulb references stored and logged

- [ ] **Task 4.5**: Implement authentication error handling (TRD R5)
  - Wrap entire method in try/except
  - Catch: `except Exception as e:`
  - Log error: `self.logger.error(f"Kasa authentication failed: {e}")`
  - Exit: `raise SystemExit(1)` (TRD R5)
  - **Status**: Authentication failures prevent bridge startup

- [ ] **Task 4.6**: Implement set_color() method (TRD Section 8.2, R36)
  - Get bulb: `bulb = self.bulbs.get(bulb_id)`
  - Validate: Raise ValueError if bulb not found
  - Set HSV (async): `asyncio.run(bulb.set_hsv(hue, saturation, brightness))` (TRD R36)
  - **Status**: Color setting via python-kasa library

- [ ] **Task 4.7**: Implement set_color() error handling (TRD R6)
  - Wrap in try/except
  - Catch: `except Exception as e:`
  - Log error: `self.logger.error(f"Failed to set color for {bulb_id}: {e}")`
  - Reraise: `raise` (caller handles per R6)
  - **Status**: Network errors logged but not fatal

- [ ] **Task 4.8**: Implement pulse() method skeleton (TRD Section 8.2, R23-R27, R37)
  - Extract effects config: `effects = self.config['effects']`
  - Get brightness values: `baseline_bri = effects['baseline_brightness']`, `pulse_max = effects['pulse_max']`
  - Get saturation: `baseline_sat = effects['baseline_saturation']`
  - Comment: "No rate limiting enforced - Kasa bulb limits untested" (TRD R37)
  - **Status**: Pulse parameters extracted

- [ ] **Task 4.9**: Implement pulse() two-step effect (TRD R24-R25)
  - Call 1 (rise): `self.set_color(bulb_id, hue, baseline_sat, pulse_max)`
  - Calculate hold time: `attack_sustain = (effects['attack_time_ms'] + effects['sustain_time_ms']) / 1000`
  - Hold at peak: `time.sleep(attack_sustain)` (TRD R25)
  - Call 2 (fall): `self.set_color(bulb_id, hue, baseline_sat, baseline_bri)`
  - **Status**: Two-step brightness pulse implemented

- [ ] **Task 4.10**: Implement pulse() error handling (TRD R27)
  - Wrap in try/except
  - Catch: `except Exception as e:`
  - Log error: `self.logger.error(f"Pulse failed for {bulb_id}: {e}")`
  - Do not reraise (pulse failures should not crash bridge)
  - **Status**: Pulse failures logged but non-fatal

- [ ] **Task 4.11**: Implement set_all_baseline() method (TRD Section 8.2)
  - Extract effects: `baseline_bri`, `baseline_sat`, `baseline_hue = effects.get('baseline_hue', 120)`
  - Loop: `for bulb_id, bulb in self.bulbs.items():`
  - Set color: `self.set_color(bulb_id, baseline_hue, baseline_sat, baseline_bri)`
  - Get bulb name from config (find matching IP)
  - Log: `self.logger.info(f"Initialized {name} to baseline")`
  - **Status**: All bulbs initialized to baseline state on startup

- [ ] **Task 4.12**: Implement set_all_baseline() error handling
  - Wrap set_color call in try/except
  - Catch: `except Exception as e:`
  - Log error: `self.logger.error(f"Failed to init {bulb_id}: {e}")`
  - Continue to next bulb (partial initialization acceptable)
  - **Status**: Initialization errors logged but non-fatal

- [ ] **Task 4.13**: Implement utility methods (TRD Section 8.2)
  - `get_latency_estimate()`: Return `100.0` (100ms average)
  - `get_bulb_for_zone(zone)`: Return `self.zone_map.get(zone)`
  - **Status**: Utility methods implemented

- [ ] **Task 4.14**: Implement print_stats() method (TRD Section 8.2)
  - Sum drops: `total_drops = sum(self.drop_stats.values())`
  - If zero: Log "No pulses dropped" and return
  - Else: Log "Drop statistics:"
  - Loop through drop_stats, find bulb name from config, log `f"  {name}: {count} pulses dropped"`
  - **Status**: Drop statistics printed on shutdown

- [ ] **Task 4.15**: Test KasaBackend imports
  - Run: `python3 -c "from lighting.src.backends.kasa_backend import KasaBackend; print('OK')"`
  - Expected: `OK`
  - Verify: No syntax errors
  - **Status**: Kasa backend importable

### Component 5: Wyze Backend Implementation (Secondary)

- [ ] **Task 5.1**: Create WyzeBackend class skeleton (TRD Section 9.2, R1)
  - File: `/home/user/corazonn/lighting/src/backends/wyze_backend.py`
  - Imports: `from wyze_sdk import Client`, `import time`, `from typing import Optional`
  - Import base: `from .base import LightingBackend`
  - Class declaration: `class WyzeBackend(LightingBackend):`
  - **Status**: Wyze backend structure created

- [ ] **Task 5.2**: Implement __init__ method (TRD Section 9.2)
  - Call super: `super().__init__(config)`
  - Initialize: `self.client = None`
  - Initialize: `self.zone_map = {}` (map zone → bulb MAC)
  - Initialize: `self.drop_stats = {}` (track drops per bulb)
  - Initialize: `self.last_request = {}` (rate limiting timestamps)
  - **Status**: Wyze backend state initialized

- [ ] **Task 5.3**: Implement authenticate() method (TRD Section 9.2, R5)
  - Extract config: `wyze_config = self.config['wyze']`
  - Create client: `self.client = Client(email=wyze_config['email'], password=wyze_config['password'])`
  - Test auth: `self.client.bulbs.list()` (will raise if credentials invalid)
  - Build zone map: Loop through `wyze_config['bulbs']`, store `self.zone_map[bulb['zone']] = bulb['id']`
  - Initialize drop stats: `self.drop_stats[bulb['id']] = 0`
  - Log: `self.logger.info(f"Wyze: {len(self.zone_map)} bulbs configured")`
  - **Status**: Wyze cloud authentication complete

- [ ] **Task 5.4**: Implement authenticate() error handling (TRD R5)
  - Wrap in try/except
  - Catch: `except Exception as e:`
  - Log: `self.logger.error(f"Wyze authentication failed: {e}")`
  - Exit: `raise SystemExit(1)`
  - **Status**: Authentication failures prevent startup

- [ ] **Task 5.5**: Implement set_color() method (TRD Section 9.2)
  - Signature: `def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:`
  - Call Wyze API: `self.client.bulbs.set_color(device_mac=bulb_id, color_temp=None, color={'hue': hue, 'saturation': saturation, 'brightness': brightness})`
  - **Status**: Color setting via Wyze cloud API

- [ ] **Task 5.6**: Implement pulse() rate limiting (TRD Section 9.2, R39-R41)
  - Get current time: `now = time.time()`
  - Get last request: `last = self.last_request.get(bulb_id, 0)`
  - Check interval: `if now - last < 2.0:` (2 sec minimum per R39)
  - If too soon: Increment `self.drop_stats[bulb_id] += 1`
  - Log drop (max 1/sec): Implement last_drop_log tracking to avoid spam
  - Log: `self.logger.warning(f"Pulse dropped for zone {zone} (rate limit)")` (R41)
  - Return early if dropped
  - **Status**: Aggressive rate limiting enforced

- [ ] **Task 5.7**: Implement pulse() effect (TRD Section 9.2, R39)
  - Update timestamp: `self.last_request[bulb_id] = now`
  - Extract effects config (same as Kasa)
  - Wrap in try/except
  - Call 1 (rise): `self.set_color(bulb_id, hue, baseline_sat, pulse_max)`
  - Hold: `time.sleep(attack_sustain)`
  - Call 2 (fall): `self.set_color(bulb_id, hue, baseline_sat, baseline_bri)`
  - Catch exceptions and log (same as Kasa)
  - **Status**: Two-step pulse with rate limiting

- [ ] **Task 5.8**: Implement set_all_baseline() method (TRD Section 9.2)
  - Similar to Kasa implementation
  - Loop through zone_map, call set_color for each bulb
  - Use baseline values from effects config
  - Handle errors gracefully
  - **Status**: Wyze bulbs initialized to baseline

- [ ] **Task 5.9**: Implement utility methods (TRD Section 9.2)
  - `get_latency_estimate()`: Return `400.0` (400ms average cloud latency)
  - `get_bulb_for_zone(zone)`: Return `self.zone_map.get(zone)`
  - **Status**: Utility methods implemented

- [ ] **Task 5.10**: Implement print_stats() method (TRD Section 9.2, R40)
  - Similar to Kasa implementation
  - Sum drops and log statistics
  - Find bulb names from config for readable output
  - Note: Expected 50-75% drop rate at typical BPM (R40)
  - **Status**: Drop statistics printed on shutdown

- [ ] **Task 5.11**: Test WyzeBackend imports
  - Run: `python3 -c "from lighting.src.backends.wyze_backend import WyzeBackend; print('OK')"`
  - Expected: `OK`
  - Verify: No syntax errors
  - **Status**: Wyze backend importable

### Component 6: WLED Backend Implementation (Secondary)

- [ ] **Task 6.1**: Create WLEDBackend class skeleton (TRD Section 10.2, R1)
  - File: `/home/user/corazonn/lighting/src/backends/wled_backend.py`
  - Imports: `import socket`, `import time`, `from typing import Optional`
  - Import base: `from .base import LightingBackend`
  - Class declaration: `class WLEDBackend(LightingBackend):`
  - **Status**: WLED backend structure created

- [ ] **Task 6.2**: Implement __init__ method (TRD Section 10.2)
  - Call super: `super().__init__(config)`
  - Initialize: `self.devices = {}` (map IP → device config)
  - Initialize: `self.zone_map = {}` (map zone → IP)
  - Create UDP socket: `self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)`
  - **Status**: WLED backend state initialized with UDP socket

- [ ] **Task 6.3**: Implement authenticate() method (TRD Section 10.2, R44)
  - Extract config: `wled_config = self.config['wled']`
  - Import requests (for HTTP connectivity test per R44)
  - Loop: `for dev in wled_config['devices']:`
  - Extract: `ip = dev['ip']`, `zone = dev['zone']`
  - Test connectivity: `resp = requests.get(f"http://{ip}/json/state", timeout=2)` (R44)
  - Check status: `if resp.status_code == 200:`
  - Store device: `self.devices[ip] = dev`
  - Store zone mapping: `self.zone_map[zone] = ip`
  - Log: `self.logger.info(f"Zone {zone} → {dev['name']} ({ip}) - OK")`
  - **Status**: WLED devices discovered and tested

- [ ] **Task 6.4**: Implement authenticate() error handling (TRD R5)
  - Wrap in try/except
  - Log connectivity failures but continue (allow partial initialization)
  - If no devices connected: Log error and `raise SystemExit(1)`
  - **Status**: Authentication failures handled gracefully

- [ ] **Task 6.5**: Implement HSV to RGB conversion helper (TRD R45)
  - Method: `def _hsv_to_rgb(self, h: int, s: int, v: int) -> bytes:`
  - Parameters: h (0-360), s (0-100), v (0-100)
  - Normalize: Convert to 0.0-1.0 range
  - Implement standard HSV→RGB algorithm (use colorsys module or manual calculation)
  - Scale to 0-255 range
  - Return: `bytes([r, g, b])` (3 bytes)
  - **Status**: HSV→RGB conversion implemented

- [ ] **Task 6.6**: Implement set_color() method (TRD Section 10.2, R42, R45)
  - Convert HSV to RGB: `rgb = self._hsv_to_rgb(hue, saturation, brightness)`
  - Get pixel count: `pixel_count = self.devices[bulb_id]['pixel_count']`
  - Build DRGB packet: `packet = bytes([2, 1]) + (rgb * pixel_count)` (R42)
  - Format: Protocol byte 2 (DRGB), timeout byte 1, then RGB repeated for each pixel
  - Send UDP: `self.sock.sendto(packet, (bulb_id, 21324))` (R42)
  - **Status**: WLED color control via UDP DRGB protocol

- [ ] **Task 6.7**: Implement pulse() method (TRD Section 10.2, R43)
  - Extract effects config (same as other backends)
  - Wrap in try/except
  - Call 1 (rise): `self.set_color(bulb_id, hue, baseline_sat, pulse_max)`
  - Hold: `time.sleep(attack_sustain)`
  - Call 2 (fall): `self.set_color(bulb_id, hue, baseline_sat, baseline_bri)`
  - No rate limiting needed (R43)
  - Catch exceptions and log
  - **Status**: WLED pulse effect with no rate limiting

- [ ] **Task 6.8**: Implement set_all_baseline() method
  - Similar to other backends
  - Loop through devices, call set_color for each
  - Use baseline values from effects config
  - Handle errors gracefully
  - **Status**: WLED devices initialized to baseline

- [ ] **Task 6.9**: Implement utility methods (TRD Section 10.2)
  - `get_latency_estimate()`: Return `5.0` (5ms UDP latency)
  - `get_bulb_for_zone(zone)`: Return `self.zone_map.get(zone)`
  - **Status**: Utility methods implemented

- [ ] **Task 6.10**: Implement print_stats() method (TRD Section 10.2)
  - Log: `self.logger.info("WLED: No pulses dropped (no rate limits")`
  - WLED has no drops, just confirm in stats
  - **Status**: Stats method implemented

- [ ] **Task 6.11**: Test WLEDBackend imports
  - Run: `python3 -c "from lighting.src.backends.wled_backend import WLEDBackend; print('OK')"`
  - Expected: `OK`
  - Verify: No syntax errors
  - **Status**: WLED backend importable

### Component 7: OSC Receiver and Effect Logic

- [ ] **Task 7.1**: Create osc_receiver.py skeleton (TRD Section 7.4, R31-R33)
  - File: `/home/user/corazonn/lighting/src/osc_receiver.py`
  - Imports: `from pythonosc.osc_server import BlockingOSCUDPServer`, `from pythonosc.dispatcher import Dispatcher`
  - Import: `from backends.base import LightingBackend`, `import logging`, `import re`
  - Initialize logger: `logger = logging.getLogger('osc')`
  - **Status**: OSC receiver module created

- [ ] **Task 7.2**: Implement bpm_to_hue() function (TRD Section 6.1, R20-R22)
  - Signature: `def bpm_to_hue(bpm: float) -> int:`
  - Clamp BPM: `bpm_clamped = max(40, min(120, bpm))` (R21)
  - Linear mapping: `hue = 240 - ((bpm_clamped - 40) / 80) * 240` (R22)
  - Return: `int(hue)` (40 BPM=240°, 120 BPM=0°)
  - **Status**: BPM→hue mapping implemented

- [ ] **Task 7.3**: Create handle_pulse() function skeleton (TRD Section 7.4, R17-R19)
  - Signature: `def handle_pulse(address: str, ibi_ms: int, backend: LightingBackend, config: dict):`
  - Wrap entire function in try/except (R19)
  - **Status**: Pulse handler skeleton created

- [ ] **Task 7.4**: Implement OSC address parsing (TRD R17)
  - Parse address: `match = re.match(r'/light/(\d+)/pulse', address)`
  - Validate: `if not match:` log warning and return
  - Extract zone: `zone = int(match.group(1))`
  - **Status**: OSC address parsed to zone number

- [ ] **Task 7.5**: Implement IBI validation (TRD R18)
  - Check range: `if not (300 <= ibi_ms <= 3000):`
  - Log warning: `logger.warning(f"IBI out of range: {ibi_ms}ms (zone {zone})")`
  - Return early if invalid
  - **Status**: Invalid IBIs rejected

- [ ] **Task 7.6**: Implement bulb lookup (TRD R32)
  - Get bulb for zone: `bulb_id = backend.get_bulb_for_zone(zone)`
  - Check: `if bulb_id is None:` log warning and return
  - Log: `logger.warning(f"No bulb configured for zone {zone}")`
  - **Status**: Unconfigured zones handled gracefully

- [ ] **Task 7.7**: Implement BPM calculation and hue mapping (TRD R20-R22)
  - Calculate BPM: `bpm = 60000 / ibi_ms` (R20)
  - Get hue: `hue = bpm_to_hue(bpm)` (R22)
  - Log: `logger.debug(f"Pulse: zone={zone} bpm={bpm:.1f} hue={hue}")`
  - **Status**: BPM→hue calculation backend-agnostic

- [ ] **Task 7.8**: Implement pulse execution (TRD R23-R27, R32)
  - Call backend: `backend.pulse(bulb_id, hue, zone)`
  - This delegates all effect logic to backend (R32)
  - **Status**: Pulse delegated to backend interface

- [ ] **Task 7.9**: Implement error handling (TRD R19)
  - Catch: `except Exception as e:`
  - Log error: `logger.error(f"Error handling pulse: {e}", exc_info=True)`
  - Do not reraise (handler failures should not crash server)
  - **Status**: OSC handler errors logged but non-fatal

- [ ] **Task 7.10**: Create start_osc_server() function (TRD Section 7.4, R15-R16)
  - Signature: `def start_osc_server(config: dict, backend: LightingBackend):`
  - Create dispatcher: `dispatcher = Dispatcher()`
  - **Status**: OSC server setup function created

- [ ] **Task 7.11**: Implement message routing (TRD Section 7.4)
  - Import partial: `from functools import partial`
  - Create handler: `handler = partial(handle_pulse, backend=backend, config=config)`
  - Map address: `dispatcher.map("/light/*/pulse", handler)`
  - Wildcard pattern matches all zone numbers
  - **Status**: OSC messages routed to handler

- [ ] **Task 7.12**: Implement OSC server creation (TRD R15-R16)
  - Create server: `server = BlockingOSCUDPServer(("0.0.0.0", config['osc']['listen_port']), dispatcher)` (R16)
  - Bind to 0.0.0.0 (all interfaces per R16)
  - Port from config (R15)
  - Log: `logger.info(f"OSC server listening on port {config['osc']['listen_port']}")`
  - Start: `server.serve_forever()` (blocks)
  - **Status**: OSC server listening and blocking

- [ ] **Task 7.13**: Test osc_receiver imports
  - Run: `python3 -c "from lighting.src.osc_receiver import bpm_to_hue; print(bpm_to_hue(60))"`
  - Expected: `180` (60 BPM = 180° hue)
  - Verify: No syntax errors
  - **Status**: OSC receiver module importable

### Component 8: Main Entry Point

- [ ] **Task 8.1**: Create main.py skeleton (TRD Section 7.3)
  - File: `/home/user/corazonn/lighting/src/main.py`
  - Imports: `import yaml`, `import logging`, `from pathlib import Path`
  - Import: `from osc_receiver import start_osc_server`
  - Import: `from backends import create_backend`
  - **Status**: Main module created

- [ ] **Task 8.2**: Implement load_config() function (TRD Section 7.3)
  - Signature: `def load_config(path: str) -> dict:`
  - Check file exists: `config_path = Path(path)`, `if not config_path.exists():`
  - Raise helpful error: `raise FileNotFoundError(f"Config not found: {path}\nCopy config.yaml.example to config.yaml and edit.")`
  - Load YAML: `with open(config_path) as f: config = yaml.safe_load(f)`
  - Call validation: `validate_config(config)`
  - Return config
  - **Status**: Config loading with helpful errors

- [ ] **Task 8.3**: Create validate_config() function skeleton (TRD Section 7.3, R7-R14)
  - Signature: `def validate_config(config: dict):`
  - Will implement validation in Tasks 8.4-8.9
  - **Status**: Validation function skeleton created

- [ ] **Task 8.4**: Implement backend selection validation (TRD R7, R13)
  - Check section exists: `if 'lighting' not in config or 'backend' not in config['lighting']:`
  - Raise: `ValueError("Missing required config: lighting.backend")` (R7)
  - Get backend name: `backend_name = config['lighting']['backend']`
  - Check valid options: `if backend_name not in ['kasa', 'wyze', 'wled']:` raise ValueError (R7)
  - Check backend section exists: `if backend_name not in config:` raise ValueError (R13)
  - **Status**: Backend selection validated

- [ ] **Task 8.5**: Implement required sections validation (TRD R8-R11)
  - Check sections: `required_sections = ['osc', 'effects', 'logging']`
  - Loop: `for section in required_sections:` check `if section not in config:` raise ValueError
  - **Status**: Required config sections validated

- [ ] **Task 8.6**: Implement port validation (TRD R8)
  - Get port: `port = config['osc'].get('listen_port')`
  - Check range: `if not port or not (1 <= port <= 65535):` raise ValueError
  - **Status**: Port range validated

- [ ] **Task 8.7**: Implement effect parameter validation (TRD R9-R10)
  - Get effects: `effects = config['effects']`
  - Required params: `['baseline_brightness', 'pulse_max', 'baseline_saturation']`
  - Loop: Check each exists and is 0-100 range
  - Raise ValueError if invalid
  - **Status**: Brightness/saturation ranges validated

- [ ] **Task 8.8**: Implement hue validation (TRD R10)
  - Check if exists: `if 'baseline_hue' in effects:`
  - Get hue: `hue = effects['baseline_hue']`
  - Check range: `if not (0 <= hue <= 360):` raise ValueError
  - **Status**: Hue range validated

- [ ] **Task 8.9**: Implement time parameter validation (TRD R11)
  - Time params: `['fade_time_ms', 'attack_time_ms', 'sustain_time_ms']`
  - Loop: Check each > 0
  - Raise ValueError if invalid
  - Note: Can be optional validation depending on strictness
  - **Status**: Time parameters validated

- [ ] **Task 8.10**: Create setup_logging() function (TRD Section 7.3)
  - Signature: `def setup_logging(config: dict):`
  - Import: `from logging.handlers import RotatingFileHandler`
  - Create logs directory: `Path('logs').mkdir(exist_ok=True)`
  - **Status**: Logging setup function created

- [ ] **Task 8.11**: Implement file handler (TRD Section 7.3)
  - Create handler: `RotatingFileHandler(config['logging']['file'], maxBytes=config['logging']['max_bytes'], backupCount=3)`
  - Set level: `file_handler.setLevel(getattr(logging, config['logging']['file_level']))`
  - **Status**: File logging configured with rotation

- [ ] **Task 8.12**: Implement console handler (TRD Section 7.3)
  - Create handler: `console_handler = logging.StreamHandler()`
  - Set level: `console_handler.setLevel(getattr(logging, config['logging']['console_level']))`
  - **Status**: Console logging configured with separate level

- [ ] **Task 8.13**: Implement log formatting (TRD Section 7.3)
  - Create formatter: `logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')`
  - Apply to both handlers: `file_handler.setFormatter(formatter)`, `console_handler.setFormatter(formatter)`
  - Configure root logger: `logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])`
  - **Status**: Log formatting consistent across handlers

- [ ] **Task 8.14**: Create main() function skeleton (TRD Section 7.3)
  - Signature: `def main():`
  - Wrap in try/except for top-level error handling
  - **Status**: Main function skeleton created

- [ ] **Task 8.15**: Implement startup sequence (TRD Section 7.3)
  - Load config: `config = load_config('config.yaml')`
  - Setup logging: `setup_logging(config)`
  - Get logger: `logger = logging.getLogger('main')`
  - Print banner: Log "=" * 60, "Heartbeat Lighting Bridge MVP v2.0 (Multi-Backend)", "=" * 60
  - **Status**: Startup banner and initialization

- [ ] **Task 8.16**: Implement backend creation (TRD Section 7.3)
  - Create backend: `backend = create_backend(config)`
  - Get backend name: `backend_name = config['lighting']['backend']`
  - Log backend: `logger.info(f"Using backend: {backend_name}")`
  - Log latency: `logger.info(f"Estimated latency: {backend.get_latency_estimate():.0f}ms")`
  - **Status**: Backend instantiated and logged

- [ ] **Task 8.17**: Implement authentication and initialization (TRD Section 7.3)
  - Authenticate: `backend.authenticate()`
  - Initialize bulbs: `backend.set_all_baseline()`
  - **Status**: Backend authenticated and bulbs initialized

- [ ] **Task 8.18**: Implement OSC server startup (TRD Section 7.3)
  - Wrap in try/except for OSError
  - Start server: `start_osc_server(config, backend)` (blocks here)
  - **Status**: OSC server started

- [ ] **Task 8.19**: Implement port conflict handling (TRD Section 7.3)
  - Catch: `except OSError as e:`
  - Import errno: `import errno as errno_module`
  - Check error: `if ('Address already in use' in str(e) or getattr(e, 'errno', None) in (48, 98, errno_module.EADDRINUSE)):`
  - Log error: Helpful message with port number
  - Return: `return 1`
  - Reraise if other OSError
  - **Status**: Port conflicts handled with helpful error

- [ ] **Task 8.20**: Implement top-level error handling (TRD Section 7.3, R14)
  - Catch FileNotFoundError: Print error, return 1
  - Catch ValueError: Print "Invalid config" error, return 1
  - Catch KeyboardInterrupt: Log shutdown, call `backend.print_stats()`, return 0
  - Catch Exception: Log fatal error with traceback, return 1
  - **Status**: All error cases handled gracefully

- [ ] **Task 8.21**: Implement script entry point (TRD Section 7.3)
  - Add: `if __name__ == '__main__': exit(main())`
  - **Status**: Script runnable as `python src/main.py`

### Component 9: Discovery Tools

- [ ] **Task 9.1**: Create discover-kasa.py (TRD Section 8.3)
  - File: `/home/user/corazonn/lighting/tools/discover-kasa.py`
  - Shebang: `#!/usr/bin/env python3`
  - Imports: `import asyncio`, `from kasa import Discover`
  - **Status**: Kasa discovery tool created

- [ ] **Task 9.2**: Implement Kasa discovery (TRD Section 8.3)
  - Function: `async def main():`
  - Print: "Scanning for Kasa devices..."
  - Discover: `devices = await Discover.discover()`
  - Filter bulbs: `bulbs = [dev for dev in devices.values() if dev.is_bulb]`
  - **Status**: Kasa network scan implemented

- [ ] **Task 9.3**: Implement Kasa results display (TRD Section 8.3)
  - Check count: `if not bulbs:` print "No Kasa bulbs found" and return
  - Print: `f"\nFound {len(bulbs)} Kasa bulbs:\n"`
  - Loop: `for bulb in bulbs:`
  - Update: `await bulb.update()`
  - Print: Name (alias), IP (host), Model, MAC
  - **Status**: Kasa discovery results formatted

- [ ] **Task 9.4**: Add Kasa entry point
  - Add: `if __name__ == '__main__': asyncio.run(main())`
  - Make executable: `chmod +x tools/discover-kasa.py`
  - **Status**: Kasa discovery tool runnable

- [ ] **Task 9.5**: Create discover-wyze.py (TRD Section 4.2)
  - File: `/home/user/corazonn/lighting/tools/discover-wyze.py`
  - Shebang: `#!/usr/bin/env python3`
  - Imports: `import argparse`, `from wyze_sdk import Client`
  - **Status**: Wyze discovery tool created

- [ ] **Task 9.6**: Implement Wyze argument parsing
  - Parser: `argparse.ArgumentParser()`
  - Add: `--email` (required), `--password` (required)
  - Parse: `args = parser.parse_args()`
  - **Status**: Wyze credentials accepted via CLI

- [ ] **Task 9.7**: Implement Wyze discovery
  - Create client: `client = Client(email=args.email, password=args.password)`
  - Get bulbs: `bulbs = client.bulbs.list()`
  - Filter color bulbs: Check device type
  - Print results: MAC address, nickname, model
  - **Status**: Wyze bulbs listed from account

- [ ] **Task 9.8**: Add Wyze entry point
  - Add: `if __name__ == '__main__':`
  - Make executable: `chmod +x tools/discover-wyze.py`
  - **Status**: Wyze discovery tool runnable

- [ ] **Task 9.9**: Create discover-wled.py (TRD Section 4.2)
  - File: `/home/user/corazonn/lighting/tools/discover-wled.py`
  - Shebang: `#!/usr/bin/env python3`
  - Imports: `from zeroconf import ServiceBrowser, Zeroconf` (requires `pip install zeroconf`)
  - **Status**: WLED discovery tool created

- [ ] **Task 9.10**: Implement WLED mDNS discovery
  - Service type: `_wled._tcp.local.`
  - Create listener class to collect devices
  - Browse: Use Zeroconf and ServiceBrowser
  - Extract IP addresses from discovered services
  - Print: IP address, device name
  - **Status**: WLED devices discovered via mDNS

- [ ] **Task 9.11**: Add WLED entry point
  - Add: `if __name__ == '__main__':`
  - Make executable: `chmod +x tools/discover-wled.py`
  - **Status**: WLED discovery tool runnable

### Component 10: Testing

- [ ] **Task 10.1**: Create test_effects.py (TRD Section 11.2)
  - File: `/home/user/corazonn/lighting/tests/test_effects.py`
  - Add path: `sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))`
  - Import: `from osc_receiver import bpm_to_hue`
  - **Status**: Effect tests module created

- [ ] **Task 10.2**: Write BPM→hue tests (TRD Section 11.2)
  - Test: `def test_bpm_to_hue():`
  - Assert: `bpm_to_hue(40) == 240` (blue)
  - Assert: `bpm_to_hue(80) == 120` (green)
  - Assert: `bpm_to_hue(120) == 0` (red)
  - **Status**: Color mapping verified

- [ ] **Task 10.3**: Write BPM clamping tests (TRD Section 11.2)
  - Test: `def test_bpm_clamping():`
  - Assert: `bpm_to_hue(30) == 240` (clamp low)
  - Assert: `bpm_to_hue(150) == 0` (clamp high)
  - **Status**: BPM range clamping verified

- [ ] **Task 10.4**: Run effect tests
  - Run: `cd /home/user/corazonn/lighting && python3 -m pytest tests/test_effects.py -v`
  - Expected: All tests pass
  - **Status**: Effect calculations correct

- [ ] **Task 10.5**: Create test_backends.py (TRD Section 11.1)
  - File: `/home/user/corazonn/lighting/tests/test_backends.py`
  - Add path: `sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))`
  - Imports: `from backends.base import LightingBackend`, all backend classes
  - **Status**: Backend tests module created

- [ ] **Task 10.6**: Write backend interface tests (TRD Section 11.1)
  - Test: `def test_kasa_implements_interface():`
  - Assert: `issubclass(KasaBackend, LightingBackend)`
  - Required methods: List from TRD Section 3.1
  - Assert: `hasattr(KasaBackend, method)` for each
  - Repeat for Wyze and WLED backends
  - **Status**: All backends implement interface

- [ ] **Task 10.7**: Write factory tests (TRD Section 11.1)
  - Test: `def test_backend_factory():`
  - Create test configs for each backend
  - Assert: `create_backend(config_kasa)` returns `KasaBackend` instance
  - Repeat for Wyze and WLED
  - Test invalid backend name raises ValueError
  - **Status**: Factory creates correct backend classes

- [ ] **Task 10.8**: Run backend tests
  - Run: `cd /home/user/corazonn/lighting && python3 -m pytest tests/test_backends.py -v`
  - Expected: All tests pass
  - **Status**: Backend interface compliance verified

- [ ] **Task 10.9**: Create test_standalone.py (TRD Section 11.3)
  - File: `/home/user/corazonn/lighting/tests/test_standalone.py`
  - Imports: `from pythonosc import udp_client`, `import time`
  - **Status**: Standalone integration test created

- [ ] **Task 10.10**: Implement standalone test (TRD Section 11.3)
  - Function: `def test_standalone():`
  - Docstring: Prerequisites (bridge running, backend configured)
  - Create client: `client = udp_client.SimpleUDPClient('127.0.0.1', 8001)`
  - Test data: List of (zone, ibi) tuples for 4 zones
  - Loop for 30 seconds: Send pulses, sleep for IBI duration
  - Print: Instructions to watch bulbs
  - **Status**: OSC sender test implemented

- [ ] **Task 10.11**: Add standalone entry point
  - Add: `if __name__ == '__main__': test_standalone()`
  - **Status**: Standalone test runnable

### Component 11: Integration Testing

- [ ] **Task 11.1**: Test config.yaml creation
  - Copy: `cp /home/user/corazonn/lighting/config.yaml.example /home/user/corazonn/lighting/config.yaml`
  - Edit: Configure for your backend (Kasa recommended)
  - Fill in: Bulb IPs/IDs and zone mappings
  - **Status**: Config file ready for testing

- [ ] **Task 11.2**: Test backend discovery (if using Kasa)
  - Run: `cd /home/user/corazonn/lighting && python3 tools/discover-kasa.py`
  - Verify: Kasa bulbs listed with IPs
  - Copy IPs to config.yaml
  - **Status**: Bulbs discovered and configured

- [ ] **Task 11.3**: Test config validation
  - Run: `cd /home/user/corazonn/lighting && python3 -c "from src.main import load_config; load_config('config.yaml')"`
  - Expected: No errors if config valid
  - Test: Try invalid config (bad port, missing section) and verify ValueError
  - **Status**: Config validation working

- [ ] **Task 11.4**: Test bridge startup
  - Run: `cd /home/user/corazonn/lighting && python3 src/main.py`
  - Verify: Startup banner displayed
  - Verify: Backend authenticated successfully
  - Verify: Bulbs initialized to baseline
  - Verify: OSC server listening on port 8001
  - **Status**: Bridge starts without errors

- [ ] **Task 11.5**: Test OSC reception with standalone test (TRD R31)
  - Terminal 1: Bridge running (Task 11.4)
  - Terminal 2: `cd /home/user/corazonn/lighting && python3 tests/test_standalone.py`
  - Verify: Console shows pulse messages received
  - Verify: Bulbs pulsing with color changes
  - Watch for 30 seconds minimum
  - **Status**: OSC messages received and processed

- [ ] **Task 11.6**: Test color mapping (TRD R30)
  - Send slow heartbeat: ~1200ms IBI (50 BPM)
  - Verify: Bulbs show blue/cyan color
  - Send medium heartbeat: ~750ms IBI (80 BPM)
  - Verify: Bulbs show green color
  - Send fast heartbeat: ~500ms IBI (120 BPM)
  - Verify: Bulbs show red/orange color
  - **Status**: BPM→color mapping visible

- [ ] **Task 11.7**: Test pulse effect (TRD R30)
  - Watch bulb during pulse
  - Verify: Brightness increases (baseline → peak)
  - Verify: Brightness decreases (peak → baseline)
  - Verify: Total pulse duration ~900ms
  - Verify: Smooth transitions (no flickering)
  - **Status**: Pulse effect working as designed

- [ ] **Task 11.8**: Test multi-zone operation
  - Edit test_standalone.py to send different IBIs per zone
  - Verify: 4 bulbs pulse independently
  - Verify: Different colors based on different IBIs
  - Verify: No interference between zones
  - **Status**: Independent zone control working

- [ ] **Task 11.9**: Test integration with Pure Data (TRD Section 2)
  - Start Pure Data patch from audio pipeline
  - Start test-osc-sender.py to feed audio pipeline
  - Verify: Lighting bridge receives /light/N/pulse messages
  - Verify: Bulbs pulse in sync with audio triggers
  - Verify: Colors match heartbeat rates
  - **Status**: Audio → lighting integration working

- [ ] **Task 11.10**: Run 30-minute stability test (TRD Section 13)
  - Start: Bridge + Pure Data + test sender (or ESP32 simulator)
  - Monitor: Console for errors
  - Monitor: Bulb behavior (no hangs, consistent pulsing)
  - Check logs: `/home/user/corazonn/lighting/logs/lighting.log`
  - Verify: No crashes, no exceptions
  - Verify: Drop statistics reasonable (Kasa: minimal, Wyze: 50-75%, WLED: 0%)
  - **Status**: Runs for 30+ minutes without issues

- [ ] **Task 11.11**: Test graceful shutdown
  - Press Ctrl+C in bridge terminal
  - Verify: "Shutting down..." message
  - Verify: Drop statistics printed
  - Verify: Clean exit (return code 0)
  - **Status**: Shutdown graceful with stats

- [ ] **Task 11.12**: Test error recovery
  - Disconnect one bulb (unplug or turn off)
  - Send pulses to that zone
  - Verify: Errors logged but bridge continues
  - Verify: Other zones unaffected
  - Reconnect bulb
  - Verify: Zone resumes working
  - **Status**: Handles offline bulbs gracefully

### Component 12: Documentation & Completion

- [ ] **Task 12.1**: Document config.yaml fields
  - Update: `/home/user/corazonn/lighting/README.md`
  - Document: Each config section (lighting, osc, effects, logging)
  - Document: Backend-specific sections (kasa, wyze, wled)
  - Document: Required vs optional fields
  - Document: Valid value ranges (TRD R7-R14)
  - **Status**: Config documentation complete

- [ ] **Task 12.2**: Document backend selection
  - Update: `/home/user/corazonn/lighting/README.md`
  - Document: Backend comparison table (TRD Section 3.2)
  - Document: When to use each backend (Kasa for production, Wyze for compatibility, WLED for performance)
  - Document: Trade-offs (latency, drop rate, cost, installation)
  - **Status**: Backend selection guide complete

- [ ] **Task 12.3**: Document discovery workflows
  - Update: `/home/user/corazonn/lighting/README.md`
  - Document: How to run each discovery tool
  - Document: How to extract IPs/MACs and add to config
  - Document: Troubleshooting discovery issues
  - **Status**: Discovery documentation complete

- [ ] **Task 12.4**: Document testing procedures
  - Update: `/home/user/corazonn/lighting/README.md`
  - Document: Standalone testing (test_standalone.py)
  - Document: Integration testing (with Pure Data)
  - Document: How to verify OSC reception
  - Document: How to verify color mapping
  - Document: 30-minute stability test procedure
  - **Status**: Testing procedures documented

- [ ] **Task 12.5**: Document architecture
  - Update: `/home/user/corazonn/lighting/README.md`
  - Document: System architecture (TRD Section 2)
  - Document: Data flow (OSC → effect → backend → bulb)
  - Document: File organization (TRD Section 7.1)
  - Document: Backend abstraction design (why it exists, how to add new backends)
  - **Status**: Architecture documented

- [ ] **Task 12.6**: Document troubleshooting
  - Update: `/home/user/corazonn/lighting/README.md`
  - Common issues: Port 8001 already in use (solution: kill other process)
  - Common issues: Kasa authentication failed (solution: check IP addresses, network connectivity)
  - Common issues: Wyze authentication failed (solution: check credentials)
  - Common issues: No bulbs pulse (solution: check zone mapping in config)
  - Common issues: High drop rate (expected for Wyze, check logs)
  - **Status**: Troubleshooting guide complete

- [ ] **Task 12.7**: Verify all TRD requirements met
  - R1-R6: Backend interface requirements (verified in Task 10.8)
  - R7-R14: Config validation (verified in Task 11.3)
  - R15-R19: OSC protocol (verified in Task 11.5)
  - R20-R22: BPM mapping (verified in Task 10.4)
  - R23-R27: Pulse effect (verified in Task 11.7)
  - R28-R30: Factory (verified in Task 10.7)
  - R31-R33: OSC receiver backend-agnostic (code review)
  - R34-R45: Backend-specific (verified per backend in integration tests)
  - **Status**: All 45 requirements implemented and tested

- [ ] **Task 12.8**: Verify all acceptance criteria met (TRD Section 13)
  - ✅ Bridge receives OSC on port 8001
  - ✅ Config validation catches errors
  - ✅ Backend selected via config file
  - ✅ All 4 bulbs pulse independently
  - ✅ Colors map to BPM (blue→green→red)
  - ✅ Pulses visible (brightness fade)
  - ✅ No crashes over 30 minutes
  - ✅ Drop statistics logged
  - ✅ Handles offline bulbs gracefully
  - ✅ Standalone test works
  - ✅ All 3 backends implemented and tested
  - **Status**: All acceptance criteria met

- [ ] **Task 12.9**: Update completion status
  - Update: `/home/user/corazonn/docs/lighting/tasks/phase1-mvp.md` (this file)
  - Mark completion date
  - Note any deviations from TRD (if any)
  - Document any issues encountered and solutions
  - **Status**: Phase 1 lighting bridge complete

---

## Task Execution Notes

**Order**: Tasks should be completed in sequence within each component. Components can be done in parallel with dependencies:
- Prerequisites (Component 0) must complete first
- Backend abstraction (Component 2-3) before backend implementations (Component 4-6)
- All backend implementations before OSC receiver (Component 7)
- OSC receiver before main entry point (Component 8)
- Discovery tools (Component 9) can be done anytime after backend implementations
- Testing (Component 10-11) requires all prior components complete

**Testing Strategy**:
- Component 0: Prerequisites and environment setup
- Component 1: Project structure
- Component 2-3: Backend abstraction layer (unit tests for interface)
- Component 4-6: Backend implementations (test imports, interface compliance)
- Component 7: OSC receiver (unit tests for effect calculations)
- Component 8: Main entry point (integration test with config validation)
- Component 9: Discovery tools (manual testing with real hardware)
- Component 10: Automated tests (pytest suite)
- Component 11: Full integration testing (bridge + OSC + bulbs)
- Component 12: Documentation and acceptance

**Test-First Approach**:
- Effect calculation (Component 7.2): Write test_effects.py first, then implement bpm_to_hue()
- Backend interface (Component 2-6): Write test_backends.py early, verify as backends are implemented
- Config validation (Component 8.3-8.9): Create invalid configs first, verify helpful errors

**Hardware Required**:
- Linux machine (or macOS/Windows with appropriate python-osc support)
- 4 Smart RGB bulbs:
  - Kasa (TP-Link): KL130 or similar (recommended)
  - Wyze: Color Bulbs A19 (if already owned)
  - WLED: ESP32 + LED strips (DIY option)
- Network: Local WiFi network for bulb discovery
- Pure Data audio pipeline (from Phase 1 audio)

**Software Required**:
- Python 3.8+ with pip
- python-osc, PyYAML (core dependencies)
- python-kasa (for Kasa backend)
- wyze-sdk (for Wyze backend)
- requests (for WLED backend)
- pytest (for automated tests)

**Backend Selection**:
- **Start with Kasa** (primary backend, most reliable)
- Wyze and WLED are optional unless you have that hardware
- Only install libraries for backends you need

**Dependencies**:
- Pure Data audio pipeline should be complete (Phase 1 audio)
- Audio pipeline sends OSC to port 8001 (lighting bridge receives)
- test-osc-sender.py from audio phase can be reused for lighting testing

**Time Estimate**:
- Prerequisites (Component 0): 15 min
- Project structure (Component 1): 10 min
- Backend abstraction (Component 2-3): 45 min
- Kasa backend (Component 4): 60 min
- Wyze backend (Component 5): 45 min (skip if not using Wyze)
- WLED backend (Component 6): 45 min (skip if not using WLED)
- OSC receiver (Component 7): 30 min
- Main entry point (Component 8): 60 min
- Discovery tools (Component 9): 30 min
- Automated tests (Component 10): 30 min
- Integration testing (Component 11): 90 min (+ 30 min stability test)
- Documentation (Component 12): 30 min
- **Total: 4-5 hours** (Kasa only), **6-7 hours** (all backends)

**Acceptance**: Phase 1 complete when all tasks checked off, bridge runs for 30+ minutes without errors, all backends tested, and all acceptance criteria verified.

**Key Features Delivered**:
- Python OSC receiver listening on port 8001
- Pluggable backend architecture (3 backends supported)
- Backend-agnostic effect calculation (BPM → hue)
- Two-step brightness pulse effect
- Config file for easy backend switching
- Discovery tools for all backends
- Drop statistics tracking and logging
- Graceful error handling (offline bulbs, network failures)
- 30-minute stability verified
- Complete documentation for expansion
