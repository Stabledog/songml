# SongML to ABC Generation

## Overview

This document describes the design and implementation of the SongML → ABC notation exporter. The exporter converts the existing SongML AST (Abstract Syntax Tree) into ABC notation files, enabling SongML compositions to be rendered as sheet music, played by ABC-compatible software, and shared in a widely-supported format.

ABC notation is a text-based music notation system that uses ASCII characters to represent musical scores. It's particularly well-suited for folk music, lead sheets, and chord charts — similar to SongML's target use case.

## Design Principles

Following SongML philosophy:

1. **Preserve intent over fidelity** — Convert chord progressions, timing, and lyrics into readable ABC
2. **Pass through unknowns** — Unknown chord symbols are written as-is; let ABC rendering tools handle them
3. **Reuse existing infrastructure** — Leverage parser timing logic and AST structures already built for MIDI export
4. **Keep it simple** — Choose predictable mappings over complex inference

## Mapping Rules: SongML → ABC

### Headers

| SongML Property | ABC Header | Conversion Rule |
|-----------------|------------|-----------------|
| `Title: Song Name` | `T: Song Name` | Direct copy |
| `Key: Fmaj` | `K: F` | Strip "maj" suffix; pass root letter through |
| `Tempo: 104` | `Q: 1/4=104` | Assume quarter note gets the beat (adjustable based on time signature) |
| `Time: 4/4` | `M: 4/4` | Direct copy numerator/denominator |
| *(computed)* | `L: 1/8` | Unit note length — see below |

**Unit Note Length (`L:`) — Fixed Formula Approach**

SongML measures durations in **beats** (floating point: 1.0, 0.5, 2.0, etc.). ABC measures durations in **fractions of a whole note**.

To convert cleanly, we need to choose a "unit" small enough that:
- 1 beat = integer number of units
- 0.5 beat (SongML's smallest timing via semicolon `;`) = integer number of units

**Formula:** `L: 1 / (time_signature_denominator × 2)`

**Examples:**
- `Time: 4/4` → denominator = 4 → `L: 1/8` (eighth notes)
  - 1 beat = 2 units, 0.5 beat = 1 unit
- `Time: 3/4` → denominator = 4 → `L: 1/8`
- `Time: 6/8` → denominator = 8 → `L: 1/16` (sixteenth notes)
  - 1 beat = 2 units, 0.5 beat = 1 unit

This ensures all SongML timing tokens (`.` = 1 beat, `;` = 0.5 beat) map to integers in ABC.

### Body: Chords and Lyrics

**Approach:** Use ABC's **chord-annotation syntax** (chords above the staff) with lyrics below.

ABC supports inline chord markers like `"C"` that appear above notation. We'll generate:
1. A chord-only voice with chord annotations at appropriate positions
2. Lyrics lines using `w:` directive, aligned bar-by-bar

**Why chord-annotation over voice-based chords:**
- Simpler implementation
- Preserves SongML's leadsheet structure
- Lyrics align naturally underneath
- Readable in ABC source

### Timing Conversion

SongML `ChordToken` has:
- `start_beat` (float, 0-based within bar)
- `duration_beats` (float)

To convert to ABC units:

```python
def beats_to_abc_units(beats: float, denominator: int) -> int:
    """Convert SongML beats to ABC unit count."""
    units_per_beat = (denominator * 2) / 4  # Derived from L: formula
    return int(beats * units_per_beat)
```

**Example (4/4 time, L: 1/8):**
- Chord at `start_beat=0.0`, `duration_beats=2.0`
  - Start: 0 × 2 = 0 units
  - Duration: 2 × 2 = 4 units → `4` in ABC (half note)
- Chord at `start_beat=3.5`, `duration_beats=0.5`
  - Start: 3.5 × 2 = 7 units offset
  - Duration: 0.5 × 2 = 1 unit → `1` in ABC (eighth note)

### Lyrics Alignment

SongML `Bar` objects may have a `lyrics` field (string or None).

ABC uses `w:` lines to attach lyrics to notes. Since we're emitting chords (not melody notes), we'll:
1. Emit a rest or placeholder note for each chord's duration
2. Attach lyrics using `w:` with space-separated syllables/words aligned to bar structure

**Complexity:** SongML lyrics are free-form strings; ABC expects space-separated tokens per note/rest. We'll split on whitespace and align tokens to chord cells within each bar.

### Special Cases

| SongML Feature | ABC Handling |
|----------------|--------------|
| Pickup bars (prefix rests `...;F`) | Emit partial first measure with rests; ABC supports partial bars |
| Slash chords (`F9/A`) | Pass through as `"F9/A"`; ABC renders chord name as-is |
| Unknown chord symbols | Pass through verbatim; no validation against `chord_voicings.tsv` |
| Empty bars (synthesized by parser) | Emit measure of rests with no chord annotation |
| Multiple chords per bar | Emit sequential chord annotations with computed durations |
| Section headers | Convert to ABC comments or `P:` part markers (e.g., `P:Intro`) |

## Implementation Plan

### Files to Create

1. **`songml-utils/src/songml_utils/abc_exporter.py`**
   - Core conversion logic
   - Functions:
     - `to_abc_string(doc: Document, unit_note_length: str | None = None, chord_style: str = 'chordline') -> str`
     - `export_abc(doc: Document, output_path: str, **kwargs) -> None`
   - Helpers:
     - `_format_abc_headers(doc: Document, unit_len_str: str) -> list[str]`
     - `_beats_to_abc_units(beats: float, denominator: int) -> int`
     - `_format_bar_as_abc(bar: Bar, beats_per_bar: int, denominator: int) -> str`
     - `_format_lyrics_line(bar: Bar) -> str | None`

2. **`songml-utils/src/songml_utils/abc_cli.py`**
   - CLI entry point for `songml-to-abc` command
   - Arguments:
     - `input_file` (required): Path to `.songml` file
     - `output_file` (required): Path to output `.abc` file
     - `--unit-length`: Override computed `L:` (e.g., `1/16`)
     - `--chord-style`: Future extension (default: `chordline`)
   - Behavior:
     - Parse input using `songml_utils.parser.parse_songml()`
     - Print warnings to stderr if any
     - Call `export_abc()`
     - Print success message

3. **`songml-utils/tests/test_abc_exporter.py`**
   - Unit tests covering:
     - Header formatting (Title, Key, Tempo, Time, L:)
     - Explicit timing (dots: `C..`) → correct ABC duration
     - Half-beat timing (semicolon: `...;F`) → correct start offset
     - 3/4 and 6/8 time signatures → correct L: and duration calculations
     - Lyrics alignment → `w:` lines match bar structure
     - Integration test using `samples/youve-got-a-way.songml`
     - Unknown chord pass-through
     - Empty/synthesized bars

### Files to Modify

1. **`songml-utils/pyproject.toml`**
   - Add to `[project.scripts]`:
     ```toml
     songml-to-abc = "songml_utils.abc_cli:main"
     ```

2. **`songml-utils/src/songml_utils/__init__.py`** *(optional)*
   - Add imports for discoverability:
     ```python
     from .abc_exporter import to_abc_string, export_abc
     ```

## API Reference

### `to_abc_string(doc, unit_note_length=None, chord_style='chordline') -> str`

Converts a SongML Document to ABC notation string.

**Parameters:**
- `doc` (Document): Parsed SongML AST
- `unit_note_length` (str | None): Override computed `L:` value (e.g., `"1/16"`)
- `chord_style` (str): Chord rendering style; currently only `'chordline'` supported

**Returns:** ABC notation as a string

**Example:**
```python
from songml_utils import parse_songml, to_abc_string

doc = parse_songml(open("song.songml").read())
abc_text = to_abc_string(doc)
print(abc_text)
```

### `export_abc(doc, output_path, **kwargs) -> None`

Exports SongML Document to ABC file.

**Parameters:**
- `doc` (Document): Parsed SongML AST
- `output_path` (str): Destination file path
- `**kwargs`: Passed to `to_abc_string()`

**Example:**
```python
from songml_utils import parse_songml, export_abc

doc = parse_songml(open("song.songml").read())
export_abc(doc, "song.abc")
```

## CLI Usage

### Basic Export

```bash
songml-to-abc samples/youve-got-a-way.songml output.abc
```

### Override Unit Length

```bash
songml-to-abc song.songml song.abc --unit-length 1/16
```

### View ABC Output

```bash
songml-to-abc song.songml - | less
```
(Use `-` for stdout)

## Example Output

**Input (SongML):**
```songml
Title: Simple Song
Key: Cmaj
Tempo: 120
Time: 4/4

[Verse - 2 bars]
| C    | F  G  |
| Hello world  |
```

**Output (ABC):**
```abc
X: 1
T: Simple Song
M: 4/4
L: 1/8
Q: 1/4=120
K: C
P:Verse
"C"z8 | "F"z4 "G"z4 |
w: Hel-lo world
```

*(Note: `z` is rest in ABC; actual implementation may use different placeholder strategy)*

## Testing Strategy

1. **Unit tests:** Test each helper function in isolation
   - Header formatting with various property combinations
   - Beat-to-unit conversion with different time signatures
   - Lyrics tokenization and alignment

2. **Integration tests:** Full SongML → ABC conversions
   - Simple 4/4 progression
   - 3/4 and 6/8 time signatures
   - Pickup bars with prefix rests
   - Complex example: `samples/youve-got-a-way.songml`

3. **Round-trip validation:** Parse ABC output with ABC tools
   - Use `abc2midi` or similar to verify ABC syntax validity
   - Visual inspection of rendered notation

4. **Edge cases:**
   - Empty bars (synthesized by parser)
   - Bars with no chords
   - Very short durations (0.5 beats)
   - Unknown chord symbols
   - Missing properties (defaults)

## Future Enhancements

- **Voice-based chord rendering:** Emit actual chord notes (using `chord_voicings.tsv`) as a playable voice
- **Melody integration:** If SongML adds melody notation, map to ABC note sequences
- **Repeat markers:** Map SongML section structure to ABC repeat syntax (`|:` `:||`)
- **Dynamics and articulation:** If added to SongML, convert to ABC annotations
- **Multiple voices:** Support harmony parts if SongML extends to multi-voice
- **Smart unit length:** Analyze document for smallest subdivision and compute optimal `L:`

## References

- **ABC Notation Standard:** http://abcnotation.com/wiki/abc:standard:v2.1
- **SongML Design Manifesto:** `docs/songml_design_manifesto.md`
- **SongML AST Structure:** `docs/songml-ast.md`
- **SongML MIDI Generation:** `docs/songml-midi-generation.md` (similar conversion logic)

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-12-19 | Use fixed formula `L: 1/(denom×2)` | Simple, predictable, handles half-beats |
| 2024-12-19 | Chord-annotation style (not voice) | Simpler implementation, readable output |
| 2024-12-19 | Pass through unknown chords | Follows SongML's forgiving philosophy |
| 2024-12-19 | No chord validation | ABC rendering will show issues naturally |
