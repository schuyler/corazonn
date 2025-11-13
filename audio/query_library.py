#!/usr/bin/env python3
"""
Query Freesound Sample Library

Explore and filter the downloaded sample library metadata for programmatic
bank curation and sample selection.

Usage:
    # Show library statistics
    ./query_library.py stats

    # List all samples
    ./query_library.py list

    # Filter by timbral family
    ./query_library.py list --family 01_Metallic_Bells

    # Filter by duration range (in seconds)
    ./query_library.py list --min-duration 2.0 --max-duration 10.0

    # Filter by tags
    ./query_library.py list --tag resonance --tag sustained

    # Filter by pitch
    ./query_library.py list --pitch C4

    # Combine filters and export to JSON
    ./query_library.py list --family 03_Synth_Tones --min-duration 5.0 --output synth_pads.json

    # Show specific sample details
    ./query_library.py show 122650

Author: Claude Code
License: See repository license
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional


# Constants
PROJECT_ROOT = Path(__file__).parent.parent
LIBRARY_ROOT = PROJECT_ROOT / "audio" / "library"
METADATA_FILE = LIBRARY_ROOT / "metadata.json"


def load_metadata() -> Dict[str, Any]:
    """Load library metadata from JSON file."""
    if not METADATA_FILE.exists():
        print(f"✗ Metadata file not found: {METADATA_FILE}")
        print("Run download_freesound_library.py first to download samples")
        sys.exit(1)

    with open(METADATA_FILE, 'r') as f:
        return json.load(f)


def show_stats(metadata: Dict[str, Any]):
    """Display library statistics."""
    samples = metadata.get('samples', [])

    print("=" * 70)
    print("SAMPLE LIBRARY STATISTICS")
    print("=" * 70)
    print(f"Library version: {metadata.get('library_version', 'unknown')}")
    print(f"Generated: {metadata.get('generated_date', 'unknown')}")
    print(f"Total samples: {len(samples)}")
    print()

    # Statistics by timbral family
    by_family = {}
    for sample in samples:
        family = sample.get('timbral_family', 'unknown')
        by_family[family] = by_family.get(family, 0) + 1

    print("Samples by timbral family:")
    for family in sorted(by_family.keys()):
        count = by_family[family]
        print(f"  {family}: {count}")
    print()

    # Statistics by license
    by_license = {}
    for sample in samples:
        license_type = sample.get('license', 'unknown')
        by_license[license_type] = by_license.get(license_type, 0) + 1

    print("Samples by license:")
    for license_type in sorted(by_license.keys()):
        count = by_license[license_type]
        print(f"  {license_type}: {count}")
    print()

    # Duration statistics
    durations = [s.get('duration_sec') for s in samples if s.get('duration_sec')]
    if durations:
        print("Duration statistics:")
        print(f"  Min: {min(durations):.2f}s")
        print(f"  Max: {max(durations):.2f}s")
        print(f"  Avg: {sum(durations)/len(durations):.2f}s")
        print()

    # Sample rate statistics
    samplerates = {}
    for sample in samples:
        sr = sample.get('samplerate')
        if sr:
            samplerates[sr] = samplerates.get(sr, 0) + 1

    if samplerates:
        print("Sample rates:")
        for sr in sorted(samplerates.keys()):
            count = samplerates[sr]
            print(f"  {sr}Hz: {count}")
        print()

    # Bit depth statistics
    bitdepths = {}
    for sample in samples:
        bd = sample.get('bitdepth')
        if bd:
            bitdepths[bd] = bitdepths.get(bd, 0) + 1

    if bitdepths:
        print("Bit depths:")
        for bd in sorted(bitdepths.keys()):
            count = bitdepths[bd]
            print(f"  {bd}-bit: {count}")

    print("=" * 70)


def filter_samples(
    samples: List[Dict],
    family: Optional[str] = None,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None,
    tags: Optional[List[str]] = None,
    pitch: Optional[str] = None,
    license_filter: Optional[str] = None,
    instrument: Optional[str] = None
) -> List[Dict]:
    """Filter samples based on criteria."""
    filtered = samples

    if family:
        filtered = [s for s in filtered if s.get('timbral_family') == family]

    if min_duration is not None:
        filtered = [s for s in filtered
                   if s.get('duration_sec') and s.get('duration_sec') >= min_duration]

    if max_duration is not None:
        filtered = [s for s in filtered
                   if s.get('duration_sec') and s.get('duration_sec') <= max_duration]

    if tags:
        for tag in tags:
            filtered = [s for s in filtered
                       if tag.lower() in [t.lower() for t in s.get('tags', [])]]

    if pitch:
        filtered = [s for s in filtered if s.get('pitch') == pitch]

    if license_filter:
        filtered = [s for s in filtered
                   if license_filter.lower() in s.get('license', '').lower()]

    if instrument:
        filtered = [s for s in filtered
                   if instrument.lower() in s.get('instrument', '').lower()]

    return filtered


def list_samples(
    samples: List[Dict],
    output_file: Optional[str] = None,
    verbose: bool = False
):
    """List samples with optional output to JSON file."""
    if not samples:
        print("No samples match the filter criteria")
        return

    if output_file:
        # Export to JSON
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(samples, f, indent=2)
        print(f"✓ Exported {len(samples)} samples to {output_path}")
    else:
        # Print to console
        print("=" * 70)
        print(f"MATCHING SAMPLES ({len(samples)} found)")
        print("=" * 70)
        print()

        for i, sample in enumerate(samples, 1):
            print(f"[{i}] {sample.get('instrument', 'unknown')} (ID: {sample.get('freesound_id')})")
            print(f"    Family: {sample.get('timbral_family')} / {sample.get('subfamily')}")
            print(f"    File: {sample.get('file_path')}")

            if verbose:
                print(f"    Name: {sample.get('name')}")
                print(f"    User: {sample.get('username')}")
                print(f"    License: {sample.get('license')}")
                print(f"    Pitch: {sample.get('pitch', 'N/A')}")

                duration = sample.get('duration_sec')
                if duration:
                    print(f"    Duration: {duration:.2f}s")

                samplerate = sample.get('samplerate')
                bitdepth = sample.get('bitdepth')
                if samplerate and bitdepth:
                    print(f"    Format: {bitdepth}-bit / {samplerate}Hz")

                tags = sample.get('tags', [])
                if tags:
                    print(f"    Tags: {', '.join(tags[:5])}")

                rating = sample.get('avg_rating')
                if rating:
                    print(f"    Rating: {rating:.1f}/5")

            print()


def show_sample(metadata: Dict[str, Any], sound_id: int):
    """Show detailed information for a specific sample."""
    samples = metadata.get('samples', [])
    sample = next((s for s in samples if s.get('freesound_id') == sound_id), None)

    if not sample:
        print(f"✗ Sample ID {sound_id} not found in library")
        return

    print("=" * 70)
    print(f"SAMPLE DETAILS: {sample.get('name')}")
    print("=" * 70)
    print()

    print(f"Freesound ID: {sample.get('freesound_id')}")
    print(f"URL: {sample.get('freesound_url')}")
    print(f"File: {sample.get('file_path')}")
    print()

    print("Classification:")
    print(f"  Timbral family: {sample.get('timbral_family')}")
    print(f"  Subfamily: {sample.get('subfamily')}")
    print(f"  Instrument: {sample.get('instrument')}")
    print(f"  Pitch: {sample.get('pitch', 'N/A')}")
    print()

    print("Technical specs:")
    print(f"  Sample rate: {sample.get('samplerate')}Hz")
    print(f"  Bit depth: {sample.get('bitdepth')}-bit")
    print(f"  Channels: {sample.get('channels')}")
    print(f"  Duration: {sample.get('duration_sec', 0):.2f}s")
    print(f"  File type: {sample.get('file_type')}")

    filesize = sample.get('filesize_bytes')
    if filesize:
        print(f"  File size: {filesize / 1024 / 1024:.2f}MB")
    print()

    print("Metadata:")
    print(f"  User: {sample.get('username')}")
    print(f"  License: {sample.get('license')}")
    print(f"  Downloads: {sample.get('num_downloads', 0)}")

    rating = sample.get('avg_rating')
    num_ratings = sample.get('num_ratings', 0)
    if rating:
        print(f"  Rating: {rating:.1f}/5 ({num_ratings} votes)")
    print()

    tags = sample.get('tags', [])
    if tags:
        print(f"Tags: {', '.join(tags)}")
        print()

    desc_plan = sample.get('description_plan')
    if desc_plan:
        print(f"Plan notes: {desc_plan}")
        print()

    desc_fs = sample.get('description_freesound')
    if desc_fs:
        print(f"Freesound description:")
        print(f"  {desc_fs[:200]}{'...' if len(desc_fs) > 200 else ''}")
        print()

    audio_features = sample.get('audio_features', {})
    if audio_features:
        print("Audio features:")
        for key, value in audio_features.items():
            if value is not None:
                print(f"  {key}: {value}")
        print()

    print(f"Downloaded: {sample.get('download_date')}")
    print("=" * 70)


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Query and filter Freesound sample library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show library statistics
  %(prog)s stats

  # List all samples
  %(prog)s list

  # Filter by family and duration
  %(prog)s list --family 01_Metallic_Bells --min-duration 2.0

  # Find sustained pads
  %(prog)s list --tag sustained --tag pad --min-duration 5.0

  # Export metallic samples over 3 seconds
  %(prog)s list --family 01_Metallic_Bells --min-duration 3.0 --output bells.json

  # Show details for specific sample
  %(prog)s show 122650
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Stats command
    subparsers.add_parser('stats', help='Show library statistics')

    # List command
    list_parser = subparsers.add_parser('list', help='List samples with optional filters')
    list_parser.add_argument(
        '--family',
        help='Filter by timbral family (e.g., 01_Metallic_Bells)'
    )
    list_parser.add_argument(
        '--min-duration',
        type=float,
        help='Minimum duration in seconds'
    )
    list_parser.add_argument(
        '--max-duration',
        type=float,
        help='Maximum duration in seconds'
    )
    list_parser.add_argument(
        '--tag',
        action='append',
        dest='tags',
        help='Filter by tag (can be used multiple times)'
    )
    list_parser.add_argument(
        '--pitch',
        help='Filter by pitch (e.g., C4, D, G)'
    )
    list_parser.add_argument(
        '--license',
        dest='license_filter',
        help='Filter by license type (e.g., CC0, Attribution)'
    )
    list_parser.add_argument(
        '--instrument',
        help='Filter by instrument name (partial match)'
    )
    list_parser.add_argument(
        '--output',
        help='Export results to JSON file'
    )
    list_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed information for each sample'
    )

    # Show command
    show_parser = subparsers.add_parser('show', help='Show details for specific sample')
    show_parser.add_argument(
        'sound_id',
        type=int,
        help='Freesound ID of the sample'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    metadata = load_metadata()

    if args.command == 'stats':
        show_stats(metadata)

    elif args.command == 'list':
        samples = metadata.get('samples', [])

        filtered = filter_samples(
            samples,
            family=args.family,
            min_duration=args.min_duration,
            max_duration=args.max_duration,
            tags=args.tags,
            pitch=args.pitch,
            license_filter=args.license_filter,
            instrument=args.instrument
        )

        list_samples(filtered, output_file=args.output, verbose=args.verbose)

    elif args.command == 'show':
        show_sample(metadata, args.sound_id)


if __name__ == '__main__':
    main()
