#!/usr/bin/env python3
"""
Process Freesound samples for AMOR:
- Convert to 48kHz mono WAV
- Normalize to -3 dB
- Fade out and trim at 2.5s if longer

Usage:
    python3 scripts/process_samples.py <input_dir> <output_dir>

Example:
    python3 scripts/process_samples.py freesound_samples/ sounds/processed/
"""

import os
import sys
import subprocess
from pathlib import Path


def get_duration(filepath):
    """Get audio file duration in seconds using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(filepath)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"WARNING: Could not get duration for {filepath}: {e}")
        return None


def process_sample(input_path, output_path, max_duration=2.5, fade_duration=0.2):
    """
    Process audio file with ffmpeg:
    - Convert to mono
    - Resample to 48kHz
    - Normalize to -3 dB
    - Fade out and trim if longer than max_duration

    Args:
        input_path: Input audio file path
        output_path: Output WAV file path
        max_duration: Maximum duration in seconds (default: 2.5)
        fade_duration: Fade duration in seconds (default: 0.2)
    """
    # Get duration
    duration = get_duration(input_path)
    if duration is None:
        print(f"SKIP: {input_path}")
        return False

    # Build ffmpeg command
    cmd = ['ffmpeg', '-i', str(input_path)]

    # Audio filters
    filters = []

    # If longer than max_duration, apply fade and trim
    if duration > max_duration:
        fade_start = max_duration - fade_duration
        filters.append(f'afade=t=out:st={fade_start}:d={fade_duration}')
        filters.append(f'atrim=0:{max_duration}')
        action = "fade+trim"
    else:
        action = "process"

    # Always: convert to mono, resample to 48kHz, normalize to -3dB
    filters.append('pan=mono|c0=c0')  # Mono (take first channel)
    filters.append('aresample=48000')  # Resample to 48kHz
    filters.append('loudnorm=I=-3:TP=-3:LRA=7')  # Normalize to -3dB

    # Combine filters
    cmd.extend(['-af', ','.join(filters)])

    # Output format
    cmd.extend([
        '-ar', '48000',  # Sample rate
        '-ac', '1',      # Mono
        '-y',            # Overwrite
        str(output_path)
    ])

    # Run ffmpeg
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"{action.upper()}: {input_path.name} ({duration:.2f}s) -> {output_path.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to process {input_path}: {e.stderr}")
        return False


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all audio files
    audio_extensions = {'.wav', '.aif', '.aiff', '.flac', '.mp3', '.ogg', '.m4a'}
    audio_files = []

    for ext in audio_extensions:
        audio_files.extend(input_dir.rglob(f'*{ext}'))

    if not audio_files:
        print(f"WARNING: No audio files found in {input_dir}")
        sys.exit(0)

    print(f"Found {len(audio_files)} audio files")
    print(f"Processing to: {output_dir}")
    print(f"Max duration: 2.5s (fade out from 2.3s)")
    print(f"Target format: 48kHz mono WAV, normalized to -3dB")
    print()

    # Process each file
    success_count = 0
    for input_path in sorted(audio_files):
        # Preserve directory structure
        rel_path = input_path.relative_to(input_dir)
        output_path = output_dir / rel_path.with_suffix('.wav')

        # Create subdirectory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if process_sample(input_path, output_path):
            success_count += 1

    print()
    print(f"COMPLETE: {success_count}/{len(audio_files)} files processed successfully")


if __name__ == '__main__':
    main()
