"""Tests for songml-validate CLI."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from songml_utils.validate import (
    _extract_chord_symbols,
    _validate_chord_voicings,
    main,
)


class TestValidateCli:
    """Tests for validate CLI entry point."""

    def test_extract_chord_symbols_basic(self):
        """_extract_chord_symbols extracts unique chord symbols with their location."""
        from songml_utils.ast import Bar, ChordToken, Document, Section

        # Create real AST objects
        chord1 = ChordToken(text="C", start_beat=1, duration_beats=1)
        chord2 = ChordToken(text="G", start_beat=2, duration_beats=1)
        bar = Bar(number=1, chords=[chord1, chord2], line_number=1)
        section = Section(name="Verse", bar_count=1, bars=[bar])
        doc = Document(items=[section])

        result = _extract_chord_symbols(doc, "test.songml")

        assert "C" in result
        assert "G" in result
        assert result["C"] == ("test.songml", 1)
        assert result["G"] == ("test.songml", 1)

    def test_extract_chord_symbols_skips_rest_markers(self):
        """_extract_chord_symbols skips rest markers ('-', '.', etc)."""
        from songml_utils.ast import Bar, ChordToken, Document, Section

        chord1 = ChordToken(text="C", start_beat=1, duration_beats=1)
        chord_rest = ChordToken(text="-", start_beat=2, duration_beats=1)
        chord_empty = ChordToken(text="", start_beat=3, duration_beats=1)
        chord2 = ChordToken(text="G", start_beat=4, duration_beats=1)
        bar = Bar(number=1, chords=[chord1, chord_rest, chord_empty, chord2], line_number=1)
        section = Section(name="Verse", bar_count=1, bars=[bar])
        doc = Document(items=[section])

        result = _extract_chord_symbols(doc, "test.songml")

        assert "C" in result
        assert "G" in result
        assert "-" not in result
        assert "" not in result

    def test_extract_chord_symbols_first_occurrence_only(self):
        """_extract_chord_symbols tracks only first occurrence of each symbol."""
        from songml_utils.ast import Bar, ChordToken, Document, Section

        chord1 = ChordToken(text="C", start_beat=1, duration_beats=1)
        bar1 = Bar(number=1, chords=[chord1], line_number=1)

        chord2 = ChordToken(text="C", start_beat=1, duration_beats=1)
        chord3 = ChordToken(text="G", start_beat=2, duration_beats=1)
        bar2 = Bar(number=2, chords=[chord2, chord3], line_number=3)

        section = Section(name="Verse", bar_count=2, bars=[bar1, bar2])
        doc = Document(items=[section])

        result = _extract_chord_symbols(doc, "test.songml")

        # C appears on line 1 first, not line 3
        assert result["C"] == ("test.songml", 1)

    def test_validate_chord_voicings_base_chord_extraction(self, monkeypatch):
        """_validate_chord_voicings extracts base chord from slash chords."""
        chord_symbols = {
            "C": ("test.songml", 1),
            "C/E": ("test.songml", 2),  # slash chord
            "G/B": ("test.songml", 3),
        }

        # Mock voicing table with C and G but not E or B
        mock_voicing_table = {
            "C": "0,4,7",
            "G": "0,2,7",
        }
        mock_validate_fn = Mock(return_value=[])

        monkeypatch.setattr(
            "songml_utils.validate.get_voicing_table", Mock(return_value=mock_voicing_table)
        )
        monkeypatch.setattr("songml_utils.validate.validate_voicing_table", mock_validate_fn)

        _validate_chord_voicings(chord_symbols, validate_all=False)

        # Should call validate_voicing_table with filtered voicing table (base chords only)
        call_arg = mock_validate_fn.call_args[0][0]
        assert "C" in call_arg
        assert "G" in call_arg

    def test_validate_chord_voicings_unknown_symbol_warning(self, monkeypatch):
        """_validate_chord_voicings warns about unknown chord symbols."""
        chord_symbols = {
            "C": ("test.songml", 1),
            "Zzz": ("test.songml", 5),  # unknown chord
        }

        mock_voicing_table = {
            "C": "0,4,7",
        }
        mock_validate_fn = Mock(return_value=[])

        monkeypatch.setattr(
            "songml_utils.validate.get_voicing_table", Mock(return_value=mock_voicing_table)
        )
        monkeypatch.setattr("songml_utils.validate.validate_voicing_table", mock_validate_fn)

        warnings = _validate_chord_voicings(chord_symbols, validate_all=False)

        # Should have warning about unknown symbol
        assert any("Unknown chord symbol" in w and "Zzz" in w for w in warnings)
        assert any("test.songml:5" in w for w in warnings)

    def test_validate_chord_voicings_validate_all_flag(self, monkeypatch):
        """_validate_chord_voicings with validate_all=True calls validate_voicing_table on full table."""
        chord_symbols = {"C": ("test.songml", 1)}

        mock_voicing_table = {
            "C": "0,4,7",
            "G": "0,2,7",
        }
        mock_validate_fn = Mock(return_value=["Theory warning: bad voicing"])

        monkeypatch.setattr(
            "songml_utils.validate.get_voicing_table", Mock(return_value=mock_voicing_table)
        )
        monkeypatch.setattr("songml_utils.validate.validate_voicing_table", mock_validate_fn)

        warnings = _validate_chord_voicings(chord_symbols, validate_all=True)

        # Should call validate_voicing_table with full table (all entries)
        call_arg = mock_validate_fn.call_args[0][0]
        assert set(call_arg.keys()) == {"C", "G"}  # full table

        # Should include theory warnings
        assert "Theory warning: bad voicing" in warnings

    def test_main_prints_summary_and_json(self, tmp_path, monkeypatch, capsys):
        """main prints parse success, summary, and doc.to_json() to stdout."""
        from songml_utils.ast import Bar, ChordToken, Document, Section

        input_file = tmp_path / "test.songml"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        # Create real document to be returned by parse
        chord = ChordToken(text="C", start_beat=1, duration_beats=1)
        bar = Bar(number=1, chords=[chord], line_number=1)
        section = Section(name="Verse", bar_count=1, bars=[bar])
        real_doc = Document(items=[section])

        mock_parse = Mock(return_value=real_doc)
        mock_extract = Mock(return_value={})  # no chords (skip voicing validation)

        monkeypatch.setattr("songml_utils.validate.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.validate._extract_chord_symbols", mock_extract)
        monkeypatch.setattr("sys.argv", ["songml-validate", str(input_file)])

        main()

        captured = capsys.readouterr()

        # Verify messages in stderr
        assert "✓ Parsed successfully:" in captured.err
        assert "Summary:" in captured.err
        assert "1 sections" in captured.err

        # Verify JSON in stdout
        assert captured.out.strip() != ""
        assert '"items":' in captured.out or '"bars"' in captured.out

    def test_main_prints_warnings_when_present(self, tmp_path, monkeypatch, capsys):
        """main prints parser warnings to stderr."""
        from songml_utils.ast import Bar, ChordToken, Document, Section

        input_file = tmp_path / "test.songml"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        # Create real document with warnings
        chord = ChordToken(text="C", start_beat=1, duration_beats=1)
        bar = Bar(number=1, chords=[chord], line_number=1)
        section = Section(name="Verse", bar_count=1, bars=[bar])
        real_doc = Document(items=[section])
        real_doc.warnings = ["Validation warning 1", "Validation warning 2"]

        mock_parse = Mock(return_value=real_doc)
        mock_extract = Mock(return_value={})

        monkeypatch.setattr("songml_utils.validate.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.validate._extract_chord_symbols", mock_extract)
        monkeypatch.setattr("sys.argv", ["songml-validate", str(input_file)])

        main()

        captured = capsys.readouterr()

        # Verify warnings printed to stderr
        assert "Warnings" in captured.err
        assert "Validation warning 1" in captured.err
        assert "Validation warning 2" in captured.err

    def test_main_parse_error_exits_1(self, tmp_path, monkeypatch, capsys):
        """ParseError causes exit with code 1."""
        input_file = tmp_path / "test.songml"
        input_file.write_text("invalid")

        from songml_utils.ast import ParseError

        mock_parse = Mock(side_effect=ParseError("Invalid syntax", 1))
        monkeypatch.setattr("songml_utils.validate.parse_songml", mock_parse)
        monkeypatch.setattr("sys.argv", ["songml-validate", str(input_file)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ Parse error:" in captured.err

    def test_main_with_all_flag_validates_full_table(
        self, tmp_path, monkeypatch, capsys, sample_doc
    ):
        """main with --all flag validates entire voicing table."""
        input_file = tmp_path / "test.songml"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        mock_parse = Mock(return_value=sample_doc)
        mock_validate_voicings_fn = Mock(return_value=[])

        monkeypatch.setattr("songml_utils.validate.parse_songml", mock_parse)
        monkeypatch.setattr(
            "songml_utils.validate.validate_voicing_table", mock_validate_voicings_fn
        )
        monkeypatch.setattr("sys.argv", ["songml-validate", str(input_file), "--all"])

        main()

        # Verify validate_voicing_table was called
        mock_validate_voicings_fn.assert_called()
        # When --all flag is used, full table is validated
        # (this is verified by presence of mock call)
