# SongML Copilot Instructions

## Repository Overview

This repository focuses on **SongML** — a text-based symbolic language for expressing music, designed as a creative interchange layer between humans, AI, and music production tools (DAWs, notation software, MIDI).

SongML is a tool for the age of AI: without being focused on strict linguistic rules, it's fairly relaxed and forgiving. In most cases, both LLMs and humans can understand, and any tools which consume or produce it are designed with this "sloppiness" in mind.

## Project Structure

```
songml/
├── .github/
│   └── copilot-instructions.md     # This file
├── docs/
│   ├── songml_design_manifesto.md  # Core design philosophy and principles
│   ├── songml-syntax.md            # Semi-formal syntax specification
│   ├── songml-ast.md               # AST structure and data flow
│   ├── songml-midi-generation.md   # MIDI export implementation
│   └── songml-create.md            # Project creation tool docs
├── samples/
│   └── youve-got-a-way.songml      # Real-world example song
├── songml-utils/
│   ├── src/songml_utils/           # Python implementation
│   ├── tests/                      # Test suite
│   └── pyproject.toml              # Python package config
└── README.md
```

## Core Philosophy

**SongML prioritizes simplicity and intent over fidelity.**

### Guiding Principles

1. **Readable by humans** — Looks like a structured leadsheet, not code
2. **Writable by LLMs** — Stable, consistent grammar; no heavy schema
3. **Lossy by design** — Translation into SongML accepts information loss; it favors clarity and intent
4. **Reconstructive, not reversible** — Translation from SongML into MIDI, XML, etc. is generative
5. **AI-assisted** — Semantic inference and reconciliation are delegated to LLMs, not hand-coded rules
6. **Forgiving** — Validators warn about problems but are permissive in what they accept
7. **Inspectable** — Plain text, version control friendly

**In short:** SongML is not about preserving data — it's about preserving *intent*.

## Language Overview

### Basic Structure

A SongML file contains:
1. **Properties** (optional header info like Title, Key, Tempo, Time)
2. **Sections** (the actual music with bar-delimited chord progressions)
3. **Free-form notes** (comments and explanatory text)

### Key Syntax Elements

- **Properties**: `PropertyName: value` (e.g., `Key: Fmaj`, `Tempo: 104`)
- **Sections**: `[Section Name - N bars]` (bar count is required)
- **Bar delimiters**: `|` marks bar boundaries
- **Chords**: Standard notation (C, Dm7, Fmaj7, G7b9, C/E)
- **Timing markers**:
  - `.` = one beat
  - `;` = half beat
  - `...` = silence/rest (e.g., `...;F` means rest for 3.5 beats, then F on beat 4-and)
  - No markers = chords split the bar evenly
  - Last chord fills remaining space
- **Comments**: `//` for end-of-line comments
- **Lyrics**: Write on separate line aligned with chord row

### Example

```songml
Title: Morning Coffee
Key: Fmaj
Tempo: 92
Time: 4/4

[Intro - 4 bars]
|      0      |   1   |  2    |   3        |
| ...;Fmaj7   | G7    | Am    | Bbmaj7.... |

[Verse 1 - 4 bars]
| F..  F9/A  Abdim7/B | Am7/E                                | Bb6  Dm7/A | Gm  C7     |
| You've got a way    | I just knew how to follow but it was | good       | The light  |
```

## Technical Implementation

### Technology Stack

- **Language**: Python 3.13+
- **Dependencies**:
  - `mido` (MIDI file generation)
  - `pychord` (chord parsing utilities)
- **Test Framework**: pytest
- **Build System**: setuptools

### Key Components

1. **Parser** (`songml-utils/src/songml_utils/parser.py`): Parses SongML text into AST
2. **AST** (see `docs/songml-ast.md`): Document → Sections → Bars → ChordTokens
3. **Formatter** (`songml-utils/src/songml_utils/formatter.py`): Reconstructs clean SongML from AST
4. **MIDI Exporter** (`songml-utils/src/songml_utils/midi_exporter.py`): Converts AST to playable MIDI files
5. **Validator** (`songml-utils/src/songml_utils/validate.py`): Checks structure and semantics (warns, doesn't reject)
6. **Chord Voicings** (`songml-utils/src/songml_utils/chord_voicings.py` + `songml-utils/src/songml_utils/data/chord_voicings.tsv`): Maps chord symbols to MIDI notes

### CLI Tools

- `songml-create` — Create new SongML projects with templates
- `songml-format` — Format and clean SongML files
- `songml-validate` — Validate syntax and structure
- `songml-to-midi` — Export to MIDI format
- `songml-bashcompletion` — Generate bash completion scripts

## Coding Principles

### Python Version

**This project requires Python 3.13+.** Use modern Python syntax:
- Use `type` keyword for type aliases (not `typing.TypeAlias`)
- Use built-in generic types (`list`, `dict`) not typing imports
- Leverage Python 3.13+ features where appropriate

### Type Annotations

**Don't use complex types in function signatures.** Use `type` keyword to give domain meaning:

```python
# ❌ Bad: Unreadable, semantics are obscured
def get_foo(input: list[tuple[int, list[str]]]) -> tuple[str, str]:
    ...

# ✅ Good: Readable, semantically meaningful
type CustomerNotes = list[str]
type CustomerIndex = tuple[int, CustomerNotes]
type CustomerIndexes = list[CustomerIndex]
type FooResult = tuple[str, str]

def get_foo(indexes: CustomerIndexes) -> FooResult:
    ...
```

### Testing

- **Always test complex logic**
- If logic is entangled with hard-to-test dependencies, isolate it through:
  - Redesign
  - Monkey-patching
  - Mocking
- Tests are essential to allow the application to evolve safely
- Run tests with: `cd songml-utils && pytest`

### Design Patterns

1. **Table-driven logic** — Prefer data tables (like `chord_voicings.tsv`) over complex parsing
2. **Minimal parsing** — Only parse what's necessary (e.g., slash chords for bass notes)
3. **Best-effort validation** — Warn about issues but accept permissive input
4. **Semantic compression** — Reduce information to capture intent, not every detail
5. **Round-trip capability** — AST should preserve enough info for reconstruction

## Key Design Decisions

### MIDI Export

- **Fixed PPQ = 480** (standard MIDI resolution)
- **Fixed velocity = 64** (neutral dynamics)
- **Single track** (matches single-voice chord progression model)
- **Root octave = 3** (places chords in audible piano range)
- **TSV voicing table** — Predictable, inspectable, extensible
- **Slash chord parsing** — Only parsing exception; splits on `/` to add bass note

### Validation vs. Parsing

- **Parsers should be permissive**: Accept anything roughly the right shape
- **Validators should be helpful**: Warn about issues with line numbers and suggestions
- **Translation tools** can be stricter and abort on ambiguity

### Timing Inference

- Chords without explicit timing split the bar evenly
- **Last chord fills remaining space** (key rule)
- Supports pickup beats with `...;` notation
- Bar numbers are sequential across sections for continuous timeline

## Working with this Repository

### Before Making Changes

1. Review relevant documentation in `docs/`
2. Look at `samples/youve-got-a-way.songml` for real-world examples
3. Run existing tests: `cd songml-utils && pytest tests/`
4. Check code style and type hints

### When Adding Features

1. **Start minimal** — Add complexity only when needed
2. **Preserve philosophy** — Keep it human-readable and forgiving
3. **Update docs** — If changing syntax or behavior, update relevant docs
4. **Add tests** — Test complex logic and edge cases
5. **Consider AI use case** — Will LLMs be able to work with this?

### When Fixing Bugs

1. **Write a test** that demonstrates the bug
2. **Fix minimally** — Change as little as possible
3. **Verify round-trip** — Ensure parse → format → parse still works
4. **Check real examples** — Test against `samples/youve-got-a-way.songml`

### File Organization

- Put implementation in `songml-utils/src/songml_utils/`
- Put tests in `songml-utils/tests/`
- Put data files (like TSV tables) in `songml-utils/src/songml_utils/data/`
- Put documentation in `docs/`
- Put examples in `samples/`

## Common Tasks

### Running Tests

```bash
cd songml-utils
pytest                    # Run all tests
pytest tests/test_parser.py -v  # Run specific test file
pytest -k "test_name"     # Run tests matching pattern
```

### Testing Changes Manually

```bash
cd songml-utils
pip install -e .          # Install in development mode

# Test the tools
songml-create "Test Song" C
songml-validate ../samples/youve-got-a-way.songml
songml-format ../samples/youve-got-a-way.songml
songml-to-midi ../samples/youve-got-a-way.songml output.mid
```

### Adding New Chord Voicings

Edit `songml-utils/src/songml_utils/data/chord_voicings.tsv`:

```tsv
ChordSymbol<TAB>Root<TAB>Offset1,Offset2,...
Cmaj13<TAB>C<TAB>0,4,7,11,14,17,21
```

No code changes needed; slash chords work automatically.

## Important Files to Reference

1. **`docs/songml-syntax.md`** — Semi-formal syntax specification
2. **`docs/songml_design_manifesto.md`** — Core philosophy and vision
3. **`docs/songml-ast.md`** — AST structure and data flow diagrams
4. **`docs/songml-midi-generation.md`** — Detailed MIDI export design
5. **`samples/youve-got-a-way.songml`** — Real song example with pickups, slash chords, lyrics

## What SongML Is NOT

- **Not a full MIDI serialization** — Doesn't capture note-level dynamics or articulation
- **Not notation software** — Doesn't handle engraving, layout, or exact rhythmic placement
- **Not a DAW replacement** — Doesn't manage audio, effects, or production details
- **Not a formal grammar** — Deliberately flexible and forgiving

## What SongML IS

- **A creative hub** for human-AI-tool collaboration
- **A leadsheet format** optimized for editing and intent
- **A text-based interchange layer** between composition tools
- **A semantic representation** that preserves musical structure and meaning

---

When in doubt, refer to the principle: **If a human can read it and understand the intent, it's valid SongML.**
