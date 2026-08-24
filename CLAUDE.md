# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Two Clones — Read This First

This repo (wherever you cloned it, e.g. `~/workarea/music-tools/songml`) is the **dev/maintenance tree**: edit, test, commit, and release from here.

A **separate clone** lives at `~/workarea/songml`, hardcoded into `~/.local/bin/songml/setup.sh` (the `songml` dotkit). Running `setup.sh songml` `git pull --ff-only`s that clone and `pip install -e ".[dev]" --user`s it into the global environment — that clone is what actually backs the `songml-*` commands on `PATH` system-wide.

Consequences:

- **Never hand-edit `~/workarea/songml`.** Anything there should only ever arrive via `git pull` of what you already committed+pushed from this tree. Stray local edits found there are safe to discard as long as they match (or are superseded by) `origin/main` — they're not a second copy of anyone's work, just install state that fell behind.
- **Bare `songml-*` commands, `pytest`, or `python3 -m songml_utils...` run from this repo still execute the *other* clone's installed code**, not your local edits here. Check with `songml-version`, or `python3 -c "import songml_utils; print(songml_utils.__file__)"`. To actually exercise local changes, run everything through `uv run` (see Commands below) or go through the full release + reinstall cycle (see Release Workflow).
- This includes `bin/test-serve.sh` (see Repository Layout) — it shells out to the global `songml-serve` binary, so it reflects the *other* clone too.

## Commands

All commands run from `songml-utils/`, through `uv` so they use this tree's own `.venv` and actually exercise your local edits (see caveat above):

```bash
# Run all tests
uv run --extra dev pytest
# equivalent: make test   (from repo root)

# Run a single test file
uv run --extra dev pytest tests/test_parser.py -v

# Run tests matching a pattern
uv run --extra dev pytest -k "test_name"

# Lint and format
uv run --extra dev ruff check src/ tests/
uv run --extra dev ruff format src/ tests/
# equivalent lint check: make lint   (from repo root)

# Manual CLI testing (via the local venv — bare `songml-*` on PATH hits the other clone)
uv run songml-create "Song Name" C       # scaffold a new .songml file from a template
uv run songml-validate ../samples/youve-got-a-way.songml
uv run songml-format ../samples/youve-got-a-way.songml
uv run songml-to-midi ../samples/youve-got-a-way.songml output.mid [--transpose N]
uv run songml-to-abc ../samples/youve-got-a-way.songml output.abc [--transpose N]
uv run songml-inspect-midi output.mid [-v]
uv run songml-serve --root ../samples [--port 8000] [--bars-per-row 8] [--reload] [--force-port-grab]
uv run songml-bashcompletion              # emit a bash completion script
uv run songml-version                     # print this venv's songml-utils version (x.y.z)

# Ableton chord-track pipeline (separate from the .songml format above)
uv run als-extract song.als > chords.txt  # extract CHORD track from an Ableton .als into a chord sheet
uv run chords-to-midi chords.txt output.mid [--transpose N]
```

## Release Workflow

`make` targets, run from the repo root (`Makefile` wraps `uv run` for testing and drives the reinstall):

| Target | Does |
|--------|------|
| `make test` | `uv run --extra dev pytest` |
| `make lint` | `uv run --extra dev ruff check src/ tests/` |
| `make bump-version` | Bumps the patch version in `songml-utils/src/songml_utils/__init__.py` (the single source of truth for the package version) |
| `make release` | Runs `bump-version`, commits **only the version file**, pushes to `origin main`, then runs `reinstall` |
| `make reinstall` | `git -C ~/.local/bin pull && setup.sh songml` — re-pulls and reinstalls the *other* clone (`~/workarea/songml`) from `origin/main`, updating the `songml-*` commands on `PATH` |

**Commit your actual code changes yourself before running `make release`.** Its commit step only `git add`s the version file — uncommitted feature/fix changes are silently left behind (not included in the push, not reverted either — just still sitting there uncommitted).

Normal flow: edit here → `uv run --extra dev pytest` (or `make test`) → commit your changes → `make release`. If `make reinstall` (or the tail end of `make release`) fails with a fast-forward error on `~/workarea/songml`, it means that clone has stray local edits blocking the pull — verify they're superseded by what you just pushed (`git diff origin/main -- <file>` from inside `~/workarea/songml` should be empty), then discard them there and re-run `make reinstall`.

## Repository Layout

All Python code and packaging lives in `songml-utils/` (single package, `songml_utils`). The other top-level directories are not separate subprojects:

- `docs/` — SongML language and design docs (see Reference Files below)
- `samples/` — example `.songml` files
- `abc-test/` — scratch ABC-notation files used to test rendering, not part of the package
- `ableton-chord-extract/` — scratch notes for `als-extract`/`chords-to-midi` development, not part of the package
- `bin/test-serve.sh` — start/stop/bounce a *dev* `songml-serve` instance (`start`/`stop`/`bounce`/`status`), default port 8081 (override with `SONGML_TEST_SERVE_PORT`); stop/bounce only ever kill whatever's bound to that port, so it's safe to use alongside the production instance on port 8080 (see README's "On the Stablebeast Coder workspace"). Invokes the global `songml-serve` binary — see the two-clones caveat above.

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
