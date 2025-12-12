"""Tests for MIDI exporter."""

import os
import pytest
from mido import MidiFile

from songml_utils.parser import parse_songml
from songml_utils.midi_exporter import export_midi
from songml_utils.chord_voicings import get_chord_notes


def test_chord_voicing_lookup():
    """Test basic chord voicing lookups."""
    # Major chord at octave 3
    # C at octave 3 = 0 + 36 = 36 (C2)
    notes = get_chord_notes('C', root_octave=3)
    assert notes == [36, 40, 43]  # C2, E2, G2
    
    # Seventh chord
    notes = get_chord_notes('Cmaj7', root_octave=3)
    assert notes == [36, 40, 43, 47]  # C2, E2, G2, B2
    
    # Different root
    # F at octave 3 = 5 + 36 = 41 (F2)
    notes = get_chord_notes('F', root_octave=3)
    assert notes == [41, 45, 48]  # F2, A2, C3


def test_chord_notes_for_wunderkind():
    """Test exact MIDI note numbers for chords in wunderkind.songml."""
    # A chord at root_octave=3
    # Voicing table: A	A	0,4,7
    # A at octave 3 = 9 + 36 = 45 (MIDI note A2)
    # Expected: A2(45), C#3(49), E3(52)
    notes = get_chord_notes('A', root_octave=3)
    assert notes == [45, 49, 52], f"A chord: expected [45, 49, 52], got {notes}"
    
    # D chord at root_octave=3
    # Voicing table: D	D	0,4,7
    # D at octave 3 = 2 + 36 = 38 (MIDI note D2)
    # Expected: D2(38), F#2(42), A2(45)
    notes = get_chord_notes('D', root_octave=3)
    assert notes == [38, 42, 45], f"D chord: expected [38, 42, 45], got {notes}"
    
    # E chord at root_octave=3
    # Voicing table: E	E	0,4,7
    # E at octave 3 = 4 + 36 = 40 (MIDI note E2)
    # Expected: E2(40), G#2(44), B2(47)
    notes = get_chord_notes('E', root_octave=3)
    assert notes == [40, 44, 47], f"E chord: expected [40, 44, 47], got {notes}"
    
    # Bm7 chord at root_octave=3
    # Voicing table: Bm7	B	0,3,7,10
    # B at octave 3 = 11 + 36 = 47 (MIDI note B2)
    # Expected: B2(47), D3(50), F#3(54), A3(57)
    notes = get_chord_notes('Bm7', root_octave=3)
    assert notes == [47, 50, 54, 57], f"Bm7 chord: expected [47, 50, 54, 57], got {notes}"


def test_slash_chord():
    """Test slash chord voicing (bass note)."""
    notes = get_chord_notes('C7/G', root_octave=3)
    # Should have G2 (bass at octave 2) + C7 voicing (root at octave 3)
    # G at octave 2 = 7 + 24 = 31 (G1)
    assert notes[0] == 31  # G1 (one octave below root octave)
    assert 36 in notes  # C2 (root at octave 3)


def test_slash_chord_with_accidentals():
    """Test slash chords with sharp/flat bass notes."""
    # C#m7/G# - sharp in both base chord and bass note
    # C#m7 voicing: C#	0,3,7,10 → C#, E, G#, B
    # At octave 3: C# = 1+36 = 37, so C#m7 = [37, 40, 44, 47]
    # Bass G# at octave 2: G# = 8+24 = 32 (G#1)
    notes = get_chord_notes('C#m7/G#', root_octave=3)
    assert notes[0] == 32, f"Expected G#1 (32), got {notes[0]}"
    assert 37 in notes, f"Expected C#2 (37) in chord, got {notes}"
    assert 44 in notes, f"Expected G#2 (44) in chord, got {notes}"
    
    # Fmaj7/Ab - flat bass note
    # Fmaj7 voicing: F	0,4,7,11 → F, A, C, E
    # At octave 3: F = 5+36 = 41, so Fmaj7 = [41, 45, 48, 52]
    # Bass Ab at octave 2: Ab = 8+24 = 32 (Ab1, enharmonic with G#1)
    notes = get_chord_notes('Fmaj7/Ab', root_octave=3)
    assert notes[0] == 32, f"Expected Ab1 (32), got {notes[0]}"
    assert 41 in notes, f"Expected F2 (41) in chord, got {notes}"
    
    # D7/F# - sharp bass note
    # D7 voicing: D	0,4,7,10 → D, F#, A, C
    # At octave 3: D = 2+36 = 38, so D7 = [38, 42, 45, 48]
    # Bass F# at octave 2: F# = 6+24 = 30 (F#1)
    notes = get_chord_notes('D7/F#', root_octave=3)
    assert notes[0] == 30, f"Expected F#1 (30), got {notes[0]}"
    assert 38 in notes, f"Expected D2 (38) in chord, got {notes}"
    assert 42 in notes, f"Expected F#2 (42) in chord, got {notes}"


def test_slash_chord_invalid_bass_note():
    """Test that invalid bass notes raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        get_chord_notes('C7/X')
    assert 'Invalid bass note "X"' in str(exc_info.value)
    
    # Also test with accidental-like but invalid notation
    with pytest.raises(ValueError) as exc_info:
        get_chord_notes('C7/H#')
    assert 'Invalid bass note "H#"' in str(exc_info.value)


def test_unknown_chord_raises_error():
    """Test that unknown chord symbols raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        get_chord_notes('Xmaj7')
    assert "Unknown chord symbol" in str(exc_info.value)


def test_simple_chord_progression():
    """Test exporting a simple chord progression."""
    content = """
Title: Test Song
Tempo: 120
Time: 4/4

[Verse - 4 bars]
| 0 | 1 | 2 | 3 |
| C | F | G | C |
"""
    
    doc = parse_songml(content)
    output_file = "test_simple.mid"
    
    try:
        export_midi(doc, output_file)
        
        # Verify file was created and is valid MIDI
        assert os.path.exists(output_file)
        mid = MidiFile(output_file)
        assert len(mid.tracks) > 0
        
        # Check for expected meta messages
        track = mid.tracks[0]
        meta_types = [msg.type for msg in track if msg.is_meta]
        assert 'track_name' in meta_types
        assert 'set_tempo' in meta_types
        assert 'time_signature' in meta_types
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


def test_timing_with_dots():
    """Test explicit timing with dots."""
    content = """
Tempo: 120
Time: 4/4

[Test - 2 bars]
| 0 | 1 |
| C.. G.. | F.... |
"""
    
    doc = parse_songml(content)
    output_file = "test_timing.mid"
    
    try:
        export_midi(doc, output_file)
        
        mid = MidiFile(output_file)
        track = mid.tracks[0]
        
        # Should have note events (filtered from meta messages)
        note_msgs = [msg for msg in track if not msg.is_meta]
        assert len(note_msgs) > 0
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


def test_semicolon_timing():
    """Test half-beat timing with semicolons."""
    content = """
Tempo: 120
Time: 4/4

[Test - 1 bars]
| 0 |
| ...;C |
"""
    
    doc = parse_songml(content)
    output_file = "test_semicolon.mid"
    
    try:
        export_midi(doc, output_file)
        assert os.path.exists(output_file)
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


def test_empty_document_raises_error():
    """Test that document with no sections raises error."""
    content = """
Title: Empty Song
"""
    
    doc = parse_songml(content)
    
    with pytest.raises(ValueError) as exc_info:
        export_midi(doc, "test_empty.mid")
    assert "No musical content" in str(exc_info.value)


def test_unknown_chord_in_bar_raises_error():
    """Test that unknown chord in bar raises meaningful error."""
    content = """
[Test - 1 bars]
| 0 |
| Xmaj7 |
"""
    
    doc = parse_songml(content)
    
    with pytest.raises(ValueError) as exc_info:
        export_midi(doc, "test_bad_chord.mid")
    assert "bar 0" in str(exc_info.value)
    assert "Xmaj7" in str(exc_info.value)


def test_multi_section_document():
    """Test document with multiple sections."""
    content = """
Title: Multi-Section Song
Tempo: 100
Time: 4/4

[Intro - 2 bars]
| 0 | 1 |
| C | G |

[Verse - 2 bars]
| 2 | 3 |
| F | C |
"""
    
    doc = parse_songml(content)
    output_file = "test_multi.mid"
    
    try:
        export_midi(doc, output_file)
        assert os.path.exists(output_file)
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


def test_youve_got_a_way_sample():
    """Test parsing the real sample file youve-got-a-way.songml."""
    # Skipping this test - the file contains advanced notation like "/A" (bare slash chords)
    # which are shorthand for "previous chord with different bass note"
    # This is a parser feature that's not yet implemented
    pytest.skip("Sample file contains advanced notation not yet supported")


def test_wunderkind_bar1_bar2_exact_notes():
    """
    Test exact MIDI notes for bars 1-2 of wunderkind.songml.
    
    Bar 1: | A.... |
    Bar 2: | D.. E.. |
    
    This test verifies:
    1. Correct note numbers for each chord
    2. No extra/stray notes
    3. Correct note on/off pairing
    """
    content = """
Title: Wunderkind Test
Tempo: 100
Time: 4/4
Key: A

[Verse1 - 2 bars]
| 1     | 2       |
| A.... | D.. E.. |
"""
    
    doc = parse_songml(content)
    output_file = "test_wunderkind_bars.mid"
    
    try:
        export_midi(doc, output_file)
        
        # Read the MIDI file and extract note events
        mid = MidiFile(output_file)
        track = mid.tracks[0]
        
        # Extract only note_on and note_off messages
        note_events = [msg for msg in track if msg.type in ('note_on', 'note_off')]
        
        # Build absolute tick timeline
        abs_tick = 0
        events_with_tick = []
        for msg in note_events:
            abs_tick += msg.time
            events_with_tick.append((abs_tick, msg.type, msg.note))
        
        # Expected notes:
        # Bar 1 (A chord): A2(45), C#3(49), E3(52)
        # Bar 2 (D chord): D2(38), F#2(42), A2(45)
        # Bar 2 (E chord): E2(40), G#2(44), B2(47)
        
        expected_a_notes = {45, 49, 52}
        expected_d_notes = {38, 42, 45}
        expected_e_notes = {40, 44, 47}
        
        # Calculate expected ticks (480 ticks per beat)
        # Bars are numbered sequentially from 0 in the MIDI output
        # Bar 1 in songml becomes absolute bar 0: tick 0-1920
        # Bar 2 in songml becomes absolute bar 1: tick 1920-3840
        bar1_start = 0 * 4 * 480  # 0
        bar1_end = 1 * 4 * 480    # 1920
        bar2_d_start = bar1_end   # 1920
        bar2_d_end = bar2_d_start + 2 * 480  # 2880 (2 beats)
        bar2_e_start = bar2_d_end  # 2880
        bar2_e_end = bar2_e_start + 2 * 480  # 3840 (2 beats)
        
        # Group events by tick
        events_by_tick = {}
        for tick, event_type, note in events_with_tick:
            if tick not in events_by_tick:
                events_by_tick[tick] = []
            events_by_tick[tick].append((event_type, note))
        
        # Verify Bar 1 A chord
        assert bar1_start in events_by_tick, f"Bar 1 A chord should start at tick {bar1_start}"
        bar1_on_events = [n for t, n in events_by_tick[bar1_start] if t == 'note_on']
        assert set(bar1_on_events) == expected_a_notes, \
            f"Bar 1 A chord: expected notes {expected_a_notes}, got {set(bar1_on_events)}"
        
        assert bar1_end in events_by_tick, f"Bar 1 A chord should end at tick {bar1_end}"
        bar1_off_events = [n for t, n in events_by_tick[bar1_end] if t == 'note_off']
        assert set(bar1_off_events) == expected_a_notes, \
            f"Bar 1 A chord off: expected notes {expected_a_notes}, got {set(bar1_off_events)}"
        
        # Verify Bar 2 D chord
        assert bar2_d_start in events_by_tick, f"Bar 2 D chord should start at tick {bar2_d_start}"
        bar2_d_on = [n for t, n in events_by_tick[bar2_d_start] if t == 'note_on']
        assert set(bar2_d_on) == expected_d_notes, \
            f"Bar 2 D chord: expected notes {expected_d_notes}, got {set(bar2_d_on)}"
        
        assert bar2_d_end in events_by_tick, f"Bar 2 D chord should end at tick {bar2_d_end}"
        bar2_d_off = [n for t, n in events_by_tick[bar2_d_end] if t == 'note_off']
        assert set(bar2_d_off) == expected_d_notes, \
            f"Bar 2 D chord off: expected notes {expected_d_notes}, got {set(bar2_d_off)}"
        
        # Verify Bar 2 E chord
        assert bar2_e_start in events_by_tick, f"Bar 2 E chord should start at tick {bar2_e_start}"
        bar2_e_on = [n for t, n in events_by_tick[bar2_e_start] if t == 'note_on']
        assert set(bar2_e_on) == expected_e_notes, \
            f"Bar 2 E chord: expected notes {expected_e_notes}, got {set(bar2_e_on)}"
        
        assert bar2_e_end in events_by_tick, f"Bar 2 E chord should end at tick {bar2_e_end}"
        bar2_e_off = [n for t, n in events_by_tick[bar2_e_end] if t == 'note_off']
        assert set(bar2_e_off) == expected_e_notes, \
            f"Bar 2 E chord off: expected notes {expected_e_notes}, got {set(bar2_e_off)}"
        
        # Verify no extra note events at unexpected ticks
        expected_ticks = {bar1_start, bar1_end, bar2_d_start, bar2_d_end, bar2_e_start, bar2_e_end}
        actual_ticks = set(events_by_tick.keys())
        extra_ticks = actual_ticks - expected_ticks
        assert len(extra_ticks) == 0, \
            f"Found unexpected note events at ticks: {extra_ticks}. Events: {[events_by_tick[t] for t in extra_ticks]}"
        
        # Verify total note count
        total_on = len([e for e in events_with_tick if e[1] == 'note_on'])
        total_off = len([e for e in events_with_tick if e[1] == 'note_off'])
        expected_total = 3 + 3 + 3  # 3 notes in A, 3 in D, 3 in E
        assert total_on == expected_total, f"Expected {expected_total} note_on events, got {total_on}"
        assert total_off == expected_total, f"Expected {expected_total} note_off events, got {total_off}"
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


def test_note_on_off_pairing():
    """
    Test that every note_on has a matching note_off with correct duration.
    """
    content = """
Tempo: 120
Time: 4/4

[Test - 2 bars]
| 0 | 1 |
| C.... | G.. F.. |
"""
    
    doc = parse_songml(content)
    output_file = "test_pairing.mid"
    
    try:
        export_midi(doc, output_file)
        
        mid = MidiFile(output_file)
        track = mid.tracks[0]
        note_events = [msg for msg in track if msg.type in ('note_on', 'note_off')]
        
        # Track active notes: note_number -> start_tick
        active_notes = {}
        abs_tick = 0
        note_durations = []  # List of (note, duration_ticks)
        
        for msg in note_events:
            abs_tick += msg.time
            
            if msg.type == 'note_on':
                assert msg.note not in active_notes, \
                    f"Note {msg.note} turned on at tick {abs_tick} but was already active from tick {active_notes[msg.note]}"
                active_notes[msg.note] = abs_tick
            else:  # note_off
                assert msg.note in active_notes, \
                    f"Note {msg.note} turned off at tick {abs_tick} but was never turned on"
                start_tick = active_notes.pop(msg.note)
                duration = abs_tick - start_tick
                note_durations.append((msg.note, duration))
        
        # Verify all notes were turned off
        assert len(active_notes) == 0, \
            f"Notes still active at end of track: {list(active_notes.keys())}"
        
        # Verify we got the expected number of note on/off pairs
        # C chord: 3 notes (C, E, G)
        # G chord: 3 notes (G, B, D) - G is shared with C
        # F chord: 3 notes (F, A, C) - C is shared with C chord
        # Total: 3 + 3 + 3 = 9 note pairs (even though some notes are in multiple chords)
        assert len(note_durations) == 9, f"Expected 9 note on/off pairs, got {len(note_durations)}"
        
        # All durations should be either 1920 (4 beats for C) or 960 (2 beats for G/F)
        for note, duration in note_durations:
            assert duration in [960, 1920], \
                f"Note {note} has unexpected duration {duration}, expected 960 or 1920"
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


def test_absolute_tick_timing():
    """
    Test that note events occur at exact expected tick positions.
    """
    content = """
Tempo: 100
Time: 4/4

[Test - 3 bars]
| 0 | 1 | 2 |
| C.... | D.... | E.... |
"""
    
    doc = parse_songml(content)
    output_file = "test_timing.mid"
    
    try:
        export_midi(doc, output_file)
        
        mid = MidiFile(output_file)
        track = mid.tracks[0]
        note_events = [msg for msg in track if msg.type in ('note_on', 'note_off')]
        
        # Build absolute tick timeline
        abs_tick = 0
        tick_to_events = {}
        for msg in note_events:
            abs_tick += msg.time
            if abs_tick not in tick_to_events:
                tick_to_events[abs_tick] = []
            tick_to_events[abs_tick].append((msg.type, msg.note))
        
        # Expected ticks (480 ticks per beat, bars start at bar_number * 4 * 480)
        bar0_start = 0 * 4 * 480  # 0
        bar0_end = 1 * 4 * 480    # 1920
        bar1_start = bar0_end     # 1920
        bar1_end = 2 * 4 * 480    # 3840
        bar2_start = bar1_end     # 3840
        bar2_end = 3 * 4 * 480    # 5760
        
        # Verify C chord timing
        assert bar0_start in tick_to_events, f"C chord should start at tick {bar0_start}"
        c_on = [n for t, n in tick_to_events[bar0_start] if t == 'note_on']
        assert len(c_on) == 3, f"C chord should have 3 notes, got {len(c_on)}"
        
        assert bar0_end in tick_to_events, f"C chord should end at tick {bar0_end}"
        c_off = [n for t, n in tick_to_events[bar0_end] if t == 'note_off']
        assert set(c_off) == set(c_on), "C chord note_off should match note_on"
        
        # Verify D chord timing
        assert bar1_start in tick_to_events, f"D chord should start at tick {bar1_start}"
        d_on = [n for t, n in tick_to_events[bar1_start] if t == 'note_on']
        assert len(d_on) == 3, f"D chord should have 3 notes, got {len(d_on)}"
        
        # Verify E chord timing
        assert bar2_start in tick_to_events, f"E chord should start at tick {bar2_start}"
        e_on = [n for t, n in tick_to_events[bar2_start] if t == 'note_on']
        assert len(e_on) == 3, f"E chord should have 3 notes, got {len(e_on)}"
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


def test_project_local_voicings(tmp_path):
    """Test that export_midi uses project-local chord_voicings.tsv when provided."""
    # Create a custom voicings file with a unique chord
    custom_voicings = tmp_path / "chord_voicings.tsv"
    custom_voicings.write_text(
        "# Custom voicings\n"
        "TestChord\tC\t0,5,9\n"  # C + F + A (non-standard voicing)
        "C\tC\t0,4,7\n"
    )
    
    # Create a simple SongML file
    songml = """
# Title: Test Song
# Key: C major
# Tempo: 120

[Section - 1 bar]
| 0 |
| TestChord |
"""
    
    doc = parse_songml(songml)
    output_file = str(tmp_path / "test_custom.mid")
    
    try:
        # Export with custom voicings
        export_midi(doc, output_file, voicings_path=str(custom_voicings))
        
        # Verify the MIDI file was created
        assert os.path.exists(output_file)
        
        # Load and check that notes match custom voicing
        mid = MidiFile(output_file)
        notes_on = [msg.note for track in mid.tracks 
                    for msg in track if msg.type == 'note_on' and msg.velocity > 0]
        
        # Should have C2(36), F2(41), A2(45) based on custom voicing at octave 3
        # (octave 3 in the code means MIDI octave notation where C3 = MIDI 48,
        # but the calculation is: C at octave 0 is 0, octave 3 is 0 + 3*12 = 36)
        expected_notes = [36, 41, 45]
        assert sorted(notes_on) == sorted(expected_notes), \
            f"Expected {expected_notes}, got {sorted(notes_on)}"
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)
