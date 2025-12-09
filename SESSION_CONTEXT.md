# SongML Project - Session Context

## Project Overview

**SongML** is a text-based symbolic language for representing musical ideas (chord progressions, structure, lyrics) designed for human–AI–tool collaboration. It sits as a **semantic hub** between humans, LLMs, and digital audio tools (DAWs, notation software).

### Philosophy
- **Simple and forgiving** - More like a musician's leadsheet than formal notation
- **Text-based** - Version control friendly, easily editable
- **Lossy by design** - Captures intent, not performance fidelity
- **AI-friendly** - LLMs can read, write, and reason about SongML

## Key Documentation

Read these files for comprehensive context:

1. **`docs/songml_design_manifesto.md`** - Core philosophy and vision
2. **`docs/songml-syntax.md`** - Language specification and examples
3. **`docs/songml-ast.md`** - Abstract syntax tree structure with Mermaid diagrams
4. **`docs/songml-midi-generation.md`** - MIDI export implementation details

## Project Structure

```
songml/
├── docs/                          # Design documentation
├── samples/                       # Example .songml files
│   ├── wunderkind.songml
│   └── youve-got-a-way.songml
└── songml-utils/                  # Python utilities
    ├── src/songml_utils/
    │   ├── parser.py              # SongML → AST
    │   ├── ast.py                 # AST data structures
    │   ├── formatter.py           # AST → pretty SongML
    │   ├── validate.py            # Structural validation
    │   ├── midi_exporter.py       # AST → MIDI file
    │   ├── chord_voicings.py      # Chord symbol → MIDI notes
    │   └── data/
    │       └── chord_voicings.tsv # Literal chord-to-notes mapping (90+ chords)
    └── tests/                     # Comprehensive test suite
```

## Current State

### Implemented ✅
- **Parser** - SongML text → AST (handles bars, chords, timing, properties, sections)
- **Formatter** - AST → clean SongML text
- **Validator** - Structural checks with warnings
- **MIDI Export** - AST → .mid files for playback/DAW import
  - Table-based chord voicing (TSV lookup)
  - Special case: slash chords parsed to add bass note one octave below
  - Timing conversion: beats → MIDI ticks (480 PPQ)
  - Properties: Tempo, Time signature, Key, Title
- **CLI Tools** - `songml-format`, `songml-validate`, `songml-to-midi`
- **Tests** - Comprehensive coverage including real-world songs

### Key Design Decisions

1. **Chord voicing** - Mostly table-based (TSV file), with one pragmatic exception: slash chords like `C7/G` are parsed to extract bass note
2. **Timing model** - AST stores `start_beat` and `duration_beats` per chord; "last chord fills remaining bar space" rule
3. **Properties** - Key-value pairs (e.g., `Tempo: 120`) that apply to subsequent sections until changed
4. **Bar numbering** - Restarts in each section for human readability, but export uses absolute bar position for timeline continuity

## Example SongML

```
Title: Morning Coffee
Key: Fmaj
Tempo: 92
Time: 4/4

[Verse - 4 bars]
| Fmaj7 | Gm7.. C7 | Fmaj7 | Bbmaj7.. C7 |

[Chorus - 4 bars]
| Dm7.. G7 | Cmaj7.. A7 | Dm7 | G7 |
```

**Timing notation:**
- `.` = one beat
- `;` = half beat (pickup)
- `..` = two beats
- Last chord in bar fills remaining space

## What We're Working On

This is a **design and implementation** project. We build features incrementally:
- Design documentation (manifesto, syntax spec, architecture docs)
- Python implementation (parser, AST, transformations)
- Tests (unit tests, integration tests with real songs)
- Iterate based on real-world usage

### Recent Work
- Implemented MIDI export with chord voicing system
- Created comprehensive documentation for MIDI generation
- Added tests for slash chords with accidentals (e.g., `C#m7/G#`)
- Clarified design philosophy: mostly table-based with minimal parsing

## Usage Quick Reference

```bash
# Format a SongML file
songml-format input.songml

# Validate structure
songml-validate input.songml

# Export to MIDI
songml-to-midi input.songml output.mid
```

```python
# Python API
from songml_utils.parser import parse_songml
from songml_utils.midi_exporter import export_midi

doc = parse_songml(content)
export_midi(doc, 'output.mid')
```

## Important Notes for Future Sessions

- **Philosophy**: Simple, forgiving, AI-friendly. Avoid overengineering.
- **Documentation style**: Similar depth to existing docs, balance technical precision with readability
- **Testing**: Real-world songs in `samples/` drive implementation
- **Dependencies**: Minimal (currently just `mido` for MIDI)
- **Design authority**: Code is authoritative; plans/prompts may drift from implementation

---

**To get started in a new session:** Read the manifesto and syntax docs, then explore the relevant code/tests for the feature you're working on.
