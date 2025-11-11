#!/usr/bin/env python3
"""
Generate placeholder WAV samples for Audio Engine.

Creates 4 WAV files (ppg_0.wav through ppg_3.wav) in the sounds/ directory.
Format: 44.1kHz, 16-bit, mono, 500ms sine tones at different frequencies.

Usage:
    python3 audio/generate_ppg_samples.py
"""

import numpy as np
import soundfile as sf
from pathlib import Path


def generate_sine_tone(frequency, duration_sec=0.5, sample_rate=44100, amplitude=0.3):
    """
    Generate a simple sine wave tone.

    Args:
        frequency (float): Frequency in Hz
        duration_sec (float): Duration in seconds (default 0.5)
        sample_rate (int): Sample rate in Hz (default 44.1kHz)
        amplitude (float): Amplitude 0-1 (default 0.3)

    Returns:
        numpy.ndarray: Audio samples as float32 in range [-1, 1]
    """
    num_samples = int(duration_sec * sample_rate)
    t = np.arange(num_samples, dtype=np.float32) / sample_rate
    waveform = amplitude * np.sin(2 * np.pi * frequency * t)
    return waveform.astype(np.float32)


def main():
    """Generate all required PPG sample files."""
    # Create sounds directory
    sounds_dir = Path(__file__).parent / "sounds"
    sounds_dir.mkdir(parents=True, exist_ok=True)

    # Define samples: ppg_id, frequency (Hz), description
    sample_specs = [
        (0, 440, "Violin A4"),
        (1, 523, "Piano C5"),
        (2, 659, "Flute E5"),
        (3, 784, "Trumpet G5"),
    ]

    sample_rate = 44100
    duration_sec = 0.5

    for ppg_id, frequency, description in sample_specs:
        filepath = sounds_dir / f"ppg_{ppg_id}.wav"
        print(f"Generating ppg_{ppg_id}.wav: {description} ({frequency} Hz)")

        waveform = generate_sine_tone(frequency, duration_sec, sample_rate)
        sf.write(str(filepath), waveform, sample_rate, subtype="PCM_16")

        print(f"  ✓ Written: {filepath}")

    print(f"\nGenerated all samples in: {sounds_dir}")


if __name__ == "__main__":
    main()
