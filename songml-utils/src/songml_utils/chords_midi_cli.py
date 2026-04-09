"""CLI entry point: chords-to-midi — convert chord sheet to MIDI file."""

from __future__ import annotations

import argparse
import sys

from mido import Message, MetaMessage, MidiFile, MidiTrack

from .chord_sheet import parse_sheet
from .chord_voicings import MIDDLE_C_OCTAVE, get_chord_notes
from .midi_exporter import MICROSECONDS_PER_MINUTE, TICKS_PER_BEAT, DEFAULT_VELOCITY, DEFAULT_CHANNEL

type MidiEvent = tuple[int, str, list[int]]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="chords-to-midi",
        description="Convert a chord sheet to a MIDI file with real chord voicings.",
    )
    parser.add_argument("chord_sheet", help="Path to chord sheet file")
    parser.add_argument("output", help="Path for output .mid file")
    parser.add_argument(
        "--tempo",
        type=float,
        metavar="BPM",
        help="Override tempo from chord sheet header",
    )
    parser.add_argument(
        "--transpose",
        type=int,
        default=0,
        metavar="SEMITONES",
        help="Transpose all chords (positive = up, negative = down, default: 0)",
    )
    args = parser.parse_args()

    try:
        with open(args.chord_sheet, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        header, entries = parse_sheet(text)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not entries:
        print("Error: chord sheet contains no chord data", file=sys.stderr)
        sys.exit(1)

    tempo_bpm = args.tempo if args.tempo is not None else header.tempo
    transpose = args.transpose

    # Resolve MIDI note events from chord entries
    events: list[MidiEvent] = []
    errors: list[str] = []

    for entry in entries:
        # Convert bar:beat back to absolute tick position
        # beat is 1-based within bar, bar is 1-based
        # We don't store beats_per_bar in the sheet, so derive from time_sig header
        try:
            beats_per_bar = int(header.time_sig.split("/")[0])
        except (ValueError, IndexError):
            beats_per_bar = 4

        abs_beat = (entry.bar - 1) * beats_per_bar + (entry.beat - 1)
        tick = int(abs_beat * TICKS_PER_BEAT)
        duration_ticks = int(entry.duration * TICKS_PER_BEAT)

        try:
            notes = get_chord_notes(entry.chord, root_octave=MIDDLE_C_OCTAVE, transpose=transpose)
        except ValueError as e:
            errors.append(f"  bar {entry.bar}:{entry.beat:g} chord {entry.chord!r}: {e}")
            continue

        events.append((tick, "note_on", notes))
        events.append((tick + duration_ticks, "note_off", notes))

    if errors:
        error_list = "\n".join(errors)
        print(f"Error: unknown chord symbols:\n{error_list}", file=sys.stderr)
        sys.exit(1)

    # Sort: by time, note_off before note_on at the same tick
    events.sort(key=lambda e: (e[0], e[1] == "note_on"))

    # Build MIDI file
    mid = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage("track_name", name=header.source or "Chord Track"))
    track.append(MetaMessage("set_tempo", tempo=int(MICROSECONDS_PER_MINUTE / tempo_bpm)))

    try:
        num, denom = (int(x) for x in header.time_sig.split("/"))
        track.append(MetaMessage("time_signature", numerator=num, denominator=denom))
    except (ValueError, TypeError):
        track.append(MetaMessage("time_signature", numerator=4, denominator=4))

    current_tick = 0
    for tick, event_type, notes in events:
        delta = tick - current_tick
        if event_type == "note_on":
            for i, note in enumerate(notes):
                track.append(
                    Message("note_on", note=note, velocity=DEFAULT_VELOCITY,
                            time=delta if i == 0 else 0, channel=DEFAULT_CHANNEL)
                )
        else:
            for i, note in enumerate(notes):
                track.append(
                    Message("note_off", note=note, velocity=0,
                            time=delta if i == 0 else 0, channel=DEFAULT_CHANNEL)
                )
        current_tick = tick

    track.append(MetaMessage("end_of_track", time=0))

    try:
        mid.save(args.output)
    except OSError as e:
        print(f"Error: cannot write {args.output!r}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Exported {len(entries)} chords to {args.output}", file=sys.stderr)
