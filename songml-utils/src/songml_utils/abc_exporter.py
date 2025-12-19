"""ABC notation export from SongML AST."""

from __future__ import annotations

__all__ = ["to_abc_string", "export_abc"]


from .ast import Bar, Document, Property, Section
from .chord_voicings import get_chord_notes

# ABC format constants
DEFAULT_REFERENCE_NUMBER: int = 1

type PropertyDict = dict[str, str]


def get_chord_voicing(chord_symbol: str) -> list[int]:
    """
    Get MIDI notes for a chord symbol, with slash chord support.

    Args:
        chord_symbol: Chord symbol (e.g., "C", "F9/A")

    Returns:
        List of MIDI note numbers
    """
    try:
        # Try to get voicing - use octave 5 (C5 = MIDI 60 = middle C)
        # This puts chords in the comfortable treble clef range
        return get_chord_notes(chord_symbol, root_octave=5)
    except (ValueError, KeyError):
        # Unknown chord
        return []


def to_abc_string(
    doc: Document, unit_note_length: str | None = None, chord_style: str = "chordline"
) -> str:
    """
    Convert SongML Document to ABC notation string.

    Args:
        doc: Parsed SongML document containing sections with bars and chords
        unit_note_length: Override computed L: value (e.g., "1/16"). If None,
                         computed as 1/(denominator*2) from time signature.
        chord_style: Chord rendering style; currently only 'chordline' supported

    Returns:
        ABC notation as a string

    Raises:
        ValueError: If document has no sections or invalid time signature
    """
    if chord_style != "chordline":
        raise ValueError(f"Unsupported chord_style: {chord_style}. Only 'chordline' is supported.")

    # Extract properties
    props = _extract_properties(doc)

    # Parse time signature
    numerator, denominator = _parse_time_signature(props["Time"])
    beats_per_bar = numerator

    # Compute or use provided unit note length
    if unit_note_length is None:
        unit_note_length = f"1/{denominator * 2}"

    # Get sections with bars
    sections = [item for item in doc.items if isinstance(item, Section)]
    if not sections:
        raise ValueError("No musical content to export (no sections found)")

    # Build ABC output
    lines: list[str] = []

    # Add headers
    lines.extend(_format_abc_headers(props, unit_note_length, numerator, denominator))
    # NOTE: No blank line after headers - ABC parsers require music to start immediately

    # Add each section
    for section in sections:
        # Add part marker
        lines.append(f"P:{section.name}")

        # Add bars with chords and lyrics
        section_lines = _format_section(section, beats_per_bar, denominator)
        lines.extend(section_lines)
        # NOTE: No blank lines between sections - ABC parsers require continuous music

    return "\n".join(lines)


def export_abc(
    doc: Document,
    output_path: str,
    unit_note_length: str | None = None,
    chord_style: str = "chordline",
) -> None:
    """
    Export SongML Document to ABC file.

    Args:
        doc: Parsed SongML document
        output_path: Path to write the .abc file
        unit_note_length: Override computed L: value
        chord_style: Chord rendering style ('chordline' only)
    """
    abc_text = to_abc_string(doc, unit_note_length, chord_style)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(abc_text)


def _extract_properties(doc: Document) -> PropertyDict:
    """Extract properties from document with defaults."""
    defaults = {"Title": "Untitled", "Key": "C", "Tempo": "120", "Time": "4/4"}

    props = defaults.copy()
    for item in doc.items:
        if isinstance(item, Property):
            props[item.name] = item.value

    return props


def _format_abc_headers(
    props: PropertyDict, unit_note_length: str, numerator: int, denominator: int
) -> list[str]:
    """Format ABC file headers."""
    lines = [
        f"X: {DEFAULT_REFERENCE_NUMBER}",
        f"T: {props['Title']}",
        f"M: {numerator}/{denominator}",
        f"L: {unit_note_length}",
        f"Q: 1/4={props['Tempo']}",
        f"K: {_normalize_key(props['Key'])}",
    ]
    return lines


def _normalize_key(key_str: str) -> str:
    """
    Normalize key string to ABC format.

    Examples:
        "Cmaj" -> "C"
        "Fmaj" -> "F"
        "Dm" -> "Dm"
        "Dmin" -> "Dm"
    """
    key_str = key_str.strip()

    # Handle major keys (check 'major' first since it contains 'maj')
    if " major" in key_str.lower():
        # Extract root before ' major'
        parts = key_str.split()
        return parts[0].strip()
    if key_str.endswith("maj"):
        root = key_str[:-3].strip()
        return root

    # Handle minor keys (check 'minor' first since it contains 'min')
    if " minor" in key_str.lower():
        # Extract root before ' minor' and add 'm'
        parts = key_str.split()
        root = parts[0].strip()
        if not root.endswith("m"):
            return root + "m"
        return root
    if key_str.endswith("min"):
        root = key_str[:-3].strip()
        if not root.endswith("m"):
            return root + "m"
        return root

    # If ends with 'm' (like "Dm"), keep as-is
    if key_str.endswith("m") and len(key_str) > 1 and key_str[-2].isalpha():
        return key_str

    # Default: assume major, return root
    return key_str


def _parse_time_signature(time_sig: str) -> tuple[int, int]:
    """Parse time signature string like '4/4' into (numerator, denominator)."""
    parts = time_sig.split("/")
    if len(parts) != 2:
        raise ValueError(f'Invalid time signature format: "{time_sig}"')
    try:
        numerator = int(parts[0])
        denominator = int(parts[1])
    except ValueError as err:
        raise ValueError(f'Invalid time signature values: "{time_sig}"') from err
    return numerator, denominator


def _format_section(section: Section, beats_per_bar: int, denominator: int) -> list[str]:
    """Format a section with bars, chords, and lyrics."""
    lines: list[str] = []

    # Group bars into lines (e.g., 4 bars per line for readability)
    bars_per_line = 4

    for i in range(0, len(section.bars), bars_per_line):
        bar_group = section.bars[i : i + bars_per_line]

        # Format chord line for this group
        chord_line = _format_bar_group_chords(bar_group, beats_per_bar, denominator)
        lines.append(chord_line)

        # Format lyrics line if any bar in group has lyrics
        lyrics_line = _format_bar_group_lyrics(bar_group, beats_per_bar, denominator)
        if lyrics_line:
            lines.append(lyrics_line)

    return lines


def _format_bar_group_chords(bars: list[Bar], beats_per_bar: int, denominator: int) -> str:
    """Format a group of bars as ABC chord notation."""
    bar_strs: list[str] = []

    for bar in bars:
        bar_str = _format_bar_chords(bar, beats_per_bar, denominator)
        bar_strs.append(bar_str)

    # Join bars with bar lines
    return "| " + " | ".join(bar_strs) + " |"


def _format_bar_chords(bar: Bar, beats_per_bar: int, denominator: int) -> str:
    """Format a single bar's chords as ABC notation."""
    if not bar.chords:
        # Empty bar: fill with rests
        total_units = _beats_to_abc_units(beats_per_bar, denominator)
        return f"z{total_units}"

    # Build ABC elements for each chord
    elements: list[str] = []

    for chord_token in bar.chords:
        # Chord annotation
        chord_annotation = f'"{chord_token.text}"'

        # Duration in ABC units
        duration_units = _beats_to_abc_units(chord_token.duration_beats, denominator)

        # Get chord voicing and use top note as melody
        try:
            voicing = get_chord_voicing(chord_token.text)
            if voicing and len(voicing) > 0:
                # Use the top note (highest pitch) as melody
                top_note_midi = voicing[-1]
                top_note_abc = _midi_to_abc_note(top_note_midi)
                elements.append(f"{chord_annotation}{top_note_abc}{duration_units}")
            else:
                # No voicing found, use rest
                elements.append(f"{chord_annotation}z{duration_units}")
        except (ValueError, KeyError):
            # Unknown chord, use rest
            elements.append(f"{chord_annotation}z{duration_units}")

    return " ".join(elements)


def _midi_to_abc_note(midi_note: int) -> str:
    """
    Convert MIDI note number to ABC notation.

    ABC notation:
    - C, D, E, F, G, A, B = octave starting at middle C (C4 = MIDI 60)
    - c, d, e, f, g, a, b = octave above middle C (c5 = MIDI 72)
    - C, D, ... = below c4, use comma: C, = MIDI 48
    - For sharps: ^C, for flats: _D

    Args:
        midi_note: MIDI note number (0-127)

    Returns:
        ABC note string (e.g., "C", "^C,", "c", "_d")
    """
    note_names = ["C", "^C", "D", "^D", "E", "F", "^F", "G", "^G", "A", "^A", "B"]

    note_in_octave = midi_note % 12
    octave = midi_note // 12

    base_note = note_names[note_in_octave]

    # ABC middle C (C) starts at MIDI 60 (octave 5)
    # Below that, use uppercase with commas
    # Above 71, use lowercase
    if midi_note < 60:
        # Lowercase base note and add commas for each octave below 60
        commas = "," * (5 - octave)
        return base_note + commas
    elif midi_note < 72:
        # Between 60-71: uppercase, no modifiers (this is the main octave)
        return base_note
    else:
        # 72 and above: lowercase
        # Use lowercase version of the note
        base_lower = base_note.replace("^", "^").lower()  # Keep accidental uppercase
        # Handle sharp - accidental stays uppercase
        base_lower = "^" + base_note[1].lower() if "^" in base_note else base_note.lower()

        # Add apostrophes for octaves above 72
        apostrophes = "'" * (octave - 5)
        return base_lower + apostrophes


def _format_bar_group_lyrics(bars: list[Bar], beats_per_bar: int, denominator: int) -> str:
    """Format lyrics line for a group of bars."""
    lyrics_parts: list[str] = []

    for bar in bars:
        if bar.lyrics:
            # Split lyrics into words/syllables
            words = bar.lyrics.split()

            # If bar has multiple chords, distribute lyrics across them
            if bar.chords:
                # Simple strategy: assign words to chords evenly
                # For now, just join all words with hyphens if multiple chords
                if len(bar.chords) > 1:
                    # Distribute words across chord positions
                    lyrics_parts.extend(words)
                else:
                    # Single chord: put all lyrics under it
                    lyrics_parts.append(" ".join(words))
            else:
                # No chords: still include lyrics
                lyrics_parts.append(" ".join(words))
        else:
            # No lyrics for this bar: use underscore for continuation
            lyrics_parts.append("_")

    if not any(part != "_" for part in lyrics_parts):
        # All underscores: no actual lyrics
        return ""

    return "w: " + " ".join(lyrics_parts)


def _beats_to_abc_units(beats: float, denominator: int) -> int:
    """
    Convert SongML beats to ABC unit count.

    Based on L: 1/(denominator*2), where:
    - 1 beat = denominator/2 units
    - 0.5 beat = denominator/4 units

    For 4/4 time (denominator=4, L:1/8):
        1 beat = 2 units
        0.5 beat = 1 unit

    For 6/8 time (denominator=8, L:1/16):
        1 beat = 4 units
        0.5 beat = 2 units
    """
    # L: 1/(denominator*2) means each unit represents (denominator*2) notes per whole
    # So 1 whole note = denominator*2 units
    # 1 beat (quarter note in 4/4) = (1/4) whole note = (denominator*2)/4 units
    units_per_beat = (denominator * 2) / 4
    return int(beats * units_per_beat)


if __name__ == "__main__":
    # Simple test
    from .parser import parse_songml

    test_songml = """
Title: Test Song
Key: Cmaj
Tempo: 120
Time: 4/4

[Verse - 2 bars]
| 0 | 1 |
| C | F G |
| Hello world |
"""

    doc = parse_songml(test_songml)
    abc_text = to_abc_string(doc)
    print(abc_text)
    print("\n---")
    export_abc(doc, "test_output.abc")
    print("Exported test_output.abc")
