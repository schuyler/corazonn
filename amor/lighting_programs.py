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
import math


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


class RotatingGradientProgram(LightingProgram):
    """Continuous color gradient rotating across all zones with beat pulses.

    Creates a smooth color gradient that rotates continuously around the room.
    Each zone maintains its position in the gradient (90° apart) while the
    entire gradient rotates. Beat pulses overlay on the current gradient color.

    Configuration:
        rotation_speed: Degrees per second to rotate gradient (default: 30.0)
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize rotating gradient with configurable speed."""
        speed = config.get('program', {}).get('config', {}).get('rotation_speed', 30.0)
        return {
            'offset': 0.0,  # Current gradient rotation offset (0-360)
            'rotation_speed': speed,  # Degrees per second
            'zone_spacing': 90,  # 90° between adjacent zones
        }

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Rotate the gradient continuously."""
        # Update rotation offset
        state['offset'] = (state['offset'] + state['rotation_speed'] * dt) % 360

        # Update all zone colors based on current gradient position
        baseline_bri = backend.config.get('effects', {}).get('baseline_brightness', 40)
        for zone in range(4):
            bulb_id = backend.get_bulb_for_zone(zone)
            if bulb_id:
                hue = int((zone * state['zone_spacing'] + state['offset']) % 360)
                backend.set_color(bulb_id, hue, 75, baseline_bri)

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Pulse at current gradient color for this zone."""
        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if bulb_id:
            # Calculate current hue for this zone based on gradient position
            hue = int((ppg_id * state['zone_spacing'] + state['offset']) % 360)
            backend.pulse(bulb_id, hue, 75)

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Reset bulbs to baseline."""
        backend.set_all_baseline()


class BreathingSyncProgram(LightingProgram):
    """All zones breathe together at the average group BPM.

    Synchronizes all bulbs to breathe in unison at the average heart rate
    of all participants. Creates a whole-room breathing effect that encourages
    group synchronization. Individual beats update the average but don't
    trigger individual pulses.

    Configuration:
        base_hue: Hue for breathing color (default: 200, calm blue)
        min_brightness: Minimum breathing brightness (default: 20)
        max_brightness: Maximum breathing brightness (default: 60)
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize breathing sync with tracked BPMs."""
        prog_config = config.get('program', {}).get('config', {})
        return {
            'recent_bpms': {0: 60.0, 1: 60.0, 2: 60.0, 3: 60.0},
            'breath_phase': 0.0,  # 0-1, cycles through breathing
            'base_hue': prog_config.get('base_hue', 200),  # Calm blue
            'min_brightness': prog_config.get('min_brightness', 20),
            'max_brightness': prog_config.get('max_brightness', 60),
        }

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Track recent BPM for each zone (no individual pulse)."""
        state['recent_bpms'][ppg_id] = bpm

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Update breathing animation for all zones."""
        # Calculate average BPM
        avg_bpm = sum(state['recent_bpms'].values()) / len(state['recent_bpms'])
        breath_rate = avg_bpm / 60.0  # Cycles per second

        # Update breath phase
        state['breath_phase'] = (state['breath_phase'] + breath_rate * dt) % 1.0

        # Calculate brightness (sine wave breathing)
        brightness_range = state['max_brightness'] - state['min_brightness']
        brightness = int(
            state['min_brightness'] +
            brightness_range * (0.5 + 0.5 * math.sin(state['breath_phase'] * 2 * math.pi))
        )

        # Apply to all zones
        for zone in range(4):
            bulb_id = backend.get_bulb_for_zone(zone)
            if bulb_id:
                backend.set_color(bulb_id, state['base_hue'], 75, brightness)

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Reset bulbs to baseline."""
        backend.set_all_baseline()


class ConvergenceProgram(LightingProgram):
    """Detects when 2+ people sync up, shifts their zones to matching color.

    Monitors BPM across all zones and detects when participants' heart rates
    converge (within threshold). Converged zones shift to a unified color
    (gold) while non-converged zones maintain their default colors. Provides
    visual feedback for group synchronization.

    Configuration:
        convergence_threshold: BPM difference ratio for convergence (default: 0.05 = 5%)
        convergence_hue: Hue for converged zones (default: 45, gold)
        convergence_saturation: Saturation for converged zones (default: 90)
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize convergence detection."""
        prog_config = config.get('program', {}).get('config', {})
        # Get default hues from zone config
        default_hues = {
            zone: backend.config['zones'][zone]['hue']
            for zone in range(4)
        }
        return {
            'recent_bpms': {0: 60.0, 1: 60.0, 2: 60.0, 3: 60.0},
            'zone_hues': default_hues.copy(),
            'default_hues': default_hues,
            'convergence_threshold': prog_config.get('convergence_threshold', 0.05),
            'convergence_hue': prog_config.get('convergence_hue', 45),  # Gold
            'convergence_saturation': prog_config.get('convergence_saturation', 90),
        }

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Update BPM and check for convergence."""
        state['recent_bpms'][ppg_id] = bpm

        # Check for convergence between all pairs
        converged_zones = set()
        for i in range(4):
            for j in range(i + 1, 4):
                bpm_i = state['recent_bpms'][i]
                bpm_j = state['recent_bpms'][j]
                # Validate BPMs are positive to avoid division by zero
                if min(bpm_i, bpm_j) > 0 and abs(bpm_i - bpm_j) / min(bpm_i, bpm_j) < state['convergence_threshold']:
                    converged_zones.add(i)
                    converged_zones.add(j)

        # Update zone hues based on convergence
        for zone in range(4):
            if zone in converged_zones:
                state['zone_hues'][zone] = state['convergence_hue']
            # else: let on_tick() handle gradual drift back to default

        # Pulse the triggering zone at current hue
        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if bulb_id:
            saturation = state['convergence_saturation'] if ppg_id in converged_zones else 75
            backend.pulse(bulb_id, int(state['zone_hues'][ppg_id]), saturation)

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Gradually drift non-converged zones back to defaults."""
        # Update baseline colors for all zones
        baseline_bri = backend.config.get('effects', {}).get('baseline_brightness', 40)
        for zone in range(4):
            bulb_id = backend.get_bulb_for_zone(zone)
            if bulb_id:
                current_hue = state['zone_hues'][zone]
                default_hue = state['default_hues'][zone]

                # If not at default, drift back slowly (20°/sec)
                if current_hue != default_hue:
                    # Calculate shortest rotation direction
                    diff = (default_hue - current_hue + 180) % 360 - 180
                    # Drift 20°/sec toward default
                    drift_rate = 20.0 * dt  # Actual degrees to move this tick
                    if abs(diff) < drift_rate:
                        new_hue = default_hue  # Close enough, snap to target
                    else:
                        new_hue = (current_hue + math.copysign(drift_rate, diff)) % 360
                    state['zone_hues'][zone] = new_hue

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Reset bulbs to baseline."""
        backend.set_all_baseline()


class WaveChaseProgram(LightingProgram):
    """Beat in one zone triggers a wave through adjacent zones.

    Each heartbeat creates a brightness wave that propagates through
    adjacent zones in a circular pattern. Multiple waves can be active
    simultaneously, creating dynamic spatial effects.

    Configuration:
        wave_duration: Total wave duration in seconds (default: 2.0)
        wave_brightness: Peak brightness of wave (default: 60)
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize wave tracking."""
        prog_config = config.get('program', {}).get('config', {})
        return {
            'active_waves': [],  # List of {origin, elapsed, hue}
            'wave_duration': prog_config.get('wave_duration', 2.0),
            'wave_brightness': prog_config.get('wave_brightness', 60),
        }

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Start a new wave from this zone."""
        hue = backend.config['zones'][ppg_id]['hue']
        state['active_waves'].append({
            'origin': ppg_id,
            'elapsed': 0.0,
            'hue': hue,
        })

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Update all active waves."""
        baseline_bri = backend.config.get('effects', {}).get('baseline_brightness', 40)

        # Update wave timers and remove expired waves
        for wave in state['active_waves'][:]:
            wave['elapsed'] += dt

            if wave['elapsed'] > state['wave_duration']:
                state['active_waves'].remove(wave)
                continue

        # Calculate brightness for each zone based on all active waves
        zone_brightness = {0: 0, 1: 0, 2: 0, 3: 0}
        zone_hue = {0: 0, 1: 0, 2: 0, 3: 0}

        for wave in state['active_waves']:
            progress = wave['elapsed'] / state['wave_duration']

            for zone in range(4):
                # Calculate circular distance from origin
                distance = abs(zone - wave['origin'])
                if distance > 2:
                    distance = 4 - distance  # Wrap around (circular)

                # Calculate brightness based on wave position
                zone_progress = distance * 0.25  # Each zone is 25% of wave
                if abs(progress - zone_progress) < 0.25:
                    # Wave is affecting this zone
                    brightness_contribution = state['wave_brightness'] * (
                        1 - abs(progress - zone_progress) / 0.25
                    )
                    if brightness_contribution > zone_brightness[zone]:
                        zone_brightness[zone] = brightness_contribution
                        zone_hue[zone] = wave['hue']

        # Apply calculated brightness to all zones
        for zone in range(4):
            bulb_id = backend.get_bulb_for_zone(zone)
            if bulb_id:
                brightness = int(baseline_bri + zone_brightness[zone])
                hue = int(zone_hue[zone]) if zone_brightness[zone] > 0 else backend.config['zones'][zone]['hue']
                backend.set_color(bulb_id, hue, 75, brightness)

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Reset bulbs to baseline."""
        backend.set_all_baseline()


class IntensityReactiveProgram(LightingProgram):
    """Brightness and saturation respond to PPG signal intensity.

    Uses the intensity parameter from beat detection to modulate both
    color saturation and pulse brightness. Higher signal quality results
    in more vivid colors. BPM still controls hue (blue=calm, red=active).

    Configuration:
        min_saturation: Minimum saturation for low intensity (default: 50)
        max_saturation: Maximum saturation for high intensity (default: 100)
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize intensity tracking."""
        prog_config = config.get('program', {}).get('config', {})
        return {
            'zone_intensities': {0: 0.5, 1: 0.5, 2: 0.5, 3: 0.5},
            'zone_hues': {0: 0, 1: 0, 2: 0, 3: 0},  # Store current hue per zone
            'min_saturation': prog_config.get('min_saturation', 50),
            'max_saturation': prog_config.get('max_saturation', 100),
        }

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Pulse with intensity-modulated saturation."""
        # Store intensity and hue
        state['zone_intensities'][ppg_id] = intensity

        # BPM to hue mapping (40 BPM=blue/240°, 120 BPM=red/0°)
        bpm_clamped = min(max(bpm, 40), 120)
        hue = int((120 - bpm_clamped) * 3)
        state['zone_hues'][ppg_id] = hue

        # Intensity to saturation mapping
        saturation_range = state['max_saturation'] - state['min_saturation']
        saturation = int(state['min_saturation'] + intensity * saturation_range)

        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if bulb_id:
            backend.pulse(bulb_id, hue, saturation)

        zone_name = backend.config['zones'][ppg_id].get('name', f'Zone {ppg_id}')
        print(f"PULSE: {zone_name} (PPG {ppg_id}), BPM: {bpm:.1f}, "
              f"Intensity: {intensity:.2f}, Hue: {hue}°, Sat: {saturation}%")

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Update bulbs to show decaying intensity."""
        baseline_bri = backend.config.get('effects', {}).get('baseline_brightness', 40)

        for zone in range(4):
            # Exponential decay with floor
            state['zone_intensities'][zone] = max(0.1, state['zone_intensities'][zone] * (0.95 ** (dt * 10)))

            # Update visual to show current intensity
            bulb_id = backend.get_bulb_for_zone(zone)
            if bulb_id:
                # Recompute saturation based on current intensity
                sat_range = state['max_saturation'] - state['min_saturation']
                saturation = int(state['min_saturation'] + state['zone_intensities'][zone] * sat_range)
                # Use stored hue from last beat
                hue = state['zone_hues'][zone]
                backend.set_color(bulb_id, hue, saturation, baseline_bri)

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Reset bulbs to baseline."""
        backend.set_all_baseline()


# ============================================================================
# PROGRAM REGISTRY
# ============================================================================

# Program registry for engine to discover programs
# Add new programs here to make them available via /program OSC command
PROGRAMS: Dict[str, type] = {
    'soft_pulse': SoftPulseProgram,
    'rotating_gradient': RotatingGradientProgram,
    'breathing_sync': BreathingSyncProgram,
    'convergence': ConvergenceProgram,
    'wave_chase': WaveChaseProgram,
    'intensity_reactive': IntensityReactiveProgram,
}
