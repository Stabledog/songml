"""Extract chord progression from Ableton Live Set (.als) CHORD track."""

from __future__ import annotations

__all__ = ["ChordEntry", "FixmeEntry", "extract_chord_clips"]

import gzip
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass(frozen=True)
class ChordEntry:
    """A single chord at a specific bar:beat position with a duration."""

    bar: int  # 1-based bar number
    beat: float  # 1-based beat within bar (e.g. 1, 2, 3, 4 in 4/4)
    chord: str  # chord symbol (e.g. "Am7", "G/B")
    duration: float  # duration in beats


@dataclass(frozen=True)
class FixmeEntry:
    """A clip that could not be cleanly parsed — requires manual editing."""

    bar: int
    beat: float
    raw_name: str  # original clip name from Ableton
    reason: str  # human-readable explanation


type ClipData = list[ChordEntry | FixmeEntry]


def extract_chord_clips(als_path: str, beats_per_bar: int = 4) -> tuple[str, ClipData]:
    """
    Extract chord progression from an Ableton Live Set (.als) file.

    Finds the first MIDI track whose name contains 'CHORD' (case-insensitive),
    reads its arrangement clips, and expands compound clip names into individual
    ChordEntry records. Problems are reported as FixmeEntry records rather than
    raising exceptions, so the caller gets a best-effort result.

    Args:
        als_path: Path to .als file (gzipped or plain XML accepted)
        beats_per_bar: Beats per bar for bar:beat calculation (default 4)

    Returns:
        (track_name, entries) where entries is an ordered mix of ChordEntry
        and FixmeEntry values.

    Raises:
        ValueError: If no CHORD track is found, or the file cannot be parsed at all.
    """
    root = _parse_als(als_path)
    track_el, track_name = _find_chord_track(root)
    raw_clips = _get_arrangement_clips(track_el)

    entries: ClipData = []
    for clip_name, abs_start, clip_duration in raw_clips:
        bar, beat = _to_bar_beat(abs_start, beats_per_bar)
        result = _parse_compound_name(clip_name, clip_duration)
        if isinstance(result, str):
            # result is an error message
            entries.append(FixmeEntry(bar=bar, beat=beat, raw_name=clip_name, reason=result))
        else:
            # Expand each sub-chord using its own absolute beat position
            abs_beat = abs_start
            for chord, dur in result:
                sub_bar, sub_beat = _to_bar_beat(abs_beat, beats_per_bar)
                entries.append(ChordEntry(bar=sub_bar, beat=sub_beat, chord=chord, duration=dur))
                abs_beat += dur

    return track_name, entries


def _parse_compound_name(name: str, duration: float) -> list[tuple[str, float]] | str:
    """
    Parse a compound clip name into (chord_symbol, beats) pairs.

    Dot syntax (same convention as SongML):
      - Dots immediately after a chord name give that chord an explicit beat count
        (one dot = one beat, two dots = two beats, etc.)
      - The last chord in a name may omit trailing dots, in which case it fills
        the remainder of the clip duration.
      - If the last chord HAS trailing dots, all dot counts must sum exactly to
        the clip duration.

    Examples (4-beat clip):
      "C"              -> [("C", 4.0)]
      "Gsus4..G7sus4"  -> [("Gsus4", 2.0), ("G7sus4", 2.0)]
      "Gsus4..G7sus4.."-> [("Gsus4", 2.0), ("G7sus4", 2.0)]  (trailing dots explicit)
      "Am7.G"          -> [("Am7", 1.0), ("G", 3.0)]
      "Bm7.E7."        -> error (1+1=2 ≠ 4)

    Returns:
        List of (chord_symbol, duration_beats) pairs, or an error string.
    """
    tokens = re.findall(r"[^.]+|\.+", name)

    if not tokens:
        return f"empty clip name"

    if len(tokens) == 1:
        # Simple chord with no dots
        return [(tokens[0].strip(), duration)]

    # Build (chord, explicit_beat_count_or_None) pairs
    pairs: list[tuple[str, int | None]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("."):
            return f"clip name starts with dots: {name!r}"
        chord = token.strip()
        if not chord:
            i += 1
            continue
        if i + 1 < len(tokens) and tokens[i + 1].startswith("."):
            pairs.append((chord, len(tokens[i + 1])))
            i += 2
        else:
            pairs.append((chord, None))
            i += 1

    if not pairs:
        return f"no chord tokens found in {name!r}"

    last_chord, last_dots = pairs[-1]
    preceding = pairs[:-1]
    preceding_total = sum(d for _, d in preceding)  # all preceding must have dot counts

    if last_dots is None:
        # Last chord fills the remainder
        remainder = duration - preceding_total
        if remainder <= 0:
            return (
                f"explicit durations ({preceding_total} beats) leave no room for "
                f"final chord in {name!r} (clip is {duration:g} beats)"
            )
        result = [(c, float(d)) for c, d in preceding]
        result.append((last_chord, float(remainder)))
        return result
    else:
        # All chords have explicit dot counts — total must equal clip duration
        total = preceding_total + last_dots
        if total != duration:
            return (
                f"explicit durations ({total:g} beats) ≠ clip duration ({duration:g} beats) "
                f"in {name!r}"
            )
        result = [(c, float(d)) for c, d in preceding]
        result.append((last_chord, float(last_dots)))
        return result


def _to_bar_beat(abs_beat: float, beats_per_bar: int) -> tuple[int, float]:
    """Convert 0-based absolute beat to 1-based (bar, beat_in_bar)."""
    bar = int(abs_beat // beats_per_bar) + 1
    beat = (abs_beat % beats_per_bar) + 1
    # Clean up floating point residue for whole-number beats
    if abs(beat - round(beat)) < 1e-9:
        beat = float(round(beat))
    return bar, beat


def _parse_als(path: str) -> ET.Element:
    """Open an .als file (gzipped or plain XML) and return the root element."""
    try:
        with gzip.open(path, "rb") as f:
            content = f.read()
        return ET.fromstring(content)
    except gzip.BadGzipFile:
        return ET.parse(path).getroot()
    except Exception as e:
        raise ValueError(f"Cannot parse {path!r}: {e}") from e


def _find_chord_track(root: ET.Element) -> tuple[ET.Element, str]:
    """Find the first MidiTrack whose UserName contains 'CHORD' (case-insensitive)."""
    for track in root.iter("MidiTrack"):
        name_el = track.find(".//UserName")
        if name_el is not None:
            name = name_el.get("Value", "")
            if "CHORD" in name.upper():
                return track, name
    raise ValueError("No CHORD track found — expected a MidiTrack with 'CHORD' in its name")


def _get_arrangement_clips(track: ET.Element) -> list[tuple[str, float, float]]:
    """
    Extract (clip_name, start_beat, duration_beats) tuples from the arrangement.

    Off-grid clips (start or end not on a whole beat) are rounded and warned
    to stderr. Clips with missing elements are silently skipped.
    """
    ct = track.find(".//ClipTimeable")
    if ct is None:
        return []

    clips = ct.findall(".//MidiClip")
    result = []

    for clip in clips:
        name_el = clip.find("Name")
        start_el = clip.find("CurrentStart")
        end_el = clip.find("CurrentEnd")

        if name_el is None or start_el is None or end_el is None:
            continue

        clip_name = name_el.get("Value", "").strip()
        try:
            start = float(start_el.get("Value", "0"))
            end = float(end_el.get("Value", "0"))
        except ValueError:
            continue

        # Round to nearest whole beat; warn if materially off-grid
        rounded_start = round(start)
        if abs(start - rounded_start) > 0.01:
            print(
                f"Warning: clip {clip_name!r} starts off-grid at {start:.4f}, "
                f"rounded to {rounded_start}",
                file=sys.stderr,
            )
        start = float(rounded_start)

        rounded_end = round(end)
        if abs(end - rounded_end) > 0.01:
            print(
                f"Warning: clip {clip_name!r} ends off-grid at {end:.4f}, "
                f"rounded to {rounded_end}",
                file=sys.stderr,
            )
        duration = float(rounded_end) - start

        if duration <= 0:
            print(f"Warning: clip {clip_name!r} has zero or negative duration, skipped", file=sys.stderr)
            continue

        result.append((clip_name, start, duration))

    return result
