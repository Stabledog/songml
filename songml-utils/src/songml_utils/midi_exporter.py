"""MIDI file export from SongML AST."""

from __future__ import annotations

__all__ = ["export_midi"]

import sys
from typing import Final

from mido import Message, MetaMessage, MidiFile, MidiTrack

from .ast import Document, Property, Section
from .chord_voicings import get_chord_notes, reload_voicing_table

# MIDI constants
TICKS_PER_BEAT: Final[int] = 480
DEFAULT_VELOCITY: Final[int] = 64
DEFAULT_CHANNEL: Final[int] = 0
DEFAULT_ROOT_OCTAVE: Final[int] = 3
MICROSECONDS_PER_MINUTE: Final[int] = 60_000_000

type MidiEvent = tuple[int, str, list[int]]
type MidiEvents = list[MidiEvent]


def export_midi(doc: Document, output_path: str, voicings_path: str | None = None) -> None:
    """
    Export SongML AST to MIDI file.

    Converts the parsed SongML document into a MIDI file using the chord voicing
    table. Each chord is rendered as simultaneous note events with timing derived
    from the AST's beat information.

    Args:
        doc: Parsed SongML document containing sections with bars and chords
        output_path: Path to write the .mid file
        voicings_path: Optional path to chord_voicings.tsv (None = auto-discover or use default)

    Raises:
        ValueError: If document has no sections, no chords, or contains
                    unknown chord symbols not in the voicing table
    """
    # Override with explicit voicings path if provided (otherwise auto-discovered)
    if voicings_path:
        reload_voicing_table(voicings_path)

    # Extract properties
    tempo_str = _get_property(doc, "Tempo", default="100")
    time_sig_str = _get_property(doc, "Time", default="4/4")
    key_str = _get_property(doc, "Key", default="Cmaj")
    title = _get_property(doc, "Title", default="Untitled")

    # Parse properties
    tempo_bpm = int(tempo_str)
    numerator, denominator = _parse_time_signature(time_sig_str)
    beats_per_bar = numerator

    # Get sections with bars
    sections = [item for item in doc.items if isinstance(item, Section)]
    if not sections:
        raise ValueError("No musical content to export (no sections found)")

    # Check if any section has bars with chords
    has_chords = any(bar.chords for section in sections for bar in section.bars)
    if not has_chords:
        raise ValueError("No musical content to export (no chords found)")

    # Create MIDI file
    mid = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    mid.tracks.append(track)

    # Add meta-events
    track.append(MetaMessage("track_name", name=title))
    track.append(MetaMessage("set_tempo", tempo=_bpm_to_microseconds(tempo_bpm)))
    track.append(MetaMessage("time_signature", numerator=numerator, denominator=denominator))

    # Add key signature (best effort - warn if invalid)
    try:
        key_sig = _parse_key_signature(key_str)
        track.append(MetaMessage("key_signature", key=key_sig))
    except ValueError as e:
        print(f"Warning: {e}, using C major", file=sys.stderr)
        track.append(MetaMessage("key_signature", key="C"))

    # Build timeline: collect all note on/off events with absolute ticks
    events: MidiEvents = []

    # Track absolute bar position across all sections
    absolute_bar_number = 0

    for section in sections:
        for bar in section.bars:
            # Use absolute bar position, not the bar's labeled number
            # (bar numbers restart in each section)
            bar_start_tick = absolute_bar_number * beats_per_bar * TICKS_PER_BEAT
            absolute_bar_number += 1

            for chord_token in bar.chords:
                tick = bar_start_tick + int(chord_token.start_beat * TICKS_PER_BEAT)
                duration_ticks = int(chord_token.duration_beats * TICKS_PER_BEAT)

                # Get MIDI notes for this chord
                try:
                    notes = get_chord_notes(chord_token.text, root_octave=DEFAULT_ROOT_OCTAVE)
                except ValueError as e:
                    raise ValueError(
                        f'Error at section "{section.name}", bar {bar.number}, beat {chord_token.start_beat}: {e}'
                    ) from e

                events.append((tick, "note_on", notes))
                events.append((tick + duration_ticks, "note_off", notes))

    # Sort events by time, then by type (note_off before note_on at same time)
    # This ensures notes are turned off before being turned on again
    events.sort(key=lambda e: (e[0], e[1] == "note_on"))

    # Convert absolute times to delta times and write to track
    current_tick = 0
    for tick, event_type, notes in events:
        delta = tick - current_tick

        if event_type == "note_on":
            for i, note in enumerate(notes):
                # Only first note in this event group gets the delta time
                track.append(
                    Message(
                        "note_on",
                        note=note,
                        velocity=DEFAULT_VELOCITY,
                        time=delta if i == 0 else 0,
                        channel=DEFAULT_CHANNEL,
                    )
                )
        else:  # note_off
            for i, note in enumerate(notes):
                # Only first note in this event group gets the delta time
                track.append(
                    Message(
                        "note_off",
                        note=note,
                        velocity=0,
                        time=delta if i == 0 else 0,
                        channel=DEFAULT_CHANNEL,
                    )
                )

        current_tick = tick

    # End of track
    track.append(MetaMessage("end_of_track", time=0))

    # Save MIDI file
    mid.save(output_path)


def _get_property(doc: Document, name: str, default: str) -> str:
    """Get property value from document, or return default."""
    for item in doc.items:
        if isinstance(item, Property) and item.name == name:
            return item.value
    return default


def _parse_time_signature(time_sig: str) -> tuple[int, int]:
    """Parse time signature string like '4/4' into (numerator, denominator)."""
    parts = time_sig.split("/")
    if len(parts) != 2:
        raise ValueError(f'Invalid time signature format: "{time_sig}"')
    return int(parts[0]), int(parts[1])


def _bpm_to_microseconds(bpm: int) -> int:
    """Convert BPM to microseconds per quarter note."""
    return int(MICROSECONDS_PER_MINUTE / bpm)


def _parse_key_signature(key_str: str) -> str:
    """
    Parse key signature string into MIDI key signature format.

    Args:
        key_str: e.g., "Cmaj", "C", "Fmaj", "Dm", "Dmin"

    Returns:
        MIDI key string like "C", "Dm", "F#m"

    Raises:
        ValueError: If key string cannot be parsed
    """
    key_str = key_str.strip()

    # Map of common formats to MIDI format
    # Handle: "Cmaj", "C major", "C", "Dm", "Dmin", "D minor"
    if key_str.endswith("maj") or key_str.endswith("major"):
        # Major key
        root = key_str.replace("maj", "").replace("major", "").strip()
        return root
    if "min" in key_str.lower() or key_str.endswith("m"):
        # Minor key
        root = key_str.replace("min", "").replace("minor", "").replace("m", "").strip()
        return root + "m"
    # Assume major if no qualifier
    return key_str


if __name__ == "__main__":
    # Simple test
    from .parser import parse_songml

    test_songml = """
Title: Test Song
Key: Cmaj
Tempo: 120
Time: 4/4

[Verse - 4 bars]
| 0 | 1 | 2 | 3 |
| C | F | G | C |
"""

    doc = parse_songml(test_songml)
    export_midi(doc, "test_output.mid")
    print("Exported test_output.mid")
