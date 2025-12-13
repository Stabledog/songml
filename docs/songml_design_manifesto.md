# SongML Design Manifesto — A Human–AI Composition Hub

## 1. Problem Statement

Modern composition tools fragment the creative process:

- **DAWs** excel at capturing and arranging performances, but they are cumbersome for structural edits or conceptual revisions.
- **Notation tools** (Sibelius, Dorico, MuseScore) are optimized for engraving, not for fluid idea development.
- **LLMs and AI assistants** can reason about musical form, but lack a symbolic language that bridges human-readable and machine-actionable representations.

This creates a semantic gap: human \u2194 LLM \u2194 DAW \u2194 notation tools all speak incompatible dialects of “music data.”

SongML aims to bridge that gap by introducing a **text-based symbolic hub** designed for collaboration between humans, AIs, and existing tools.

---

## 2. Design Philosophy

**SongML prioritizes simplicity and intent over fidelity.**

It does not seek to be a full serialization of musical performance (like MIDI) or engraving (like MusicXML). Instead, it captures the *editable musical idea* — sections, chord progressions, key, tempo, lyrics, and broad structure — in a compact text format that both humans and LLMs can reliably read, edit, and regenerate.

### Guiding Principles
- **Readable by humans.** Looks like a structured leadsheet, not code.
- **Writable by LLMs.** Stable, consistent grammar; no heavy schema.
- **Lossy by design.** Translation *into* SongML accepts information loss; it favors clarity and intent.
- **Reconstructive, not reversible.** Translation *from* SongML into MIDI, XML, etc. is generative.
- **AI-assisted.** Semantic inference and reconciliation are delegated to LLMs, not hand-coded rules.

---

## 3. Architecture Overview

```
             [MusicXML]    [LilyPond]
                  ↑              ↑
                  |              |
[ABC] ⇄ [SONGML] ⇄ [MIDI] ⇄ [DAW]
                  |
                  ↓
             [AI / LLM Layer]
```

### Roles
- **SongML (the hub):** Text-based symbolic representation.
- **Spokes:** Existing ecosystems (DAWs, notation, performance data).
- **Converters:** Small, scriptable tools to translate to/from SongML.
- **LLM layer:** Performs semantic compression, editing, and reconciliation.

---

## 4. The Project Bundle

SongML works within a *project scope* — a simple folder bundle that groups human-readable and machine-reference data:

```
mysong/
 ├── songml/skylight.songml
 ├── sources/
 │   ├── drums.mid
 │   ├── bass.mid
 │   ├── keys.mid
 │   └── vox.mid
 └── meta/
     ├── conversion-map.json
     └── timeline.json
```

- **`songml/`**: Editable core file(s) for structure and content.
- **`sources/`**: Original performance or notation data.
- **`meta/`**: Correlation data, version notes, timestamps, section offsets.

Humans edit the SongML; LLMs reconcile and maintain metadata.

---

## 5. Example Representation

```
# Title: Skylight
# Key: F major
# Tempo: 92
# Time: 4/4
// Example for songml syntax development.  Musically this is junk.
/*  We do comments C++ style: blocks or // end-of-line snippets

[Verse 1]
Bar start: 8
| Fmaj7 | Gm7.. C7 | Fmaj7 | Bbmaj7.. C7 | // Borinnngg...
Lyrics: "Some - where | there's a | sky - light | " 

[Chorus]
Bar start: 32
Key: continue
| Dm7..  G7 | Cmaj7..  A7 | Dm7 | G7 |

[Outro] // Key is tbd
| V7..VI+ | IVmaj7 | III6 | Imaj7add9 |


@annotations:
  sources: ["keys.mid", "bass.mid"]
  times: ["01:23.400–01:40.200"]
  confidence: 0.88
```

Readable by musicians, editable by humans or LLMs, and trivially diffable in version control.

---

## 6. Workflow Example

### Import (semantic reduction)
1. User exports multiple DAW tracks as MIDI.
2. The `midi-to-songml` tool submits the files to an LLM along with SongML documentation.
3. The model analyzes, merges, and emits SongML plus annotations linking back to original files and timecodes.

### Edit (human creativity)
- The songwriter revises structure, chord changes, or lyrics directly in the text.

### Reconcile (semantic regeneration)
1. The revised SongML is sent back to the LLM with the original metadata.
2. The model generates DAW-edit instructions or updated MIDI files to match the new structure.

Result: a closed loop of human and AI collaboration around a clean, inspectable text layer.

---

## 7. Information Model

### Core Elements
- **Header:** title, key, tempo, time signature, composer, notes.
- **Sections:** labeled blocks with chords, melodies, lyrics, comments.
- **Annotations:** cross-reference data, confidence, and conversion metadata.

### Optional Extensions
- Performance markings, groove references, instrument tags.
- LLM-generated summaries or TODOs (e.g., `@ai_note:`).

### Deliberate Omissions
- Note-level dynamics, articulation, controller data.
- Exact rhythmic placement below the bar level.

SongML remains conceptually closer to a jazz chart than a DAW session.

---

## Coding principles:

- Don't use complex types in function signatures, e.g. 
  ```python
  def get_foo(input: list[tuple[int, list[str]]]) -> tuple[str, str]:
     ...  # ick. Unreadable, semantics are obscured
  ```

  Instead, use `TypeAlias` to give domain meaning:
  
  ```python
  from typing import TypeAlias
  
  CustomerNotes: TypeAlias = list[str]
  CustomerIndex: TypeAlias = tuple[int, CustomerNotes]
  CustomerIndexes: TypeAlias = list[CustomerIndex]

  def get_foo(indexes: CustomerIndexes) -> FooResult:
    ...  # Yes. Now I have some idea what this thing is doing.
  ```

- Always test complex logic.  If the logic is entangled with dependencies that are hard to test, isolate the complex logic from the dependencies with redesign, or monkey-patching, or mocking.   Tests are essential to allow the application to evolve safely.


## 8. The Human–AI Contract

| Layer | Function | Actor |
|--------|-----------|-------|
| **SongML** | Expressive, editable representation of musical ideas | Human + LLM |
| **Metadata** | Technical correlations, file references, version deltas | LLM / scripts |
| **Spokes** | Rendering and playback | DAW / notation tools |

SongML is not a high-fidelity storage format. It is a **creative interchange layer** where the human’s edits drive the AI’s reconstruction of detailed data.

---

## 9. Future Work

- Define a minimal grammar for SongML (tokens, indentation, quoting rules).
- Build prototype translators using `music21` or `miditoolkit` for MIDI import/export.
- Define reconciliation prompt templates for LLMs ("given old + new SongML, update metadata").
- Explore OSC or Ableton Live API bridges for automatic DAW synchronization.

---

## 10. Summary

SongML provides a text-based **semantic hub** for music composition that:
- Unifies humans, AIs, and digital tools under one editable format.
- Accepts information loss in favor of clarity and editability.
- Enables round-trip creative collaboration between text, sound, and structure.

**In short:** SongML is not about preserving data — it’s about preserving *intent*.

