#!/usr/bin/env python3
"""
Prototype Heartbeat Synthesis - Generate realistic heartbeat audio from beat events

This standalone script demonstrates the heartbeat synthesis approach:
1. Generates synthetic beat events (BPM + intensity over time)
2. Synthesizes heartbeat sounds (S1 "lub" + S2 "dub") for each beat
3. Outputs continuous audio file for evaluation

Usage:
    python3 audio/prototype_heartbeat_synth.py
    python3 audio/prototype_heartbeat_synth.py --duration 30 --bpm 75
    python3 audio/prototype_heartbeat_synth.py --preset electronic
"""

import argparse
import numpy as np
import soundfile as sf
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
from scipy import signal


@dataclass
class HeartbeatPreset:
    """Parameters for heartbeat sound synthesis."""
    s1_freq: float           # S1 center frequency (Hz)
    s1_duration: float       # S1 duration (seconds)
    s2_freq: float           # S2 center frequency (Hz)
    s2_duration: float       # S2 duration (seconds)
    s2_delay_ratio: float    # S2 delay as fraction of inter-beat interval
    noise_mix: float         # 0-1: noise vs sine wave mix (0=pure sine, 1=pure noise)
    variation_ms: float      # ±timing randomization (milliseconds)
    pitch_variation: float   # ±frequency randomization (fraction, e.g., 0.05 = ±5%)


# Preset definitions
PRESETS = {
    "natural": HeartbeatPreset(
        s1_freq=75,
        s1_duration=0.12,
        s2_freq=150,
        s2_duration=0.08,
        s2_delay_ratio=0.35,
        noise_mix=0.3,
        variation_ms=10,
        pitch_variation=0.05,
    ),
    "electronic": HeartbeatPreset(
        s1_freq=60,
        s1_duration=0.08,
        s2_freq=120,
        s2_duration=0.06,
        s2_delay_ratio=0.30,
        noise_mix=0.0,  # Pure sine
        variation_ms=0,  # No variation
        pitch_variation=0.0,
    ),
    "sub-bass": HeartbeatPreset(
        s1_freq=45,
        s1_duration=0.15,
        s2_freq=90,
        s2_duration=0.10,
        s2_delay_ratio=0.40,
        noise_mix=0.1,
        variation_ms=15,
        pitch_variation=0.08,
    ),
    "percussive": HeartbeatPreset(
        s1_freq=100,
        s1_duration=0.05,
        s2_freq=200,
        s2_duration=0.04,
        s2_delay_ratio=0.25,
        noise_mix=0.6,  # More noise = more percussive
        variation_ms=5,
        pitch_variation=0.03,
    ),
}


class HeartbeatSynthesizer:
    """Generates realistic heartbeat audio from beat events."""

    def __init__(self, sample_rate: int = 48000, preset: str = "natural"):
        """
        Initialize synthesizer.

        Args:
            sample_rate: Audio sample rate (Hz)
            preset: Preset name from PRESETS dict
        """
        self.sample_rate = sample_rate
        self.preset_name = preset
        self.preset = PRESETS[preset]
        self.rng = np.random.default_rng(seed=42)  # Reproducible randomness

    def generate_heartbeat(self, bpm: float, intensity: float) -> Tuple[np.ndarray, float]:
        """
        Generate complete heartbeat (S1 + S2) for one beat event.

        Args:
            bpm: Beats per minute
            intensity: 0-1 intensity value (affects amplitude and character)

        Returns:
            (audio, duration): Audio array and total duration in seconds
        """
        # Calculate inter-beat interval
        ibi = 60.0 / bpm

        # Generate S1 ("lub")
        s1_audio = self._generate_heart_sound(
            duration=self.preset.s1_duration,
            center_freq=self.preset.s1_freq,
            intensity=intensity,
            noise_mix=self.preset.noise_mix,
            is_s1=True,
        )

        # Generate S2 ("dub") - slightly quieter, higher pitch
        s2_audio = self._generate_heart_sound(
            duration=self.preset.s2_duration,
            center_freq=self.preset.s2_freq,
            intensity=intensity * 0.7,  # S2 quieter than S1
            noise_mix=self.preset.noise_mix,
            is_s1=False,
        )

        # Calculate S2 delay with randomization
        base_delay = ibi * self.preset.s2_delay_ratio
        delay_variation = self.preset.variation_ms / 1000.0
        s2_delay = base_delay + self.rng.uniform(-delay_variation, delay_variation)
        s2_delay = max(self.preset.s1_duration + 0.01, s2_delay)  # Ensure S2 after S1

        # Create combined buffer for full heartbeat
        total_duration = max(ibi, s2_delay + self.preset.s2_duration + 0.1)
        total_samples = int(total_duration * self.sample_rate)
        combined = np.zeros(total_samples, dtype=np.float32)

        # Place S1 at start
        s1_len = len(s1_audio)
        combined[:s1_len] += s1_audio

        # Place S2 at calculated delay
        s2_start = int(s2_delay * self.sample_rate)
        s2_len = len(s2_audio)
        combined[s2_start:s2_start + s2_len] += s2_audio

        return combined, total_duration

    def _generate_heart_sound(
        self,
        duration: float,
        center_freq: float,
        intensity: float,
        noise_mix: float,
        is_s1: bool,
    ) -> np.ndarray:
        """
        Generate individual heart sound (S1 or S2).

        Args:
            duration: Sound duration (seconds)
            center_freq: Center frequency (Hz)
            intensity: Amplitude scaling (0-1)
            noise_mix: 0-1, amount of noise vs sine (0=pure sine, 1=pure noise)
            is_s1: True for S1, False for S2 (affects envelope)

        Returns:
            Audio samples as float32 array
        """
        num_samples = int(duration * self.sample_rate)

        # Apply pitch variation
        freq_variation = self.preset.pitch_variation
        freq = center_freq * (1 + self.rng.uniform(-freq_variation, freq_variation))

        # Generate noise component (bandpassed)
        if noise_mix > 0:
            noise = self.rng.standard_normal(num_samples).astype(np.float32)
            noise = self._bandpass_filter(noise, freq - 25, freq + 25)
        else:
            noise = np.zeros(num_samples, dtype=np.float32)

        # Generate sine component
        t = np.arange(num_samples, dtype=np.float32) / self.sample_rate
        sine = np.sin(2 * np.pi * freq * t).astype(np.float32)

        # Mix noise and sine
        mixed = (noise_mix * noise + (1 - noise_mix) * sine)

        # Apply envelope (exponential decay, faster for S2)
        decay_rate = 0.25 if is_s1 else 0.15
        envelope = np.exp(-np.arange(num_samples) / (num_samples * decay_rate))

        # Add sharp attack for more percussive quality
        attack_samples = int(0.005 * self.sample_rate)  # 5ms attack
        attack_env = np.ones(num_samples, dtype=np.float32)
        if attack_samples > 0:
            attack_env[:attack_samples] = np.linspace(0, 1, attack_samples)

        # Combine envelopes
        full_envelope = envelope * attack_env

        # Apply intensity and envelope
        output = mixed * full_envelope * intensity

        # Normalize to prevent clipping
        peak = np.abs(output).max()
        if peak > 0.8:
            output = output * (0.8 / peak)

        return output

    def _bandpass_filter(self, audio: np.ndarray, low_freq: float, high_freq: float) -> np.ndarray:
        """
        Apply bandpass filter to audio.

        Args:
            audio: Input audio
            low_freq: Low cutoff frequency (Hz)
            high_freq: High cutoff frequency (Hz)

        Returns:
            Filtered audio
        """
        nyquist = self.sample_rate / 2
        low = max(1, low_freq) / nyquist
        high = min(nyquist - 1, high_freq) / nyquist

        # Use butter filter (4th order)
        sos = signal.butter(4, [low, high], btype='band', output='sos')
        filtered = signal.sosfilt(sos, audio)

        return filtered.astype(np.float32)


def generate_synthetic_beats(duration_sec: float, base_bpm: float) -> List[Tuple[float, float, float]]:
    """
    Generate synthetic beat events with varying BPM and intensity.

    Args:
        duration_sec: Total duration (seconds)
        base_bpm: Base BPM (will vary ±10%)

    Returns:
        List of (timestamp, bpm, intensity) tuples
    """
    beats = []
    current_time = 0.0
    rng = np.random.default_rng(seed=123)

    while current_time < duration_sec:
        # Vary BPM ±10%
        bpm = base_bpm * (1 + rng.uniform(-0.1, 0.1))

        # Vary intensity (0.5 to 1.0)
        intensity = rng.uniform(0.5, 1.0)

        beats.append((current_time, bpm, intensity))

        # Calculate next beat time
        ibi = 60.0 / bpm
        current_time += ibi

    return beats


def synthesize_audio(beats: List[Tuple[float, float, float]], synthesizer: HeartbeatSynthesizer) -> np.ndarray:
    """
    Synthesize continuous audio from beat events.

    Args:
        beats: List of (timestamp, bpm, intensity) tuples
        synthesizer: HeartbeatSynthesizer instance

    Returns:
        Continuous audio array
    """
    if not beats:
        return np.array([], dtype=np.float32)

    # Calculate total duration (add buffer for last beat)
    last_timestamp = beats[-1][0]
    last_bpm = beats[-1][1]
    buffer_duration = (60.0 / last_bpm) * 2  # Two beats worth
    total_duration = last_timestamp + buffer_duration

    total_samples = int(total_duration * synthesizer.sample_rate)
    output = np.zeros(total_samples, dtype=np.float32)

    print(f"Synthesizing {len(beats)} heartbeats...")

    for i, (timestamp, bpm, intensity) in enumerate(beats):
        # Generate heartbeat audio
        heartbeat, _ = synthesizer.generate_heartbeat(bpm, intensity)

        # Place in output buffer
        start_sample = int(timestamp * synthesizer.sample_rate)
        end_sample = start_sample + len(heartbeat)

        if end_sample <= total_samples:
            output[start_sample:end_sample] += heartbeat
        else:
            # Truncate if exceeds buffer
            remaining = total_samples - start_sample
            output[start_sample:] += heartbeat[:remaining]

        # Progress indicator
        if (i + 1) % 10 == 0 or i == len(beats) - 1:
            print(f"  Processed {i + 1}/{len(beats)} beats")

    # Normalize to prevent clipping
    peak = np.abs(output).max()
    if peak > 0.9:
        output = output * (0.9 / peak)
        print(f"  Normalized audio (peak was {peak:.2f})")

    return output


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prototype heartbeat synthesis from synthetic beat events"
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=20.0,
        help='Duration of output audio (seconds, default: 20)'
    )
    parser.add_argument(
        '--bpm',
        type=float,
        default=70.0,
        help='Base BPM (will vary ±10%%, default: 70)'
    )
    parser.add_argument(
        '--preset',
        type=str,
        default='natural',
        choices=list(PRESETS.keys()),
        help=f'Synthesis preset (default: natural)'
    )
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=48000,
        help='Audio sample rate (default: 48000)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (default: audio/heartbeat_<preset>.wav)'
    )

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path(__file__).parent
        output_path = output_dir / f"heartbeat_{args.preset}.wav"

    print(f"Heartbeat Synthesis Prototype")
    print(f"{'=' * 60}")
    print(f"Preset: {args.preset}")
    print(f"Duration: {args.duration}s")
    print(f"Base BPM: {args.bpm} (±10% variation)")
    print(f"Sample rate: {args.sample_rate} Hz")
    print(f"Output: {output_path}")
    print()

    # Generate synthetic beats
    print("Generating synthetic beat events...")
    beats = generate_synthetic_beats(args.duration, args.bpm)
    print(f"  Generated {len(beats)} beats")
    print()

    # Create synthesizer
    synthesizer = HeartbeatSynthesizer(
        sample_rate=args.sample_rate,
        preset=args.preset
    )

    # Synthesize audio
    audio = synthesize_audio(beats, synthesizer)
    print()

    # Write output file
    print(f"Writing audio file...")
    sf.write(str(output_path), audio, args.sample_rate, subtype='PCM_16')
    print(f"  ✓ Written: {output_path}")
    print()

    # Print statistics
    duration = len(audio) / args.sample_rate
    print(f"Output Statistics:")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Samples: {len(audio)}")
    print(f"  Peak amplitude: {np.abs(audio).max():.3f}")
    print(f"  RMS level: {np.sqrt(np.mean(audio**2)):.3f}")
    print()
    print(f"Listen to the output and experiment with different presets:")
    print(f"  {', '.join(PRESETS.keys())}")


if __name__ == "__main__":
    main()
