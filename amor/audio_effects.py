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

from typing import Dict, List, Any, Optional
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

        # Load per-PPG effect chains
        ppg_effects = config.get('ppg_effects', {})
        for ppg_id in range(4):
            chain_config = ppg_effects.get(ppg_id, [])
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
}
