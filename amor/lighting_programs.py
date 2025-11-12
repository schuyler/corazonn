#!/usr/bin/env python3
"""
Lighting Programs - Stateful callback-based lighting controllers

Programs control all 4 zones simultaneously with state preserved between callbacks.
Each program receives beat events and continuous tick updates to create dynamic effects.

ARCHITECTURE:
- LightingProgram: Base class defining callback interface
- Concrete programs: SoftPulseProgram, RotatingGradientProgram, etc.
- State management: Simple dicts mutated in-place by callbacks
- Thread safety: Callbacks protected by engine's program_lock
- Backend injection: KasaBackend passed to all callbacks

CALLBACK INTERFACE:
- on_init(config, backend): Called once at program start, returns initial state dict
- on_beat(state, ppg_id, timestamp_ms, bpm, intensity, backend): Called on /beat/{ppg_id}
- on_tick(state, dt, backend): Called every ~100ms (10 FPS) for continuous updates
- on_cleanup(state, backend): Called when switching away from program

THREAD SAFETY:
- on_tick() runs on dedicated tick thread (serial execution)
- on_beat() runs on OSC handler thread (may interrupt tick)
- Both protected by engine's program_lock
- Backend methods are thread-safe (spawn separate threads)

CONFIGURATION:
Programs receive config from lighting.yaml's 'program.config' section.
Global config (zones, effects, kasa) available via engine's self.config.
"""

from typing import Dict, Any, Optional


class LightingProgram:
    """Base class for stateful lighting programs controlling all zones.

    Programs control all 4 zones simultaneously with state preserved between callbacks.
    Subclasses implement callbacks to respond to beat events and continuous updates.

    Callbacks:
        on_init: Initialize program state
        on_beat: Handle individual heartbeat events
        on_tick: Continuous updates (called ~10 FPS)
        on_cleanup: Cleanup when switching away

    Thread Safety:
        All callbacks run on same thread (engine's tick thread) except on_beat
        which may run concurrently from OSC handler thread. Programs must be
        thread-safe if they modify state in both on_beat and on_tick.

    State Management:
        Programs mutate state dict in-place. State is reset on program switch.
        Keep state small (<1KB) for performance. Pre-compute large data in on_init.
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Called once when program starts. Return initial state dict.

        Args:
            config (dict): Full lighting configuration from yaml
            backend (KasaBackend): Backend for bulb control

        Returns:
            dict: Initial state dictionary for this program

        Example:
            def on_init(self, config, backend):
                rotation_speed = config.get('program', {}).get('config', {}).get('rotation_speed', 30.0)
                return {
                    'hue_offset': 0.0,
                    'rotation_speed': rotation_speed,
                }
        """
        return {}

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Called on each /beat/{ppg_id} message.

        Runs on OSC handler thread. May execute concurrently with on_tick.
        Typically triggers visual pulse or effect synchronized to heartbeat.

        Args:
            state (dict): Mutable state dictionary (modify in-place)
            ppg_id (int): PPG sensor ID (0-3), maps to zone
            timestamp_ms (int): Unix time (milliseconds) when beat detected
            bpm (float): Heart rate in beats per minute
            intensity (float): Signal strength 0.0-1.0
            backend (KasaBackend): Backend for bulb control

        Example:
            def on_beat(self, state, ppg_id, timestamp_ms, bpm, intensity, backend):
                # Pulse the bulb for this zone
                bulb_id = backend.get_bulb_for_zone(ppg_id)
                hue = state.get('current_hue', 0)
                backend.pulse(bulb_id, hue, 75)
        """
        pass

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Called every frame (~10 FPS). dt in seconds since last tick.

        Runs on dedicated tick thread. Use for continuous animations,
        gradients, fades, or effects that update independent of beats.

        Args:
            state (dict): Mutable state dictionary (modify in-place)
            dt (float): Time since last tick in seconds (typically ~0.1)
            backend (KasaBackend): Backend for bulb control

        Example:
            def on_tick(self, state, dt, backend):
                # Rotate gradient continuously
                state['offset'] = (state['offset'] + 30 * dt) % 360
                for zone in range(4):
                    hue = (zone * 90 + state['offset']) % 360
                    backend.set_color(bulb_id, int(hue), 75, 40)
        """
        pass

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Called when switching away from this program.

        Use to reset bulbs, release resources, or save state.
        Program should leave bulbs in a reasonable state for next program.

        Args:
            state (dict): Final state dictionary
            backend (KasaBackend): Backend for bulb control

        Example:
            def on_cleanup(self, state, backend):
                # Set all bulbs to baseline
                backend.set_all_baseline()
        """
        pass


class SoftPulseProgram(LightingProgram):
    """Original soft_pulse behavior: fixed color per zone, pulse on beat.

    Each zone has a fixed hue (defined in config), and the bulb pulses
    brightness from baseline to peak and back on each heartbeat.

    This program is stateless and only responds to beats (no tick updates).
    Maintains backward compatibility with original lighting.py behavior.

    Configuration:
        Uses zones[N].hue for each zone's fixed color
        Uses effects.baseline_saturation for color saturation
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize soft pulse program (no state needed)."""
        # Set all bulbs to baseline on program start
        backend.set_all_baseline()
        return {}

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Lighting program: Fixed color per zone, brightness pulse on beat.

        Each zone has a fixed hue (defined in config), and the bulb pulses
        brightness from baseline to peak and back on each heartbeat.

        Args:
            state (dict): Program state (unused, stateless program)
            ppg_id (int): PPG sensor ID (0-3), maps to zone
            timestamp_ms (int): Unix time (milliseconds) when beat detected
            bpm (float): Heart rate in beats per minute (unused in this program)
            intensity (float): Signal strength 0.0-1.0 (unused in this program)
            backend (KasaBackend): Backend for bulb control
        """
        # Get bulb for this zone
        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if bulb_id is None:
            print(f"WARNING: No bulb configured for zone {ppg_id}")
            return

        # Get fixed hue and saturation for this zone
        zone_cfg = backend.config['zones'][ppg_id]
        hue = zone_cfg['hue']
        saturation = backend.config['effects'].get('baseline_saturation', 75)

        # Execute pulse
        backend.pulse(bulb_id, hue, saturation)

        zone_name = zone_cfg.get('name', f'Zone {ppg_id}')
        print(f"PULSE: {zone_name} (PPG {ppg_id}), BPM: {bpm:.1f}, Hue: {hue}°")

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Cleanup: set all bulbs to baseline."""
        backend.set_all_baseline()


# ============================================================================
# PROGRAM REGISTRY
# ============================================================================

# Program registry for engine to discover programs
# Add new programs here to make them available via /program OSC command
PROGRAMS: Dict[str, type] = {
    'soft_pulse': SoftPulseProgram,
    # Future programs:
    # 'rotating_gradient': RotatingGradientProgram,
    # 'bpm_morph': BpmMorphProgram,
    # 'convergence': ConvergenceProgram,
}
