"""CLI entry point for songml-to-midi command."""

from __future__ import annotations

import sys

from .ast import ParseError
from .midi_exporter import export_midi
from .parser import parse_songml


def main() -> None:
    """CLI entry point for songml-to-midi command.
    
    Converts a SongML file to MIDI format using the chord voicing table.
    
    Usage:
        songml-to-midi INPUT.songml OUTPUT.mid
    
    Exit codes:
        0: Success
        1: Parse error, export error, or file not found
    """
    if len(sys.argv) < 3:
        print("Usage: songml-to-midi INPUT.songml OUTPUT.mid", file=sys.stderr)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc = parse_songml(content)
        export_midi(doc, output_file)
        
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
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
