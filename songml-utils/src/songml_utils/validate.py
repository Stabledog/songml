"""SongML validation CLI - parses and outputs AST as JSON."""

from __future__ import annotations

import argparse
import sys

from .ast import ChordToken, ParseError, Property, Section
from .chord_voicings import get_voicing_table
from .parser import parse_songml
from .voicing_validator import validate_voicing_table


def main() -> None:
    """CLI entry point for songml-validate command."""
    parser = argparse.ArgumentParser(
        description="Parse and validate a SongML file, output AST as JSON.",
        epilog="Validation messages go to stderr, JSON output to stdout."
    )
    parser.add_argument('file', metavar='FILE',
                        help='SongML file to validate')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Validate all chords in voicing table, not just those used in the song')
    
    args = parser.parse_args()
    filename = args.file
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc = parse_songml(content)
        
        # Validation messages to stderr
        print(f"✓ Parsed successfully: {len(doc.items)} top-level items", file=sys.stderr)
        
        if doc.warnings:
            print(f"\nWarnings ({len(doc.warnings)}):", file=sys.stderr)
            for warning in doc.warnings:
                print(f"  {warning}", file=sys.stderr)
        
        # Validate chord voicings
        chord_symbols = _extract_chord_symbols(doc)
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


def _extract_chord_symbols(doc) -> set[str]:
    """Extract all unique chord symbols from the parsed document."""
    symbols = set()
    
    for item in doc.items:
        if isinstance(item, Section):
            for bar in item.bars:
                for chord_token in bar.chords:
                    # Skip rest markers and empty chords
                    if chord_token.text and chord_token.text not in ('-', '.', ''):
                        symbols.add(chord_token.text)
    
    return symbols


def _validate_chord_voicings(chord_symbols: set[str], validate_all: bool = False) -> list[str]:
    """Validate chord voicings for symbols used in the document (or all if validate_all=True)."""
    voicing_table = get_voicing_table()
    
    if validate_all:
        # Validate entire voicing table
        theory_warnings = validate_voicing_table(voicing_table)
        return theory_warnings
    
    # For slash chords, only validate the base chord (before the '/')
    # Any bass note can be used with slash chords, so we don't validate the full symbol
    base_chord_symbols = set()
    for chord in chord_symbols:
        if '/' in chord:
            base_chord_symbols.add(chord.split('/')[0])
        else:
            base_chord_symbols.add(chord)
    
    # Filter table to only base chords used in this document
    used_voicings = {
        symbol: voicing 
        for symbol, voicing in voicing_table.items() 
        if symbol in base_chord_symbols
    }
    
    # Check for unknown symbols (base chords not in voicing table)
    warnings = []
    unknown_symbols = base_chord_symbols - set(voicing_table.keys())
    for symbol in sorted(unknown_symbols):
        warnings.append(f"Unknown chord symbol '{symbol}' (not in voicing table)")
    
    # Validate known voicings
    theory_warnings = validate_voicing_table(used_voicings)
    warnings.extend(theory_warnings)
    
    return warnings


if __name__ == "__main__":
    main()
