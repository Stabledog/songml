"""Read and write the intermediate chord sheet text format.

Chord sheet is a human-editable text file that sits between .als extraction
and MIDI conversion. Format:

    # Source: sunday-morning.als
    # Track: 🎵 CHORD
    # Tempo: 120
    # Time: 4/4

     1:1  C           4
     2:1  Am          4
     3:1  F           4
    # FIXME [21:1]: compound duration mismatch "Bm7.E7." — total 2 beats ≠ clip 4 beats
    32:1  E+13        2
    32:3  E7          2

Each data line: <bar>:<beat>  <chord>  <duration_beats>
FIXME lines are comment lines beginning with "# FIXME".
"""

from __future__ import annotations

__all__ = ["format_sheet", "parse_sheet", "SheetEntry", "SheetHeader"]

import re
from dataclasses import dataclass

from .als_parser import ChordEntry, FixmeEntry

# Matches a data line: bar:beat  chord  duration  (optional trailing comment)
_DATA_LINE = re.compile(
    r"^\s*(\d+):(\d+(?:\.\d+)?)\s+(\S+)\s+(\d+(?:\.\d+)?)\s*(?:#(?!FIXME).*)?$",
    re.IGNORECASE,
)
_FIXME_LINE = re.compile(r"^\s*#\s*FIXME", re.IGNORECASE)
_HEADER_LINE = re.compile(r"^\s*#\s*(\w+):\s*(.+)$")


@dataclass(frozen=True)
class SheetEntry:
    """A parsed chord entry from a chord sheet data line."""

    bar: int
    beat: float
    chord: str
    duration: float


@dataclass(frozen=True)
class SheetHeader:
    """Metadata parsed from chord sheet header comments."""

    source: str = ""
    track: str = ""
    tempo: float = 120.0
    time_sig: str = "4/4"


def format_sheet(
    entries: list[ChordEntry | FixmeEntry],
    source: str,
    track: str,
    tempo: float = 120.0,
    time_sig: str = "4/4",
) -> str:
    """
    Render chord entries as a human-editable chord sheet string.

    ChordEntry values become data lines. FixmeEntry values become
    '# FIXME [bar:beat]: reason' comment lines, preserving their position
    in the sequence so a human editor can see exactly what needs fixing.

    Args:
        entries: Ordered list of ChordEntry and FixmeEntry values
        source: Original filename (used in header comment)
        track: Ableton track name (used in header comment)
        tempo: BPM (written to header; used by chords-to-midi)
        time_sig: Time signature string e.g. "4/4" (written to header)

    Returns:
        Formatted chord sheet as a string (no trailing newline).
    """
    lines = [
        f"# Source: {source}",
        f"# Track: {track}",
        f"# Tempo: {tempo:g}",
        f"# Time: {time_sig}",
        "",
    ]

    for entry in entries:
        pos = _fmt_pos(entry.bar, entry.beat)
        if isinstance(entry, ChordEntry):
            lines.append(f"{pos}  {entry.chord:<14}  {entry.duration:g}")
        else:
            lines.append(f"# FIXME [{pos.strip()}]: {entry.reason} (raw: {entry.raw_name!r})")

    return "\n".join(lines)


def parse_sheet(text: str) -> tuple[SheetHeader, list[SheetEntry]]:
    """
    Parse a chord sheet string into header metadata and chord entries.

    Raises:
        ValueError: If any FIXME lines are present. The error message lists
                    every FIXME line so the editor knows exactly what to fix
                    before conversion can proceed.

    Returns:
        (header, entries) — header contains tempo/time_sig/etc., entries are
        the parsed chord data lines.
    """
    fixmes: list[str] = []
    entries: list[SheetEntry] = []
    header_fields: dict[str, str] = {}

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()

        if not line:
            continue

        if _FIXME_LINE.match(line):
            fixmes.append(f"  line {lineno}: {line}")
            continue

        if line.startswith("#"):
            m = _HEADER_LINE.match(line)
            if m:
                header_fields[m.group(1).lower()] = m.group(2).strip()
            continue

        m = _DATA_LINE.match(line)
        if m:
            bar = int(m.group(1))
            beat = float(m.group(2))
            chord = m.group(3)
            duration = float(m.group(4))
            entries.append(SheetEntry(bar=bar, beat=beat, chord=chord, duration=duration))
        else:
            raise ValueError(f"Line {lineno}: cannot parse {raw_line!r}")

    if fixmes:
        fixme_list = "\n".join(fixmes)
        raise ValueError(
            f"Chord sheet has {len(fixmes)} unresolved FIXME(s) — "
            f"edit the file before converting:\n{fixme_list}"
        )

    header = SheetHeader(
        source=header_fields.get("source", ""),
        track=header_fields.get("track", ""),
        tempo=float(header_fields.get("tempo", "120")),
        time_sig=header_fields.get("time", "4/4"),
    )

    return header, entries


def _fmt_pos(bar: int, beat: float) -> str:
    """Format bar:beat as a fixed-width right-aligned string for column alignment."""
    beat_str = f"{beat:g}"
    return f"{bar}:{beat_str}".rjust(7)
