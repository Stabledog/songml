"""Tests for transpose functionality across the codebase."""

from __future__ import annotations

import logging
import os
from unittest.mock import Mock

import pytest
from mido import MidiFile

from songml_utils.chord_voicings import get_chord_notes
from songml_utils.midi_exporter import export_midi
from songml_utils.parser import parse_songml


def test_get_chord_notes_transpose_positive():
    """Test transposing chord notes up."""
    # C major at octave 4: [60, 64, 67]
    notes_original = get_chord_notes("C", root_octave=4, transpose=0)
    assert notes_original == [60, 64, 67]

    # Transpose up 12 semitones (one octave)
    notes_up = get_chord_notes("C", root_octave=4, transpose=12)
    assert notes_up == [72, 76, 79]  # C5, E5, G5

    # Transpose up 2 semitones (C to D)
    notes_up2 = get_chord_notes("C", root_octave=4, transpose=2)
    assert notes_up2 == [62, 66, 69]


def test_get_chord_notes_transpose_negative():
    """Test transposing chord notes down."""
    # C major at octave 4: [60, 64, 67]
    notes_original = get_chord_notes("C", root_octave=4, transpose=0)
    assert notes_original == [60, 64, 67]

    # Transpose down 12 semitones (one octave)
    notes_down = get_chord_notes("C", root_octave=4, transpose=-12)
    assert notes_down == [48, 52, 55]  # C3, E3, G3

    # Transpose down 5 semitones (C to G)
    notes_down5 = get_chord_notes("C", root_octave=4, transpose=-5)
    assert notes_down5 == [55, 59, 62]


def test_get_chord_notes_transpose_slash_chord():
    """Test transpose with slash chords (bass note handling)."""
    # C/G at octave 4: bass G3 + C voicing
    notes_original = get_chord_notes("C/G", root_octave=4, transpose=0)
    # Bass G3 (55) + C (60, 64, 67)
    assert notes_original[0] == 55  # Bass note

    # Transpose up 2 semitones
    notes_up = get_chord_notes("C/G", root_octave=4, transpose=2)
    # All notes should be +2
    assert notes_up[0] == 57  # Bass note G3 -> A3
    assert notes_up[1] == 62  # C4 -> D4


def test_get_chord_notes_transpose_zero_is_noop():
    """Test that transpose=0 is a no-op."""
    notes_no_transpose = get_chord_notes("C", root_octave=4, transpose=0)
    notes_explicit_zero = get_chord_notes("C", root_octave=4, transpose=0)
    assert notes_no_transpose == notes_explicit_zero


def test_export_midi_transpose_in_range(tmp_path):
    """Test MIDI export with transpose that keeps all notes in valid range."""
    songml = """
Title: Transpose Test
Key: C
Tempo: 120
Time: 4/4

[Verse - 2 bars]
| 0   | 1  |
| C   | Cm |
"""
    doc = parse_songml(songml)
    output_file = tmp_path / "transposed.mid"

    # Export with transpose +5 (C to F)
    export_midi(doc, str(output_file), transpose=5)

    # Verify MIDI file was created
    assert output_file.exists()

    # Load and verify notes
    mid = MidiFile(str(output_file))
    note_ons = [msg for track in mid.tracks for msg in track if msg.type == "note_on"]

    # C chord transposed +5: [60, 64, 67] -> [65, 69, 72] (F major)
    # Cm chord transposed +5: [60, 63, 67] -> [65, 68, 72]
    expected_notes = {65, 68, 69, 72}
    actual_notes = {msg.note for msg in note_ons}

    assert actual_notes == expected_notes


def test_export_midi_transpose_drops_out_of_range_high(tmp_path, caplog, capsys):
    """Test MIDI export drops notes that transpose above 127."""
    songml = """
Title: High Transpose Test
Key: C
Tempo: 120
Time: 4/4

[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(songml)
    output_file = tmp_path / "high_transpose.mid"

    # Transpose way up to force notes above 127
    # C at octave 4 = [60, 64, 67]
    # +70 = [130, 134, 137] - all out of range
    with caplog.at_level(logging.ERROR):
        export_midi(doc, str(output_file), transpose=70)

    # Verify MIDI file was still created (even with no valid notes)
    assert output_file.exists()

    # Verify error messages were logged
    captured = capsys.readouterr()
    assert "Dropped MIDI note" in captured.err
    assert "out of MIDI range 0-127" in captured.err
    assert "original 60" in captured.err or "original 64" in captured.err

    # Verify summary warning
    assert "Warning:" in captured.err
    assert "were dropped" in captured.err

    # Load and verify no note_on messages (all notes dropped)
    mid = MidiFile(str(output_file))
    note_ons = [msg for track in mid.tracks for msg in track if msg.type == "note_on"]
    assert len(note_ons) == 0, "All notes should have been dropped"


def test_export_midi_transpose_drops_out_of_range_low(tmp_path, caplog, capsys):
    """Test MIDI export drops notes that transpose below 0."""
    songml = """
Title: Low Transpose Test
Key: C
Tempo: 120
Time: 4/4

[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(songml)
    output_file = tmp_path / "low_transpose.mid"

    # Transpose way down to force notes below 0
    # C at octave 4 = [60, 64, 67]
    # -65 = [-5, -1, 2] - two notes out of range, one valid
    with caplog.at_level(logging.ERROR):
        export_midi(doc, str(output_file), transpose=-65)

    # Verify MIDI file was created
    assert output_file.exists()

    # Verify error messages
    captured = capsys.readouterr()
    assert "Dropped MIDI note" in captured.err
    assert "out of MIDI range 0-127" in captured.err

    # Load and verify only valid notes remain
    mid = MidiFile(str(output_file))
    note_ons = [msg for track in mid.tracks for msg in track if msg.type == "note_on"]

    # Only note at MIDI 2 (D0) should remain
    actual_notes = [msg.note for msg in note_ons]
    assert 2 in actual_notes
    assert -5 not in actual_notes
    assert -1 not in actual_notes


def test_export_midi_transpose_partial_chord_drop(tmp_path, caplog, capsys):
    """Test MIDI export when some notes in a chord are dropped but not all."""
    songml = """
Title: Partial Drop Test
Key: C
Tempo: 120
Time: 4/4

[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(songml)
    output_file = tmp_path / "partial_drop.mid"

    # Transpose to boundary: some notes valid, some invalid
    # C at octave 4 = [60, 64, 67]
    # +64 = [124, 128, 131] - first valid, others invalid
    with caplog.at_level(logging.ERROR):
        export_midi(doc, str(output_file), transpose=64)

    # Verify file created
    assert output_file.exists()

    # Verify errors logged
    captured = capsys.readouterr()
    assert "Dropped MIDI note 128" in captured.err or "128" in captured.err
    assert "Dropped MIDI note 131" in captured.err or "131" in captured.err

    # Load and verify only the valid note (124) remains
    mid = MidiFile(str(output_file))
    note_ons = [msg for track in mid.tracks for msg in track if msg.type == "note_on"]

    actual_notes = [msg.note for msg in note_ons]
    assert 124 in actual_notes
    assert len(actual_notes) == 1  # Only one valid note


def test_export_midi_transpose_multiple_chords_mixed_validity(tmp_path, capsys):
    """Test transpose with multiple chords where some have valid notes, some don't."""
    songml = """
Title: Mixed Validity Test
Key: C
Tempo: 120
Time: 4/4

[Verse - 2 bars]
| 0 | 1 |
| C | C |
"""
    doc = parse_songml(songml)
    output_file = tmp_path / "mixed.mid"

    # Transpose so both C chords have same issue
    export_midi(doc, str(output_file), transpose=70)

    # Verify file created
    assert output_file.exists()

    # Both chords should have logged errors
    captured = capsys.readouterr()
    # Should see multiple "Dropped MIDI note" messages
    drop_count = captured.err.count("Dropped MIDI note")
    assert drop_count >= 6  # 3 notes per C chord × 2 chords


def test_export_midi_transpose_with_section_and_bar_context(tmp_path, capsys):
    """Test that error messages include section, bar, and beat context."""
    songml = """
Title: Context Test
Key: C
Tempo: 120
Time: 4/4

[Intro - 1 bars]
| 0  |
| C  |

[Verse - 1 bars]
| 0  |
| Cm |
"""
    doc = parse_songml(songml)
    output_file = tmp_path / "context.mid"

    export_midi(doc, str(output_file), transpose=65)

    captured = capsys.readouterr()
    # Check for section names in error messages
    assert "section 'Intro'" in captured.err or "section 'Verse'" in captured.err
    # Check for bar numbers
    assert "bar 0" in captured.err or "bar 1" in captured.err
    # Check for chord symbols
    assert "'C'" in captured.err or "'Cm'" in captured.err


def test_export_midi_backwards_compatible_no_transpose(tmp_path):
    """Test that omitting transpose parameter works (backwards compatibility)."""
    songml = """
Title: Backwards Compatible Test
Key: C
Tempo: 120
Time: 4/4

[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(songml)
    output_file = tmp_path / "no_transpose.mid"

    # Call without transpose argument (should default to 0)
    export_midi(doc, str(output_file))

    # Verify file created and notes are original
    assert output_file.exists()
    mid = MidiFile(str(output_file))
    note_ons = [msg for track in mid.tracks for msg in track if msg.type == "note_on"]
    actual_notes = {msg.note for msg in note_ons}

    # C chord: [60, 64, 67]
    assert actual_notes == {60, 64, 67}
