# SongML Syntax Specification (Draft)

## Overview

SongML is a text-based symbolic language for representing musical ideas in a human-readable and LLM-editable format. It prioritizes **intent over fidelity**, capturing structure, chords, lyrics, and broad musical concepts rather than performance details.

---

## File Structure

A SongML file consists of three main regions:

1. **Header Block** — Metadata about the composition
2. **Section Blocks** — Musical content organized by song structure
3. **Annotations Block** (optional) — Technical metadata and cross-references

---

## 1. Header Block

The header uses `# Key: Value` format for core metadata.

### Fields

```
# Title: <song title> // default: "song1"
# Key: <key signature> // default: Cmaj
# Tempo: <bpm>         // default: 100 
# Time: <time signature> // default: 4/4
# Composer: <name>     // default: (none, optional)
# Version: <date|mm.nn> // default: generation date YYYY-MM-DDTHH:MM:SS
# Notes: <freeform text>
```

### Example
```
# Title: Skylight
# Key: F major
# Tempo: 92
# Time: 4/4
```

---

## 2. Comments

SongML uses C++ style comments:

- **Line comments:** `// comment text`
- **Block comments:** `/* comment text */`

Comments can appear anywhere and are ignored during processing.

---

## 3. Section Blocks

Sections represent structural divisions (Verse, Chorus, Bridge, etc.).

### Syntax
```
[Section Name]
<section properties>
<musical content>
```

### Section Properties

**Bar start:** Indicates the bar number where this section begins (for correlation with source files)
```
Bar start: 8
```

**Key:** Specifies key changes or continuation
```
Key: G major          // Change to new key
Key: continue         // Use previous key
Key: tbd             // To be determined
```

### Example
```
[Verse 1]
Bar start: 8
Key: F major
| Fmaj7 | Gm7.. C7 | Fmaj7 | Bbmaj7.. C7 |
```

---

## 4. Chord Notation

Chords are written within bar delimiters `|` with spaces separating elements.

### Bar Delimiters
```
| Cmaj7 | Dm7 | G7 | Cmaj7 |
```

Each `|` represents a bar line. Content between pipes is one bar's worth of chords.

### Chord timing

Use `.` as a beat duration indicator, infer other information 
like a musician would:

| C..F | // Play C for 2 beats, then F for remainder of measure
| C. F... | // C for 1 beat, F for 3, total of 4
| C F Am G | // One chord per beat
| C F |  // Divide beats evenly between 2 chords

- If no '.' follows a chord, inference rules take over
- The semicolon ; indicates 1/2 of a beat (an eight note on 4/4 time)
- If the bar isn't 'full', the last chord stretches to fill it
    ```
    | C; F; Am |  // e.g. Am must be 3 beats long in 4/4 time
    ```


### Chord Symbols

SongML accepts standard chord notation:
- **Triads:** `C`, `Dm`, `G7`, `Fmaj7`
- **Extensions:** `Cmaj9`, `G13`, `Dm11`
- **Alterations:** `G7b9`, `C7#5`, `Dm7b5`
- **Slash chords:** `C/E`, `Dm7/G`

### Roman Numeral Analysis

Sections may use Roman numerals for harmonic analysis:
```
[Outro]
| V7..VI+ | IVmaj7 | III6 | Imaj7add9 |
```

This indicates functional harmony relative to the current key.

---

## 5. Lyrics

Lyrics are specified on separate lines using the `Lyrics:` prefix.

### Syntax
```
Lyrics: | lyric text with | bar separators | for alignment
```
- As with chords, periods and semicolons may be used as timing indicators
```
Lyrics: | She; gave | . a solemn... | frost. to. the.. | air     |
      //|  1  2 3 4 | 1 2   3   4   | 1      2   3 4   | 1 2 3 4 |
```
- The '.' character is not to be used as a conventional sentence end indicator in lyrics.

### Bar Alignment

Use `|` within the lyrics string to align syllables with bar boundaries:

```
| Fmaj7 | Gm7.. C7 | Fmaj7 | Bbmaj7.. C7 |
Lyrics: |Some..  where | there's a | sky... light |  |
```


---

## 7. Grammar Summary

TODO: reverse-engineer a grammar from above content


---

## 8. Design Principles Reflected

- **Human-readable:** Looks like a structured leadsheet
- **LLM-friendly:** Consistent, predictable structure
- **Lossy by design:** No performance details, only musical intent
- **Diff-friendly:** Line-based structure works with version control
- **Extensible:** Comments and annotations allow evolution

---

## 9. Design Concerns & Open Questions

### Resolved by Current Spec

1. ~~**Chord duration semantics**~~ — RESOLVED: `.` = beat duration, `;` = half-beat, inference for unmarked chords
2. ~~**Lyrics timing**~~ — RESOLVED: Same timing notation applies to lyrics

### Ambiguities Requiring Clarification

1. **Bar numbering semantics**
   - Is `Bar start:` absolute (measure 8 from song start) or relative to previous section?
   - How do we handle pickup bars or partial measures?
   - Proposal: Always absolute, use `Bar start: 0.5` for pickup bars?

2. **Key changes mid-section**
   - Can key change within a section block, or must it trigger a new section?
   - Inline syntax needed? `Key: -> G major` on a chord line?
   - Or force new section: `[Verse 1b]` with `Key: G major`?

3. **Timing inference edge cases**
   - What happens with odd divisions? `| C D E |` in 4/4 — is each chord 1.33 beats?
   - Should we warn/error, or allow "close enough" inference?
   - Maximum complexity before explicit timing required?

4. **Roman numeral context**
   - When using Roman numerals, is key context always from section `Key:` property?
   - Mixed notation in one line: `| Cmaj7 | IVmaj7 |` — allowed or forbidden?
   - Should we require `Key:` declaration before Roman numerals?

5. **Lyrics without bar markers**
   - Is `Lyrics: Some text here` valid for free-form sections?
   - Or must lyrics always align to bars with `|` delimiters?

### Unresolved Questions

6. **Repeat structures**
   - How to indicate repeats, codas, D.S. al Coda?
   - Proposed: `[Verse 1] x2` modifier on section header?
   - Or: `@structure: Verse1, Chorus, Verse1, Chorus` in annotations?
   - Or: `[Verse 1]` followed by `Repeat: 2` property?

7. **Tempo/time signature changes mid-song**
   - Can tempo change between sections? Within sections?
   - Syntax: `Tempo: 120` as section property?
   - How to represent ritardando, fermatas, or tempo marks like "Freely", "A tempo"?
   - `Tempo: rit.` or `Tempo: 92 -> 80` for gradual changes?

8. **Time signature changes**
   - `Time: 3/4` as section property?
   - Mixed meters within section: `| C |` (4/4) then `| F |` (3/4)?

9. **Voice leading / counterpoint**
   - Is SongML limited to single-line harmony?
   - Multi-voice syntax: `Voice 1: | ... |` and `Voice 2: | ... |` on separate lines?
   - Or keep it conceptual and rely on annotations for voice separation?

10. **Chord voicing hints**
    - Should we allow voicing suggestions (e.g., `Cmaj7{drop2}`, `G7{rootless}`)?
    - Tension with "conceptual not performance" philosophy
    - Perhaps reserve for annotations: `@voicing: "guitar drop2 shapes"`?

11. **Groove/feel notation**
    - How to indicate "swing", "straight 8ths", "half-time feel"?
    - Section property: `Feel: swing` or `Groove: laid-back`?
    - Or header-level: `# Feel: swing throughout`?

12. **Whitespace and formatting**
    - Is indentation significant for section properties?
    - Required indentation level (2 spaces, 4 spaces, tabs)?
    - Or purely stylistic with flexible parsing?

13. **Escaping in lyrics**
    - How to handle literal pipes `|` in lyrics (e.g., "either/or" or "him|her")?
    - Standard escaping: `\|` for literal pipe?
    - What about periods that aren't timing markers: "Mr. Jones"?
    - Escape with backslash: `Mr\. Jones` or context-aware parsing?

14. **Rest bars and tacet sections**
    - Notation for full rest bars: `| - |` or `| rest |` or `| % |`?
    - Longer tacet: `Tacet: 8 bars` as section property?
    - Or separate section: `[Drum Solo] \n Chords: (tacet)`?

15. **Chord alternatives / slash notation ambiguity**
    - Alternate harmonies: `| Cmaj7 / Am7 |` — is this "C or Am7" or "C over Am7 bass"?
    - Current spec: `/` means slash chord (bass note)
    - For alternatives: `| Cmaj7 | @alt: Am7` annotation?
    - Or new syntax: `| Cmaj7 ~ Am7 |` for either/or?

16. **Melody notation**
    - Should SongML support explicit melodic content beyond lyrics?
    - Syntax: `Melody: | C. D E. F | G... A |` using same timing notation?
    - Or keep melody out of scope entirely?

17. **Annotations block placement**
    - Must `@annotations:` come at end of file?
    - Can sections have local annotations?
    - Syntax: `@section_note:` within section block?

18. **Version comparison**
    - Should `# Version:` support semantic versioning?
    - How to indicate relationship to previous versions?
    - `# Version: 2.1 (from 2.0, shortened bridge)`?

19. **Default value inheritance**
    - When `Key: continue` is used, does it inherit from previous section or header?
    - If section omits `Bar start:`, how do we infer it?
    - Auto-increment from previous section's bar count?

20. **Incomplete bars and fermatas**
    - How to notate a bar that intentionally doesn't fill the meter?
    - `| C... |` in 4/4 — does C hold 3 beats or 4?
    - Fermata syntax: `| Cmaj7^ |` for "hold this"?

### Next Steps

- Build reference parser to validate timing inference rules
- Create comprehensive test suite with edge cases (odd meters, pickup bars, modulations)
- Establish conventions for common patterns (intros, endings, breaks, solos)
- Define formal EBNF or PEG grammar
- Design reconciliation protocol between old/new SongML versions
- Decide on strictness level: permissive (infer everything) vs. explicit (require declarations)
