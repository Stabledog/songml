"""
Chord voicing table loader - reads literal chord-to-notes mappings.

The voicing table is a TSV file with no chord symbol parsing.
Each line: ChordSymbol<TAB>Root<TAB>Offset1,Offset2,...
"""

from __future__ import annotations

__all__ = ["get_chord_notes", "load_voicing_table", "reload_voicing_table", "get_voicing_table", "NOTE_TO_MIDI"]

import os
from typing import Final

# Map of note names to MIDI numbers at octave 0
NOTE_TO_MIDI: Final[dict[str, int]] = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
    'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
}


def load_voicing_table(tsv_path: str | None = None) -> dict[str, tuple[str, list[int]]]:
    """
    Load chord voicing table from TSV file.
    
    Search order:
    1. Explicit tsv_path if provided
    2. ./chord_voicings.tsv (current working directory)
    3. data/chord_voicings.tsv (package default)
    
    Args:
        tsv_path: Path to TSV file (default: search local, then package)
        
    Returns:
        Dict mapping chord symbol → (root_note, [semitone_offsets])
        
    Raises:
        ValueError: If table has invalid format
    """
    if tsv_path is None:
        # Try local directory first
        local_path = os.path.join(os.getcwd(), 'chord_voicings.tsv')
        if os.path.exists(local_path):
            tsv_path = local_path
        else:
            # Fall back to package default
            tsv_path = os.path.join(os.path.dirname(__file__), 'data', 'chord_voicings.tsv')
    
    table = {}
    with open(tsv_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            if len(parts) != 3:
                raise ValueError(
                    f"Line {line_num}: Expected 3 tab-separated fields, got {len(parts)}"
                )
            
            chord_symbol, root_note, offsets_str = parts
            
            # Validate root note
            if root_note not in NOTE_TO_MIDI:
                raise ValueError(f"Line {line_num}: Invalid root note \"{root_note}\"")
            
            # Parse offsets
            try:
                offsets = [int(x.strip()) for x in offsets_str.split(',')]
            except ValueError as e:
                raise ValueError(
                    f"Line {line_num}: Invalid offsets \"{offsets_str}\": {e}"
                ) from e
            
            table[chord_symbol] = (root_note, offsets)
    
    return table


# Global voicing table - loaded once at module import, can be reloaded
_VOICING_TABLE: dict[str, tuple[str, list[int]]] = load_voicing_table()


def reload_voicing_table(tsv_path: str | None = None) -> None:
    """
    Reload the global voicing table from a different TSV file.
    
    Args:
        tsv_path: Path to TSV file (None = use default)
    """
    global _VOICING_TABLE
    _VOICING_TABLE = load_voicing_table(tsv_path)


def get_voicing_table() -> dict[str, tuple[str, list[int]]]:
    """
    Get the currently loaded voicing table.
    
    Returns:
        Dict mapping chord symbol → (root_note, [semitone_offsets])
    """
    return _VOICING_TABLE


def get_chord_notes(chord_symbol: str, root_octave: int = 3) -> list[int]:
    """
    Get MIDI note numbers for a chord symbol.
    
    Args:
        chord_symbol: Exact chord symbol (e.g., "Cmaj7", "F9/A")
        root_octave: Octave for root note (default 3 = C3=48)
        
    Returns:
        List of MIDI note numbers
        
    Raises:
        ValueError: If chord symbol not in voicing table
    """
    # Handle slash chords: "C7/G" → use "C7" voicing, add bass note
    base_chord = chord_symbol
    bass_note = None
    
    if '/' in chord_symbol:
        base_chord, bass_str = chord_symbol.split('/', 1)
        bass_note = bass_str.strip()
        if bass_note not in NOTE_TO_MIDI:
            raise ValueError(
                f"Invalid bass note \"{bass_note}\" in chord \"{chord_symbol}\""
            )
    
    # Lookup chord voicing
    if base_chord not in _VOICING_TABLE:
        raise ValueError(
            f"Unknown chord symbol \"{base_chord}\" (not in voicing table)"
        )
    
    root_note, offsets = _VOICING_TABLE[base_chord]
    
    # Calculate MIDI note numbers
    root_midi = NOTE_TO_MIDI[root_note] + (root_octave * 12)
    notes = [root_midi + offset for offset in offsets]
    
    # Add bass note an octave below if slash chord
    if bass_note:
        bass_midi = NOTE_TO_MIDI[bass_note] + ((root_octave - 1) * 12)
        notes = [bass_midi] + notes
    
    return notes
