"""Wyze backend for Wyze smart bulbs (cloud control)."""

import time
from typing import Optional
from wyze_sdk import Client
from wyze_sdk.models.devices import Device
from .base import LightingBackend


class WyzeBackend(LightingBackend):
    """
    Wyze bulb control via cloud API.

    Features:
    - Cloud API (requires internet)
    - 300-500ms latency
    - Rate limiting (2.0 sec minimum between commands)
    - Tracks pulses dropped due to rate limiting
    """

    def __init__(self, config: dict):
        """Initialize WyzeBackend with empty bulb collections."""
        super().__init__(config)
        self.client = None  # Wyze SDK client
        self.bulbs = {}  # Map bulb_id (device_id) -> Device object
        self.zone_map = {}  # Map zone -> bulb_id (device_id)
        self.drop_stats = {}  # Track drops per bulb
        self.last_command_time = {}  # Track last command time for rate limiting

    def authenticate(self) -> None:
        """Initialize connection to Wyze bulbs via cloud API."""
        try:
            wyze_config = self.config.get('wyze', {})

            # Initialize Wyze SDK client
            email = wyze_config.get('email')
            password = wyze_config.get('password')

            if not email or not password:
                raise ValueError("Wyze config missing 'email' or 'password'")

            self.client = Client(email=email, password=password)

            # Fetch bulbs from cloud
            devices = self.client.bulbs.list()

            # Map configured bulbs
            bulb_configs = {b['device_id']: b for b in wyze_config.get('bulbs', [])}

            for device in devices:
                device_id = device.device_id
                if device_id not in bulb_configs:
                    continue  # Skip unconfigured bulbs

                bulb_cfg = bulb_configs[device_id]
                zone = bulb_cfg['zone']
                name = bulb_cfg['name']

                self.logger.info(f"Connecting to {name} ({device_id})...")

                # Store references
                self.bulbs[device_id] = device
                self.zone_map[zone] = device_id
                self.drop_stats[device_id] = 0
                self.last_command_time[device_id] = 0.0

                self.logger.info(f"Zone {zone} → {name} ({device_id}) - OK")

            self.logger.info(f"Wyze: {len(self.bulbs)} bulbs connected")

        except Exception as e:
            self.logger.error(f"Wyze authentication failed: {e}")
            raise SystemExit(1)

    def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:
        """Set Wyze bulb to HSV values with rate limiting."""
        # Check rate limiting (2.0 sec minimum)
        now = time.time()
        last = self.last_command_time.get(bulb_id, 0.0)
        time_since = now - last

        if time_since < 2.0:
            wait_time = 2.0 - time_since
            self.logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {bulb_id}")
            time.sleep(wait_time)

        try:
            bulb = self.bulbs.get(bulb_id)
            if not bulb:
                raise ValueError(f"Unknown bulb ID: {bulb_id}")

            # Set color via Wyze API (expects HSV)
            self.client.bulbs.set_color(
                device_id=bulb_id,
                color=(hue, saturation, brightness)
            )

            self.last_command_time[bulb_id] = time.time()

        except Exception as e:
            self.logger.error(f"Failed to set color for {bulb_id}: {e}")
            raise

    def pulse(self, bulb_id: str, hue: int, zone: int) -> None:
        """Execute brightness pulse effect with rate limiting and drop tracking."""
        try:
            effects = self.config.get('effects', {})
            baseline_bri = effects.get('baseline_brightness', 40)
            pulse_max = effects.get('pulse_max', 70)
            baseline_sat = effects.get('baseline_saturation', 75)

            # Check if we can execute (rate limit check before rising)
            now = time.time()
            last = self.last_command_time.get(bulb_id, 0.0)

            if now - last < 2.0:
                # Drop this pulse due to rate limiting
                self.drop_stats[bulb_id] += 1
                self.logger.debug(f"Pulse dropped for {bulb_id} (rate limit)")
                return

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
        """Initialize all Wyze bulbs to baseline (continue on errors)."""
        effects = self.config.get('effects', {})
        baseline_bri = effects.get('baseline_brightness', 40)
        baseline_sat = effects.get('baseline_saturation', 75)
        baseline_hue = effects.get('baseline_hue', 120)

        for bulb_id, bulb in self.bulbs.items():
            try:
                self.set_color(bulb_id, baseline_hue, baseline_sat, baseline_bri)

                # Get bulb name from config for logging
                bulb_cfg = next(
                    (b for b in self.config.get('wyze', {}).get('bulbs', [])
                     if b['device_id'] == bulb_id),
                    None
                )
                name = bulb_cfg['name'] if bulb_cfg else bulb_id
                self.logger.info(f"Initialized {name} to baseline")

            except Exception as e:
                self.logger.error(f"Failed to init {bulb_id}: {e}")

    def get_latency_estimate(self) -> float:
        """Return Wyze typical latency (300-500ms, return 400.0)."""
        return 400.0

    def print_stats(self) -> None:
        """Print drop statistics."""
        total_drops = sum(self.drop_stats.values())

        if total_drops == 0:
            self.logger.info("Wyze: No pulses dropped")
            return

        self.logger.info("Wyze drop statistics:")
        for bulb_id, count in self.drop_stats.items():
            bulb_cfg = next(
                (b for b in self.config.get('wyze', {}).get('bulbs', [])
                 if b['device_id'] == bulb_id),
                None
            )
            name = bulb_cfg['name'] if bulb_cfg else bulb_id
            self.logger.info(f"  {name}: {count} pulses dropped (rate limit)")

    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        """Map zone number to bulb device_id."""
        return self.zone_map.get(zone)
