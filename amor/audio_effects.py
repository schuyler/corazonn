#!/usr/bin/env python3
"""
Audio Effects Processing - Biometric-responsive real-time effects.

Provides Effect base class and concrete implementations (Reverb, Phaser) for
applying audio effects to mono samples with dynamic parameter mapping from
biometric data (BPM, intensity).

Architecture follows the LightingProgram callback pattern:
- Effect base class with on_init/process/on_cleanup lifecycle
- State dict pattern for effect-specific state
- Registry pattern for effect discovery
- Per-PPG effect chains managed by EffectsProcessor

Example YAML configuration:

    audio_effects:
      enable: true
      ppg_effects:
        0:  # PPG 0 effect chain
          - type: reverb
            room_size:
              bpm_min: 40
              bpm_max: 120
              range: [0.3, 0.8]
            damping: 0.5
        1:  # PPG 1 effect chain
          - type: phaser
            rate:
              base: 0.5
              intensity_scale: 2.0
            depth: 1.0

Usage:

    from amor.audio_effects import EffectsProcessor

    # Initialize from config
    processor = EffectsProcessor(config, sample_rate=44100)

    # Process mono sample through PPG's effect chain
    processed = processor.process(
        mono_sample,
        ppg_id=0,
        bpm=75.0,
        intensity=0.8
    )
"""

from typing import Dict, List, Any, Optional, Set
import numpy as np


class Effect:
    """Base class for audio effects applied per-PPG.

    Effects process mono audio samples before panning, with parameters
    dynamically controlled by biometric data (BPM, intensity).

    Lifecycle:
        on_init: Initialize effect-specific state (called once at startup)
        process: Apply effect to mono audio sample (called per beat)
        on_cleanup: Release resources (called at shutdown)

    Subclasses should implement these methods and use the state dict for
    maintaining effect-specific state (e.g., plugin instances, config).
    """

    def on_init(self, config: dict, sample_rate: float) -> dict:
        """Initialize effect state.

        Called once when effect is loaded. Create pedalboard plugin instances,
        parse configuration, and return initial state dict.

        Args:
            config: Effect configuration from YAML
            sample_rate: Audio sample rate (44100 or 48000 Hz)

        Returns:
            dict: Initial state for this effect instance
        """
        return {}

    def process(self, state: dict, mono_sample: np.ndarray,
                ppg_id: int, bpm: float, intensity: float) -> np.ndarray:
        """Process mono audio sample through effect.

        Called for each beat. Update effect parameters based on biometric data,
        then process audio. Modify state dict in-place if needed.

        Args:
            state: Mutable state dict (modify in-place)
            mono_sample: 1D float32 numpy array (mono audio)
            ppg_id: PPG sensor ID (0-3)
            bpm: Current heart rate (beats per minute)
            intensity: Signal strength (0.0-1.0)

        Returns:
            Processed mono sample (same shape as input)
        """
        return mono_sample

    def on_cleanup(self, state: dict) -> None:
        """Cleanup resources when effect is removed.

        Called at shutdown. Release plugin instances, close files, etc.

        Args:
            state: State dict from on_init
        """
        pass

    @staticmethod
    def map_linear(value: float, in_min: float, in_max: float,
                   out_min: float, out_max: float) -> float:
        """Linear interpolation from input range to output range.

        Maps value in [in_min, in_max] to [out_min, out_max] with clamping.

        Args:
            value: Input value
            in_min: Input range minimum
            in_max: Input range maximum
            out_min: Output range minimum
            out_max: Output range maximum

        Returns:
            Mapped value clamped to output range
        """
        value_norm = (value - in_min) / (in_max - in_min)
        value_clamped = max(0.0, min(1.0, value_norm))
        return out_min + value_clamped * (out_max - out_min)


class ReverbEffect(Effect):
    """Reverb effect with biometric parameter mapping.

    Applies reverb (room simulation) with room size dynamically controlled
    by heart rate. Higher BPM creates larger, more spacious reverb.

    Configuration (YAML):
        type: reverb
        room_size:
          bpm_min: 40        # BPM for minimum room size
          bpm_max: 120       # BPM for maximum room size
          range: [0.3, 0.8]  # Room size range (0.0-1.0)
        damping: 0.5         # Fixed damping factor (0.0-1.0)
        wet_level: 0.33      # Wet signal level (0.0-1.0)
        dry_level: 0.67      # Dry signal level (0.0-1.0)

    BPM mapping: room_size = linear_map(bpm, bpm_min, bpm_max, range[0], range[1])
    """

    def on_init(self, config: dict, sample_rate: float) -> dict:
        """Initialize reverb plugin."""
        try:
            from pedalboard import Reverb

            # Extract config with defaults
            room_cfg = config.get('room_size', {})

            # If room_size is a simple number (no mapping), use as base value
            if isinstance(room_cfg, (int, float)):
                room_size_base = float(room_cfg)
                room_cfg = {'base': room_size_base}
            else:
                # Get base value or calculate from range midpoint
                if 'base' in room_cfg:
                    room_size_base = room_cfg['base']
                elif 'range' in room_cfg:
                    room_size_base = (room_cfg['range'][0] + room_cfg['range'][1]) / 2
                else:
                    room_size_base = 0.5

            damping = config.get('damping', 0.5)
            wet_level = config.get('wet_level', 0.33)
            dry_level = config.get('dry_level', 0.67)

            # Create pedalboard effect
            reverb = Reverb(
                room_size=room_size_base,
                damping=damping,
                wet_level=wet_level,
                dry_level=dry_level
            )

            return {
                'reverb': reverb,
                'room_size_config': room_cfg,
                'sample_rate': sample_rate,
            }
        except ImportError:
            print("WARNING: pedalboard not available, reverb disabled")
            return {'reverb': None}

    def process(self, state: dict, mono_sample: np.ndarray,
                ppg_id: int, bpm: float, intensity: float) -> np.ndarray:
        """Apply reverb with BPM-controlled room size."""
        reverb = state.get('reverb')
        if reverb is None:
            return mono_sample  # Graceful degradation

        # Map BPM to room size if mapping configured
        room_cfg = state['room_size_config']
        if 'bpm_min' in room_cfg and 'bpm_max' in room_cfg and 'range' in room_cfg:
            # Dynamic BPM mapping
            room_size = self.map_linear(
                bpm,
                room_cfg['bpm_min'],
                room_cfg['bpm_max'],
                room_cfg['range'][0],
                room_cfg['range'][1]
            )
            reverb.room_size = room_size
        # else: Use base value set in on_init

        # Process audio
        # Pedalboard expects 2D array (samples, channels)
        stereo_in = np.column_stack([mono_sample, mono_sample])
        stereo_out = reverb(stereo_in, sample_rate=state['sample_rate'])

        # Extract mono (take left channel)
        return stereo_out[:, 0]


class PhaserEffect(Effect):
    """Phaser effect with intensity-controlled rate.

    Applies phaser (sweeping notch filter) with LFO rate dynamically controlled
    by signal intensity. Higher intensity creates faster phasing.

    Configuration (YAML):
        type: phaser
        rate:
          base: 0.5          # Base LFO rate (Hz)
          intensity_scale: 2.0  # Multiplier for intensity
        depth: 1.0             # Sweep depth (0.0-1.0)
        centre_frequency: 1300 # Center frequency (Hz)
        feedback: 0.0          # Feedback amount (0.0-1.0)
        mix: 0.5               # Dry/wet mix (0.0-1.0)

    Rate mapping: rate_hz = base + intensity * intensity_scale
    """

    def on_init(self, config: dict, sample_rate: float) -> dict:
        """Initialize phaser plugin."""
        try:
            from pedalboard import Phaser

            rate_cfg = config.get('rate', {})

            # If rate is a simple number, use as base value
            if isinstance(rate_cfg, (int, float)):
                base_rate = float(rate_cfg)
                rate_cfg = {'base': base_rate, 'intensity_scale': 0.0}
            else:
                base_rate = rate_cfg.get('base', 0.5)

            depth = config.get('depth', 1.0)
            centre_frequency = config.get('centre_frequency', 1300.0)
            feedback = config.get('feedback', 0.0)
            mix = config.get('mix', 0.5)

            phaser = Phaser(
                rate_hz=base_rate,
                depth=depth,
                centre_frequency=centre_frequency,
                feedback=feedback,
                mix=mix
            )

            return {
                'phaser': phaser,
                'rate_config': rate_cfg,
                'sample_rate': sample_rate,
            }
        except ImportError:
            print("WARNING: pedalboard not available, phaser disabled")
            return {'phaser': None}

    def process(self, state: dict, mono_sample: np.ndarray,
                ppg_id: int, bpm: float, intensity: float) -> np.ndarray:
        """Apply phaser with intensity-controlled rate."""
        phaser = state.get('phaser')
        if phaser is None:
            return mono_sample

        # Map intensity to rate if configured
        rate_cfg = state['rate_config']
        base_rate = rate_cfg.get('base', 0.5)
        intensity_scale = rate_cfg.get('intensity_scale', 0.0)

        rate_hz = base_rate + intensity * intensity_scale
        phaser.rate_hz = max(0.1, rate_hz)  # Clamp to reasonable minimum

        # Process audio
        stereo_in = np.column_stack([mono_sample, mono_sample])
        stereo_out = phaser(stereo_in, sample_rate=state['sample_rate'])

        return stereo_out[:, 0]


class DelayEffect(Effect):
    """Delay effect with BPM-synced timing.

    Applies echo/delay with delay time synchronized to heartbeat rhythm.
    Creates rhythmic echoes that pulse with the heart.

    Configuration (YAML):
        type: delay
        delay_seconds:
          bpm_sync: true         # Sync to BPM (60/bpm = seconds per beat)
          subdivisions: 1.0      # 1.0 = quarter note, 0.5 = eighth, 2.0 = half
        feedback: 0.4            # Echo feedback (0.0-1.0)
        mix: 0.3                 # Dry/wet mix (0.0-1.0)

    BPM mapping: delay_seconds = (60 / bpm) * subdivisions
    """

    def on_init(self, config: dict, sample_rate: float) -> dict:
        """Initialize delay plugin."""
        try:
            from pedalboard import Delay

            delay_cfg = config.get('delay_seconds', {})

            # If delay_seconds is a simple number, use as fixed delay
            if isinstance(delay_cfg, (int, float)):
                delay_seconds = float(delay_cfg)
                delay_cfg = {'bpm_sync': False, 'subdivisions': 1.0}
            else:
                # Calculate initial delay (will update per beat if bpm_sync)
                if delay_cfg.get('bpm_sync', False):
                    # Use 60 BPM as default for initialization
                    delay_seconds = (60.0 / 60.0) * delay_cfg.get('subdivisions', 1.0)
                else:
                    delay_seconds = delay_cfg.get('base', 0.5)

            feedback = config.get('feedback', 0.4)
            mix = config.get('mix', 0.3)

            delay = Delay(
                delay_seconds=delay_seconds,
                feedback=feedback,
                mix=mix
            )

            return {
                'delay': delay,
                'delay_config': delay_cfg,
                'feedback': feedback,
                'mix': mix,
                'sample_rate': sample_rate,
            }
        except ImportError:
            print("WARNING: pedalboard not available, delay disabled")
            return {'delay': None}

    def process(self, state: dict, mono_sample: np.ndarray,
                ppg_id: int, bpm: float, intensity: float) -> np.ndarray:
        """Apply delay with BPM-synced timing."""
        delay = state.get('delay')
        if delay is None:
            return mono_sample

        # Calculate BPM-synced delay time if configured
        delay_cfg = state['delay_config']
        if delay_cfg.get('bpm_sync', False):
            subdivisions = delay_cfg.get('subdivisions', 1.0)
            # delay_seconds = (60 / bpm) * subdivisions
            # Clamp BPM to reasonable range
            bpm_clamped = max(40.0, min(180.0, bpm))
            delay_seconds = (60.0 / bpm_clamped) * subdivisions

            # Clamp delay to reasonable range (10ms to 5 seconds)
            delay_seconds = max(0.01, min(5.0, delay_seconds))

            # Update delay time
            delay.delay_seconds = delay_seconds

        # Process audio
        stereo_in = np.column_stack([mono_sample, mono_sample])
        stereo_out = delay(stereo_in, sample_rate=state['sample_rate'])

        return stereo_out[:, 0]


class ChorusEffect(Effect):
    """Chorus effect with heart rate sync.

    Applies chorus (subtle pitch/time modulation) with rate synchronized
    to heartbeat rhythm. Creates gentle shimmer that breathes with the heart.

    Configuration (YAML):
        type: chorus
        rate_hz:
          bpm_sync: true         # Sync to BPM
          scale: 0.02            # Very slow: (bpm/60) * scale
        depth: 0.5               # Modulation depth (0.0-1.0)
        centre_delay_ms: 7.0     # Center delay time (ms)
        feedback: 0.0            # Feedback amount (0.0-1.0)
        mix: 0.5                 # Dry/wet mix (0.0-1.0)

    BPM mapping: rate_hz = (bpm / 60) * scale
    """

    def on_init(self, config: dict, sample_rate: float) -> dict:
        """Initialize chorus plugin."""
        try:
            from pedalboard import Chorus

            rate_cfg = config.get('rate_hz', {})

            # If rate_hz is a simple number, use as fixed rate
            if isinstance(rate_cfg, (int, float)):
                rate_hz = float(rate_cfg)
                rate_cfg = {'bpm_sync': False, 'scale': 0.02}
            else:
                # Calculate initial rate (will update per beat if bpm_sync)
                if rate_cfg.get('bpm_sync', False):
                    # Use 60 BPM as default for initialization
                    rate_hz = (60.0 / 60.0) * rate_cfg.get('scale', 0.02)
                else:
                    rate_hz = rate_cfg.get('base', 1.0)

            depth = config.get('depth', 0.5)
            centre_delay_ms = config.get('centre_delay_ms', 7.0)
            feedback = config.get('feedback', 0.0)
            mix = config.get('mix', 0.5)

            chorus = Chorus(
                rate_hz=rate_hz,
                depth=depth,
                centre_delay_ms=centre_delay_ms,
                feedback=feedback,
                mix=mix
            )

            return {
                'chorus': chorus,
                'rate_config': rate_cfg,
                'sample_rate': sample_rate,
            }
        except ImportError:
            print("WARNING: pedalboard not available, chorus disabled")
            return {'chorus': None}

    def process(self, state: dict, mono_sample: np.ndarray,
                ppg_id: int, bpm: float, intensity: float) -> np.ndarray:
        """Apply chorus with BPM-synced rate."""
        chorus = state.get('chorus')
        if chorus is None:
            return mono_sample

        # Calculate BPM-synced rate if configured
        rate_cfg = state['rate_config']
        if rate_cfg.get('bpm_sync', False):
            scale = rate_cfg.get('scale', 0.02)
            # rate_hz = (bpm / 60) * scale
            # Clamp BPM to reasonable range
            bpm_clamped = max(40.0, min(180.0, bpm))
            rate_hz = (bpm_clamped / 60.0) * scale

            # Clamp rate to reasonable range (0.01 to 10 Hz)
            rate_hz = max(0.01, min(10.0, rate_hz))

            # Update rate
            chorus.rate_hz = rate_hz

        # Process audio
        stereo_in = np.column_stack([mono_sample, mono_sample])
        stereo_out = chorus(stereo_in, sample_rate=state['sample_rate'])

        return stereo_out[:, 0]


class LowPassFilterEffect(Effect):
    """Low-pass filter with inverse BPM mapping.

    Applies low-pass filter that darkens/warms the sound as heart rate increases.
    Creates calming response - the installation "soothes" agitation.

    Configuration (YAML):
        type: lowpass
        cutoff_hz:
          bpm_min: 60            # Resting heart rate
          bpm_max: 120           # Excited heart rate
          range: [8000, 3000]    # Bright → warm (inverse mapping)

    Inverse BPM mapping: High BPM → lower cutoff → darker/warmer sound

    Note: Uses simple low-pass filter without resonance control (Q factor).
    For meditative applications, gentle filtering is preferred over resonant peaks.
    """

    def on_init(self, config: dict, sample_rate: float) -> dict:
        """Initialize lowpass filter plugin."""
        try:
            from pedalboard import LowpassFilter

            cutoff_cfg = config.get('cutoff_hz', {})

            # If cutoff_hz is a simple number, use as fixed cutoff
            if isinstance(cutoff_cfg, (int, float)):
                cutoff_hz = float(cutoff_cfg)
                cutoff_cfg = {'bpm_min': 60, 'bpm_max': 120, 'range': [cutoff_hz, cutoff_hz]}
            else:
                # Use midpoint of range for initialization
                cutoff_range = cutoff_cfg.get('range', [8000, 3000])
                cutoff_hz = (cutoff_range[0] + cutoff_range[1]) / 2

            lowpass = LowpassFilter(cutoff_frequency_hz=cutoff_hz)

            return {
                'lowpass': lowpass,
                'cutoff_config': cutoff_cfg,
                'sample_rate': sample_rate,
            }
        except ImportError:
            print("WARNING: pedalboard not available, lowpass disabled")
            return {'lowpass': None}

    def process(self, state: dict, mono_sample: np.ndarray,
                ppg_id: int, bpm: float, intensity: float) -> np.ndarray:
        """Apply lowpass filter with inverse BPM mapping."""
        lowpass = state.get('lowpass')
        if lowpass is None:
            return mono_sample

        # Map BPM to cutoff frequency if configured
        cutoff_cfg = state['cutoff_config']
        if 'bpm_min' in cutoff_cfg and 'bpm_max' in cutoff_cfg and 'range' in cutoff_cfg:
            # Inverse mapping: high BPM → low cutoff (darker/warmer)
            cutoff_hz = self.map_linear(
                bpm,
                cutoff_cfg['bpm_min'],
                cutoff_cfg['bpm_max'],
                cutoff_cfg['range'][0],  # High cutoff at low BPM
                cutoff_cfg['range'][1]   # Low cutoff at high BPM
            )

            # Clamp to reasonable range
            cutoff_hz = max(100.0, min(20000.0, cutoff_hz))

            # Update cutoff
            lowpass.cutoff_frequency_hz = cutoff_hz

        # Process audio
        stereo_in = np.column_stack([mono_sample, mono_sample])
        stereo_out = lowpass(stereo_in, sample_rate=state['sample_rate'])

        return stereo_out[:, 0]


class EffectsProcessor:
    """Manages per-PPG effect chains with biometric parameter mapping.

    Processes mono audio samples through configurable effect chains before
    panning. Each PPG (0-3) has independent effect chain.

    Attributes:
        ppg_chains: Dict[int, List[Effect]] - Effect instances per PPG
        ppg_states: Dict[int, List[dict]] - State dicts per effect per PPG
        sample_rate: Audio sample rate
    """

    def __init__(self, config: dict, sample_rate: float):
        """Initialize effects processor from configuration.

        Args:
            config: Effects configuration from YAML (audio_effects section)
            sample_rate: Audio sample rate (44100 or 48000 Hz)
        """
        self.sample_rate = sample_rate
        self.ppg_chains: Dict[int, List[Effect]] = {}
        self.ppg_states: Dict[int, List[dict]] = {}

        # Track active effect names per PPG for dynamic toggling
        self.active_effects: Dict[int, Set[str]] = {i: set() for i in range(4)}

        # Store effect configs (for dynamic rebuild)
        self.effect_configs: Dict[str, dict] = {}

        # Load per-PPG effect chains from config
        ppg_effects = config.get('ppg_effects', {})
        for ppg_id in range(4):
            chain_config = ppg_effects.get(ppg_id, [])

            # Track active effects from config
            for effect_cfg in chain_config:
                effect_type = effect_cfg.get('type')
                if effect_type in EFFECTS:
                    self.active_effects[ppg_id].add(effect_type)
                    # Store default config for this effect type
                    if effect_type not in self.effect_configs:
                        self.effect_configs[effect_type] = effect_cfg

            self._load_chain(ppg_id, chain_config)

    def _load_chain(self, ppg_id: int, chain_config: list) -> None:
        """Load effect chain for one PPG.

        Args:
            ppg_id: PPG sensor ID (0-3)
            chain_config: List of effect configs from YAML
        """
        effects = []
        states = []

        for effect_cfg in chain_config:
            effect_type = effect_cfg.get('type')
            if effect_type not in EFFECTS:
                print(f"WARNING: Unknown effect type '{effect_type}' for PPG {ppg_id}, skipping")
                continue

            # Instantiate effect
            effect_class = EFFECTS[effect_type]
            effect = effect_class()

            # Initialize state
            try:
                state = effect.on_init(effect_cfg, self.sample_rate)
                effects.append(effect)
                states.append(state)
            except Exception as e:
                print(f"WARNING: Failed to initialize {effect_type} for PPG {ppg_id}: {e}")

        self.ppg_chains[ppg_id] = effects
        self.ppg_states[ppg_id] = states

        if effects:
            effect_names = [type(e).__name__ for e in effects]
            print(f"  PPG {ppg_id}: {len(effects)} effect(s) loaded - {', '.join(effect_names)}")

    def process(self, mono_sample: np.ndarray, ppg_id: int,
                bpm: float, intensity: float) -> np.ndarray:
        """Process mono sample through PPG's effect chain.

        Args:
            mono_sample: 1D float32 numpy array (mono audio)
            ppg_id: PPG sensor ID (0-3)
            bpm: Current heart rate (beats per minute)
            intensity: Signal strength (0.0-1.0)

        Returns:
            Processed mono sample (same shape as input)
        """
        effects = self.ppg_chains.get(ppg_id, [])
        states = self.ppg_states.get(ppg_id, [])

        # Process through chain (serial: output of effect N feeds input of effect N+1)
        output = mono_sample
        for effect, state in zip(effects, states):
            try:
                output = effect.process(state, output, ppg_id, bpm, intensity)
            except Exception as e:
                print(f"WARNING: Effect processing failed for PPG {ppg_id}: {e}")
                # Continue with unprocessed audio on error

        return output

    def toggle_effect(self, ppg_id: int, effect_name: str) -> None:
        """Toggle an effect on/off for a PPG, rebuilding the effect chain.

        Args:
            ppg_id: PPG sensor ID (0-3)
            effect_name: Effect name ('reverb', 'phaser', 'delay', 'chorus', 'lowpass')

        Raises:
            ValueError: If ppg_id invalid or effect_name unknown
        """
        if ppg_id < 0 or ppg_id > 3:
            raise ValueError(f"PPG ID must be 0-3, got {ppg_id}")

        if effect_name not in EFFECTS:
            raise ValueError(f"Unknown effect '{effect_name}'. Available: {list(EFFECTS.keys())}")

        # Toggle effect in active set
        if effect_name in self.active_effects[ppg_id]:
            self.active_effects[ppg_id].remove(effect_name)
        else:
            self.active_effects[ppg_id].add(effect_name)

        # Rebuild chain
        self._rebuild_chain(ppg_id)

    def clear_effects(self, ppg_id: int) -> None:
        """Clear all effects for a PPG, rebuilding with empty chain.

        Args:
            ppg_id: PPG sensor ID (0-3)

        Raises:
            ValueError: If ppg_id invalid
        """
        if ppg_id < 0 or ppg_id > 3:
            raise ValueError(f"PPG ID must be 0-3, got {ppg_id}")

        # Clear active effects
        self.active_effects[ppg_id].clear()

        # Rebuild chain (will be empty)
        self._rebuild_chain(ppg_id)

    def _rebuild_chain(self, ppg_id: int) -> None:
        """Rebuild effect chain for a PPG from active_effects set.

        Cleans up old chain, then initializes new chain based on active effects.
        Effects are processed in canonical order: reverb, phaser, delay, chorus, lowpass.

        Args:
            ppg_id: PPG sensor ID (0-3)
        """
        # Cleanup old chain
        old_effects = self.ppg_chains.get(ppg_id, [])
        old_states = self.ppg_states.get(ppg_id, [])
        for effect, state in zip(old_effects, old_states):
            try:
                effect.on_cleanup(state)
            except Exception as e:
                print(f"WARNING: Cleanup failed during rebuild for PPG {ppg_id}: {e}")

        # Build new chain from active effects (in canonical order)
        # Canonical order: reverb → phaser → delay → chorus → lowpass
        canonical_order = ['reverb', 'phaser', 'delay', 'chorus', 'lowpass']
        chain_config = []

        for effect_name in canonical_order:
            if effect_name in self.active_effects[ppg_id]:
                # Use stored config if available, otherwise use minimal config
                if effect_name in self.effect_configs:
                    chain_config.append(self.effect_configs[effect_name])
                else:
                    # Minimal config with just type (use defaults)
                    chain_config.append({'type': effect_name})

        # Load new chain
        self._load_chain(ppg_id, chain_config)

        if chain_config:
            effect_names = [cfg['type'] for cfg in chain_config]
            print(f"  PPG {ppg_id}: Rebuilt chain with {len(chain_config)} effect(s): {', '.join(effect_names)}")
        else:
            print(f"  PPG {ppg_id}: Rebuilt chain (empty - no effects)")

    def cleanup(self) -> None:
        """Cleanup all effects."""
        for ppg_id in range(4):
            effects = self.ppg_chains.get(ppg_id, [])
            states = self.ppg_states.get(ppg_id, [])
            for effect, state in zip(effects, states):
                try:
                    effect.on_cleanup(state)
                except Exception as e:
                    print(f"WARNING: Cleanup failed for PPG {ppg_id}: {e}")


# Effect registry - maps effect type strings to classes
EFFECTS: Dict[str, type] = {
    'reverb': ReverbEffect,
    'phaser': PhaserEffect,
    'delay': DelayEffect,
    'chorus': ChorusEffect,
    'lowpass': LowPassFilterEffect,
}
