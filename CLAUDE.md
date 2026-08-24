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
songml-create "Song Name" C              # scaffold a new .songml file from a template
songml-validate ../samples/youve-got-a-way.songml
songml-format ../samples/youve-got-a-way.songml
songml-to-midi ../samples/youve-got-a-way.songml output.mid [--transpose N]
songml-to-abc ../samples/youve-got-a-way.songml output.abc [--transpose N]
songml-inspect-midi output.mid [-v]
songml-serve --root ../samples [--port 8000] [--bars-per-row 8] [--reload] [--force-port-grab]
songml-bashcompletion                    # emit a bash completion script
songml-version                           # print the installed songml-utils version (x.y.z)

# Ableton chord-track pipeline (separate from the .songml format above)
als-extract song.als > chords.txt        # extract CHORD track from an Ableton .als into a chord sheet
chords-to-midi chords.txt output.mid [--transpose N]
```

## Repository Layout

All Python code and packaging lives in `songml-utils/` (single package, `songml_utils`). The other top-level directories are not separate subprojects:

- `docs/` — SongML language and design docs (see Reference Files below)
- `samples/` — example `.songml` files
- `abc-test/` — scratch ABC-notation files used to test rendering, not part of the package
- `ableton-chord-extract/` — scratch notes for `als-extract`/`chords-to-midi` development, not part of the package

## Architecture

SongML is a text-based symbolic language for music, acting as a hub between humans, AI, and music tools (MIDI, DAWs, notation software). There are two parallel data flows:

**SongML flow** — the primary language, hand-written or LLM-written `.songml` files:

```
text → Parser → AST → Formatter → text
                   ↓
              MIDI Exporter    → .mid
              ABC Exporter     → .abc
              HTML Exporter    → beat-grid chord chart (also served live by songml-serve)
              Validator        → diagnostics (JSON to stdout, warnings to stderr)
```

**Ableton chord-track flow** — a separate pipeline for pulling chord progressions out of Ableton Live sets, independent of the SongML AST:

```
.als (gzipped XML) → als_parser.extract_chord_clips → chord sheet (text) → chords_midi_cli → .mid
```

The chord sheet is a human-editable intermediate format (bar:beat, chord, duration-in-beats) so FIXME lines flagging ambiguous compound chord names can be resolved by hand before MIDI export. See the docstring in `chord_sheet.py` for the format.

**AST hierarchy (SongML flow only):** `Document` → `Section[]` → `Bar[]` → `ChordToken[]`

Key modules in `songml-utils/src/songml_utils/`:

| Module | Purpose |
|--------|---------|
| `ast.py` | Frozen dataclasses: `Document`, `Section`, `Bar`, `ChordToken`, `Property`, `TextBlock` |
| `parser.py` | `parse_songml(text) -> Document` — single-pass, permissive |
| `formatter.py` | `format_songml()` — reconstructs clean SongML with aligned bar columns; also `songml-format` CLI |
| `create.py` | `songml-create` CLI — scaffolds a new `.songml` file from `data/templates/` for a given key |
| `midi_exporter.py` | `export_midi(doc, path, transpose=...)` — MIDI via `mido`; fixed PPQ=480, velocity=64, root octave=3 |
| `abc_exporter.py` | `to_abc_string(doc, transpose=...)` / `export_abc(doc, path)` — ABC notation |
| `html_exporter.py` | `to_html_string(doc, bars_per_row=...)` — renders a beat-grid chord chart as standalone HTML |
| `web_server.py` | `songml-serve` CLI — LAN `ThreadingHTTPServer` that lists `.songml` files under `--root` and serves them as HTML chord charts and MIDI downloads; `--reload` re-parses on each request for live editing; `--force-port-grab` kills whatever process is listening on `--port` (SIGTERM then SIGKILL) and takes it over |
| `validate.py` | CLI: parses AST to JSON, warns about structural issues |
| `midi_inspector.py` / `midi_inspector_cli.py` | `songml-inspect-midi` CLI — reports tempo, time/key signature, notes, and instruments from a `.mid` file via `pretty_midi` |
| `chord_voicings.py` | Loads `data/chord_voicings.tsv` → maps chord symbols to MIDI note offsets; shared by MIDI/ABC export and the Ableton pipeline |
| `voicing_validator.py` | Validates `chord_voicings.tsv` entries against `pychord` music theory; standalone `data/voicing-validator.py` script wraps it for one-off table checks |
| `als_parser.py` | `extract_chord_clips(als_path)` — parses the gzipped-XML `.als` format, finds the CHORD track, and emits `ChordEntry`/`FixmeEntry` objects |
| `als_cli.py` | `als-extract` CLI — writes an `.als` CHORD track out as a chord sheet |
| `chord_sheet.py` | `format_sheet()` / `parse_sheet()` — read/write the intermediate chord sheet text format |
| `chords_midi_cli.py` | `chords-to-midi` CLI — converts a chord sheet directly to MIDI, bypassing the SongML AST |
| `bashcompletion.py` | `songml-bashcompletion` CLI — emits `data/bash_completion.sh` for all `songml-*`/`als-extract`/`chords-to-midi` commands |
| `version_cli.py` | `songml-version` CLI — prints `songml_utils.__version__` (x.y.z), the package's single source of truth (`pyproject.toml` reads it dynamically); use to tell which clone/install a `songml-*` command on `PATH` is actually running |

## Key Design Decisions

- **Permissive parsing, helpful validation**: Parsers accept anything roughly the right shape. Validators warn with line numbers but don't reject.
- **Timing inference**: Chords without explicit markers split the bar evenly. Last chord fills remaining space. `.` = 1 beat, `;` = 0.5 beat, `...` = silence/rest.
- **Slash chords**: Only parsing exception — split on `/` to extract bass note.
- **Chord voicings**: Add new chords by editing `data/chord_voicings.tsv` only (TSV: `ChordSymbol<TAB>Root<TAB>offset1,offset2,...`). No code changes needed. Validate the table with `voicing_validator.py`.
- **Lossy by design**: Translation *into* SongML accepts information loss (intent over fidelity). Translation *from* SongML is generative.
- **Chord sheet is a checkpoint, not a format**: it exists so a human can fix ambiguous `.als` compound-chord extraction (see FIXME lines) before committing to MIDI — it's not meant to round-trip back into SongML.

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
- `docs/songml-create.md` — `songml-create` usage
- `docs/songml-midi-generation.md` — MIDI export design
- `docs/songml-to-abc.md` — ABC export design
- `samples/youve-got-a-way.songml` — real example with pickup beats, slash chords, and lyrics
