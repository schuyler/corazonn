"""Kasa backend for TP-Link Kasa smart bulbs (local control)."""

import asyncio
import time
from typing import Optional
from kasa.iot import IotBulb
from .base import LightingBackend


class KasaBackend(LightingBackend):
    """
    TP-Link Kasa bulb control via local network.

    Features:
    - Local TCP control (no cloud)
    - 50-150ms latency
    - No rate limiting (bulb limits untested)
    - Async library wrapped in sync calls
    """

    def __init__(self, config: dict):
        """Initialize KasaBackend with empty bulb collections."""
        super().__init__(config)
        self.bulbs = {}  # Map bulb_id (IP) -> IotBulb object
        self.zone_map = {}  # Map zone -> bulb_id (IP)
        self.drop_stats = {}  # Track drops per bulb (network/device failures only)

    def authenticate(self) -> None:
        """Initialize connection to Kasa bulbs (R35, R36)."""
        try:
            kasa_config = self.config.get('kasa', {})

            # Connect to each configured bulb
            for bulb_cfg in kasa_config.get('bulbs', []):
                ip = bulb_cfg['ip']
                zone = bulb_cfg['zone']
                name = bulb_cfg['name']

                self.logger.info(f"Connecting to {name} ({ip})...")

                # Create IotBulb instance (R35: connect via IP from config)
                bulb = IotBulb(ip)

                # Update device info (R36: wrap async calls with asyncio.run())
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
        """Set Kasa bulb to HSV values (R36)."""
        try:
            bulb = self.bulbs.get(bulb_id)
            if not bulb:
                raise ValueError(f"Unknown bulb ID: {bulb_id}")

            # python-kasa uses async, wrap in sync call (R36)
            asyncio.run(bulb.set_hsv(hue, saturation, brightness))

        except Exception as e:
            self.logger.error(f"Failed to set color for {bulb_id}: {e}")
            raise

    def pulse(self, bulb_id: str, hue: int, zone: int) -> None:
        """Execute brightness pulse effect (R37: NO rate limiting)."""
        # No rate limiting enforced - Kasa bulb limits untested (R37)
        # Implementation sends all pulses; bulb behavior at high frequency unknown

        try:
            effects = self.config.get('effects', {})
            baseline_bri = effects.get('baseline_brightness', 40)
            pulse_max = effects.get('pulse_max', 70)
            baseline_sat = effects.get('baseline_saturation', 75)

            # Call 1: Rise to peak brightness
            self.set_color(bulb_id, hue, baseline_sat, pulse_max)

            # Hold at peak for attack + sustain time
            attack_sustain = (effects.get('attack_time_ms', 200) +
                            effects.get('sustain_time_ms', 100)) / 1000
            time.sleep(attack_sustain)

            # Call 2: Fall back to baseline brightness
            self.set_color(bulb_id, hue, baseline_sat, baseline_bri)

        except Exception as e:
            self.logger.error(f"Pulse failed for {bulb_id}: {e}")

    def set_all_baseline(self) -> None:
        """Initialize all Kasa bulbs to baseline (continue on errors)."""
        effects = self.config.get('effects', {})
        baseline_bri = effects.get('baseline_brightness', 40)
        baseline_sat = effects.get('baseline_saturation', 75)
        baseline_hue = effects.get('baseline_hue', 120)

        for bulb_id, bulb in self.bulbs.items():
            try:
                self.set_color(bulb_id, baseline_hue, baseline_sat, baseline_bri)

                # Get bulb name from config for logging
                bulb_cfg = next(
                    (b for b in self.config.get('kasa', {}).get('bulbs', [])
                     if b['ip'] == bulb_id),
                    None
                )
                name = bulb_cfg['name'] if bulb_cfg else bulb_id
                self.logger.info(f"Initialized {name} to baseline")

            except Exception as e:
                self.logger.error(f"Failed to init {bulb_id}: {e}")

    def get_latency_estimate(self) -> float:
        """Return Kasa typical latency (R34: 50-150ms, return 100.0)."""
        return 100.0

    def print_stats(self) -> None:
        """Print drop statistics (R37: will be 0 for Kasa since no rate limiting)."""
        total_drops = sum(self.drop_stats.values())

        if total_drops == 0:
            self.logger.info("Kasa: No pulses dropped")
            return

        self.logger.info("Kasa drop statistics:")
        for bulb_id, count in self.drop_stats.items():
            bulb_cfg = next(
                (b for b in self.config.get('kasa', {}).get('bulbs', [])
                 if b['ip'] == bulb_id),
                None
            )
            name = bulb_cfg['name'] if bulb_cfg else bulb_id
            self.logger.info(f"  {name}: {count} pulses dropped")

    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        """Map zone number to bulb IP."""
        return self.zone_map.get(zone)
