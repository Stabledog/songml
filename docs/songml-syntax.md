# SongML Syntax Specification (Draft)

## Overview

SongML is a text-based symbolic language for representing musical ideas. It's meant to be **simple and forgiving** — more like a musician's scratch pad than a formal specification.

**Philosophy:** Start minimal, add complexity only when needed. Tools should warn about problems but be permissive in what they accept.

---

## Basic Structure

A SongML file contains:
1. **Properties** (optional header info)
2. **Sections** (the actual music)
3. **Free-form notes** (anything else)

---

## 1. Properties

Properties precede the section(s) to which they apply. Format: `PropertyName: value`

Common properties:
```
Title: You've got a way
Key: Fmaj
Tempo: 104
Time: 4/4
```

**There's no strict list of properties.** Write what makes sense. Tools will recognize common ones (Title, Key, Tempo ) and ignore unknown ones.

---

## 2. Comments and Notes

- `//` starts an end-of-line comment
- Any line that doesn't match a recognized pattern is ignored

This means you can write whatever you want:
```
Note: This is just explanatory text
TODO: Fix the bridge
Key: Cmaj  // This is a comment

The validator will warn about beat counts but won't reject the file.
```


---

## 3. Sections

Sections are labeled with brackets:

```
[Intro]
[Verse 1]
[Chorus - 8 bars]
```

The validator recognizes `[Section Name]` and optionally `[Section Name - NN bars]` for documentation and bar count validation or generation.

The validator warns on duplicate section names

---

## 4. Bar Lines and Numbering

Use `|` to mark bars. Numbering bars is optional but helpful:

```
|   0   |   1   |  2      |   3        |
| ...;F | F.... | Am .... | Bbmaj7.... |
```

**Alignment isn't meaningful.** The parser just looks for `|` symbols. A formatting tool can clean up alignment later.


---

## 5. Chords

Write chords between bar lines. Use standard notation:
- Basic: `C`, `Dm`, `G7`, `Fmaj7`
- Extensions: `Cmaj9`, `G13`, `Dm11`
- Alterations: `G7b9`, `C7#5`
- Slash chords: `C/E`, `Dm7/G`

### Timing

Use `.` to indicate beat duration:
```
| F.... |              // F for 4 beats
| C.. G.. |            // C for 2, G for 2
| C. D. E. F. |        // One beat each
| C D E F |            // One beat each.  The '.' are implicit
```

Use `;` for half-beats:
```
| ...;F |              // Pickup: F on beat 4-and
| C; D; E.. |          // C on 1, D on 1-and E on 2-4
```

**Without timing marks:** Chords split the bar evenly.
```
| C F |                // Each gets 2 beats in 4/4
| C F G |              // C and F get 1 beat, G gets 2 (last chord fills the frame that's left)
```

**The last chord fills remaining space:**
```
| C; F; Am |           // Am stretches to fill beats 2-4
```

---

## 6. Lyrics

Write lyrics on a separate line under chords:
```
| F .  .  F9/A  Abdim7/B | Am7/E |
| You've got a way        | I just knew how to follow |
```

You can use `|` for alignment if you want, or timing markers:
```
| You've. got. a. way. |
```

**Keep it simple.** Lyrics are for humans reading the chart. Perfect alignment isn't required.

---

## 7. Key Changes

Set `Key: Gmaj` as a property outside sections to change key. Roman numerals use the current key context.

---

## 8. What This Spec Doesn't Define

**Deliberately vague or permissive:**

- Exact timing inference rules (tools decide)
- Whether bar numbers must be accurate (validators warn)
- How to handle odd time signatures or complex rhythms (add dots as needed, tools figure it out)
- Repeat structures, codas, dynamics (add them as text notes for now)
- Voice leading, counterpoint (out of scope)

**The principle:** If a human can read it and understand the intent, it's valid SongML.

---

## 9. Validation vs. Parsing

**Parsers should be permissive:** Accept anything that's roughly the right shape.

**Validators should be helpful:** Warn about:
- Bar numbers that don't match section lengths
- Beat counts that don't add up
- Unrecognizable chord symbols
- Missing required properties

But validators don't reject files. They provide line numbers and suggestions.

**Translation tools** (MIDI→SongML, SongML→MusicXML) can be stricter and abort on ambiguity.

---

## 10. Examples

### Minimal
```
Title: Test Song

[Verse]
| C | F | G | C |
```

### With timing and lyrics
```
Title: You've Got a Way
Key: Fmaj
Tempo: 104

[Verse 1 - 12 bars]
|      5                           |                 6                    |
| F .  .            F9/A  Abdim7/B | Am7/E                                |
| You've got a way                 | I just knew how to follow but it was |
```

### With bar numbers in chord row
```
[Bridge - 6 bars]
|  37       |   38          | 39            | 40            |
| A/C#.. A  | A7/C#.. A7/E  |  E6/G# .. E6  | Edim7/G..  /A |
```

---

## Design Principles

1. **Human-first:** If it looks reasonable to a musician, it's probably fine
2. **Tool-friendly:** Consistent enough for tools to parse, flexible enough to evolve
3. **Forgiving:** Warnings, not errors
4. **Minimal:** Add features when needed, not preemptively
5. **Inspectable:** Plain text, version control friendly

---

## Open Questions (for later)

- Repeat notation (`[Verse] x2` or `Repeat: Verse, Chorus`?)
- Tempo changes mid-song
- Multiple voices / counterpoint
- Groove/feel annotations
- How to handle transcription confidence from AI tools
- Formal grammar (EBNF) — do we need one?
