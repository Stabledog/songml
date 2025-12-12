"""
Chord voicing validator - validates TSV voicings against music theory.

Uses pychord library to parse chord symbols and compare against declared voicings.
"""

from __future__ import annotations

__all__ = ["validate_chord_voicing", "validate_voicing_table"]

import re
from typing import Final

try:
    from pychord import Chord
    PYCHORD_AVAILABLE = True
except ImportError:
    PYCHORD_AVAILABLE = False
    Chord = None  # type: ignore


# Map note names to pitch classes (0-11)
NOTE_TO_PC: Final[dict[str, int]] = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
    'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
}


def validate_chord_voicing(
    chord_symbol: str,
    root_note: str,
    offsets: list[int]
) -> tuple[bool, str | None]:
    """
    Validate a chord voicing against music theory.
    
    Uses pychord to parse the chord symbol and compare the TSV voicing
    (root + offsets) against the expected chord components.
    
    Args:
        chord_symbol: Chord symbol (e.g., "Cmaj7", "F9/A")
        root_note: Root note name (e.g., "C", "F#")
        offsets: Semitone offsets from root (e.g., [0, 4, 7, 11])
        
    Returns:
        (is_valid, warning_message)
        - is_valid: True if voicing passes validation
        - warning_message: None if valid, otherwise description of the problem
        
    Examples:
        >>> validate_chord_voicing("Cmaj7", "C", [0, 4, 7, 11])
        (True, None)
        
        >>> validate_chord_voicing("Cmaj7", "C", [0, 3, 7, 10])
        (False, "Voicing pitch classes {0,3,7,10} do not match expected components ['C','E','G','B'] -> {0,4,7,11}")
    """
    if not PYCHORD_AVAILABLE:
        return (True, None)  # Skip validation if pychord not installed
    
    # Handle slash chords: extract base chord
    base_symbol = chord_symbol.split('/')[0] if '/' in chord_symbol else chord_symbol
    
    # Normalize '+' to 'aug' for pychord compatibility
    # pychord supports '7#5' for augmented 7th, but not '+7' or 'aug7'
    if '+7' in base_symbol:
        base_symbol = base_symbol.replace('+7', '7#5')
    else:
        # Replace standalone '+' with 'aug' (for triads like F#+, G+)
        base_symbol = base_symbol.replace('+', 'aug')
    
    # Try to parse with pychord
    try:
        chord = Chord(base_symbol)
        expected_components = chord.components()
    except Exception as e:
        # pychord can't parse this symbol - warn but don't fail
        return (False, f"Cannot parse chord symbol '{base_symbol}' with pychord: {e}")
    
    # Get root pitch class
    if root_note not in NOTE_TO_PC:
        return (False, f"Invalid root note '{root_note}'")
    
    root_pc = NOTE_TO_PC[root_note]
    
    # Convert offsets to pitch classes
    voicing_pcs = {(root_pc + offset) % 12 for offset in offsets}
    
    # Convert expected components to pitch classes
    try:
        expected_pcs = {NOTE_TO_PC[note] for note in expected_components}
    except KeyError as e:
        return (False, f"Cannot map expected component to pitch class: {e}")
    
    # Compare: voicing should contain all expected chord tones
    # (Allow extra notes like doubled roots, octave extensions, etc.)
    if not expected_pcs.issubset(voicing_pcs):
        missing = expected_pcs - voicing_pcs
        missing_notes = [note for note, pc in NOTE_TO_PC.items() if pc in missing]
        return (
            False,
            f"Voicing missing expected chord tones: {sorted(missing_notes)} "
            f"(voicing PCs: {sorted(voicing_pcs)}, expected PCs: {sorted(expected_pcs)})"
        )
    
    # Also warn if voicing has unexpected pitch classes
    # (This is lenient - we just warn, don't fail)
    extra = voicing_pcs - expected_pcs
    if extra:
        extra_notes = [note for note, pc in NOTE_TO_PC.items() if pc in extra]
        return (
            False,
            f"Voicing contains unexpected pitch classes: {sorted(extra_notes)} "
            f"(voicing PCs: {sorted(voicing_pcs)}, expected PCs: {sorted(expected_pcs)})"
        )
    
    return (True, None)


def validate_voicing_table(
    table: dict[str, tuple[str, list[int]]]
) -> list[str]:
    """
    Validate all entries in a chord voicing table.
    
    Args:
        table: Dict mapping chord_symbol -> (root_note, offsets)
        
    Returns:
        List of warning messages (empty if all valid)
        
    Example:
        >>> table = {"Cmaj7": ("C", [0, 4, 7, 11]), "Dm7": ("D", [0, 3, 7, 10])}
        >>> warnings = validate_voicing_table(table)
        >>> len(warnings)
        0
    """
    warnings = []
    
    for chord_symbol, (root_note, offsets) in table.items():
        is_valid, warning_msg = validate_chord_voicing(chord_symbol, root_note, offsets)
        if not is_valid and warning_msg:
            warnings.append(f"Chord '{chord_symbol}': {warning_msg}")
    
    return warnings
