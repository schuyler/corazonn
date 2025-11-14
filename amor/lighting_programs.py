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
import time

from amor.log import get_logger

logger = get_logger(__name__)


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
            'time_since_update': 0.0,  # Time accumulator for 2s throttle
        }

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Rotate the gradient continuously."""
        # Always update rotation offset (internal state)
        state['offset'] = (state['offset'] + state['rotation_speed'] * dt) % 360

        # Accumulate time for throttling
        state['time_since_update'] += dt

        # Only update bulbs every 2 seconds (hardware transition minimum)
        if state['time_since_update'] < 2.0:
            return

        state['time_since_update'] = 0.0

        # Update all zone colors with smooth 2s transitions
        baseline_bri = backend.config.get('effects', {}).get('baseline_brightness', 40)
        for zone in range(4):
            bulb_id = backend.get_bulb_for_zone(zone)
            if bulb_id:
                hue = int((zone * state['zone_spacing'] + state['offset']) % 360)
                backend.set_color(bulb_id, hue, 75, baseline_bri, transition=2000)

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Pulse at current gradient color for this zone using smooth fade."""
        if bpm <= 0:
            return

        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if not bulb_id:
            return

        # Calculate current hue for this zone based on gradient position
        hue = int((ppg_id * state['zone_spacing'] + state['offset']) % 360)

        # Fast attack smooth fade (same as FastAttackProgram)
        baseline_bri = backend.config['effects'].get('baseline_brightness', 40)
        pulse_max = backend.config['effects'].get('pulse_max', 70)

        ibi_ms = 60000.0 / bpm
        fade_beats = math.ceil(2000.0 / ibi_ms)
        fade_ms = int(fade_beats * ibi_ms)

        # Instant attack, smooth fade
        backend.set_color(bulb_id, hue, 75, pulse_max, transition=0)
        backend.set_color(bulb_id, hue, 75, baseline_bri, transition=fade_ms)

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
            'time_since_update': 0.0,  # Time accumulator for 2s throttle
        }

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Track recent BPM for each zone (no individual pulse)."""
        state['recent_bpms'][ppg_id] = bpm

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Update breathing animation with 2s smooth transitions."""
        # Always update breath phase (internal state)
        avg_bpm = sum(state['recent_bpms'].values()) / len(state['recent_bpms'])
        breath_rate = avg_bpm / 60.0  # Cycles per second
        state['breath_phase'] = (state['breath_phase'] + breath_rate * dt) % 1.0

        # Accumulate time for throttling
        state['time_since_update'] += dt

        # Only update bulbs every 2 seconds (hardware transition minimum)
        if state['time_since_update'] < 2.0:
            return

        state['time_since_update'] = 0.0

        # Calculate target brightness 2 seconds in the future
        future_phase = (state['breath_phase'] + breath_rate * 2.0) % 1.0
        brightness_range = state['max_brightness'] - state['min_brightness']
        target_brightness = int(
            state['min_brightness'] +
            brightness_range * (0.5 + 0.5 * math.sin(future_phase * 2 * math.pi))
        )

        # Apply to all zones with smooth 2s transition
        for zone in range(4):
            bulb_id = backend.get_bulb_for_zone(zone)
            if bulb_id:
                backend.set_color(bulb_id, state['base_hue'], 75, target_brightness, transition=2000)

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
        if bpm <= 0:
            return

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

        # Pulse with smooth fade (fast_attack pattern)
        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if not bulb_id:
            return

        hue = int(state['zone_hues'][ppg_id])
        saturation = state['convergence_saturation'] if ppg_id in converged_zones else 75
        baseline_bri = backend.config['effects'].get('baseline_brightness', 40)
        pulse_max = backend.config['effects'].get('pulse_max', 70)

        # Calculate BPM-adaptive fade
        ibi_ms = 60000.0 / bpm
        fade_beats = math.ceil(2000.0 / ibi_ms)
        fade_ms = int(fade_beats * ibi_ms)

        # Instant attack, smooth fade
        backend.set_color(bulb_id, hue, saturation, pulse_max, transition=0)
        backend.set_color(bulb_id, hue, saturation, baseline_bri, transition=fade_ms)

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
    """Beat in one zone triggers sequential smooth pulses through adjacent zones.

    Each heartbeat creates a cascade effect: origin zone pulses first, then
    adjacent zones pulse in sequence with staggered timing. Uses smooth 2s
    transitions for each zone's pulse.

    Configuration:
        stagger_ms: Time offset between zone pulses (default: 500ms)
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize wave chase."""
        prog_config = config.get('program', {}).get('config', {})
        backend.set_all_baseline()
        return {
            'stagger_ms': prog_config.get('stagger_ms', 500),  # 500ms between zones
        }

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Trigger sequential cascade starting from this zone."""
        if bpm <= 0:
            return

        # Get config values
        baseline_bri = backend.config['effects'].get('baseline_brightness', 40)
        pulse_max = backend.config['effects'].get('pulse_max', 70)
        saturation = backend.config['effects'].get('baseline_saturation', 75)
        stagger_ms = state['stagger_ms']

        # Calculate fade duration
        ibi_ms = 60000.0 / bpm
        fade_beats = math.ceil(2000.0 / ibi_ms)
        fade_ms = int(fade_beats * ibi_ms)

        # Trigger cascade through 4 zones in circular order
        for offset in range(4):
            zone = (ppg_id + offset) % 4
            bulb_id = backend.get_bulb_for_zone(zone)
            if not bulb_id:
                continue

            hue = backend.config['zones'][zone]['hue']
            delay_ms = offset * stagger_ms

            # Schedule pulse with delay (use threading for stagger)
            if delay_ms == 0:
                # Origin zone: instant attack, smooth fade
                backend.set_color(bulb_id, hue, saturation, pulse_max, transition=0)
                backend.set_color(bulb_id, hue, saturation, baseline_bri, transition=fade_ms)
            else:
                # Delayed zones: use thread to wait then pulse
                import threading
                def delayed_pulse(bulb, h, s, delay):
                    time.sleep(delay / 1000.0)
                    backend.set_color(bulb, h, s, pulse_max, transition=0)
                    backend.set_color(bulb, h, s, baseline_bri, transition=fade_ms)

                thread = threading.Thread(
                    target=delayed_pulse,
                    args=(bulb_id, hue, saturation, delay_ms),
                    daemon=True
                )
                thread.start()

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
        """Pulse with intensity-modulated saturation and smooth fade."""
        if bpm <= 0:
            return

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
        if not bulb_id:
            return

        # Fast attack smooth fade
        baseline_bri = backend.config['effects'].get('baseline_brightness', 40)
        pulse_max = backend.config['effects'].get('pulse_max', 70)

        ibi_ms = 60000.0 / bpm
        fade_beats = math.ceil(2000.0 / ibi_ms)
        fade_ms = int(fade_beats * ibi_ms)

        # Instant attack, smooth fade
        backend.set_color(bulb_id, hue, saturation, pulse_max, transition=0)
        backend.set_color(bulb_id, hue, saturation, baseline_bri, transition=fade_ms)

        zone_name = backend.config['zones'][ppg_id].get('name', f'Zone {ppg_id}')
        logger.info(f"PULSE: {zone_name} (PPG {ppg_id}), BPM: {bpm:.1f}, "
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


class FastAttackProgram(LightingProgram):
    """Instant attack to peak, BPM-adaptive smooth fade to baseline.

    On each beat: snap instantly to peak brightness, then smoothly fade back
    to baseline over N beats where N is the smallest integer such that
    N * IBI >= 2000ms (Kasa hardware transition minimum).

    The fade duration automatically adapts to heart rate, creating longer
    decays at slower heart rates and shorter decays at faster rates, while
    respecting the 2s minimum for smooth hardware transitions.

    Configuration:
        Uses effects.baseline_brightness for resting brightness
        Uses effects.pulse_max for peak brightness
        Uses zones[N].hue for each zone's fixed color
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize fast attack program (stateless)."""
        backend.set_all_baseline()
        return {}

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Execute instant attack + smooth fade on beat."""
        # Validate BPM to prevent division by zero
        if bpm <= 0:
            logger.warning(f"Invalid BPM {bpm} for zone {ppg_id}, ignoring beat")
            return

        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if not bulb_id:
            logger.warning(f"No bulb configured for zone {ppg_id}")
            return

        # Get colors from config
        zone_cfg = backend.config['zones'][ppg_id]
        hue = zone_cfg['hue']
        saturation = backend.config['effects'].get('baseline_saturation', 75)
        baseline_bri = backend.config['effects'].get('baseline_brightness', 40)
        pulse_max = backend.config['effects'].get('pulse_max', 70)

        # Calculate fade duration (smallest multiple of IBI >= 2000ms)
        ibi_ms = 60000.0 / bpm
        fade_beats = math.ceil(2000.0 / ibi_ms)
        fade_ms = int(fade_beats * ibi_ms)

        # Call 1: Instant attack to peak (transition=0)
        backend.set_color(bulb_id, hue, saturation, pulse_max, transition=0)

        # Call 2: Smooth fade to baseline (hardware handles transition)
        backend.set_color(bulb_id, hue, saturation, baseline_bri, transition=fade_ms)

        zone_name = zone_cfg.get('name', f'Zone {ppg_id}')
        logger.info(f"FAST_ATTACK: {zone_name} (PPG {ppg_id}), BPM={bpm:.1f}, "
                    f"fade={fade_beats} beats ({fade_ms}ms)")

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Reset bulbs to baseline."""
        backend.set_all_baseline()


class SlowPulseProgram(LightingProgram):
    """Symmetric fade-in/out with peaks synchronized to beats.

    State machine per zone:
    - at_baseline: Waiting for beat to trigger fade-in
    - fade_in_active: Fading to peak, ignoring new beats
    - at_peak_waiting: At peak brightness, waiting for beat to trigger fade-out
    - fade_out_active: Fading to baseline, ignoring new beats

    Fade duration calculated per beat: N beats where N * IBI >= 2000ms.
    Beats arriving during active fades are ignored (phase protection).
    When fade completes, zone freezes at peak/baseline until next beat.

    Configuration:
        Uses effects.baseline_brightness for resting brightness
        Uses effects.pulse_max for peak brightness
        Uses zones[N].hue for each zone's fixed color
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize slow pulse with per-zone state machines."""
        backend.set_all_baseline()

        # Per-zone state tracking
        zone_states = {}
        for zone in range(4):
            zone_states[zone] = {
                'phase': 'at_baseline',  # at_baseline | fade_in_active | at_peak_waiting | fade_out_active
                'transition_start_ms': 0.0,
                'fade_duration_ms': 2000,
            }
        return {'zones': zone_states}

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Handle beat: start fade-in from baseline or fade-out from peak."""
        # Validate BPM to prevent division by zero
        if bpm <= 0:
            logger.warning(f"Invalid BPM {bpm} for zone {ppg_id}, ignoring beat")
            return

        zone_state = state['zones'][ppg_id]
        phase = zone_state['phase']

        # Only respond to beats in stable states (not during active transitions)
        if phase not in ['at_baseline', 'at_peak_waiting']:
            logger.debug(f"SLOW_PULSE Zone {ppg_id}: Ignoring beat during {phase}")
            return

        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if not bulb_id:
            logger.warning(f"No bulb configured for zone {ppg_id}")
            return

        # Get config values
        zone_cfg = backend.config['zones'][ppg_id]
        hue = zone_cfg['hue']
        saturation = backend.config['effects'].get('baseline_saturation', 75)
        baseline_bri = backend.config['effects'].get('baseline_brightness', 40)
        pulse_max = backend.config['effects'].get('pulse_max', 70)

        # Calculate fade duration (smallest multiple of IBI >= 2000ms)
        ibi_ms = 60000.0 / bpm
        fade_beats = math.ceil(2000.0 / ibi_ms)
        fade_ms = int(fade_beats * ibi_ms)
        zone_state['fade_duration_ms'] = fade_ms

        zone_name = zone_cfg.get('name', f'Zone {ppg_id}')

        if phase == 'at_baseline':
            # Start fade-in to peak
            backend.set_color(bulb_id, hue, saturation, pulse_max, transition=fade_ms)
            zone_state['phase'] = 'fade_in_active'
            zone_state['transition_start_ms'] = timestamp_ms
            logger.info(f"SLOW_PULSE {zone_name}: Fade-in start "
                        f"({fade_beats} beats, {fade_ms}ms) @ BPM={bpm:.1f}")

        elif phase == 'at_peak_waiting':
            # Start fade-out to baseline
            backend.set_color(bulb_id, hue, saturation, baseline_bri, transition=fade_ms)
            zone_state['phase'] = 'fade_out_active'
            zone_state['transition_start_ms'] = timestamp_ms
            logger.info(f"SLOW_PULSE {zone_name}: Fade-out start "
                        f"({fade_beats} beats, {fade_ms}ms) @ BPM={bpm:.1f}")

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Check for transition completion and advance state machine."""
        current_time_ms = time.time() * 1000

        for zone in range(4):
            zone_state = state['zones'][zone]
            phase = zone_state['phase']

            if phase in ['fade_in_active', 'fade_out_active']:
                elapsed_ms = current_time_ms - zone_state['transition_start_ms']

                if elapsed_ms >= zone_state['fade_duration_ms']:
                    # Transition complete
                    if phase == 'fade_in_active':
                        zone_state['phase'] = 'at_peak_waiting'
                        logger.debug(f"SLOW_PULSE Zone {zone}: Reached peak, waiting for beat")
                    else:  # fade_out_active
                        zone_state['phase'] = 'at_baseline'
                        logger.debug(f"SLOW_PULSE Zone {zone}: Back at baseline, waiting for beat")

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Reset bulbs to baseline."""
        backend.set_all_baseline()


class IntensitySlowPulseProgram(LightingProgram):
    """Slow symmetric pulse with intensity-modulated saturation and BPM-reactive hue.

    Combines SlowPulseProgram's smooth fade-in/out state machine with
    IntensityReactiveProgram's intensity and BPM mapping. Hue changes based
    on heart rate (blue=calm, red=active), saturation based on signal quality.

    State machine per zone (same as SlowPulseProgram):
    - at_baseline → fade_in_active → at_peak_waiting → fade_out_active → at_baseline

    Configuration:
        min_saturation: Minimum saturation for low intensity (default: 50)
        max_saturation: Maximum saturation for high intensity (default: 100)
    """

    def on_init(self, config: dict, backend: 'KasaBackend') -> dict:
        """Initialize slow pulse with intensity tracking."""
        prog_config = config.get('program', {}).get('config', {})
        backend.set_all_baseline()

        # Per-zone state tracking
        zone_states = {}
        for zone in range(4):
            zone_states[zone] = {
                'phase': 'at_baseline',
                'transition_start_ms': 0.0,
                'fade_duration_ms': 2000,
                'hue': 200,  # Default calm blue
                'saturation': 75,  # Default saturation
            }

        return {
            'zones': zone_states,
            'min_saturation': prog_config.get('min_saturation', 50),
            'max_saturation': prog_config.get('max_saturation', 100),
        }

    def on_beat(self, state: dict, ppg_id: int, timestamp_ms: int, bpm: float,
                intensity: float, backend: 'KasaBackend') -> None:
        """Handle beat: start fade-in or fade-out with BPM/intensity reactive colors."""
        if bpm <= 0:
            return

        zone_state = state['zones'][ppg_id]
        phase = zone_state['phase']

        # Only respond to beats in stable states
        if phase not in ['at_baseline', 'at_peak_waiting']:
            return

        bulb_id = backend.get_bulb_for_zone(ppg_id)
        if not bulb_id:
            return

        # Calculate reactive hue from BPM (40 BPM=blue/240°, 120 BPM=red/0°)
        bpm_clamped = min(max(bpm, 40), 120)
        hue = int((120 - bpm_clamped) * 3)
        zone_state['hue'] = hue

        # Calculate saturation from intensity
        saturation_range = state['max_saturation'] - state['min_saturation']
        saturation = int(state['min_saturation'] + intensity * saturation_range)
        zone_state['saturation'] = saturation

        # Get brightness values
        baseline_bri = backend.config['effects'].get('baseline_brightness', 40)
        pulse_max = backend.config['effects'].get('pulse_max', 70)

        # Calculate fade duration (smallest multiple of IBI >= 2000ms)
        ibi_ms = 60000.0 / bpm
        fade_beats = math.ceil(2000.0 / ibi_ms)
        fade_ms = int(fade_beats * ibi_ms)
        zone_state['fade_duration_ms'] = fade_ms

        if phase == 'at_baseline':
            # Start fade-in to peak
            backend.set_color(bulb_id, hue, saturation, pulse_max, transition=fade_ms)
            zone_state['phase'] = 'fade_in_active'
            zone_state['transition_start_ms'] = timestamp_ms
            logger.info(f"INTENSITY_SLOW_PULSE Zone {ppg_id}: Fade-in, BPM={bpm:.1f}, "
                        f"Intensity={intensity:.2f}, Hue={hue}°, Sat={saturation}%")

        elif phase == 'at_peak_waiting':
            # Start fade-out to baseline
            backend.set_color(bulb_id, hue, saturation, baseline_bri, transition=fade_ms)
            zone_state['phase'] = 'fade_out_active'
            zone_state['transition_start_ms'] = timestamp_ms
            logger.info(f"INTENSITY_SLOW_PULSE Zone {ppg_id}: Fade-out, BPM={bpm:.1f}")

    def on_tick(self, state: dict, dt: float, backend: 'KasaBackend') -> None:
        """Check for transition completion and advance state machine."""
        current_time_ms = time.time() * 1000

        for zone in range(4):
            zone_state = state['zones'][zone]
            phase = zone_state['phase']

            if phase in ['fade_in_active', 'fade_out_active']:
                elapsed_ms = current_time_ms - zone_state['transition_start_ms']

                if elapsed_ms >= zone_state['fade_duration_ms']:
                    # Transition complete
                    if phase == 'fade_in_active':
                        zone_state['phase'] = 'at_peak_waiting'
                    else:  # fade_out_active
                        zone_state['phase'] = 'at_baseline'

    def on_cleanup(self, state: dict, backend: 'KasaBackend') -> None:
        """Reset bulbs to baseline."""
        backend.set_all_baseline()


# ============================================================================
# PROGRAM REGISTRY
# ============================================================================

# Program registry for engine to discover programs
# Add new programs here to make them available via /program OSC command
PROGRAMS: Dict[str, type] = {
    'rotating_gradient': RotatingGradientProgram,
    'breathing_sync': BreathingSyncProgram,
    'convergence': ConvergenceProgram,
    'wave_chase': WaveChaseProgram,
    'intensity_reactive': IntensityReactiveProgram,
    'fast_attack': FastAttackProgram,
    'slow_pulse': SlowPulseProgram,
    'intensity_slow_pulse': IntensitySlowPulseProgram,
}
