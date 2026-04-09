"""CLI entry point: als-extract — extract chord track from Ableton .als to chord sheet."""

from __future__ import annotations

import argparse
import sys

from .als_parser import extract_chord_clips
from .chord_sheet import format_sheet


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="als-extract",
        description="Extract the CHORD track from an Ableton .als file and write a chord sheet.",
    )
    parser.add_argument("als_file", help="Path to .als file")
    parser.add_argument(
        "--time",
        default="4/4",
        metavar="N/D",
        help="Time signature (default: 4/4)",
    )
    parser.add_argument(
        "--tempo",
        type=float,
        default=120.0,
        metavar="BPM",
        help="Tempo in BPM (default: 120)",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Output file (default: stdout)",
    )
    args = parser.parse_args()

    try:
        numerator = int(args.time.split("/")[0])
    except (ValueError, IndexError):
        print(f"Error: invalid time signature {args.time!r}", file=sys.stderr)
        sys.exit(1)

    try:
        track_name, entries = extract_chord_clips(args.als_file, beats_per_bar=numerator)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    import os

    source = os.path.basename(args.als_file)
    fixme_count = sum(1 for e in entries if not hasattr(e, "chord"))

    text = format_sheet(
        entries,
        source=source,
        track=track_name,
        tempo=args.tempo,
        time_sig=args.time,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
        print(f"✓ Wrote {args.output}", file=sys.stderr)
    else:
        print(text)

    if fixme_count:
        print(
            f"⚠  {fixme_count} FIXME(s) written — edit before running chords-to-midi",
            file=sys.stderr,
        )
        sys.exit(2)  # Distinct exit code: partial success, needs editing
