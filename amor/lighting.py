#!/usr/bin/env python3
"""
Lighting Engine - Amor Kasa Smart Bulb Control

Receives beat events from sensor processor, controls TP-Link Kasa smart bulbs
with programmable lighting effects per zone.

ARCHITECTURE:
- OSC server listening on port 8002 for beat input (/beat/{0-3} messages)
- Uses SO_REUSEPORT socket option to allow port sharing across processes
- KasaBackend for local TCP control of TP-Link Kasa bulbs
- Per-zone lighting programs (soft_pulse, future: bpm_morph, chase, etc.)
- Two-step pulse effect (rise to peak, fall to baseline)
- Statistics tracking for pulse events

LIGHTING PROGRAMS:
- soft_pulse: Fixed color per zone, brightness pulse on beat
- (Future programs can be added with minimal code changes)

ZONE ASSIGNMENT:
- Zone 0 (PPG 0) → Person 1
- Zone 1 (PPG 1) → Person 2
- Zone 2 (PPG 2) → Person 3
- Zone 3 (PPG 3) → Person 4

INPUT OSC MESSAGES:
    Address: /beat/{ppg_id}  where ppg_id is 0-3
    Arguments: [timestamp_ms, bpm, intensity]
    - timestamp_ms: int, Unix time (milliseconds) when beat detected
    - bpm: float, heart rate in beats per minute
    - intensity: float, signal strength 0.0-1.0 (reserved for future use)

KASA CONTROL:
- Local TCP communication (no cloud)
- ~100ms latency typical
- Async library wrapped in sync calls
- HSV color control (hue 0-360°, saturation 0-100%, brightness 0-100%)

USAGE:
    # Start with default settings (port 8002, config)
    python3 -m amor.lighting

    # Custom port and config
    python3 -m amor.lighting --port 8002 --config amor/config/lighting.yaml

Reference: docs/amor-lighting-design.md
"""

import argparse
import asyncio
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
import yaml
from pythonosc import dispatcher
from kasa.iot import IotBulb

from amor import osc


# ============================================================================
# KASA BACKEND (Simplified from /lighting/src/backends/kasa_backend.py)
# ============================================================================

class KasaBackend:
    """
    TP-Link Kasa bulb control via local network.

    Features:
    - Local TCP control (no cloud)
    - 50-150ms latency
    - Async library wrapped in sync calls
    - Zone → bulb IP mapping
    """

    def __init__(self, config: dict):
        """Initialize KasaBackend with empty bulb collections."""
        self.config = config
        self.bulbs = {}  # Map bulb_id (IP) → IotBulb object
        self.zone_map = {}  # Map zone → bulb_id (IP)
        self.stats = {
            'total_pulses': 0,
            'backend_pulse_errors': 0,
        }

    def authenticate(self) -> None:
        """Initialize connection to Kasa bulbs."""
        try:
            kasa_config = self.config.get('kasa', {})

            # Connect to each configured bulb
            for bulb_cfg in kasa_config.get('bulbs', []):
                ip = bulb_cfg['ip']
                zone = bulb_cfg['zone']
                name = bulb_cfg['name']

                print(f"Connecting to {name} ({ip})...")

                # Create IotBulb instance
                bulb = IotBulb(ip)

                # Update device info (wrap async calls with asyncio.run())
                asyncio.run(bulb.update())

                # Store references
                self.bulbs[ip] = bulb
                self.zone_map[zone] = ip

                print(f"  Zone {zone} → {name} ({ip}) - OK")

            print(f"Kasa: {len(self.bulbs)} bulbs connected")

        except Exception as e:
            print(f"ERROR: Kasa authentication failed: {e}", file=sys.stderr)
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
            raise RuntimeError(f"Failed to set color for {bulb_id}: {e}")

    def pulse(self, bulb_id: str, hue: int, saturation: int) -> None:
        """Execute brightness pulse effect (non-blocking via thread).

        Launches _blocking_pulse() in a daemon thread to avoid blocking
        the OSC message handler. This allows multiple simultaneous pulses
        across different zones without queuing delays.
        """
        thread = threading.Thread(
            target=self._blocking_pulse,
            args=(bulb_id, hue, saturation),
            daemon=True
        )
        thread.start()

    def _blocking_pulse(self, bulb_id: str, hue: int, saturation: int) -> None:
        """Internal blocking pulse implementation (two-step: rise, hold, fall).

        Called by pulse() in a separate thread to avoid blocking OSC handler.
        """
        try:
            self.stats['total_pulses'] += 1

            effects = self.config.get('effects', {})
            baseline_bri = effects.get('baseline_brightness', 40)
            pulse_max = effects.get('pulse_max', 70)

            # Call 1: Rise to peak brightness
            self.set_color(bulb_id, hue, saturation, pulse_max)

            # Hold at peak for attack + sustain time
            attack_sustain = (effects.get('attack_time_ms', 200) +
                            effects.get('sustain_time_ms', 100)) / 1000
            time.sleep(attack_sustain)

            # Call 2: Fall back to baseline brightness (instant return)
            self.set_color(bulb_id, hue, saturation, baseline_bri)

        except Exception as e:
            self.stats['backend_pulse_errors'] += 1
            print(f"WARNING: Pulse failed for {bulb_id}: {e}")

    def set_all_baseline(self) -> None:
        """Initialize all Kasa bulbs to baseline (continue on errors)."""
        effects = self.config.get('effects', {})
        baseline_bri = effects.get('baseline_brightness', 40)
        baseline_sat = effects.get('baseline_saturation', 75)

        zones_config = self.config.get('zones', {})

        for zone, bulb_id in self.zone_map.items():
            try:
                # Get zone-specific hue from config
                zone_cfg = zones_config.get(zone, {})
                hue = zone_cfg.get('hue', 120)  # Default green if not specified

                self.set_color(bulb_id, hue, baseline_sat, baseline_bri)

                # Get bulb name from config for logging
                bulb_cfg = next(
                    (b for b in self.config.get('kasa', {}).get('bulbs', [])
                     if b['ip'] == bulb_id),
                    None
                )
                name = bulb_cfg['name'] if bulb_cfg else bulb_id
                print(f"  Initialized {name} (zone {zone}) to baseline: hue={hue}°")

            except Exception as e:
                print(f"WARNING: Failed to init {bulb_id}: {e}")

    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        """Map zone number to bulb IP."""
        return self.zone_map.get(zone)

    def print_stats(self) -> None:
        """Print pulse statistics."""
        print("\n" + "=" * 60)
        print("KASA BACKEND STATISTICS")
        print("=" * 60)
        print(f"Total Pulses: {self.stats['total_pulses']}")
        print(f"Backend Pulse Errors: {self.stats['backend_pulse_errors']}")
        if self.stats['total_pulses'] > 0:
            success_rate = ((self.stats['total_pulses'] - self.stats['backend_pulse_errors'])
                          / self.stats['total_pulses'] * 100)
            print(f"Success Rate: {success_rate:.1f}%")
        print("=" * 60)


# ============================================================================
# LIGHTING ENGINE
# ============================================================================

class LightingEngine:
    """OSC server for beat event lighting control using Kasa bulbs.

    Manages beat reception, timestamp validation, and programmable lighting
    effects per zone. Uses KasaBackend for local TCP bulb control.

    Architecture:
        - OSC server on port (default 8002) listening for /beat/{0-3} messages
        - Four zones mapped to Kasa bulbs via configuration
        - Per-zone lighting programs (soft_pulse, future extensibility)
        - Message validation and statistics tracking

    Attributes:
        port (int): UDP port for beat input (default: 8002)
        config_path (str): Path to lighting.yaml configuration
        config (dict): Loaded configuration
        backend (KasaBackend): Kasa bulb controller
        programs (dict): Zone → program name mapping
        stats (osc.MessageStatistics): Message counters
    """

    # Timestamp age threshold in milliseconds
    TIMESTAMP_THRESHOLD_MS = 500

    def __init__(self, port=8002, config_path="amor/config/lighting.yaml"):
        """Initialize lighting engine and load configuration.

        Args:
            port (int): OSC port to listen on (default 8002)
            config_path (str): Path to lighting.yaml configuration

        Raises:
            FileNotFoundError: If config file is missing
            ValueError: If config validation fails
            SystemExit: If Kasa authentication fails
        """
        self.port = port
        self.config_path = config_path

        # Load and validate configuration
        self.config = self.load_config(config_path)

        # Initialize Kasa backend
        self.backend = KasaBackend(self.config)

        # Initialize per-zone programs (all start with soft_pulse)
        self.programs = {
            0: "soft_pulse",
            1: "soft_pulse",
            2: "soft_pulse",
            3: "soft_pulse",
        }

        # Statistics
        self.stats = osc.MessageStatistics()

        print(f"Lighting Engine initialized")
        print(f"  Port: {port}")
        print(f"  Config: {config_path}")
        print(f"  Programs: {self.programs}")

    def load_config(self, config_path: str) -> dict:
        """Load and validate YAML configuration.

        Args:
            config_path: Path to lighting.yaml

        Returns:
            Validated configuration dict

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config validation fails
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Create amor/config/lighting.yaml with zone and bulb configuration."
            )

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        # Validate structure
        if 'zones' not in config:
            raise ValueError("Config missing 'zones' section")
        if 'kasa' not in config:
            raise ValueError("Config missing 'kasa' section")
        if 'effects' not in config:
            raise ValueError("Config missing 'effects' section")

        # Validate zones (0-3, each with hue)
        zones = config['zones']
        for zone_id in range(4):
            if zone_id not in zones:
                raise ValueError(f"Config missing zone {zone_id} definition")
            zone_cfg = zones[zone_id]
            if 'hue' not in zone_cfg:
                raise ValueError(f"Zone {zone_id} missing 'hue' parameter")
            hue = zone_cfg['hue']
            if not (0 <= hue <= 360):
                raise ValueError(f"Zone {zone_id} hue must be 0-360, got {hue}")

        # Validate Kasa bulbs
        kasa_config = config.get('kasa', {})
        bulbs = kasa_config.get('bulbs', [])
        if len(bulbs) == 0:
            raise ValueError("No Kasa bulbs configured")

        # Validate zone assignments are 0-3 and unique
        zones_assigned = [b.get('zone') for b in bulbs]
        for z in zones_assigned:
            if z is not None and not (0 <= z <= 3):
                raise ValueError(f"Invalid zone: {z} (must be 0-3)")
        if len(zones_assigned) != len(set(zones_assigned)):
            raise ValueError("Duplicate zones in Kasa bulb configuration")

        # Validate effect parameters
        effects = config.get('effects', {})
        for param in ['baseline_brightness', 'pulse_max', 'baseline_saturation']:
            val = effects.get(param)
            if val is not None and not (0 <= val <= 100):
                raise ValueError(f"{param} must be 0-100, got {val}")

        for param in ['attack_time_ms', 'sustain_time_ms']:
            val = effects.get(param)
            if val is not None and val <= 0:
                raise ValueError(f"{param} must be > 0, got {val}")

        print(f"Loaded config from {config_path}")
        print(f"  Zones: {len(zones)} defined")
        print(f"  Bulbs: {len(bulbs)} configured")

        return config

    def validate_timestamp(self, timestamp_ms: int) -> tuple[bool, float]:
        """Validate beat timestamp age.

        Args:
            timestamp_ms (int): Unix time in milliseconds

        Returns:
            tuple: (is_valid, age_ms)
                - is_valid (bool): True if timestamp < 500ms old
                - age_ms (float): Age of timestamp in milliseconds
        """
        now_ms = time.time() * 1000.0
        age_ms = now_ms - timestamp_ms

        is_valid = age_ms < self.TIMESTAMP_THRESHOLD_MS
        return is_valid, age_ms

    def validate_message(self, address: str, args: tuple) -> tuple:
        """Validate OSC message format and content.

        Expected format:
            Address: /beat/{ppg_id}  where ppg_id is 0-3
            Arguments: [timestamp_ms, bpm, intensity]

        Args:
            address (str): OSC message address
            args (tuple): Message arguments

        Returns:
            tuple: (is_valid, ppg_id, timestamp_ms, bpm, intensity, error_message)
        """
        # Validate address pattern: /beat/[0-3]
        is_valid, ppg_id, error_msg = osc.validate_beat_address(address)
        if not is_valid:
            return False, None, None, None, None, error_msg

        # Validate argument count (should be 3: timestamp_ms, bpm, intensity)
        if len(args) != 3:
            return False, ppg_id, None, None, None, (
                f"Expected 3 arguments, got {len(args)} (PPG {ppg_id})"
            )

        # Extract and validate arguments
        try:
            timestamp_ms = int(args[0])
            bpm = float(args[1])
            intensity = float(args[2])
        except (TypeError, ValueError) as e:
            return False, ppg_id, None, None, None, (
                f"Invalid argument types: {e} (PPG {ppg_id})"
            )

        # Timestamp should be non-negative
        if timestamp_ms < 0:
            return False, ppg_id, timestamp_ms, bpm, intensity, (
                f"Invalid timestamp: {timestamp_ms} (PPG {ppg_id})"
            )

        return True, ppg_id, timestamp_ms, bpm, intensity, None

    # ========================================================================
    # LIGHTING PROGRAMS
    # ========================================================================

    def program_soft_pulse(self, ppg_id: int, bpm: float, intensity: float) -> None:
        """Lighting program: Fixed color per zone, brightness pulse on beat.

        Each zone has a fixed hue (defined in config), and the bulb pulses
        brightness from baseline to peak and back on each heartbeat.

        Args:
            ppg_id (int): PPG sensor ID (0-3), maps to zone
            bpm (float): Heart rate in beats per minute (unused in this program)
            intensity (float): Signal strength 0.0-1.0 (unused in this program)
        """
        # Get bulb for this zone
        bulb_id = self.backend.get_bulb_for_zone(ppg_id)
        if bulb_id is None:
            print(f"WARNING: No bulb configured for zone {ppg_id}")
            return

        # Get fixed hue and saturation for this zone
        zone_cfg = self.config['zones'][ppg_id]
        hue = zone_cfg['hue']
        saturation = self.config['effects'].get('baseline_saturation', 75)

        # Execute pulse
        self.backend.pulse(bulb_id, hue, saturation)

        zone_name = zone_cfg.get('name', f'Zone {ppg_id}')
        print(f"PULSE: {zone_name} (PPG {ppg_id}), BPM: {bpm:.1f}, Hue: {hue}°")

    def handle_beat_message(self, ppg_id: int, timestamp_ms: int, bpm: float, intensity: float) -> None:
        """Process a beat message and execute lighting program.

        Called after validation. Checks timestamp age, dispatches to
        appropriate lighting program based on zone configuration.

        Args:
            ppg_id (int): PPG sensor ID (0-3)
            timestamp_ms (int): Unix time (milliseconds) of beat
            bpm (float): Heart rate in beats per minute
            intensity (float): Signal strength 0.0-1.0
        """
        # Validate timestamp age
        is_valid, age_ms = self.validate_timestamp(timestamp_ms)

        if not is_valid:
            self.stats.increment('dropped_messages')
            print(f"DROPPED: PPG {ppg_id}, age: {age_ms:.1f}ms (threshold: {self.TIMESTAMP_THRESHOLD_MS}ms)")
            return

        self.stats.increment('valid_messages')

        # Dispatch to program
        program = self.programs.get(ppg_id, "soft_pulse")

        try:
            if program == "soft_pulse":
                self.program_soft_pulse(ppg_id, bpm, intensity)
            # Future programs:
            # elif program == "bpm_morph":
            #     self.program_bpm_morph(ppg_id, bpm, intensity)
            # elif program == "chase":
            #     self.program_chase(ppg_id, bpm, intensity)
            else:
                print(f"WARNING: Unknown program '{program}' for PPG {ppg_id}")
                return

            self.stats.increment('pulses_executed')

        except Exception as e:
            self.stats.increment('failed_pulses')
            print(f"WARNING: Failed to execute {program} for PPG {ppg_id}: {e}")

    def handle_osc_beat_message(self, address: str, *args) -> None:
        """Handle incoming beat OSC message.

        Called by OSC dispatcher when /beat/{0-3} message arrives.
        Validates message and processes through beat handler.

        Args:
            address (str): OSC address (e.g., "/beat/0")
            *args: Variable arguments from OSC message
        """
        # Count ALL messages here (valid and invalid)
        self.stats.increment('total_messages')

        # Validate message
        is_valid, ppg_id, timestamp_ms, bpm, intensity, error_msg = self.validate_message(
            address, args
        )

        if not is_valid:
            self.stats.increment('dropped_messages')
            if error_msg:
                print(f"WARNING: {error_msg}")
            return

        # Process valid beat (don't increment total_messages again)
        self.handle_beat_message(ppg_id, timestamp_ms, bpm, intensity)

    def run(self) -> None:
        """Start the OSC server and process beat messages.

        Blocks indefinitely, listening for /beat/{0-3} messages on the port.
        Handles Ctrl+C gracefully with clean shutdown and statistics.
        """
        # Authenticate and initialize backend
        print("Authenticating Kasa backend...")
        self.backend.authenticate()

        print("Setting all bulbs to baseline...")
        self.backend.set_all_baseline()

        # Create dispatcher and bind handler
        disp = dispatcher.Dispatcher()
        disp.map("/beat/*", self.handle_osc_beat_message)

        # Create OSC server with SO_REUSEPORT for port sharing
        server = osc.ReusePortBlockingOSCUDPServer(("0.0.0.0", self.port), disp)

        print(f"\nLighting Engine listening on port {self.port}")
        print(f"Expecting /beat/{{0-3}} messages with [timestamp_ms, bpm, intensity]")
        print(f"Timestamp validation: drop if >= {self.TIMESTAMP_THRESHOLD_MS}ms old")
        print(f"Programs: {self.programs}")
        print(f"Waiting for messages... (Ctrl+C to stop)\n")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        except Exception as e:
            print(f"\nERROR: Server crashed: {e}", file=sys.stderr)
        finally:
            server.shutdown()
            self.stats.print_stats("LIGHTING ENGINE STATISTICS")
            self.backend.print_stats()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point with command-line argument parsing.

    Parses arguments for port and config file path,
    creates LightingEngine instance, and handles runtime errors.

    Command-line arguments:
        --port N            UDP port to listen for beat input (default: 8002)
        --config PATH       Path to lighting.yaml (default: amor/config/lighting.yaml)

    Example usage:
        python3 -m amor.lighting
        python3 -m amor.lighting --port 8002
        python3 -m amor.lighting --config /path/to/lighting.yaml
    """
    parser = argparse.ArgumentParser(description="Lighting Engine - Beat lighting control (Kasa)")
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="UDP port to listen for beat input (default: 8002)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="amor/config/lighting.yaml",
        help="Path to lighting.yaml config (default: amor/config/lighting.yaml)",
    )

    args = parser.parse_args()

    # Validate port
    try:
        osc.validate_port(args.port)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Create and run engine
    try:
        engine = LightingEngine(port=args.port, config_path=args.config)
        engine.run()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Port {args.port} already in use", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
