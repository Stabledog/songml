"""CLI entry point for songml-inspect-midi command."""

from __future__ import annotations

import argparse
import sys

from .midi_inspector import format_inspection, inspect_midi


def main() -> None:
    """CLI entry point for songml-inspect-midi command."""
    parser = argparse.ArgumentParser(
        description="Inspect a MIDI file and display its properties.",
        epilog="Example:\n  %(prog)s song.mid",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", metavar="INPUT", help="MIDI file to inspect")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print per-track note listings and raw details",
    )

    args = parser.parse_args()
    input_file = args.input

    try:
        inspection = inspect_midi(input_file)
        output = format_inspection(inspection)
        # If verbose requested, append more detailed output (notes already included)
        if args.verbose:
            # format_inspection already includes notes if present; simply print
            print(output)
        else:
            print(output)

    except FileNotFoundError as e:
        print(f"✗ File error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"✗ Inspection error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
