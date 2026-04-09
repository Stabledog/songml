"""Tests for ALS chord track extraction."""

from __future__ import annotations

import gzip
import textwrap
from pathlib import Path

import pytest

from songml_utils.als_parser import (
    ChordEntry,
    FixmeEntry,
    _parse_compound_name,
    _to_bar_beat,
    extract_chord_clips,
)


# ---------------------------------------------------------------------------
# _to_bar_beat
# ---------------------------------------------------------------------------


class TestToBarBeat:
    def test_first_beat(self):
        assert _to_bar_beat(0.0, 4) == (1, 1.0)

    def test_second_bar(self):
        assert _to_bar_beat(4.0, 4) == (2, 1.0)

    def test_mid_bar(self):
        assert _to_bar_beat(5.0, 4) == (2, 2.0)

    def test_last_beat_of_bar(self):
        assert _to_bar_beat(3.0, 4) == (1, 4.0)

    def test_half_beat(self):
        bar, beat = _to_bar_beat(1.5, 4)
        assert bar == 1
        assert abs(beat - 2.5) < 1e-9

    def test_bar_32_beat_3(self):
        # bar 32 starts at beat 124 (0-based)
        assert _to_bar_beat(126.0, 4) == (32, 3.0)

    def test_three_four_time(self):
        assert _to_bar_beat(3.0, 3) == (2, 1.0)
        assert _to_bar_beat(4.0, 3) == (2, 2.0)


# ---------------------------------------------------------------------------
# _parse_compound_name
# ---------------------------------------------------------------------------


class TestParseCompoundName:
    """Unit tests for compound clip name parsing."""

    # Simple single chords

    def test_single_chord(self):
        assert _parse_compound_name("C", 4.0) == [("C", 4.0)]

    def test_single_chord_with_duration(self):
        assert _parse_compound_name("Am7", 2.0) == [("Am7", 2.0)]

    def test_slash_chord(self):
        assert _parse_compound_name("G/B", 4.0) == [("G/B", 4.0)]

    # Compound — last chord fills remainder (no trailing dots)

    def test_two_chords_explicit_then_remainder(self):
        result = _parse_compound_name("Gsus4..G/F#", 4.0)
        assert result == [("Gsus4", 2.0), ("G/F#", 2.0)]

    def test_one_beat_then_remainder(self):
        result = _parse_compound_name("Am7.G", 4.0)
        assert result == [("Am7", 1.0), ("G", 3.0)]

    def test_three_chords_last_fills(self):
        result = _parse_compound_name("C..F.G", 4.0)
        assert result == [("C", 2.0), ("F", 1.0), ("G", 1.0)]

    # Compound — all chords have explicit trailing dots

    def test_two_chords_both_explicit_match(self):
        result = _parse_compound_name("Gsus4..G7sus4..", 4.0)
        assert result == [("Gsus4", 2.0), ("G7sus4", 2.0)]

    def test_two_chords_one_beat_each_two_beat_clip(self):
        # A 2-beat clip: D7b9 for 1 beat, Ebdim7 for 1 beat — valid
        result = _parse_compound_name("D7b9.Ebdim7.", 2.0)
        assert result == [("D7b9", 1.0), ("Ebdim7", 1.0)]

    def test_slash_chord_in_compound(self):
        result = _parse_compound_name("G/F..Gsus/E", 4.0)
        assert result == [("G/F", 2.0), ("Gsus/E", 2.0)]

    # Error cases

    def test_mismatch_total_too_short(self):
        # 1+1=2 beats in a 4-beat clip with explicit trailing dots → FIXME
        result = _parse_compound_name("Bm7.E7.", 4.0)
        assert isinstance(result, str)
        assert "2" in result  # mentions the incorrect total
        assert "4" in result  # mentions the clip duration

    def test_mismatch_total_too_long(self):
        result = _parse_compound_name("C...F...", 4.0)
        assert isinstance(result, str)

    def test_empty_name(self):
        result = _parse_compound_name("", 4.0)
        assert isinstance(result, str)

    def test_explicit_fills_no_remainder(self):
        # Three chords summing to 4 with last having no dots — valid
        result = _parse_compound_name("C..F.G", 4.0)
        assert result == [("C", 2.0), ("F", 1.0), ("G", 1.0)]

    def test_preceding_fills_exactly_leaves_no_room(self):
        # Am7 for 4 beats, then G needs space — but there's none
        result = _parse_compound_name("Am7....G", 4.0)
        assert isinstance(result, str)
        assert "no room" in result


# ---------------------------------------------------------------------------
# extract_chord_clips — integration tests using synthetic XML
# ---------------------------------------------------------------------------


def _make_als_xml(clips: list[tuple[str, float, float]]) -> bytes:
    """Build minimal Ableton XML with a CHORD track containing the given clips."""
    clip_els = ""
    for i, (name, start, end) in enumerate(clips):
        clip_els += textwrap.dedent(f"""
            <MidiClip Id="{i}" Time="{start}">
              <CurrentStart Value="{start}"/>
              <CurrentEnd Value="{end}"/>
              <Name Value="{name}"/>
            </MidiClip>
        """)

    xml = textwrap.dedent(f"""
        <Ableton>
          <LiveSet>
            <Tracks>
              <MidiTrack>
                <Name>
                  <UserName Value="🎵 CHORD"/>
                </Name>
                <DeviceChain>
                  <MainSequencer>
                    <ClipTimeable>
                      <ArrangerAutomation>
                        <Events>
                          {clip_els}
                        </Events>
                      </ArrangerAutomation>
                    </ClipTimeable>
                  </MainSequencer>
                </DeviceChain>
              </MidiTrack>
            </Tracks>
          </LiveSet>
        </Ableton>
    """).strip()
    return xml.encode()


def _write_als(tmp_path: Path, clips: list[tuple[str, float, float]]) -> Path:
    """Write a gzipped ALS file to tmp_path and return its path."""
    content = _make_als_xml(clips)
    path = tmp_path / "test.als"
    with gzip.open(path, "wb") as f:
        f.write(content)
    return path


class TestExtractChordClips:
    def test_simple_single_chords(self, tmp_path):
        path = _write_als(tmp_path, [
            ("C", 0.0, 4.0),
            ("Am", 4.0, 8.0),
            ("F", 8.0, 12.0),
        ])
        track_name, entries = extract_chord_clips(str(path), beats_per_bar=4)

        assert track_name == "🎵 CHORD"
        assert len(entries) == 3
        assert all(isinstance(e, ChordEntry) for e in entries)

        assert entries[0] == ChordEntry(bar=1, beat=1.0, chord="C", duration=4.0)
        assert entries[1] == ChordEntry(bar=2, beat=1.0, chord="Am", duration=4.0)
        assert entries[2] == ChordEntry(bar=3, beat=1.0, chord="F", duration=4.0)

    def test_compound_clip_expands(self, tmp_path):
        path = _write_als(tmp_path, [
            ("Gsus4..G7sus4..", 0.0, 4.0),
        ])
        _, entries = extract_chord_clips(str(path), beats_per_bar=4)

        assert len(entries) == 2
        assert entries[0] == ChordEntry(bar=1, beat=1.0, chord="Gsus4", duration=2.0)
        assert entries[1] == ChordEntry(bar=1, beat=3.0, chord="G7sus4", duration=2.0)

    def test_compound_clip_crossing_bar(self, tmp_path):
        # A compound clip that crosses a bar boundary
        path = _write_als(tmp_path, [
            ("Am..F", 2.0, 6.0),  # 4-beat clip: Am for 2 (bar 1 beats 3-4), F for 2 (bar 2 beats 1-2)
        ])
        _, entries = extract_chord_clips(str(path), beats_per_bar=4)

        assert len(entries) == 2
        assert entries[0] == ChordEntry(bar=1, beat=3.0, chord="Am", duration=2.0)
        assert entries[1] == ChordEntry(bar=2, beat=1.0, chord="F", duration=2.0)

    def test_fixme_on_bad_compound(self, tmp_path):
        path = _write_als(tmp_path, [
            ("Bm7.E7.", 0.0, 4.0),  # 1+1=2 ≠ 4 beats — FIXME
        ])
        _, entries = extract_chord_clips(str(path), beats_per_bar=4)

        assert len(entries) == 1
        assert isinstance(entries[0], FixmeEntry)
        assert entries[0].bar == 1
        assert entries[0].beat == 1.0
        assert entries[0].raw_name == "Bm7.E7."

    def test_mixed_good_and_fixme(self, tmp_path):
        path = _write_als(tmp_path, [
            ("C", 0.0, 4.0),
            ("Bm7.E7.", 4.0, 8.0),  # FIXME
            ("Am", 8.0, 12.0),
        ])
        _, entries = extract_chord_clips(str(path), beats_per_bar=4)

        assert len(entries) == 3
        assert isinstance(entries[0], ChordEntry)
        assert isinstance(entries[1], FixmeEntry)
        assert isinstance(entries[2], ChordEntry)

    def test_half_bar_chords(self, tmp_path):
        path = _write_als(tmp_path, [
            ("E+13", 0.0, 2.0),
            ("E7", 2.0, 4.0),
        ])
        _, entries = extract_chord_clips(str(path), beats_per_bar=4)

        assert entries[0] == ChordEntry(bar=1, beat=1.0, chord="E+13", duration=2.0)
        assert entries[1] == ChordEntry(bar=1, beat=3.0, chord="E7", duration=2.0)

    def test_no_chord_track_raises(self, tmp_path):
        xml = b"<Ableton><LiveSet><Tracks><MidiTrack><Name><UserName Value='Piano'/></Name></MidiTrack></Tracks></LiveSet></Ableton>"
        path = tmp_path / "test.als"
        with gzip.open(path, "wb") as f:
            f.write(xml)

        with pytest.raises(ValueError, match="No CHORD track"):
            extract_chord_clips(str(path))

    def test_plain_xml_accepted(self, tmp_path):
        """Plain (non-gzipped) XML should also be parseable."""
        content = _make_als_xml([("C", 0.0, 4.0)])
        path = tmp_path / "test.xml"
        path.write_bytes(content)

        track_name, entries = extract_chord_clips(str(path), beats_per_bar=4)
        assert len(entries) == 1
        assert entries[0].chord == "C"

    def test_off_grid_clip_rounded(self, tmp_path, capsys):
        path = _write_als(tmp_path, [
            ("C", 0.3959, 4.0),  # slightly off-grid start
        ])
        _, entries = extract_chord_clips(str(path), beats_per_bar=4)

        captured = capsys.readouterr()
        assert "off-grid" in captured.err
        assert len(entries) == 1
        assert entries[0].bar == 1
        assert entries[0].beat == 1.0
