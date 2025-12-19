"""Tests for ABC exporter."""

import os

import pytest

from songml_utils.abc_exporter import (
    _beats_to_abc_units,
    _extract_properties,
    _format_bar_chords,
    _normalize_key,
    _parse_time_signature,
    export_abc,
    to_abc_string,
)
from songml_utils.ast import Bar, ChordToken
from songml_utils.parser import parse_songml


def test_extract_properties_with_defaults():
    """Test property extraction uses defaults when properties absent."""
    content = """
[Intro - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)
    props = _extract_properties(doc)

    assert props["Title"] == "Untitled"
    assert props["Key"] == "C"
    assert props["Tempo"] == "120"
    assert props["Time"] == "4/4"


def test_extract_properties_with_values():
    """Test property extraction from document."""
    content = """
Title: My Song
Key: Fmaj
Tempo: 104
Time: 3/4

[Intro - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)
    props = _extract_properties(doc)

    assert props["Title"] == "My Song"
    assert props["Key"] == "Fmaj"
    assert props["Tempo"] == "104"
    assert props["Time"] == "3/4"


def test_normalize_key_major():
    """Test key normalization for major keys."""
    assert _normalize_key("Cmaj") == "C"
    assert _normalize_key("Fmaj") == "F"
    assert _normalize_key("C major") == "C"
    assert _normalize_key("C") == "C"


def test_normalize_key_minor():
    """Test key normalization for minor keys."""
    assert _normalize_key("Dm") == "Dm"
    assert _normalize_key("Dmin") == "Dm"
    assert _normalize_key("D minor") == "Dm"
    assert _normalize_key("Am") == "Am"


def test_parse_time_signature():
    """Test time signature parsing."""
    assert _parse_time_signature("4/4") == (4, 4)
    assert _parse_time_signature("3/4") == (3, 4)
    assert _parse_time_signature("6/8") == (6, 8)

    with pytest.raises(ValueError):
        _parse_time_signature("invalid")

    with pytest.raises(ValueError):
        _parse_time_signature("4-4")


def test_beats_to_abc_units_4_4_time():
    """Test beat conversion for 4/4 time (L:1/8)."""
    # In 4/4, denominator=4, L:1/8
    # 1 beat = 2 units, 0.5 beat = 1 unit
    assert _beats_to_abc_units(1.0, 4) == 2
    assert _beats_to_abc_units(0.5, 4) == 1
    assert _beats_to_abc_units(2.0, 4) == 4
    assert _beats_to_abc_units(4.0, 4) == 8


def test_beats_to_abc_units_3_4_time():
    """Test beat conversion for 3/4 time (L:1/8)."""
    # Same as 4/4: denominator=4, L:1/8
    assert _beats_to_abc_units(1.0, 4) == 2
    assert _beats_to_abc_units(0.5, 4) == 1
    assert _beats_to_abc_units(3.0, 4) == 6


def test_beats_to_abc_units_6_8_time():
    """Test beat conversion for 6/8 time (L:1/16)."""
    # In 6/8, denominator=8, L:1/16
    # 1 beat = 4 units, 0.5 beat = 2 units
    assert _beats_to_abc_units(1.0, 8) == 4
    assert _beats_to_abc_units(0.5, 8) == 2
    assert _beats_to_abc_units(6.0, 8) == 24


def test_format_bar_chords_single_chord():
    """Test formatting a bar with a single chord."""
    chord = ChordToken(text="C", start_beat=0.0, duration_beats=4.0)
    bar = Bar(number=0, chords=[chord])

    result = _format_bar_chords(bar, beats_per_bar=4, denominator=4)
    # 4 beats = 8 units in 4/4 time
    # C chord top note is G (MIDI 67)
    assert result == '"C"G8'


def test_format_bar_chords_multiple_chords():
    """Test formatting a bar with multiple chords."""
    chords = [
        ChordToken(text="C", start_beat=0.0, duration_beats=2.0),
        ChordToken(text="F", start_beat=2.0, duration_beats=2.0),
    ]
    bar = Bar(number=0, chords=chords)

    result = _format_bar_chords(bar, beats_per_bar=4, denominator=4)
    # 2 beats each = 4 units each
    # C chord top note is G (MIDI 67), F chord top note is c' (MIDI 72)
    assert result == '"C"G4 "F"c\'4'


def test_format_bar_chords_empty_bar():
    """Test formatting an empty bar (no chords)."""
    bar = Bar(number=0, chords=[])

    result = _format_bar_chords(bar, beats_per_bar=4, denominator=4)
    # 4 beats = 8 units
    assert result == "z8"


def test_format_bar_chords_half_beat():
    """Test formatting with half-beat duration."""
    chord = ChordToken(text="F", start_beat=3.5, duration_beats=0.5)
    bar = Bar(number=0, chords=[chord])

    result = _format_bar_chords(bar, beats_per_bar=4, denominator=4)
    # 0.5 beats = 1 unit
    # F chord top note is c' (MIDI 72)
    assert result == '"F"c\'1'


def test_simple_4_4_progression():
    """Test simple 4/4 chord progression export."""
    content = """
Title: Simple Song
Key: Cmaj
Tempo: 120
Time: 4/4

[Verse - 2 bars]
| 0 | 1 |
| C | F |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    assert "X: 1" in abc
    assert "T: Simple Song" in abc
    assert "M: 4/4" in abc
    assert "L: 1/8" in abc
    assert "Q: 1/4=120" in abc
    assert "K: C" in abc
    assert "P:Verse" in abc
    # C chord top note is G, F chord top note is c'
    assert '"C"G8' in abc
    assert '"F"c\'8' in abc


def test_3_4_time_signature():
    """Test 3/4 time signature and L: computation."""
    content = """
Time: 3/4

[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    assert "M: 3/4" in abc
    assert "L: 1/8" in abc  # denominator=4 → L:1/8
    # C chord top note is G (MIDI 67)
    assert '"C"G6' in abc  # 3 beats = 6 units


def test_6_8_time_signature():
    """Test 6/8 time signature and L: computation."""
    content = """
Time: 6/8

[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    assert "M: 6/8" in abc
    assert "L: 1/16" in abc  # denominator=8 → L:1/16
    # C chord top note is G (MIDI 67)
    assert '"C"G24' in abc  # 6 beats = 24 units


def test_explicit_dot_timing():
    """Test explicit timing with dots."""
    content = """
Time: 4/4

[Verse - 1 bars]
| 0 |
| C.. F.. |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    # C lasts 2 beats = 4 units, F lasts 2 beats = 4 units
    # C chord top note is G, F chord top note is c'
    assert '"C"G4 "F"c\'4' in abc


def test_semicolon_half_beat_timing():
    """Test semicolon half-beat timing."""
    content = """
Time: 4/4

[Intro - 1 bars]
| 0 |
| ...;F |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    # F starts at beat 3.5, lasts 0.5 beats = 1 unit
    # F chord top note is c' (MIDI 72)
    assert '"F"c\'1' in abc


def test_lyrics_alignment():
    """Test lyrics in ABC output."""
    content = """
Time: 4/4

[Verse - 2 bars]
| 0 | 1 |
| C | F G |
| Hello | wonderful world |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    # Check lyrics line is present
    assert "w:" in abc
    assert "Hello" in abc
    assert "wonderful" in abc or "world" in abc


def test_slash_chord_passthrough():
    """Test that slash chords are passed through as-is."""
    content = """
[Verse - 1 bars]
| 0 |
| C7/G |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    # Chord should appear as-is in ABC
    assert '"C7/G"' in abc


def test_unknown_chord_passthrough():
    """Test that unknown chord symbols are passed through."""
    content = """
[Verse - 1 bars]
| 0 |
| Xweird |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    # Unknown chord should still appear in ABC
    assert '"Xweird"' in abc


def test_empty_synthesized_bars():
    """Test that empty/synthesized bars produce rests."""
    content = """
[Verse - 3 bars]
| 0 | 1 | 2 |
| C | F | G |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    # Should have 3 bars total in output (4 pipe symbols for 3 bars: | bar1 | bar2 | bar3 |)
    assert abc.count("|") >= 4
    assert '"C"' in abc
    assert '"F"' in abc
    assert '"G"' in abc


def test_multiple_sections():
    """Test multiple sections with part markers."""
    content = """
[Verse - 1 bars]
| 0 |
| C |

[Chorus - 1 bars]
| 0 |
| F |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc)

    assert "P:Verse" in abc
    assert "P:Chorus" in abc


def test_export_abc_to_file(tmp_path):
    """Test exporting to a file."""
    content = """
Title: Test Export
[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)

    output_path = tmp_path / "output.abc"
    export_abc(doc, str(output_path))

    assert output_path.exists()

    with open(output_path, encoding="utf-8") as f:
        abc_content = f.read()

    assert "T: Test Export" in abc_content
    assert '"C"' in abc_content


def test_unit_length_override():
    """Test overriding unit note length."""
    content = """
Time: 4/4

[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)
    abc = to_abc_string(doc, unit_note_length="1/16")

    assert "L: 1/16" in abc


def test_integration_youve_got_a_way():
    """Integration test using real sample file."""
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "youve-got-a-way.songml"
    )

    if not os.path.exists(sample_path):
        pytest.skip("Sample file not found")

    with open(sample_path, encoding="utf-8") as f:
        content = f.read()

    doc = parse_songml(content)
    abc = to_abc_string(doc)

    # Basic structure checks
    assert "X: 1" in abc
    assert "T: You've got a way" in abc or "T: You've got a way" in abc
    assert "K: F" in abc
    assert "M: 4/4" in abc
    assert "L: 1/8" in abc
    assert "Q: 1/4=104" in abc

    # Check sections are present
    assert "P:Intro" in abc
    assert "P:Verse 1" in abc or "P:Verse" in abc

    # Check some chords are present
    assert '"F' in abc  # Some F chord variant
    assert "|" in abc  # Bar lines


def test_no_sections_error():
    """Test that document with no sections raises error."""
    content = """
Title: No Content
"""
    doc = parse_songml(content)

    with pytest.raises(ValueError) as exc_info:
        to_abc_string(doc)
    assert "No musical content" in str(exc_info.value)


def test_unsupported_chord_style():
    """Test that unsupported chord style raises error."""
    content = """
[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)

    with pytest.raises(ValueError) as exc_info:
        to_abc_string(doc, chord_style="voice")
    assert "Unsupported chord_style" in str(exc_info.value)
