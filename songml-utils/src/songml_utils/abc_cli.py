"""CLI entry point for songml-to-abc command."""

from __future__ import annotations

import argparse
import sys

from .ast import ParseError
from .parser import parse_songml


def main() -> None:
    """CLI entry point for songml-to-abc command."""
    parser = argparse.ArgumentParser(
        description="Convert a SongML file to ABC notation format.",
        epilog="Example:\n  %(prog)s song.songml song.abc",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", metavar="INPUT", help="input SongML file")
    parser.add_argument("output", metavar="OUTPUT", help='output ABC file (use "-" for stdout)')
    parser.add_argument(
        "--unit-length", metavar="L", help='override computed unit note length (e.g., "1/16")'
    )
    parser.add_argument(
        "--chord-style",
        metavar="STYLE",
        default="chordline",
        help="chord rendering style (default: chordline)",
    )
    parser.add_argument(
        "-t",
        "--transpose",
        type=int,
        default=0,
        metavar="SEMITONES",
        help="transpose by semitones (positive = up, negative = down, default: 0)",
    )

    args = parser.parse_args()
    input_file = args.input
    output_file = args.output

    try:
        with open(input_file, encoding="utf-8") as f:
            content = f.read()

        doc = parse_songml(content)

        # Print warnings if any
        if doc.warnings:
            for warning in doc.warnings:
                print(f"Warning: {warning}", file=sys.stderr)

        # Generate ABC
        from .abc_exporter import to_abc_string

        abc_text = to_abc_string(
            doc,
            unit_note_length=args.unit_length,
            chord_style=args.chord_style,
            transpose=args.transpose,
        )

        # Output to file or stdout
        if output_file == "-":
            print(abc_text)
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(abc_text)
            print(f"✓ Exported to {output_file}", file=sys.stderr)

    except ParseError as e:
        print(f"✗ Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"✗ Export error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"✗ File error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # pragma: no cover
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
