# Plan: Design AST and Parser for SongML

Parse document as sequence of `TextBlock`, `Property`, and `Section` nodes. Single-pass parser with persistent property state (defaults: 4/4, Cmaj, 100 bpm, "Untitled"). Sections contain flat bar sequences. Row detection: digit in first cell = bar-numbers (required), otherwise = chords/lyrics. Properties terminate sections. Chords are opaque text. Last-chord-fills timing.

## Steps

### 1. Define AST node classes in `ast.py`

Create dataclasses: 
- `Document` (items: List[TextBlock | Property | Section], warnings: List[str])
- `TextBlock` (lines: List[str], line_number: int)
- `Property` (name: str, value: str, line_number: int)
- `Section` (name: str, bar_count: int, bars: List[Bar], line_number: int)
- `Bar` (number: int, chords: List[ChordToken], lyrics: Optional[str], line_number: int)
- `ChordToken` (text: str, start_beat: float, duration_beats: float)
- `ParseError` (message: str, line_number: int)

### 2. Implement single-pass parser in `parser.py`

Initialize property state (`Time: 4/4`, `Key: Cmaj`, `Tempo: 100`, `Title: Untitled`). Scan lines: 
- `PropertyName: value` → terminate current section, create `Property`, update state
- `[Section - N bars]` → start section
- text/comments → `TextBlock`

Track section names, warn on duplicates. Raise error on empty sections.

### 3. Build section parser with strict row detection

Parse `[Name - N bars]` header (raise if no count). Parse bar-delimited rows: 
- First cell starts with digit = bar-numbers (first cell must have int, sets counter, auto-increment left-to-right, validate cells with numbers)
- Next row = chords
- Optional next row without digit first cell = lyrics
- Repeat for multi-group

Split on `|`, validate delimiter counts match. Flatten into single bar sequence, synthesize empty bars if total < N, raise if > N or if no bars found.

### 4. Implement last-chord-fills timing with overflow detection

For non-empty bars: split chord cell on whitespace into opaque text tokens. Parse timing markers: 
- `.` = 1 beat
- `;` suffix = +0.5 to previous beats (e.g., `...;F` = 3.5 beats rest then F)

Calculate `start_beat` sequentially. Unmarked chords: first N-1 get 1 beat, last fills remaining. Extract beats-per-bar from `Time:` (validate denominator is 4 or 8). Raise `ParseError` immediately if beats exceed time signature before last chord.

### 5. Create comprehensive test suite in `test_parser.py`

Test:
- Property defaults/state persistence
- Property terminates section
- Multi-group flattening
- Bar-number detection (require digit first cell)
- Bar counter (first cell sets start, increment, validate)
- Lyric detection (non-digit after chords)
- Delimiter matching
- Last-chord-fills (4/4, 3/4, 6/8)
- Semicolon timing (`...;F`, `C;`)
- Empty bars
- Empty section error
- Duplicate section warning
- Invalid time signature (reject 5/7)
- Beat overflow
- Validate against `youve-got-a-way.songml`

### 6. Validate AST design sufficiency

After tests pass, confirm AST enables round-tripping:
- `ChordToken.text`/`start_beat`/`duration_beats` reconstruct timing
- `Bar.number` preserves sequence
- `Document.items` preserves ordering
- `Document.warnings` for non-fatal issues

Document any gaps discovered during testing before implementing formatter.

## Key Design Decisions

1. **Property state is persistent** — Once set, properties apply to all subsequent sections until changed. Defaults: `Time: 4/4`, `Key: Cmaj`, `Tempo: 100`, `Title: Untitled`.

2. **Row detection is deterministic** — Bar-delimited row with digit in first cell = bar-numbers (required for section), otherwise = chords/lyrics depending on position.

3. **Bar numbers auto-increment** — First cell in bar-number row sets starting number, subsequent cells auto-increment (validate if cell contains number).

4. **Multi-group sections flatten** — Visual layout groups (multiple bar-number/chord/lyric sets) flatten into single sequential bar list in AST.

5. **Chords are opaque text** — Parser does not interpret chord symbols (root, quality, extensions). Just space-delimited text tokens.

6. **Last-chord-fills timing** — Unmarked chords: first N-1 get 1 beat each, last chord fills remaining beats in bar.

7. **Semicolon suffix notation** — `...;F` = 3.5 beats before F starts. `;F` = 0.5 beats before F. The `;` adds 0.5 to previous beat count.

8. **Time signature validation** — Accept only denominators 4 or 8. Numerator = beats per bar (e.g., 6/8 = 6 beats).

9. **Properties terminate sections** — Encountering a property line ends current section parsing.

10. **Empty sections are errors** — Section must have at least one bar-number/chord row. Synthesize empty bars only if declared count > parsed count.

11. **Strict delimiter matching** — Bar-number, chord, and lyric rows must have same number of `|` delimiters.

12. **Fail fast with clear errors** — Parser raises `ParseError` with line number on structural issues. No recovery attempts.

## Examples

### Basic section with timing
```
[Verse - 4 bars]
| 0 | 1 | 2 | 3 |
| C.. F.. | G.... | Am.. Dm.. | C.... |
| Hello world | music time | how are you | doing today |
```

Result: 4 bars, bar 0: C(2 beats) F(2 beats), bar 1: G(4 beats), etc.

### Half-beat pickup
```
[Intro - 2 bars]
| 0 | 1 |
| ...;F | F.... |
```

Result: Bar 0: F starts at beat 3.5, duration 0.5 beats. Bar 1: F for 4 beats.

### Multi-group section (flattened)
```
[Verse - 6 bars]
| 0 | 1 | 2 |
| C | F | G |
| She sells sea |

| 3 | 4 | 5 |
| Dm | Am | G |
| shells by the sea |
```

Result: Single section with 6 bars sequentially numbered 0-5.

### Implicit timing (last-chord-fills)
```
[Chorus - 1 bar]
| 0 |
| C F G |
```

Result in 4/4: C=1 beat, F=1 beat, G=2 beats (fills remaining).
Result in 3/4: C=1 beat, F=1 beat, G=1 beat.
Result in 6/8: C=1 beat, F=1 beat, G=4 beats (fills remaining).

### Property state persistence
```
Title: My Song
Key: Cmaj
Time: 4/4

[Verse - 2 bars]
| 0 | 1 |
| C | F |

Key: Gmaj

[Chorus - 2 bars]
| 2 | 3 |
| G | D |
```

Result: Verse uses Cmaj, Chorus uses Gmaj (property persists after change). Time: 4/4 applies to both.
