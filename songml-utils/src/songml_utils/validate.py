"""SongML validation CLI - parses and outputs AST as JSON."""

from __future__ import annotations

import argparse
import sys

from .ast import ParseError, Property, Section
from .chord_voicings import get_voicing_table
from .parser import parse_songml
from .voicing_validator import validate_voicing_table

type ChordLocation = tuple[str, int]
type ChordLocations = dict[str, ChordLocation]


def main() -> None:
    """CLI entry point for songml-validate command."""
    parser = argparse.ArgumentParser(
        description="Parse and validate a SongML file, output AST as JSON.",
        epilog="Validation messages go to stderr, JSON output to stdout.",
    )
    parser.add_argument("file", metavar="FILE", help="SongML file to validate")
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Validate all chords in voicing table, not just those used in the song",
    )

    args = parser.parse_args()
    filename = args.file
    try:
        with open(filename, encoding="utf-8") as f:
            content = f.read()

        doc = parse_songml(content)

        # Validation messages to stderr
        print(f"✓ Parsed successfully: {len(doc.items)} top-level items", file=sys.stderr)

        if doc.warnings:
            print(f"\nWarnings ({len(doc.warnings)}):", file=sys.stderr)
            for warning in doc.warnings:
                print(f"  {warning}", file=sys.stderr)

        # Validate chord voicings
        chord_symbols = _extract_chord_symbols(doc, filename)
        if chord_symbols or args.all:
            voicing_warnings = _validate_chord_voicings(chord_symbols, validate_all=args.all)
            if voicing_warnings:
                print(f"\nChord Voicing Warnings ({len(voicing_warnings)}):", file=sys.stderr)
                for warning in voicing_warnings:
                    print(f"  {warning}", file=sys.stderr)

        # Print summary to stderr
        section_count = sum(1 for item in doc.items if isinstance(item, Section))
        property_count = sum(1 for item in doc.items if isinstance(item, Property))
        print(f"\nSummary: {section_count} sections, {property_count} properties", file=sys.stderr)

        # AST JSON to stdout
        print(doc.to_json())

    except ParseError as e:
        print(f"✗ Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def _extract_chord_symbols(doc, filename: str) -> ChordLocations:
    """Extract all unique chord symbols from the parsed document with their first occurrence location.

    Returns:
        Dict mapping chord_symbol -> (source_file, line_number)
    """
    symbols: ChordLocations = {}

    for item in doc.items:
        if isinstance(item, Section):
            for bar in item.bars:
                for chord_token in bar.chords:
                    # Skip rest markers and empty chords
                    if (
                        chord_token.text
                        and chord_token.text not in ("-", ".", "")
                        and chord_token.text not in symbols
                    ):
                        # Track first occurrence only
                        symbols[chord_token.text] = (filename, bar.line_number)

    return symbols


def _validate_chord_voicings(
    chord_symbols_with_loc: ChordLocations, validate_all: bool = False
) -> list[str]:
    """Validate chord voicings for symbols used in the document (or all if validate_all=True).

    Args:
        chord_symbols_with_loc: Dict mapping chord_symbol -> (source_file, line_number)
        validate_all: If True, validate entire voicing table regardless of usage
    """
    voicing_table = get_voicing_table()

    if validate_all:
        # Validate entire voicing table
        theory_warnings = validate_voicing_table(voicing_table)
        return theory_warnings

    # For slash chords, only validate the base chord (before the '/')
    # Any bass note can be used with slash chords, so we don't validate the full symbol
    base_chord_to_full = {}  # Map base chord -> (full_symbol, source, line)
    for chord, (source, line) in chord_symbols_with_loc.items():
        if "/" in chord:
            base = chord.split("/")[0]
            # Track first occurrence of each base chord
            if base not in base_chord_to_full:
                base_chord_to_full[base] = (chord, source, line)
        else:
            if chord not in base_chord_to_full:
                base_chord_to_full[chord] = (chord, source, line)

    # Filter table to only base chords used in this document
    used_voicings = {
        symbol: voicing for symbol, voicing in voicing_table.items() if symbol in base_chord_to_full
    }

    # Check for unknown symbols (base chords not in voicing table)
    warnings = []
    unknown_symbols = set(base_chord_to_full.keys()) - set(voicing_table.keys())
    for symbol in sorted(unknown_symbols):
        full_symbol, source, line = base_chord_to_full[symbol]
        warnings.append(f"{source}:{line}: Unknown chord symbol '{symbol}' (not in voicing table)")

    # Validate known voicings
    theory_warnings = validate_voicing_table(used_voicings)
    warnings.extend(theory_warnings)

    return warnings


if __name__ == "__main__":
    main()
