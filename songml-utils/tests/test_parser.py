"""Tests for SongML parser."""

import pytest

from songml_utils.ast import ParseError, Property, Section, TextBlock
from songml_utils.parser import parse_songml


def test_property_defaults():
    """Test that parser uses defaults when properties not specified."""
    content = """
[Intro - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)

    # Properties should have defaults even if not in document
    sections = [item for item in doc.items if isinstance(item, Section)]
    assert len(sections) == 1
    assert sections[0].bars[0].chords[0].duration_beats == 4.0  # 4/4 time default


def test_property_parsing_and_state():
    """Test property parsing and state persistence."""
    content = """
Title: Test Song
Key: Cmaj
Tempo: 120
Time: 4/4

[Verse - 2 bars]
| 0 | 1 |
| C | F |

Key: Gmaj

[Chorus - 2 bars]
| 2 | 3 |
| G | D |
"""
    doc = parse_songml(content)

    # Check properties
    props = [item for item in doc.items if isinstance(item, Property)]
    assert len(props) == 5
    assert props[0].name == "Title"
    assert props[0].value == "Test Song"

    # Check sections
    sections = [item for item in doc.items if isinstance(item, Section)]
    assert len(sections) == 2


def test_section_header_parsing():
    """Test section header parsing with bar count."""
    content = """
[Intro - 4 bars]
| 0 | 1 | 2 | 3 |
| C | F | G | C |
"""
    doc = parse_songml(content)

    sections = [item for item in doc.items if isinstance(item, Section)]
    assert len(sections) == 1
    assert sections[0].name == "Intro"
    assert sections[0].bar_count == 4
    assert len(sections[0].bars) == 4


def test_section_header_same_row_modifier():
    """Test that a ', same-row' modifier sets Section.same_row and is case-insensitive."""
    content = """
[Intro - 4 bars]
| 1 | 2 | 3 | 4 |
| C | F | G | C |

[Verse - 4 bars, Same-Row]
| 5 | 6 | 7 | 8 |
| C | F | G | C |
"""
    doc = parse_songml(content)

    sections = [item for item in doc.items if isinstance(item, Section)]
    assert sections[0].same_row is False
    assert sections[1].same_row is True
    assert doc.warnings == []


def test_section_header_unknown_modifier_warns():
    """Test that an unrecognized modifier is ignored but produces a warning."""
    content = """
[Intro - 4 bars, bogus]
| 0 | 1 | 2 | 3 |
| C | F | G | C |
"""
    doc = parse_songml(content)

    sections = [item for item in doc.items if isinstance(item, Section)]
    assert sections[0].same_row is False
    assert any("Unknown section modifier" in w for w in doc.warnings)


def test_section_header_missing_bar_count():
    """Test that section without bar count raises ParseError."""
    content = """
[Intro]
| 0 |
| C |
"""
    # Section header without bar count should raise ParseError
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "must declare bar count" in str(exc_info.value)
    assert "[Section Name - N bars]" in str(exc_info.value)


def test_invalid_section_headers():
    """Test various invalid section header formats all raise ParseError."""
    test_cases = [
        ("[Intro]", "simple section without bar count"),
        ("[Verse 1]", "section with number but no bar count"),
        ("[Chorus - complex name]", "section with dash but no bar count"),
        ("[Bridge - 8]", "section with number but missing 'bars' keyword"),
        ("[Outro - bars]", "section with 'bars' but no number"),
    ]

    for header, description in test_cases:
        content = f"""
Title: Test Song
{header}
| C | F | G | C |
"""
        with pytest.raises(ParseError) as exc_info:
            parse_songml(content)

        error_msg = str(exc_info.value)
        assert "must declare bar count" in error_msg, f"Failed for {description}: {header}"
        assert "[Section Name - N bars]" in error_msg, f"Failed for {description}: {header}"


def test_bar_number_detection_and_validation():
    """Test bar number row detection and sequential validation."""
    content = """
[Verse - 3 bars]
| 0 | 1 | 2 |
| C | F | G |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    assert section.bars[0].number == 0
    assert section.bars[1].number == 1
    assert section.bars[2].number == 2


def test_bar_number_auto_increment():
    """Test bar number auto-increment for empty cells."""
    content = """
[Verse - 3 bars]
| 0 | | 2 |
| C | F | G |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    assert section.bars[0].number == 0
    assert section.bars[1].number == 1
    assert section.bars[2].number == 2


def test_bar_number_gap_error():
    """Test that gaps in bar numbers raise error."""
    content = """
[Verse - 2 bars]
| 0 | 2 |
| C | F |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "gap" in str(exc_info.value).lower()


def test_bar_number_first_cell_required():
    """Test that first cell in bar-number row must have digit."""
    content = """
[Verse - 2 bars]
| | 1 |
| C | F |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "first cell" in str(exc_info.value).lower()


def test_delimiter_count_matching():
    """Test that bar-number, chord, and lyric rows have matching delimiter counts."""
    content = """
[Verse - 2 bars]
| 0 | 1 |
| C | F | G |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "chord row has" in str(exc_info.value).lower()


def test_lyrics_optional():
    """Test that lyric rows are optional."""
    content = """
[Verse - 2 bars]
| 0 | 1 |
| C | F |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    assert section.bars[0].lyrics is None
    assert section.bars[1].lyrics is None


def test_lyrics_present():
    """Test parsing with lyric rows."""
    content = """
[Verse - 2 bars]
| 0 | 1 |
| C | F |
| Hello | world |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    assert section.bars[0].lyrics == "Hello"
    assert section.bars[1].lyrics == "world"


def test_explicit_timing_dots():
    """Test explicit timing with dots."""
    content = """
[Verse - 1 bars]
| 0 |
| C.. F.. |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    chords = section.bars[0].chords
    assert len(chords) == 2
    assert chords[0].text == "C"
    assert chords[0].start_beat == 0.0
    assert chords[0].duration_beats == 2.0
    assert chords[1].text == "F"
    assert chords[1].start_beat == 2.0
    assert chords[1].duration_beats == 2.0


def test_half_beat_timing_semicolon():
    """Test half-beat timing with semicolon suffix."""
    content = """
[Intro - 1 bars]
| 0 |
| ...;F |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    chords = section.bars[0].chords
    assert len(chords) == 1
    assert chords[0].text == "F"
    assert chords[0].start_beat == 3.5
    assert chords[0].duration_beats == 0.5


def test_half_beat_on_beat_one():
    """Test semicolon on beat one (;F)."""
    content = """
[Intro - 1 bars]
| 0 |
| ;F G.. |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    chords = section.bars[0].chords
    assert chords[0].text == "F"
    assert chords[0].start_beat == 0.5
    assert chords[1].text == "G"
    assert chords[1].start_beat == 1.5


def test_implicit_timing_last_chord_fills():
    """Test implicit timing with last-chord-fills in 4/4."""
    content = """
[Verse - 1 bars]
| 0 |
| C F G |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    chords = section.bars[0].chords
    assert len(chords) == 3
    assert chords[0].text == "C"
    assert chords[0].duration_beats == 1.0
    assert chords[1].text == "F"
    assert chords[1].duration_beats == 1.0
    assert chords[2].text == "G"
    assert chords[2].duration_beats == 2.0  # Fills remaining


def test_implicit_timing_3_4_time():
    """Test implicit timing in 3/4 time."""
    content = """
Time: 3/4

[Verse - 1 bars]
| 0 |
| C F G |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    chords = section.bars[0].chords
    assert chords[0].duration_beats == 1.0
    assert chords[1].duration_beats == 1.0
    assert chords[2].duration_beats == 1.0  # All equal in 3/4


def test_implicit_timing_6_8_time():
    """Test implicit timing in 6/8 time (6 beats)."""
    content = """
Time: 6/8

[Verse - 1 bars]
| 0 |
| C F G |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    chords = section.bars[0].chords
    assert chords[0].duration_beats == 1.0
    assert chords[1].duration_beats == 1.0
    assert chords[2].duration_beats == 4.0  # Fills remaining (6 - 2)


def test_empty_bars_in_chords():
    """Test that empty chord cells create bars with no chords."""
    content = """
[Verse - 2 bars]
| 0 | 1 |
| C | |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    assert len(section.bars[0].chords) == 1
    assert len(section.bars[1].chords) == 0


def test_bar_synthesis():
    """Test that parser synthesizes empty bars when declared count > parsed."""
    content = """
[Verse - 8 bars]
| 0 | 1 | 2 |
| C | F | G |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    assert len(section.bars) == 8
    # First 3 have chords
    assert len(section.bars[0].chords) == 1
    assert len(section.bars[1].chords) == 1
    assert len(section.bars[2].chords) == 1
    # Remaining 5 are empty (synthesized)
    for i in range(3, 8):
        assert len(section.bars[i].chords) == 0
        assert section.bars[i].number == i


def test_too_many_bars_error():
    """Test that parser raises error when parsed bars > declared count."""
    content = """
[Verse - 2 bars]
| 0 | 1 | 2 |
| C | F | G |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "declares 2 bars but has 3" in str(exc_info.value)


def test_empty_section_error():
    """Test that section without bars raises error."""
    content = """
[Verse - 4 bars]

[Chorus - 2 bars]
| 0 | 1 |
| C | F |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "has no bars" in str(exc_info.value).lower()


def test_duplicate_section_warning():
    """Test that duplicate section names generate warnings."""
    content = """
[Verse - 2 bars]
| 1 | 2 |
| C | F |

[Verse - 2 bars]
| 3 | 4 |
| G | Am |
"""
    doc = parse_songml(content)

    # Should warn about duplicate section name
    assert len(doc.warnings) == 1
    assert "Duplicate section name" in doc.warnings[0]
    assert "Verse" in doc.warnings[0]


def test_invalid_time_signature_denominator():
    """Test that invalid time signature denominator raises error."""
    content = """
Time: 5/7

[Verse - 1 bars]
| 0 |
| C |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "denominator must be 4 or 8" in str(exc_info.value).lower()


def test_beat_overflow_error():
    """Test that beat overflow before last chord raises error."""
    content = """
[Verse - 1 bars]
| 0 |
| C.... D F |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "overflow" in str(exc_info.value).lower()


def test_chord_dot_chord_without_space_error():
    """Test that two chords glued together by dots (no space) raises an error."""
    content = """
[Verse - 1 bars]
| 0 |
| Am7..Am7/C |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "Am7..Am7/C" in str(exc_info.value)
    assert "whitespace" in str(exc_info.value).lower()


def test_chord_root_case_is_repaired():
    """Test that a lowercase chord root and bass note are uppercased (case carries no meaning)."""
    content = """
[Verse - 1 bars]
| 0 |
| em7 g d/f# /a |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    chords = section.bars[0].chords
    assert chords[0].text == "Em7"
    assert chords[1].text == "G"
    assert chords[2].text == "D/F#"
    assert chords[3].text == "/A"


def test_multi_group_flattening():
    """Test that multiple row groups flatten into single bar sequence."""
    content = """
[Verse - 6 bars]
| 0 | 1 | 2 |
| C | F | G |
| She | sells | sea |

| 3 | 4 | 5 |
| Dm | Am | G |
| shells | by | shore |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    assert len(section.bars) == 6
    assert section.bars[0].number == 0
    assert section.bars[3].number == 3
    assert section.bars[0].lyrics == "She"
    assert section.bars[3].lyrics == "shells"


def test_property_terminates_section():
    """Test that property line terminates current section."""
    content = """
[Verse - 2 bars]
| 0 | 1 |
| C | F |

Key: Gmaj

[Chorus - 2 bars]
| 2 | 3 |
| G | D |
"""
    doc = parse_songml(content)

    sections = [item for item in doc.items if isinstance(item, Section)]
    assert len(sections) == 2
    props = [item for item in doc.items if isinstance(item, Property)]
    assert any(p.name == "Key" and p.value == "Gmaj" for p in props)


def test_text_blocks():
    """Test that free text is captured in TextBlock nodes."""
    content = """
This is some free text.
// A comment

Title: Test

More text here.

[Verse - 1 bars]
| 0 |
| C |
"""
    doc = parse_songml(content)

    text_blocks = [item for item in doc.items if isinstance(item, TextBlock)]
    assert len(text_blocks) >= 1


def test_commented_out_row_with_pipes_is_ignored():
    """A '#'-prefixed line containing '|' must never be parsed as a bar row."""
    content = """
[Verse 1 - 1 bars]
| 0 |
| C |
| Punch on in |

#| Smile when it hurts and frown it don't | keep em guessin |
"""
    doc = parse_songml(content)

    sections = [item for item in doc.items if isinstance(item, Section)]
    assert len(sections) == 1
    assert len(sections[0].bars) == 1


def test_commented_out_row_with_double_slash_is_ignored():
    """A '//'-prefixed line containing '|' must never be parsed as a bar row."""
    content = """
[Verse 1 - 1 bars]
| 0 |
| C |

// | draft lyric | another draft |
"""
    doc = parse_songml(content)

    sections = [item for item in doc.items if isinstance(item, Section)]
    assert len(sections) == 1
    assert len(sections[0].bars) == 1


def test_commented_line_immediately_after_chord_row_is_not_a_lyric_row():
    """A comment directly following the chord row must not be mistaken for
    (and validated as) the optional lyric row."""
    content = """
[Verse 1 - 1 bars]
| 0 |
| C |
#| this comment has | two cells, not one |
"""
    doc = parse_songml(content)

    sections = [item for item in doc.items if isinstance(item, Section)]
    assert len(sections) == 1
    assert len(sections[0].bars) == 1
    assert sections[0].bars[0].lyrics is None


def test_commented_line_immediately_after_bar_number_row_is_not_a_chord_row():
    """A comment directly following the bar-number row must not be mistaken
    for the required chord row."""
    content = """
[Verse 1 - 1 bars]
| 0 |
#| a comment, not chords |
| C |
"""
    doc = parse_songml(content)

    sections = [item for item in doc.items if isinstance(item, Section)]
    assert len(sections) == 1
    assert sections[0].bars[0].chords[0].text == "C"


def test_opaque_chord_text():
    """Test that parser treats chords as opaque text (doesn't validate symbols)."""
    content = """
[Verse - 1 bars]
| 0 |
| XYZ123 /F# Cmaj9#11 |
"""
    doc = parse_songml(content)

    section = [item for item in doc.items if isinstance(item, Section)][0]
    chords = section.bars[0].chords
    assert chords[0].text == "XYZ123"
    assert chords[1].text == "/F#"
    assert chords[2].text == "Cmaj9#11"


def test_youve_got_a_way_sample():
    """Test parsing the real sample file youve-got-a-way.songml."""
    import os

    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "youve-got-a-way.songml"
    )

    if not os.path.exists(sample_path):
        pytest.skip(f"Sample file not found: {sample_path}")

    with open(sample_path, encoding="utf-8") as f:
        content = f.read()

    doc = parse_songml(content)

    # Check basic structure
    sections = [item for item in doc.items if isinstance(item, Section)]
    # All sections now have bar counts and should be parsed correctly
    assert len(sections) == 6  # Intro, Verse 1, Verse 2, Chorus, Bridge, Return

    props = [item for item in doc.items if isinstance(item, Property)]
    title_props = [p for p in props if p.name == "Title"]
    assert len(title_props) == 1
    assert "way" in title_props[0].value.lower()

    # Check first section (Intro, which now has proper bar count)
    intro = sections[0]
    assert intro.name == "Intro"
    assert intro.bar_count == 5

    # Check second section (Verse 1)
    verse1 = sections[1]
    assert verse1.name == "Verse 1"
    assert verse1.bar_count == 12
    assert len(verse1.bars) == 12


def test_section_closes_when_bar_count_met():
    """A section ends the moment its declared bar count is reached; a following
    valid header starts a new section even with no blank line between them."""
    content = """
[V1 - 4 bars]
| 0 | 1 | 2 | 3 |
| C | F | G | C |
[V2 - 4 bars, same-row]
| 4 | 5 | 6 | 7 |
| C | F | G | C |
"""
    doc = parse_songml(content)
    sections = [item for item in doc.items if isinstance(item, Section)]
    assert [s.name for s in sections] == ["V1", "V2"]
    assert all(len(s.bars) == 4 for s in sections)
    assert sections[1].same_row is True


def test_mistyped_header_after_completed_section_is_not_swallowed():
    """A bracketed line that fails header parsing (here: missing the '-') must
    raise, not be skipped so the next section's rows bleed into this one.

    This is the blackened-blue.songml failure: '[V2b.2 4 bars, same-row]' with
    no dash was silently dropped, and V2b.1 ended up with 8 bars instead of 4.
    """
    content = """
[V1 - 4 bars]
| 0 | 1 | 2 | 3 |
| C | F | G | C |
[V2 4 bars, same-row]
| 4 | 5 | 6 | 7 |
| C | F | G | C |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "must declare bar count" in str(exc_info.value)
    assert exc_info.value.line_number == 5  # the mistyped header, not the V1 header


def test_mistyped_header_while_previous_section_under_count():
    """Same, but the previous section hasn't met its bar count yet, so the bad
    header is seen from inside section-content parsing."""
    content = """
[V1 - 8 bars]
| 0 | 1 |
| C | F |
[V2 4 bars]
| 2 | 3 | 4 | 5 |
| C | F | G | C |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "must declare bar count" in str(exc_info.value)
    assert exc_info.value.line_number == 5


def test_stray_text_inside_section_body_raises():
    """Non-blank, non-comment text inside a section body (before the bar count
    is met) is a ParseError - use a comment for notes in the song body."""
    content = """
[V1 - 8 bars]
| 0 | 1 |
| C | F |
TODO fix this bridge
| 2 | 3 |
| G | C |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "Unexpected text inside section" in str(exc_info.value)
    assert exc_info.value.line_number == 5


def test_comment_inside_section_body_still_allowed():
    """A '#' or '//' line inside a section body is fine and does not split it."""
    content = """
[V1 - 4 bars]
| 0 | 1 |
| C | F |
# second half
// still going
| 2 | 3 |
| G | C |
"""
    doc = parse_songml(content)
    section = next(item for item in doc.items if isinstance(item, Section))
    assert len(section.bars) == 4


def test_extra_bar_row_after_full_section_raises():
    """Bars split across groups that overshoot the declared count are rejected,
    not silently dropped (early-close leaves the extra row at the top level)."""
    content = """
[V1 - 2 bars]
| 0 | 1 |
| C | F |
| 2 | 3 |
| G | C |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "already has its declared 2 bars" in str(exc_info.value)
    assert exc_info.value.line_number == 5


def test_bar_row_before_any_section_raises():
    """A bar row with no section header above it anywhere is a ParseError."""
    content = """
Title: Test
| 0 | 1 |
| C | F |
"""
    with pytest.raises(ParseError) as exc_info:
        parse_songml(content)
    assert "outside any section" in str(exc_info.value)


def test_free_text_before_first_section_still_allowed():
    """Free-form notes outside section bodies remain legal (spec section 2)."""
    content = """
Some notes about the arrangement.
TODO: rework the bridge

Title: Test
[V1 - 2 bars]
| 0 | 1 |
| C | F |
"""
    doc = parse_songml(content)
    text_blocks = [item for item in doc.items if isinstance(item, TextBlock)]
    assert any("notes about the arrangement" in "".join(tb.lines) for tb in text_blocks)
