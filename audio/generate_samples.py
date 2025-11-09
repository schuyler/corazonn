#!/usr/bin/env python3
"""
Generate placeholder test tone samples for Pure Data audio engine.

Creates simple sine wave samples (48kHz, mono, 16-bit WAV) for:
- kick-01.wav (low frequency tone)
- snare-01.wav (mid frequency tone)
- hat-01.wav (high frequency tone)
- clap-01.wav (very high frequency tone)
"""

import wave
import struct
import math
from pathlib import Path


def generate_tone(frequency, duration_ms, sample_rate=48000, amplitude=0.8):
    """
    Generate a simple sine wave tone.

    Args:
        frequency: Frequency in Hz
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz (default 48kHz)
        amplitude: Wave amplitude (0-1)

    Returns:
        List of 16-bit sample values
    """
    samples = []
    num_samples = int((duration_ms / 1000.0) * sample_rate)

    for i in range(num_samples):
        # Generate sine wave
        t = i / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)

        # Convert to 16-bit signed integer
        sample = int(value * 32767)
        samples.append(sample)

    return samples


def write_wav_file(filepath, samples, sample_rate=48000):
    """
    Write samples to a WAV file.

    Args:
        filepath: Output file path
        samples: List of 16-bit sample values
        sample_rate: Sample rate in Hz
    """
    num_channels = 1  # Mono
    sample_width = 2  # 16-bit = 2 bytes

    with wave.open(str(filepath), 'wb') as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)

        # Convert samples to bytes
        packed_data = b''
        for sample in samples:
            # Pack as signed 16-bit little-endian
            packed_data += struct.pack('<h', sample)

        wav_file.writeframes(packed_data)


def main():
    """Generate all required sample files."""
    sample_dir = Path('/home/user/corazonn/audio/samples/percussion/starter')
    sample_dir.mkdir(parents=True, exist_ok=True)

    # Define samples: (filename, frequency_hz, duration_ms, description)
    sample_specs = [
        ('kick-01.wav', 60, 200, 'Low frequency kick drum'),
        ('snare-01.wav', 200, 150, 'Mid frequency snare'),
        ('hat-01.wav', 8000, 100, 'High frequency hi-hat'),
        ('clap-01.wav', 6000, 120, 'High frequency clap'),
    ]

    for filename, frequency, duration, description in sample_specs:
        filepath = sample_dir / filename
        print(f"Generating {filename}: {description}")

        samples = generate_tone(frequency, duration)
        write_wav_file(filepath, samples)
        print(f"  Written: {filepath} ({len(samples)} samples)")

    print(f"\nGenerated all samples in {sample_dir}")


if __name__ == '__main__':
    main()
