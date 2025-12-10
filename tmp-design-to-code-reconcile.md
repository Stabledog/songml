# Code to Design Reconciliation

## Task 1: Code vs Design Inconsistencies

### Category A: Documentation Accuracy

**A1. Slash Chord Handling Description**
- **Design claim** (songml-midi-generation.md): "one pragmatic exception: slash chord bass notes"
- **Code reality**: Slash chords are fully parsed in `chord_voicings.py:get_chord_notes()`, splitting on `/` and adding bass note programmatically
- **Status**: ✓ Accurate. Code matches design philosophy and implementation description.

**A2. Timing Marker Semicolon Semantics**  
- **Design claim** (songml-syntax.md): "`;` for half-beats" with examples like `...;F` meaning "F on beat 4-and"
- **Code reality**: `parser.py:_parse_chord_tokens()` correctly implements: prefix dots + optional semicolon = rest, then chord starts
- **Status**: ✓ Accurate. Implementation matches specification.

**A3. Last-Chord-Fills Rule**
- **Design claim** (songml-syntax.md): "The last chord fills remaining space"
- **Code reality**: `parser.py:_parse_chord_tokens()` implements this by checking if chord is last, then calculating `beats_per_bar - current_beat - dots_ahead`
- **Status**: ✓ Accurate. Complex logic with lookahead for standalone dots is correctly implemented.

**A4. Property State Persistence**
- **Design claim** (songml-syntax.md): Properties "precede the section(s) to which they apply"
- **Code reality**: `parser.py:parse_songml()` maintains `property_state` dict that persists across sections until overridden
- **Status**: ✓ Accurate. Implementation matches design intent.

**A5. Validation vs Parsing Philosophy**
- **Design claim** (songml-syntax.md): "Parsers should be permissive... Validators should be helpful"
- **Code reality**: Parser raises `ParseError` on structural issues (missing bars, invalid timing), but accepts unknown properties and provides warnings
- **Status**: ⚠️ Partially accurate. Parser is more strict than design suggests. May need to clarify what constitutes "structural error" vs "validation warning".

---

### Category B: Missing Features

**B1. Formatter Implementation**
- **Design**: Multiple references to formatting/pretty-printing capability
- **Code**: `formatter.py` raises `NotImplementedError`
- **Impact**: Medium. Users can't clean up SongML files programmatically.

**B2. Repeat Notation**
- **Design claim** (songml-syntax.md): Lists as "Open Question"
- **Code**: No support in parser or AST
- **Impact**: Low. Explicitly deferred in design.

**B3. Multiple Time Signatures**
- **Design claim** (songml-syntax.md): "Tempo changes mid-song" listed under open questions
- **Code**: Single tempo/time signature for entire document
- **Impact**: Low. Explicitly deferred, but MIDI exporter assumes single tempo.

**B4. AST Deserialization**
- **Design**: Round-trip capability mentioned in songml-ast.md
- **Code**: `Document.from_dict()` raises `NotImplementedError`
- **Impact**: Low. Forward direction (text→AST→MIDI) works. Reverse not needed yet.

**B5. Comments Support**
- **Design claim** (songml-syntax.md): "`//` starts an end-of-line comment"
- **Code**: Parser treats lines with `//` as `TextBlock`, no special handling
- **Impact**: Medium. Comments aren't stripped from lyrics or chord rows, could cause parsing issues.

---

### Category C: Type Alias Usage

**C1. Complex Type Signatures**
- **Coding principle**: "Don't use complex types in function signatures... use `TypeAlias`"
- **Code violations**:
  - `parser.py:_parse_chord_tokens()` returns `list[ChordToken]` (acceptable - domain type)
  - `chord_voicings.py:load_voicing_table()` returns `dict[str, tuple[str, list[int]]]` ❌ Violates principle
  - `parser.py:_parse_section_content()` args include `dict[str, str]` (acceptable - simple)
- **Impact**: Low-Medium. `load_voicing_table` return type is cryptic.

**C2. Suggested Type Aliases**
```python
# For chord_voicings.py
ChordOffsets: TypeAlias = list[int]  # Semitone offsets from root
ChordVoicing: TypeAlias = tuple[str, ChordOffsets]  # (root_note, offsets)
VoicingTable: TypeAlias = dict[str, ChordVoicing]  # symbol → voicing

# For midi_exporter.py
MidiNotes: TypeAlias = list[int]  # List of MIDI note numbers
MidiEvent: TypeAlias = tuple[int, str, MidiNotes]  # (tick, event_type, notes)
MidiTimeline: TypeAlias = list[MidiEvent]
```

---

### Category D: Design Document Completeness

**D1. Missing: Bar Number Auto-Increment Rules**
- **Design**: songml-syntax.md mentions auto-numbering as future enhancement
- **Code**: `parser.py:_parse_bar_number_row()` implements strict auto-increment with validation
- **Gap**: Design doesn't document implemented behavior: first cell sets counter, subsequent empty cells auto-increment, non-empty cells must match expected sequence.

**D2. Missing: Section Name Validation**
- **Design**: No mention of duplicate section name handling
- **Code**: Parser warns on duplicate section names but continues
- **Gap**: Design should document this behavior (warning, not error).

**D3. Missing: Synthesized Empty Bars**
- **Design**: No mention of what happens when parsed bar count < declared bar count
- **Code**: `_finalize_section()` synthesizes empty bars to match declared count
- **Gap**: Design should document this reconciliation behavior.

**D4. Overly Detailed: MIDI Technical Details**
- **Design**: songml-midi-generation.md includes extensive MIDI implementation details
- **Reality**: This is implementation documentation masquerading as design
- **Gap**: Could separate "MIDI Export Design" from "MIDI Export Implementation Guide".

**D5. Missing: Error Context in Exceptions**
- **Code**: `ParseError` includes `line_number`, MIDI exporter provides section/bar/beat context
- **Design**: No documentation of error reporting philosophy or message format conventions
- **Gap**: Should document error message structure (especially for unknown chords).

---

### Category E: Inconsistencies Between Design Docs

**E1. Property Declaration Syntax**
- **songml-syntax.md**: `PropertyName: value`
- **songml_design_manifesto.md** example: Uses `#` prefix (`# Title: Skylight`)
- **Code**: Implements colon syntax, no `#` prefix support
- **Resolution**: Manifesto example is illustrative fiction, not actual syntax. Manifesto should note "syntax shown is conceptual".

**E2. Comment Syntax**
- **songml-syntax.md**: "`//` for comments"
- **songml_design_manifesto.md** example: Uses `//` and `/* */` C++ style comments
- **Code**: No comment parsing, treated as text
- **Resolution**: Design is aspirational, code hasn't implemented. Mark as TODO in syntax doc.

**E3. Annotation Syntax**
- **songml_design_manifesto.md**: Shows `@annotations:` section with YAML-style metadata
- **Other docs**: No mention of annotations
- **Code**: No support
- **Resolution**: Manifesto is vision/future direction, not current spec. Should clarify "future extension" in manifesto.

**E4. Roman Numeral Chords**
- **songml_design_manifesto.md** example: Shows `V7`, `IVmaj7`, `III6`, `Imaj7add9`
- **Other docs**: No mention
- **Code**: Would be rejected (not in voicing table)
- **Resolution**: Manifesto example is conceptual. Either add disclaimer or remove from example.

---

### Category F: Terminology Consistency

**F1. "Bar" vs "Measure"**
- **Usage**: Design docs consistently use "bar", code uses "bar"
- **Status**: ✓ Consistent

**F2. "Section" vs "Part"**  
- **Usage**: Consistently "section" throughout
- **Status**: ✓ Consistent

**F3. "Chord Token" vs "Chord Symbol"**
- **Design**: Uses both terms somewhat interchangeably
- **Code**: AST class is `ChordToken`, voicing table uses "chord symbol"
- **Clarification needed**: "Token" = parsed syntax element with timing, "Symbol" = musical identifier (text string)
- **Status**: ⚠️ Could clarify in design docs

**F4. "Beat" vs "Tick"**
- **Design**: User-facing docs use "beat", MIDI doc uses both
- **Code**: AST uses `*_beat` attributes, MIDI exporter uses `*_tick` variables
- **Status**: ✓ Appropriate. Beat = musical unit, tick = MIDI unit. Clear separation.

---

## Task 2: Design Outdated/Incomplete/Wrong

### Category G: Design Needs Updates

**G1. Bar Numbering Semantics**
- **Current design**: Mentions bar numbers as "optional but helpful", warns on mismatch
- **Code behavior**: Bar numbers are **required** for sections to parse, strict validation with auto-increment
- **Update needed**: songml-syntax.md should document:
  - Bar number row is mandatory
  - First cell sets initial number
  - Empty cells auto-increment
  - Non-empty cells must match expected sequence
  - Gap detection raises ParseError

**G2. Section Without Bar Number Row**
- **Current design**: Doesn't address this case
- **Code**: Raises `ParseError("Section must start with bar-number row")`
- **Update needed**: Document that sections require bar-number row (future: could support auto-numbering from 0).

**G3. Timing Marker Edge Cases**
- **Current design**: Shows examples but doesn't exhaustively document parsing rules
- **Code**: Handles complex cases: prefix dots, semicolon, suffix dots, standalone dots, lookahead for last-chord-fills
- **Update needed**: Add formal timing marker grammar to syntax doc:
  ```
  TimingMarker := DotPrefix SemicolonFlag? ChordText DotSuffix?
  DotPrefix    := '.'*
  SemicolonFlag := ';'
  DotSuffix    := '.'*
  ChordText    := [^.|;]+
  StandaloneDot := '.'
  ```

**G4. Property Parsing Rules**
- **Current design**: "PropertyName: value" with "no strict list"
- **Code**: Regex `^([A-Z][A-Za-z]*)\s*:\s*(.+)$` requires capital first letter
- **Gap**: Should document case-sensitivity requirement

**G5. MIDI Export Defaults**
- **Current design**: Lists defaults but scattered across paragraphs
- **Improvement**: Add summary table at top of songml-midi-generation.md:
  
  | Parameter | Default | Configurable? |
  |-----------|---------|---------------|
  | PPQ | 480 | No |
  | Velocity | 64 | No |
  | Channel | 0 | No |
  | Root Octave | 3 | No |
  | Tempo | 100 BPM | Via property |
  | Time Sig | 4/4 | Via property |
  | Key | Cmaj | Via property |

**G6. Voicing Table Extension Process**
- **Current design**: Mentions "add new voicings by adding TSV rows"
- **Missing**: No documentation of TSV format validation, how to test new voicings, naming conventions
- **Update needed**: Add "Contributing Voicings" section to MIDI doc

---

### Category H: Design Philosophically Wrong

**H1. "Forgiving Parser" vs Reality**
- **Design claim**: "Parsers should be permissive... not reject files"
- **Code reality**: Parser raises `ParseError` on:
  - Malformed sections
  - Invalid bar numbering
  - Beat overflow
  - Missing bar number rows
- **Assessment**: Design is **aspirational but impractical**. Parser must enforce structural integrity for MIDI export to work.
- **Resolution**: Revise philosophy to distinguish:
  - **Structural errors** (break AST invariants) → ParseError
  - **Semantic warnings** (questionable but parseable) → warnings list
  - Examples of warnings: duplicate sections, unknown properties, beat count mismatches

**H2. "No Strict Grammar" Philosophy**
- **Design claim**: Deliberately vague, permissive
- **Code reality**: Precise regex patterns, strict bar structure, exact timing calculations
- **Assessment**: Design undersells the implementation. The grammar **is** well-defined, just not overly rigid about content.
- **Resolution**: Reframe as "Simple, stable grammar with permissive content" rather than "vague rules"

---

### Category I: Missing Design Guidance

**I1. Lyric Timing Alignment**
- **Current state**: Lyrics are freeform text per bar
- **Missing**: No guidance on syllable-to-beat alignment, hyphenation, melisma notation
- **Impact**: Low for current scope (lyrics are human-readable only), but future MIDI lyric export will need this

**I2. Chord Symbol Canonicalization**
- **Current state**: Voicing table uses exact string match
- **Missing**: No guidance on equivalent symbols (`Cmaj7` vs `CM7` vs `CΔ7`)
- **Impact**: Medium. Users may use different notation styles.
- **Recommendation**: Document "preferred notation" in voicing table, consider future normalization layer

**I3. Multi-File Projects**
- **Manifesto mentions**: Project bundles with sources/, meta/, songml/
- **Other docs**: Treat files as standalone
- **Missing**: No design for how parser/tools handle project context
- **Impact**: Low for current scope, but needed for manifesto vision

**I4. Version/Migration Strategy**
- **Code**: AST has `version: "1.0"` in JSON output
- **Design**: No mention of versioning, backward compatibility, or migration
- **Missing**: Policy for breaking changes, version detection
- **Impact**: Low now, critical before 1.0 release

**I5. Error Recovery**
- **Current**: Parser fails fast on first error
- **Missing**: No design for collecting multiple errors, partial parsing, recovery strategies
- **Impact**: Medium. Users want to see all issues, not just first one.

---

## Recommended Reconciliation Passes

### Pass 1: Quick Wins (Documentation Fixes)
1. Add bar numbering rules to songml-syntax.md (G1, G2, D1)
2. Document duplicate section warning behavior (D2)
3. Document synthesized empty bars (D3)
4. Add defaults table to MIDI doc (G5)
5. Clarify manifesto examples as "conceptual" (E1, E3, E4)
6. Add timing marker grammar (G3)
7. Document property case-sensitivity (G4)

### Pass 2: Code Quality (Type Aliases)
1. Add type aliases to chord_voicings.py (C1, C2)
2. Add type aliases to midi_exporter.py (C2)
3. Extract complex types in other modules as needed

### Pass 3: Feature Completion
1. Implement comment stripping in parser (B5)
2. Implement formatter (B1)
3. Consider error recovery/multi-error collection (I5)

### Pass 4: Design Refinement
1. Revise "forgiving parser" philosophy (H1)
2. Clarify grammar stability vs permissiveness (H2)
3. Add chord symbol canonicalization guidance (I2)
4. Add voicing table contribution guide (G6)

### Pass 5: Future Planning
1. Add repeat notation design (B2)
2. Add tempo change design (B3)
3. Design lyric timing alignment (I1)
4. Design multi-file project support (I3)
5. Define versioning/migration policy (I4)

---

## Priority Assessment

**Critical (Blocks current use):**
- None. System works as implemented.

**High (Documentation debt):**
- G1: Bar numbering rules
- H1: Parser philosophy clarification
- G3: Timing marker grammar
- D1, D2, D3: Document implemented behaviors

**Medium (Quality/UX):**
- C1, C2: Type aliases for readability
- B5: Comment support
- I5: Multi-error reporting
- G6: Voicing contribution guide

**Low (Future work):**
- B1: Formatter
- B2, B3: Deferred features
- I1-I4: Future capabilities

---

## Summary

**Overall Assessment**: The code is **more rigorous and feature-complete** than the design documents suggest. The primary gaps are:

1. **Documentation lags implementation** - Many working features aren't documented
2. **Philosophy mismatch** - Design claims extreme permissiveness, code is appropriately strict
3. **Type alias discipline** - Coding principle not consistently followed
4. **Design doc split needed** - Manifesto vision vs current specification

**Codebase Health**: ✓ Good. Well-structured, follows AST design, comprehensive testing.

**Design Doc Health**: ⚠️ Needs updates to match implementation reality and clarify philosophy.

**Biggest Risk**: Users reading syntax doc will expect more lenient parsing than they get. Fix by clarifying structural vs semantic validation.
