"""Tests for chord sheet format/parse."""

from __future__ import annotations

import pytest

from songml_utils.als_parser import ChordEntry, FixmeEntry
from songml_utils.chord_sheet import SheetEntry, SheetHeader, format_sheet, parse_sheet


# ---------------------------------------------------------------------------
# format_sheet
# ---------------------------------------------------------------------------


class TestFormatSheet:
    def test_header_fields(self):
        text = format_sheet([], source="song.als", track="🎵 CHORD", tempo=95, time_sig="4/4")
        assert "# Source: song.als" in text
        assert "# Track: 🎵 CHORD" in text
        assert "# Tempo: 95" in text
        assert "# Time: 4/4" in text

    def test_chord_entry_line(self):
        entries = [ChordEntry(bar=1, beat=1.0, chord="C", duration=4.0)]
        text = format_sheet(entries, source="s.als", track="CHORD")
        assert "1:1" in text
        assert "C" in text
        assert "4" in text

    def test_fixme_entry_line(self):
        entries = [FixmeEntry(bar=5, beat=3.0, raw_name="Bm7.E7.", reason="duration mismatch")]
        text = format_sheet(entries, source="s.als", track="CHORD")
        assert "# FIXME" in text
        assert "5:3" in text
        assert "duration mismatch" in text
        assert "Bm7.E7." in text

    def test_ordering_preserved(self):
        entries = [
            ChordEntry(bar=1, beat=1.0, chord="C", duration=4.0),
            FixmeEntry(bar=2, beat=1.0, raw_name="XXX", reason="unknown"),
            ChordEntry(bar=3, beat=1.0, chord="Am", duration=4.0),
        ]
        text = format_sheet(entries, source="s.als", track="CHORD")
        lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#") or "FIXME" in l]
        # C comes before FIXME comes before Am in the output
        c_pos = next(i for i, l in enumerate(lines) if "C" in l and "FIXME" not in l)
        fixme_pos = next(i for i, l in enumerate(lines) if "FIXME" in l)
        am_pos = next(i for i, l in enumerate(lines) if "Am" in l and "FIXME" not in l)
        assert c_pos < fixme_pos < am_pos

    def test_half_bar_positions(self):
        entries = [
            ChordEntry(bar=1, beat=1.0, chord="E+13", duration=2.0),
            ChordEntry(bar=1, beat=3.0, chord="E7", duration=2.0),
        ]
        text = format_sheet(entries, source="s.als", track="CHORD")
        assert "1:1" in text
        assert "1:3" in text

    def test_tempo_integer_formatting(self):
        # Tempo 120.0 should render as "120" not "120.0"
        text = format_sheet([], source="s.als", track="CHORD", tempo=120.0)
        assert "# Tempo: 120\n" in text or text.endswith("# Tempo: 120")


# ---------------------------------------------------------------------------
# parse_sheet
# ---------------------------------------------------------------------------


class TestParseSheet:
    def test_parses_clean_sheet(self):
        text = "\n".join([
            "# Source: song.als",
            "# Track: 🎵 CHORD",
            "# Tempo: 120",
            "# Time: 4/4",
            "",
            "  1:1  C             4",
            "  2:1  Am            4",
            "  3:1  F             4",
        ])
        header, entries = parse_sheet(text)
        assert header.source == "song.als"
        assert header.tempo == 120.0
        assert header.time_sig == "4/4"
        assert len(entries) == 3
        assert entries[0] == SheetEntry(bar=1, beat=1.0, chord="C", duration=4.0)
        assert entries[2] == SheetEntry(bar=3, beat=1.0, chord="F", duration=4.0)

    def test_raises_on_fixme(self):
        text = "\n".join([
            "# Source: song.als",
            "# Track: CHORD",
            "# Tempo: 120",
            "# Time: 4/4",
            "",
            "  1:1  C    4",
            "# FIXME [2:1]: duration mismatch (raw: 'Bm7.E7.')",
            "  3:1  Am   4",
        ])
        with pytest.raises(ValueError, match="FIXME"):
            parse_sheet(text)

    def test_fixme_error_lists_all_fixmes(self):
        text = "\n".join([
            "# Tempo: 120",
            "# Time: 4/4",
            "  1:1  C    4",
            "# FIXME [2:1]: first problem",
            "# FIXME [3:1]: second problem",
        ])
        with pytest.raises(ValueError) as exc:
            parse_sheet(text)
        msg = str(exc.value)
        assert "first problem" in msg
        assert "second problem" in msg
        assert "2" in msg  # should mention line numbers or bar positions

    def test_raises_on_unparseable_line(self):
        text = "1:1  C  4\nnot a valid line at all\n"
        with pytest.raises(ValueError, match="cannot parse"):
            parse_sheet(text)

    def test_empty_sheet_returns_empty_entries(self):
        text = "# Source: nothing\n# Tempo: 120\n# Time: 4/4\n"
        header, entries = parse_sheet(text)
        assert entries == []

    def test_header_defaults_when_missing(self):
        text = "  1:1  C  4\n"
        header, entries = parse_sheet(text)
        assert header.tempo == 120.0
        assert header.time_sig == "4/4"

    def test_fractional_beat(self):
        text = "  1:1.5  C  2\n"
        _, entries = parse_sheet(text)
        assert entries[0].beat == 1.5

    def test_fractional_duration(self):
        text = "  1:1  C  0.5\n"
        _, entries = parse_sheet(text)
        assert entries[0].duration == 0.5

    def test_ignores_blank_lines_and_comments(self):
        text = "\n# This is a comment\n\n  1:1  C  4\n\n"
        _, entries = parse_sheet(text)
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# Round-trip: format → parse
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_chord_entries_survive_round_trip(self):
        original = [
            ChordEntry(bar=1, beat=1.0, chord="C", duration=4.0),
            ChordEntry(bar=2, beat=1.0, chord="Am", duration=4.0),
            ChordEntry(bar=3, beat=1.0, chord="F", duration=4.0),
            ChordEntry(bar=3, beat=3.0, chord="G", duration=2.0),
        ]
        text = format_sheet(original, source="test.als", track="CHORD", tempo=95, time_sig="4/4")
        header, parsed = parse_sheet(text)

        assert header.tempo == 95.0
        assert header.time_sig == "4/4"
        assert len(parsed) == len(original)
        for orig, result in zip(original, parsed):
            assert result.bar == orig.bar
            assert result.beat == orig.beat
            assert result.chord == orig.chord
            assert result.duration == orig.duration

    def test_fixme_entries_do_not_survive_parse(self):
        """Sheets with FIXME entries cannot be parsed — editing is required."""
        entries = [
            ChordEntry(bar=1, beat=1.0, chord="C", duration=4.0),
            FixmeEntry(bar=2, beat=1.0, raw_name="XXX", reason="unknown chord"),
        ]
        text = format_sheet(entries, source="test.als", track="CHORD")
        with pytest.raises(ValueError, match="FIXME"):
            parse_sheet(text)
