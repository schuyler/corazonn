#!/bin/bash
# Process Freesound samples for AMOR using sox:
# - Convert to 48kHz mono WAV
# - Normalize to -3 dB
# - Fade out and trim at 2.5s if longer
#
# Usage:
#   ./process_samples.sh <input_dir> <output_dir>
#
# Example:
#   ./process_samples.sh ../freesound_samples/ processed/

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <input_dir> <output_dir>"
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
MAX_DURATION=2.5
FADE_DURATION=0.2

if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: Input directory not found: $INPUT_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "Processing samples from: $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Max duration: ${MAX_DURATION}s (fade out from $((MAX_DURATION - FADE_DURATION))s)"
echo "Target format: 48kHz mono WAV, normalized to -3dB"
echo ""

SUCCESS=0
TOTAL=0

# Find all audio files
find "$INPUT_DIR" -type f \( \
    -iname "*.wav" -o \
    -iname "*.aif" -o \
    -iname "*.aiff" -o \
    -iname "*.flac" -o \
    -iname "*.mp3" -o \
    -iname "*.ogg" \
\) | sort | while read -r INPUT_FILE; do

    TOTAL=$((TOTAL + 1))

    # Get relative path and create output path
    REL_PATH="${INPUT_FILE#$INPUT_DIR/}"
    OUTPUT_FILE="$OUTPUT_DIR/${REL_PATH%.*}.wav"

    # Create output subdirectory if needed
    mkdir -p "$(dirname "$OUTPUT_FILE")"

    # Get duration using soxi
    DURATION=$(soxi -D "$INPUT_FILE" 2>/dev/null || echo "0")

    if [ "$DURATION" = "0" ]; then
        echo "SKIP: $INPUT_FILE (could not read duration)"
        continue
    fi

    # Check if we need to fade and trim
    NEEDS_TRIM=$(awk -v d="$DURATION" -v m="$MAX_DURATION" 'BEGIN { print (d > m) ? 1 : 0 }')

    if [ "$NEEDS_TRIM" -eq 1 ]; then
        # Long file: convert, normalize, fade out, and trim
        sox "$INPUT_FILE" "$OUTPUT_FILE" \
            remix 1 \
            rate 48000 \
            gain -n -3 \
            fade t 0 "$MAX_DURATION" "$FADE_DURATION" \
            2>/dev/null

        echo "FADE+TRIM: $(basename "$INPUT_FILE") (${DURATION}s) -> $(basename "$OUTPUT_FILE")"
    else
        # Short file: just convert and normalize
        sox "$INPUT_FILE" "$OUTPUT_FILE" \
            remix 1 \
            rate 48000 \
            gain -n -3 \
            2>/dev/null

        echo "PROCESS: $(basename "$INPUT_FILE") (${DURATION}s) -> $(basename "$OUTPUT_FILE")"
    fi

    SUCCESS=$((SUCCESS + 1))
done

echo ""
echo "COMPLETE: Processed samples in $OUTPUT_DIR"
