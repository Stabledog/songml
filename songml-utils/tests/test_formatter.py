"""Tests for SongML formatter."""

from songml_utils.formatter import (
    BarGroup,
    BarLine,
    TextBlock,
    align_bar_group,
    calculate_column_widths,
    detect_bar_line,
    format_songml,
    group_bar_lines,
    pad_cell,
    split_bar_line,
)


def test_detect_bar_line():
    """Test detection of lines containing bar markers."""
    assert detect_bar_line("| F | G |") is True
    assert detect_bar_line("| 1 | 2 | 3 |") is True
    assert detect_bar_line("Title: My Song") is False
    assert detect_bar_line("[Verse - 4 bars]") is False
    assert detect_bar_line("") is False


def test_split_bar_line():
    """Test splitting lines by bar markers."""
    assert split_bar_line("| F | G |") == ["", " F ", " G ", ""]
    assert split_bar_line("| 1 | 2 | 3 |") == ["", " 1 ", " 2 ", " 3 ", ""]
    assert split_bar_line("|F|G|") == ["", "F", "G", ""]
    # Preserve empty cells
    assert split_bar_line("| | |") == ["", " ", " ", ""]


def test_pad_cell():
    """Test padding cells to target width."""
    # Basic padding
    assert pad_cell(" F ", 10) == " F        "
    assert pad_cell("Am7", 8) == "Am7     "

    # Already at or beyond target width
    assert pad_cell("Very long content", 5) == "Very long content"
    assert pad_cell("Exact", 5) == "Exact"

    # Preserve internal spacing exactly
    assert pad_cell(" F.. G7sus ", 20) == " F.. G7sus          "
    assert pad_cell(" F . . G7sus ", 20) == " F . . G7sus        "
    # These are different and must stay different
    assert pad_cell(" F.. ", 10) != pad_cell(" F . . ", 10)


def test_calculate_column_widths_basic():
    """Test basic column width calculation."""
    lines = [
        BarLine("", ["", " F ", " G ", ""], 0),
        BarLine("", ["", " Am ", " Bm ", ""], 1),
    ]
    group = BarGroup(lines=lines, start_line=0, end_line=1)

    widths = calculate_column_widths(group)
    assert len(widths) == 4
    # Cells have lengths: ["", " F ", " G ", ""] and ["", " Am ", " Bm ", ""]
    assert widths[0] == 0  # Empty start
    assert widths[1] == 4  # " Am " is longer than " F "
    assert widths[2] == 4  # " Bm " is longer than " G "
    assert widths[3] == 0  # Empty end


def test_calculate_column_widths_lyrics_priority():
    """Test that column width calculation handles all content."""
    lines = [
        BarLine("", ["", " F ", " Am ", ""], 0),
        BarLine("", ["", " You've got a way ", " I just knew ", ""], 1),
    ]
    group = BarGroup(lines=lines, start_line=0, end_line=1)

    widths = calculate_column_widths(group)
    # Longer content determines width
    assert widths[1] == 18  # " You've got a way "
    assert widths[2] == 13  # " I just knew "


def test_calculate_column_widths_uneven():
    """Test width calculation with uneven column counts."""
    lines = [
        BarLine("", ["", " F ", " G ", " Am ", ""], 0),
        BarLine("", ["", " You've got a way ", ""], 1),
    ]
    group = BarGroup(lines=lines, start_line=0, end_line=1)

    widths = calculate_column_widths(group)
    assert len(widths) == 5  # Max columns
    assert widths[1] == 18  # Longest content wins


def test_align_bar_group_basic():
    """Test basic bar group alignment."""
    lines = [
        BarLine("", ["", " F ", " G ", ""], 0),
        BarLine("", ["", " Am ", " Bm ", ""], 1),
    ]
    group = BarGroup(lines=lines, start_line=0, end_line=1)
    widths = [0, 4, 4, 0]

    aligned = align_bar_group(group, widths)

    assert len(aligned) == 2
    # Check vertical alignment of | markers
    assert aligned[0] == "| F  | G  |"
    assert aligned[1] == "| Am | Bm |"


def test_align_bar_group_preserves_content():
    """Test that alignment preserves cell content exactly."""
    lines = [
        BarLine("", ["", " F.. G7sus ", " Am ", ""], 0),
        BarLine("", ["", " Dm ", " Bm7 ", ""], 1),
    ]
    group = BarGroup(lines=lines, start_line=0, end_line=1)
    widths = [0, 12, 6, 0]

    aligned = align_bar_group(group, widths)

    # Ensure F.. G7sus is NOT changed to F . . G7sus or similar
    assert " F.. G7sus " in aligned[0]
    # Check the alignment (cell is padded to width 12)
    assert aligned[0] == "| F.. G7sus  | Am   |"
    assert aligned[1] == "| Dm         | Bm7  |"


def test_group_bar_lines_basic():
    """Test grouping consecutive bar lines."""
    lines = [
        "Title: My Song",
        "",
        "[Verse - 2 bars]",
        "| 1 | 2 |",
        "| F | G |",
        "",
        "Some text",
    ]

    blocks = group_bar_lines(lines)

    assert len(blocks) == 3
    # First block: text (Title, blank, section header)
    assert isinstance(blocks[0], TextBlock)
    assert len(blocks[0].content) == 3

    # Second block: bar group
    assert isinstance(blocks[1], BarGroup)
    assert len(blocks[1].lines) == 2

    # Third block: text (blank, "Some text")
    assert isinstance(blocks[2], TextBlock)
    assert len(blocks[2].content) == 2


def test_group_bar_lines_multiple_groups():
    """Test grouping multiple separate bar groups."""
    lines = [
        "Title: Song",
        "| 1 | 2 |",
        "| F | G |",
        "",
        "[Bridge]",
        "| 3 | 4 |",
        "| Am | Dm |",
    ]

    blocks = group_bar_lines(lines)

    # Should have: text, bar_group, text, bar_group
    assert len(blocks) == 4
    assert isinstance(blocks[0], TextBlock)  # Title
    assert isinstance(blocks[1], BarGroup)  # First bars
    assert isinstance(blocks[2], TextBlock)  # Blank + section
    assert isinstance(blocks[3], BarGroup)  # Second bars


def test_format_songml_basic():
    """Test basic formatting of SongML content."""
    content = """Title: Test Song

[Verse - 2 bars]
| 1 | 2 |
| F | G |
| You | Me |"""

    formatted = format_songml(content)
    lines = formatted.split("\n")

    # Title should be preserved
    assert lines[0] == "Title: Test Song"
    # Empty line preserved
    assert lines[1] == ""
    # Section header preserved
    assert lines[2] == "[Verse - 2 bars]"
    # Bar lines should be aligned
    assert lines[3] == "| 1   | 2  |"
    assert lines[4] == "| F   | G  |"
    assert lines[5] == "| You | Me |"


def test_format_songml_preserves_cell_content():
    """Test that formatting preserves cell content exactly."""
    content = """[Verse]
| F.. G7sus | Am |
| Dm | Bm7 |"""

    formatted = format_songml(content)
    lines = formatted.split("\n")

    # Check that F.. G7sus is preserved exactly (not changed to F . . G7sus)
    assert " F.. G7sus " in lines[1]
    # Check alignment
    assert lines[1] == "| F.. G7sus | Am  |"
    assert lines[2] == "| Dm        | Bm7 |"


def test_format_songml_empty_cells():
    """Test handling of empty cells."""
    content = """[Verse]
| F |  | Am |
| Dm | G | Bm |"""

    formatted = format_songml(content)
    lines = formatted.split("\n")

    # Empty cells should be preserved with proper spacing
    assert lines[1] == "| F  |   | Am |"
    assert lines[2] == "| Dm | G | Bm |"


def test_format_songml_uneven_columns():
    """Test handling of lines with different column counts."""
    content = """[Verse]
| F | G | Am | Dm |
| You | Me |"""

    formatted = format_songml(content)
    lines = formatted.split("\n")

    # Should handle gracefully - no crash
    assert len(lines) == 3
    assert lines[1].startswith("|")
    assert lines[2].startswith("|")


def test_format_songml_real_world_example():
    """Test with a realistic example similar to youve-got-a-way.songml."""
    content = """Title: Test Song
Key: Fmaj

[Verse 1 - 4 bars]
|      1                           |                 2                    |
| F..               F9/A  Abdim7/B | Am7/E              A+7/C#            |
| You've got a way                 | I just knew how to follow but it was |

| 3      | 4                     |
| Dm  Fm6  | G       F#+            |
| -stood   | and never turning back |"""

    formatted = format_songml(content)
    lines = formatted.split("\n")

    # Properties preserved
    assert lines[0] == "Title: Test Song"
    assert lines[1] == "Key: Fmaj"

    # Section header preserved
    assert lines[3] == "[Verse 1 - 4 bars]"

    # Bar numbers aligned
    assert lines[4].startswith("|")
    # Chords aligned with preserved spacing (F.. not changed)
    assert " F.. " in lines[5]
    assert " F9/A  Abdim7/B " in lines[5]
    # Lyrics aligned
    assert "You've got a way" in lines[6]


def test_format_songml_round_trip():
    """Test that formatting is idempotent (format twice = format once)."""
    content = """[Verse]
| F | G | Am |
| You | Me | Them |"""

    formatted_once = format_songml(content)
    formatted_twice = format_songml(formatted_once)

    # Should be identical
    assert formatted_once == formatted_twice


def test_format_songml_preserves_timing_semantics():
    """Test critical requirement: spacing within cells has timing semantics."""
    # These two lines have DIFFERENT timing semantics
    content1 = """[Test]
| F.. |"""

    content2 = """[Test]
| F . . |"""

    formatted1 = format_songml(content1)
    formatted2 = format_songml(content2)

    # The cell content must remain different
    assert " F.. " in formatted1
    assert " F . . " in formatted2
    assert formatted1 != formatted2


def test_format_songml_complex_chords():
    """Test formatting with complex chord names."""
    content = """[Verse]
| Abdim7/B | C+7/Ab | Bbmaj7 |
| Am | F | G |"""

    formatted = format_songml(content)
    lines = formatted.split("\n")

    # Chord names preserved exactly
    assert "Abdim7/B" in lines[1]
    assert "C+7/Ab" in lines[1]
    assert "Bbmaj7" in lines[1]


def test_format_songml_blank_lines():
    """Test that blank lines are preserved."""
    content = """Title: Song

[Verse]

| F | G |

[Chorus]
| Am | Dm |"""

    formatted = format_songml(content)
    lines = formatted.split("\n")

    # Check blank lines preserved
    assert lines[1] == ""
    assert lines[3] == ""
    assert lines[5] == ""


def test_format_songml_section_spacing():
    """Test formatting with typical section spacing."""
    content = """[Intro - 2 bars]
| 1 | 2 |
| F | G |


[Verse 1 - 2 bars]
| 3 | 4 |
| Am | Dm |"""

    formatted = format_songml(content)
    lines = formatted.split("\n")

    # Multiple blank lines preserved
    assert lines[3] == ""
    assert lines[4] == ""


def test_cli_stdout_default():
    """Test that default behavior prints to stdout."""
    import subprocess
    import tempfile

    # Create a temporary input file with valid SongML format
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".songml", delete=False, encoding="utf-8"
    ) as f:
        f.write("""[Test - 2 bars]
| 1 | 2 |
| F | G |
| Am | Dm |""")
        temp_file = f.name

    try:
        # Run without -i flag, should print to stdout
        result = subprocess.run(
            ["python", "-m", "songml_utils.formatter", temp_file], capture_output=True, text=True
        )

        # Should succeed
        assert result.returncode == 0
        # Should print formatted content to stdout
        assert "| F  | G  |" in result.stdout or "| F | G |" in result.stdout
        assert "| Am | Dm |" in result.stdout
        # stderr should be empty (no "Formatted to..." message)
        assert result.stderr == "" or "warnings" not in result.stderr.lower()

    finally:
        import os

        os.unlink(temp_file)


def test_cli_inplace_flag():
    """Test that -i flag modifies file in-place."""
    import subprocess
    import tempfile

    # Create a temporary input file with valid SongML
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".songml", delete=False, encoding="utf-8"
    ) as f:
        f.write("""[Test - 2 bars]
| 1 | 2 |
| F | G |
| Am | Dm |""")
        temp_file = f.name

    try:
        # Run with -i flag
        result = subprocess.run(
            ["python", "-m", "songml_utils.formatter", temp_file, "-i"],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0
        # stderr should show success message
        assert f"Formatted to {temp_file}" in result.stderr

        # Read the file to verify it was modified
        with open(temp_file, encoding="utf-8") as f:
            content = f.read()

        # Should be formatted
        assert "| F  | G  |" in content
        assert "| Am | Dm |" in content

    finally:
        import os

        os.unlink(temp_file)


def test_cli_output_file():
    """Test specifying an output file."""
    import subprocess
    import tempfile

    # Create temporary input and output files with valid SongML
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".songml", delete=False, encoding="utf-8"
    ) as f:
        f.write("""[Test - 2 bars]
| 1 | 2 |
| F | G |
| Am | Dm |""")
        input_file = f.name

    with tempfile.NamedTemporaryFile(suffix=".songml", delete=False) as f:
        output_file = f.name

    try:
        # Run with output file specified
        result = subprocess.run(
            ["python", "-m", "songml_utils.formatter", input_file, output_file],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0
        # stderr should show success message
        assert f"Formatted to {output_file}" in result.stderr

        # Read the output file
        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Should be formatted
        assert "| F  | G  |" in content
        assert "| Am | Dm |" in content

        # Input file should be unchanged
        with open(input_file, encoding="utf-8") as f:
            original = f.read()
        assert "| F | G |" in original  # Original spacing preserved

    finally:
        import os

        os.unlink(input_file)
        os.unlink(output_file)


def test_bar_number_renumbering():
    """Test that formatter automatically fixes incorrect bar numbering."""
    from songml_utils.formatter import format_songml
    from songml_utils.parser import parse_songml

    # Input with incorrect bar numbering (Bridge restarts at 1)
    content = """Title: Test Song
Key: C

[Verse - 4 bars]
| 1 | 2 | 3 | 4 |
| C | F | G | Am |

[Chorus - 2 bars]
| 1 | 2 |
| Dm | G |
"""

    # Parse and fix
    doc = parse_songml(content)
    from songml_utils.formatter import _fix_bar_numbers_in_ast

    _fix_bar_numbers_in_ast(doc)

    # Verify AST bar numbers are corrected
    sections = [item for item in doc.items if hasattr(item, "bars")]
    assert len(sections) == 2

    # Verse should be bars 1-4
    verse = sections[0]
    assert verse.bars[0].number == 1
    assert verse.bars[-1].number == 4

    # Chorus should be bars 5-6 (not 1-2)
    chorus = sections[1]
    assert chorus.bars[0].number == 5
    assert chorus.bars[-1].number == 6

    # Format and verify output has correct bar numbers
    formatted = format_songml(content, parsed_doc=doc)

    # The formatted output should show corrected bar numbers
    # Check that bar 5 and 6 appear (spacing may vary)
    assert "| 5" in formatted and "| 6" in formatted
    # Verify it's in the Chorus section
    lines = formatted.split("\n")
    chorus_idx = next(i for i, line in enumerate(lines) if "[Chorus" in line)
    # Bar numbers should be in next line after section header
    assert "5" in lines[chorus_idx + 1] and "6" in lines[chorus_idx + 1]


def test_bar_renumbering_with_gaps():
    """Test bar renumbering when sections have large gaps."""
    from songml_utils.formatter import _fix_bar_numbers_in_ast, format_songml
    from songml_utils.parser import parse_songml

    content = """[Intro - 2 bars]
| 1 | 2 |
| C | F |

[Verse - 4 bars]
| 1 | 2 | 3 | 4 |
| G | Am | Dm | Em |

[Bridge - 2 bars]
| 100 | 101 |
| F | G |
"""

    doc = parse_songml(content)
    _fix_bar_numbers_in_ast(doc)

    # Check all sections are sequential
    sections = [item for item in doc.items if hasattr(item, "bars")]
    assert sections[0].bars[0].number == 1  # Intro: 1-2
    assert sections[1].bars[0].number == 3  # Verse: 3-6
    assert sections[2].bars[0].number == 7  # Bridge: 7-8 (not 100-101)

    # Format and verify
    formatted = format_songml(content, parsed_doc=doc)
    assert "| 7 | 8 |" in formatted or "| 7  | 8  |" in formatted


def test_formatter_helper_functions():
    """Test individual helper functions for bar renumbering."""
    from songml_utils.formatter import (
        BarLine,
        _extract_bar_renumbering,
        _fix_bar_numbers_in_ast,
        _is_bar_number_row,
        _replace_bar_numbers,
    )
    from songml_utils.parser import parse_songml

    # Test _fix_bar_numbers_in_ast
    content = """[A - 2 bars]
| 5 | 6 |
| C | D |

[B - 2 bars]
| 1 | 2 |
| E | F |
"""
    doc = parse_songml(content)
    _fix_bar_numbers_in_ast(doc)

    sections = [item for item in doc.items if hasattr(item, "bars")]
    assert sections[0].bars[0].number == 1  # Was 5, now 1
    assert sections[1].bars[0].number == 3  # Was 1, now 3

    # Test _extract_bar_renumbering
    bar_map = _extract_bar_renumbering(doc)
    assert isinstance(bar_map, dict)
    assert len(bar_map) > 0

    # Test _is_bar_number_row
    bar_line_with_numbers = BarLine(
        original_content="| 1 | 2 |", cells=["", " 1 ", " 2 ", ""], line_number=5
    )
    assert _is_bar_number_row(bar_line_with_numbers) is True

    chord_line = BarLine(original_content="| C | D |", cells=["", " C ", " D ", ""], line_number=6)
    assert _is_bar_number_row(chord_line) is False

    # Test _replace_bar_numbers
    new_line = _replace_bar_numbers(bar_line_with_numbers, [10, 11])
    assert "10" in new_line.cells[1]
    assert "11" in new_line.cells[2]
