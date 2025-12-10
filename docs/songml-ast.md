# SongML Abstract Syntax Tree

This document visualizes the AST structure used by the SongML parser.

## Class Structure

```mermaid
classDiagram
    class Document {
        +List~Union[TextBlock, Property, Section]~ items
        +List~str~ warnings
    }
    
    class TextBlock {
        +List~str~ lines
        +int line_number
    }
    
    class Property {
        +str name
        +str value
        +int line_number
    }
    
    class Section {
        +str name
        +int bar_count
        +List~Bar~ bars
        +int line_number
    }
    
    class Bar {
        +int number
        +List~ChordToken~ chords
        +Optional~str~ lyrics
        +int line_number
    }
    
    class ChordToken {
        +str text
        +float start_beat
        +float duration_beats
    }
    
    class ParseError {
        +str message
        +int line_number
    }
    
    Document "1" *-- "0..*" TextBlock : contains
    Document "1" *-- "0..*" Property : contains
    Document "1" *-- "0..*" Section : contains
    Section "1" *-- "0..*" Bar : contains
    Bar "1" *-- "0..*" ChordToken : contains
```

## Data Flow

```mermaid
flowchart TD
    A[SongML Text] --> B[Parser]
    B --> C{Line Type?}
    C -->|PropertyName: value| D[Property Node]
    C -->|Section Header| E[Section Node]
    C -->|Bar-delimited rows| F[Parse Bar Group]
    C -->|Other text| G[TextBlock Node]
    
    D --> H[Update Property State]
    H --> I[Add to Document]
    
    E --> J[Create Section]
    F --> K[Parse Bar Numbers]
    F --> L[Parse Chord Row]
    F --> M[Parse Optional Lyrics]
    K --> N[Create Bar Nodes]
    L --> N
    M --> N
    N --> O[Add ChordTokens]
    O --> P[Apply Timing Rules]
    P --> J
    J --> I
    
    G --> I
    
    I[Document] --> Q[AST Ready]
    
    style A fill:#e1f5ff
    style Q fill:#d4edda
    style H fill:#fff3cd
```

## Property State Persistence

The parser maintains a property state dictionary throughout parsing. Properties encountered update this state and apply to all subsequent sections until changed:

```mermaid
stateDiagram-v2
    [*] --> Defaults: Parser Init
    state "Time: 4/4<br/>Key: Cmaj<br/>Tempo: 100<br/>Title: Untitled" as Defaults
    
    Defaults --> Section1: Parse Section
    Section1 --> PropertyChange: Encounter Property
    PropertyChange --> UpdatedState: Update State
    state "Time: 3/4<br/>Key: Cmaj<br/>Tempo: 100<br/>Title: Untitled" as UpdatedState
    
    UpdatedState --> Section2: Parse Section
    Section2 --> [*]
```

## Timing Inference

ChordToken timing is calculated using the last-chord-fills rule:

```mermaid
flowchart LR
    A[Chord Cell Text] --> B[Split on Whitespace]
    B --> C[Parse Each Token]
    C --> D{Has Dots/Semicolon?}
    D -->|Yes| E[Calculate Explicit Duration]
    D -->|No| F{Is Last Chord?}
    F -->|Yes| G[Fill Remaining Beats]
    F -->|No| H[Default: 1 Beat]
    
    E --> I[Create ChordToken]
    G --> I
    H --> I
    
    I --> J{More Tokens?}
    J -->|Yes| C
    J -->|No| K[Return ChordToken List]
    
    style G fill:#d4edda
    style H fill:#fff3cd
```

## Round-Trip Design

The AST preserves sufficient information to enable reconstruction:

- **ChordToken**: `text` (opaque), `start_beat`, `duration_beats` → reconstruct timing markers
- **Bar**: `number`, `chords`, `lyrics` → reconstruct bar rows
- **Section**: `name`, `bar_count`, `bars` → reconstruct section header and content
- **Property**: `name`, `value` → reconstruct property declarations
- **Document**: `items` (ordered sequence) → preserves document structure
- **Document**: `warnings` → non-fatal issues for user feedback
