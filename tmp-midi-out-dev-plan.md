Stabledog: Follow instructions in [plan-astAndParser.prompt.md](file:///c%3A/Projects/songml/docs/plan-astAndParser.prompt.md).
The attachments are context about "songml".  Let's focus on the AST created by #file:parser.py -- as the hub of translation between representations, I'd like to:
1. add a mermaid diagram which represents the AST design visually
2. Plan an addition to songml-utils which emits MIDI from the AST, such that one could ingest songml and emit MIDI.

GitHub Copilot: I'll research the codebase to understand the AST structure and then create a plan for adding a Mermaid diagram and MIDI emission capability. 

Read [](file:///c%3A/Projects/songml/songml-utils/src/songml_utils/ast.py)

Read [](file:///c%3A/Projects/songml/songml-utils/README.md)

Read [](file:///c%3A/Projects/songml/songml-utils/src/songml_utils)

Read [](file:///c%3A/Projects/songml/songml-utils/src/songml_utils/formatter.py)

Searched for regex `mido|pretty_midi|music21|miditoolkit` (`**/songml-utils/**`), no results

Read [](file:///c%3A/Projects/songml/songml-utils/pyproject.toml)

Searched codebase for "MIDI export conversion music generation chord to note midi library", 20 results

Now I have comprehensive context about the SongML AST structure. Let me create a plan for:
1. Adding a Mermaid diagram to visualize the AST
2. Planning a MIDI emission module

## Plan: AST Visualization and MIDI Export

Enhance songml-utils with a Mermaid class diagram documenting the AST structure and design a new MIDI export module to convert parsed SongML documents into playable MIDI files.

### Steps

#### 1. Create Mermaid diagram for AST in `docs/ast-diagram.md`

Add a Mermaid class diagram showing:
- All 7 dataclasses (`Document`, `Section`, `Bar`, `ChordToken`, `Property`, `TextBlock`, `ParseError`)
- Relationships: `Document` contains list of `Section|Property|TextBlock`, `Section` contains `Bar` list, `Bar` contains `ChordToken` list and optional lyrics
- Key attributes for each class (name, value, start_beat, duration_beats, etc.)
- Document property state flow and how properties affect section parsing

#### 2. Design `midi_exporter.py` module architecture

Create new file `songml_utils/midi_exporter.py` with:
- `export_midi(doc: Document, output_path: str, **options)` — main entry point
- `_ChordVoicer` class — converts opaque chord text to MIDI notes using music theory rules
- `_TimelineBuilder` class — converts AST timing (bars, beats) to absolute MIDI ticks
- Support for `Key`, `Tempo`, `Time` properties from document
- Configurable voicing strategies (root-only, triads, 4-note voicings, piano-style)

#### 3. Choose and integrate MIDI library dependency

Evaluate options:
- **mido** (lightweight, pure Python, good for simple MIDI generation)
- **music21** (heavyweight, comprehensive theory support, chord parsing)
- **pretty_midi** (performance-focused, clean API)

Recommendation: Start with **mido** for minimal dependencies, add optional `music21` integration for chord interpretation. Update pyproject.toml dependencies.

#### 4. Implement chord-to-notes voicing logic

Build `_ChordVoicer` to parse opaque chord text:
- Root note extraction (C, F#, Bb, etc.)
- Quality detection (maj, min, 7, dim, aug, etc.)
- Extension parsing (9, 11, 13, b9, #11, etc.)
- Slash chord bass note handling
- Fallback: if unparseable, use middle C (warning logged)
- Generate MIDI note numbers based on voicing strategy

#### 5. Build timeline and MIDI message generation

Implement `_TimelineBuilder`:
- Convert `Bar.number` and `ChordToken.start_beat`/`duration_beats` to absolute MIDI ticks
- Use `Tempo` property for ticks-per-beat calculation (default 480 PPQ)
- Handle `Time` signature for bar length calculation
- Generate MIDI track with: tempo map, time signature events, note on/off messages
- Set reasonable velocity (default 64), channel (default 0)

#### 6. Add CLI command and tests

Create:
- `songml-to-midi` script entry point in pyproject.toml
- CLI with options: `--voicing [root|triad|seventh|piano]`, `--velocity`, `--transpose`
- Test suite `tests/test_midi_exporter.py` covering:
  - Simple chord progression export
  - Timing accuracy (dots, semicolons)
  - Key/tempo/time signature handling
  - Unparseable chord fallback
  - Multi-section documents
  - Round-trip validation: export then re-import with music21

### Further Considerations

1. **Chord parsing complexity** — Start simple (basic triads/sevenths), expand incrementally. Consider optional `music21` integration for advanced parsing vs. keeping minimal dependencies with `mido` only?

2. **Voicing strategy** — Default to root-position triads (piano range C3-C5) or allow configuration? Consider adding `Instrument:` property support for future MIDI channel/program selection?

3. **Lyrics handling** — MIDI supports lyric meta-events. Include lyrics as MIDI text events or skip initially?

4. **Multiple tracks** — Current AST is single-voice. For MVP, generate single MIDI track. Future: support `Instrument:` sections or multi-track export from multiple SongML files?

---

**This is a draft plan for review.** Let me know if you'd like to adjust the voicing approach, library choice, or scope of the MIDI export features.
