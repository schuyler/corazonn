#!/usr/bin/env python3
"""
Analyze fundamental frequency of audio samples.

Usage:
    python analyze_pitch.py path/to/sample.wav
    python analyze_pitch.py sounds/ppg/*.wav  # Batch analyze
"""

import sys
import librosa
import numpy as np
from pathlib import Path


def hz_to_note(hz):
    """Convert frequency in Hz to note name (e.g., 440 Hz -> A4)."""
    if hz <= 0:
        return "Unknown"

    # A4 = 440 Hz is MIDI note 69
    midi_note = 69 + 12 * np.log2(hz / 440.0)
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    note_num = int(round(midi_note))
    octave = (note_num // 12) - 1
    note_name = note_names[note_num % 12]

    cents_off = (midi_note - note_num) * 100

    return f"{note_name}{octave}", cents_off


def analyze_pitch(filepath):
    """Analyze fundamental frequency of an audio file.

    Args:
        filepath: Path to audio file (WAV, MP3, etc.)

    Returns:
        tuple: (frequency_hz, note_name, cents_off, confidence)
    """
    # Load audio
    y, sr = librosa.load(filepath, sr=None)

    # Extract pitch using YIN algorithm (good for harmonic sounds)
    # fmin: minimum frequency to detect (50 Hz = low bass)
    # fmax: maximum frequency to detect (2000 Hz = high treble)
    f0 = librosa.yin(y, fmin=50, fmax=2000, sr=sr)

    # Filter out non-voiced frames (where pitch is uncertain)
    # YIN returns very high or very low values for non-pitched sounds
    valid_f0 = f0[(f0 > 50) & (f0 < 2000)]

    if len(valid_f0) == 0:
        return None, "No pitch", 0, 0.0

    # Use median to avoid outliers
    fundamental = np.median(valid_f0)

    # Confidence = how many frames agree with median (within 5%)
    confidence = np.sum(np.abs(valid_f0 - fundamental) < (fundamental * 0.05)) / len(valid_f0)

    note_name, cents_off = hz_to_note(fundamental)

    return fundamental, note_name, cents_off, confidence


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_pitch.py <audio_file> [<audio_file> ...]")
        print("Example: python analyze_pitch.py sounds/ppg/*.wav")
        sys.exit(1)

    files = []
    for arg in sys.argv[1:]:
        # Support glob patterns
        if '*' in arg or '?' in arg:
            files.extend(Path('.').glob(arg))
        else:
            files.append(Path(arg))

    if not files:
        print("No files found")
        sys.exit(1)

    print(f"{'File':<40} {'Hz':>8} {'Note':>6} {'Cents':>6} {'Confidence':>10}")
    print("-" * 75)

    for filepath in sorted(files):
        if not filepath.exists():
            print(f"{filepath.name:<40} File not found")
            continue

        try:
            hz, note, cents, conf = analyze_pitch(filepath)

            if hz is None:
                print(f"{filepath.name:<40} {note}")
            else:
                cents_str = f"{cents:+.0f}" if abs(cents) > 1 else "±0"
                print(f"{filepath.name:<40} {hz:8.1f} {note:>6} {cents_str:>6} {conf:>9.0%}")
        except Exception as e:
            print(f"{filepath.name:<40} Error: {e}")


if __name__ == "__main__":
    main()
