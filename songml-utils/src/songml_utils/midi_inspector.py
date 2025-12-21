"""MIDI file inspection using pretty_midi."""

from __future__ import annotations

import os
from dataclasses import dataclass

import pretty_midi


@dataclass
class MIDIInspection:
    """Result of MIDI file inspection."""

    filename: str
    tempo: float
    time_signature_numerator: int
    time_signature_denominator: int
    key_signature: str
    total_notes: int
    duration_seconds: float
    instruments: list[InstrumentInfo]


@dataclass
class InstrumentInfo:
    """Information about a MIDI instrument/track."""

    program: int
    program_name: str
    is_drum: bool
    note_count: int
    notes: list[NoteInfo] | None = None


@dataclass
class NoteInfo:
    pitch: int
    name: str
    start: float
    end: float
    velocity: int


def inspect_midi(midi_path: str) -> MIDIInspection:
    """
    Inspect a MIDI file and extract key information.

    Args:
        midi_path: Path to MIDI file to inspect

    Returns:
        MIDIInspection object with extracted information

    Raises:
        ValueError: If MIDI file cannot be loaded or parsed
        FileNotFoundError: If MIDI file does not exist
    """
    # Check file existence first to provide better error message
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    # Check file existence first to provide better error message
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    try:
        midi_data = pretty_midi.PrettyMIDI(midi_path)
    except Exception as e:
        raise ValueError(f"Failed to load MIDI file: {e}") from e

    # Extract tempo (use first tempo change, or default if none)
    tempo = 120.0
    if midi_data.get_tempo_changes()[0].size > 0:
        tempo = float(midi_data.get_tempo_changes()[1][0])

    # Extract time signature (use first, or default to 4/4)
    time_sig_num = 4
    time_sig_den = 4
    if midi_data.time_signature_changes:
        ts = midi_data.time_signature_changes[0]
        time_sig_num = ts.numerator
        time_sig_den = ts.denominator

    # Extract key signature (use first, or default to C major)
    key_sig = "C"
    if midi_data.key_signature_changes:
        ks = midi_data.key_signature_changes[0]
        key_sig = _key_number_to_string(ks.key_number)

    # Count total notes across all instruments
    total_notes = sum(len(inst.notes) for inst in midi_data.instruments)

    # Collect per-instrument info including note details
    instruments = []
    for inst in midi_data.instruments:
        note_infos: list[NoteInfo] = []
        for n in inst.notes:
            note_infos.append(
                NoteInfo(
                    pitch=n.pitch,
                    name=_note_number_to_name(n.pitch),
                    start=n.start,
                    end=n.end,
                    velocity=n.velocity,
                )
            )

        instruments.append(
            InstrumentInfo(
                program=inst.program,
                program_name=pretty_midi.program_to_instrument_name(inst.program),
                is_drum=inst.is_drum,
                note_count=len(inst.notes),
                notes=note_infos,
            )
        )

    return MIDIInspection(
        filename=midi_path,
        tempo=tempo,
        time_signature_numerator=time_sig_num,
        time_signature_denominator=time_sig_den,
        key_signature=key_sig,
        total_notes=total_notes,
        duration_seconds=midi_data.get_end_time(),
        instruments=instruments,
    )


def _key_number_to_string(key_number: int) -> str:
    """
    Convert MIDI key signature number to key name.

    Args:
        key_number: MIDI key signature number (-7 to +7, where 0 = C major/A minor)

    Returns:
        Key signature string (e.g., "C", "G", "F#", "Bb")
    """
    # Major key signatures from -7 flats to +7 sharps
    major_keys = ["Cb", "Gb", "Db", "Ab", "Eb", "Bb", "F", "C", "G", "D", "A", "E", "B", "F#", "C#"]

    # Offset: -7 maps to index 0, 0 maps to index 7, +7 maps to index 14
    idx = key_number + 7
    if 0 <= idx < len(major_keys):
        return major_keys[idx]
    return "C"  # Default fallback


def _note_number_to_name(pitch: int) -> str:
    """Convert MIDI pitch number to note name with octave (e.g., 60 -> C4)."""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (pitch // 12) - 1
    name = names[pitch % 12]
    return f"{name}{octave}"


def format_inspection(inspection: MIDIInspection) -> str:
    """
    Format inspection results as human-readable string.

    Args:
        inspection: MIDIInspection result to format

    Returns:
        Formatted string with inspection details
    """
    lines = [
        f"File: {inspection.filename}",
        f"Duration: {inspection.duration_seconds:.2f} seconds",
        f"Tempo: {inspection.tempo:.1f} BPM",
        f"Time Signature: {inspection.time_signature_numerator}/{inspection.time_signature_denominator}",
        f"Key Signature: {inspection.key_signature}",
        f"Total Notes: {inspection.total_notes}",
        "",
        f"Instruments: {len(inspection.instruments)}",
    ]

    for i, inst in enumerate(inspection.instruments):
        drum_marker = " (drums)" if inst.is_drum else ""
        lines.append(
            f"  {i + 1}. Program {inst.program}: {inst.program_name}{drum_marker} "
            f"({inst.note_count} notes)"
        )

        # If notes are present, include a concise listing
        if inst.notes:
            lines.append("    Notes:")
            for n in inst.notes:
                # Print pitch with note name, start, end, velocity
                lines.append(
                    f"      - {n.name} (pitch={n.pitch}) start={n.start:.3f}s end={n.end:.3f}s vel={n.velocity}"
                )

    return "\n".join(lines)
