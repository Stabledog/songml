# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands run from `songml-utils/`:

```bash
# Install for development
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_parser.py -v

# Run tests matching a pattern
pytest -k "test_name"

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Manual CLI testing
songml-validate ../samples/youve-got-a-way.songml
songml-format ../samples/youve-got-a-way.songml
songml-to-midi ../samples/youve-got-a-way.songml output.mid
```

## Architecture

SongML is a text-based symbolic language for music, acting as a hub between humans, AI, and music tools (MIDI, DAWs, notation software). The data flow is:

```
text → Parser → AST → Formatter → text
                   ↓
              MIDI Exporter → .mid
              ABC Exporter  → .abc
              Validator     → diagnostics (JSON to stdout, warnings to stderr)
```

**AST hierarchy:** `Document` → `Section[]` → `Bar[]` → `ChordToken[]`

Key modules in `songml-utils/src/songml_utils/`:

| Module | Purpose |
|--------|---------|
| `ast.py` | Frozen dataclasses: `Document`, `Section`, `Bar`, `ChordToken`, `Property`, `TextBlock` |
| `parser.py` | `parse_songml(text) -> Document` — single-pass, permissive |
| `formatter.py` | `format_songml()` — reconstructs clean SongML with aligned bar columns |
| `midi_exporter.py` | `export_midi(doc, path)` — MIDI via `mido`; fixed PPQ=480, velocity=64, root octave=3 |
| `abc_exporter.py` | `to_abc_string(doc)` / `export_abc(doc, path)` — ABC notation |
| `validate.py` | CLI: parses AST to JSON, warns about structural issues |
| `chord_voicings.py` | Loads `data/chord_voicings.tsv` → maps chord symbols to MIDI note offsets |

## Key Design Decisions

- **Permissive parsing, helpful validation**: Parsers accept anything roughly the right shape. Validators warn with line numbers but don't reject.
- **Timing inference**: Chords without explicit markers split the bar evenly. Last chord fills remaining space. `.` = 1 beat, `;` = 0.5 beat, `...` = silence/rest.
- **Slash chords**: Only parsing exception — split on `/` to extract bass note.
- **Chord voicings**: Add new chords by editing `data/chord_voicings.tsv` only (TSV: `ChordSymbol<TAB>Root<TAB>offset1,offset2,...`). No code changes needed.
- **Lossy by design**: Translation *into* SongML accepts information loss (intent over fidelity). Translation *from* SongML is generative.

## Python Style

Requires **Python 3.12+**. Use modern syntax:

- `type` keyword for type aliases (not `typing.TypeAlias`)
- Built-in generics (`list[str]`, `dict[str, int]`) not `typing` imports
- **Name complex types** rather than embedding them in function signatures:

```python
# Bad
def export(events: list[tuple[int, str, list[int]]]) -> None: ...

# Good
type MidiEvent = tuple[int, str, list[int]]
def export(events: list[MidiEvent]) -> None: ...
```

## Reference Files

- `docs/songml-syntax.md` — syntax specification
- `docs/songml-ast.md` — AST structure and data flow diagrams
- `docs/songml_design_manifesto.md` — core philosophy
- `samples/youve-got-a-way.songml` — real example with pickup beats, slash chords, and lyrics
