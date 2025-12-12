"""CLI entry point for songml-to-midi command."""

from __future__ import annotations

import argparse
import os
import sys

from .ast import ParseError
from .midi_exporter import export_midi
from .parser import parse_songml


def main() -> None:
    """CLI entry point for songml-to-midi command."""
    parser = argparse.ArgumentParser(
        description="Convert a SongML file to MIDI format using chord voicing table.",
        epilog="Example:\n  %(prog)s song.songml song.mid",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('input', metavar='INPUT',
                        help='input SongML file')
    parser.add_argument('output', metavar='OUTPUT',
                        help='output MIDI file')
    
    args = parser.parse_args()
    input_file = args.input
    output_file = args.output
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc = parse_songml(content)
        
        # Check for project-local chord_voicings.tsv
        input_dir = os.path.dirname(os.path.abspath(input_file))
        local_voicings = os.path.join(input_dir, 'chord_voicings.tsv')
        voicings_path = local_voicings if os.path.exists(local_voicings) else None
        
        export_midi(doc, output_file, voicings_path)
        
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
