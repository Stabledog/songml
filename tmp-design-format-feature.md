# Scratchpad -- designing the formatting feature

## Overview

The formatting feature will align bar markers (`|`) vertically within section groups while preserving the original format of free-form text blocks. This creates readable, tabular-like alignment for musical content.

## Key Design Principles

1. **Vertical bar alignment** - All `|` characters line up within a section
2. **Lyrics drive width** - Since lyrics are typically the longest content, they determine column widths
3. **Preserve text blocks** - Comments, notes, and non-musical content remain untouched
4. **Minimal disruption** - Only format lines that contain bar markers
5. **Preserve cell content exactly** - Never modify spacing within cells as it has timing semantics

## Target Format Example

```
[Verse 1 - 12 bars]
|      5                           |                 6                    |
| F .  .            F9/A  Abdim7/B | Am7/E                                |
| You've got a way                 | I just knew how to follow but it was |

|      7                           |                 8                    |
| Dm7/F                            | G7sus4           G7                  |
| hard to see you through the      | haze                                 |
```

## Critical Constraint: Preserve Cell Content

**The formatter MUST NOT modify content within cells.** Spacing patterns like `F..` vs `F . .` have different timing semantics in SongML. The formatter only:
- Adds padding **outside** cell content to achieve alignment
- Never changes spacing **inside** cells between `|` markers

### Example of CORRECT behavior:
```
Input:  | F.. G7sus | Am |
Output: | F.. G7sus  | Am   |
        ^^^ preserve exactly ^^^
```

### Example of INCORRECT behavior:
```
Input:  | F.. G7sus | Am |
Output: | F . . G7sus | Am |  ❌ WRONG! Changed F.. to F . .
```

## Python Implementation Details

### Module Structure
```
songml/
├── parser/
│   ├── __init__.py
│   ├── ast_nodes.py        # AST node definitions
│   ├── tokenizer.py        # Basic line-by-line parsing
│   └── section_parser.py   # Section and bar line parsing
├── formatter/
│   ├── __init__.py         # NEW MODULE
│   ├── bar_aligner.py      # NEW - Core alignment logic
│   ├── column_calc.py      # NEW - Width calculation
│   └── format_engine.py    # NEW - Main formatting entry point
├── cli/
│   ├── __init__.py
│   ├── main.py            # MODIFY - Add format command
│   └── commands.py        # MODIFY - Add format subcommand
└── utils/
    ├── __init__.py
    └── text_utils.py      # NEW - Helper functions for text processing
```

### New AST Node Types

Add to `songml/parser/ast_nodes.py`:

```python
from typing import TypeAlias
from dataclasses import dataclass
from enum import Enum

BarCells: TypeAlias = list[str]  # Content between | markers
ColumnWidths: TypeAlias = list[int]  # Width for each column

class BarLineType(Enum):
    BAR_NUMBERS = "bar_numbers"
    CHORDS = "chords"
    LYRICS = "lyrics"
    MIXED = "mixed"

@dataclass
class BarLine:
    """A single line containing | markers"""
    original_content: str
    cells: BarCells
    line_type: BarLineType
    line_number: int

@dataclass
class BarGroup:
    """Consecutive lines with | markers that should be aligned together"""
    lines: list[BarLine]
    column_widths: ColumnWidths
    start_line: int
    end_line: int

@dataclass
class FormattedSection:
    """A section with potentially multiple bar groups and preserved text"""
    section_header: str
    content_blocks: list[BarGroup | TextBlock]

@dataclass
class TextBlock:
    """Non-musical content preserved as-is"""
    content: str
    line_numbers: list[int]
    preserve_formatting: bool = True
```

### Core Formatting Modules

**`songml/formatter/column_calc.py`** - Width calculation logic:
```python
from ..parser.ast_nodes import BarGroup, BarLine, ColumnWidths

class ColumnCalculator:
    def calculate_widths(self, bar_group: BarGroup) -> ColumnWidths:
        """Calculate optimal column widths for alignment"""

    def _detect_content_type(self, cell_content: str) -> BarLineType:
        """Heuristic to identify if cell contains chords, lyrics, etc."""

    def _weight_by_content_type(self, width: int, content_type: BarLineType) -> int:
        """Apply weighting - lyrics get priority for width calculation"""
```

**`songml/formatter/bar_aligner.py`** - Alignment engine:
```python
from ..parser.ast_nodes import BarGroup, BarLine

class BarAligner:
    def align_bar_group(self, bar_group: BarGroup) -> list[str]:
        """Convert BarGroup to list of aligned text lines"""

    def _pad_cell(self, content: str, target_width: int) -> str:
        """Add trailing spaces without modifying internal content"""

    def _preserve_cell_content(self, cell: str) -> str:
        """Validate that cell content timing semantics are preserved"""
```

**`songml/formatter/format_engine.py`** - Main entry point:
```python
from ..parser.ast_nodes import SongMLDocument, FormattedSection
from .column_calc import ColumnCalculator
from .bar_aligner import BarAligner

class SongMLFormatter:
    def __init__(self, config: FormatterConfig = None):
        self.calculator = ColumnCalculator()
        self.aligner = BarAligner()

    def format_document(self, doc: SongMLDocument) -> str:
        """Format entire SongML document"""

    def format_section(self, section: Section) -> FormattedSection:
        """Format a single section, preserving non-bar content"""

    def _group_bar_lines(self, section_lines: list[str]) -> list[BarGroup | TextBlock]:
        """Identify consecutive bar lines vs. other content"""
```

### Modified Modules

**`songml/cli/main.py`** - Add format command:
```python
# ...existing imports...
from ..formatter.format_engine import SongMLFormatter

def main():
    parser = argparse.ArgumentParser(description="SongML tools")
    subparsers = parser.add_subparsers(dest='command')

    # ...existing subcommands...

    # Add format command
    format_parser = subparsers.add_parser('format', help='Format SongML file with aligned bars')
    format_parser.add_argument('input', help='Input SongML file')
    format_parser.add_argument('-o', '--output', help='Output file (default: overwrite input)')
    format_parser.add_argument('--dry-run', action='store_true', help='Show formatted output without writing')

    args = parser.parse_args()

    if args.command == 'format':
        format_file(args.input, args.output, args.dry_run)
```

**`songml/utils/text_utils.py`** - Helper functions:
```python
def split_bar_line(line: str) -> list[str]:
    """Split line by | markers, preserving empty cells"""

def detect_bar_line(line: str) -> bool:
    """Check if line contains bar markers"""

def strip_line_comments(line: str) -> str:
    """Remove // comments while preserving bar content"""

def count_columns(lines: list[str]) -> int:
    """Find maximum number of | delimited columns across lines"""
```

### Integration with Existing Parser

**Modify `songml/parser/section_parser.py`**:
```python
# ...existing code...

def parse_section_content(self, lines: list[str]) -> SectionContent:
    """Parse section content, identifying bar groups for formatting"""
    bar_groups = []
    text_blocks = []

    # Group consecutive bar lines
    # Preserve non-bar content as TextBlocks
    # Return structured content ready for formatting
```

### Configuration

**`songml/formatter/config.py`** - Formatting options:
```python
@dataclass
class FormatterConfig:
    min_column_width: int = 3
    column_padding: int = 1
    preserve_bar_numbers: bool = True
    align_section_headers: bool = False
    max_line_length: int = 120  # Wrap very long lines
```

## Implementation Strategy

### 1. Parse Structure
- Identify section boundaries `[Section Name - N bars]`
- Group consecutive lines with bar markers (`|`) within each section
- Preserve non-musical content (comments, blank lines, properties) as-is

### 2. Column Width Calculation
For each group of bar lines:
- Split content by `|` to identify columns
- Calculate maximum width needed per column (lyrics typically longest)
- Add padding for readability

### 3. Formatting Algorithm
```
For each section:
  - Find all consecutive bar-containing lines
  - Split each line by | to extract cell content
  - Calculate column widths across the group
  - Reformat by padding cells with trailing spaces only
  - Never modify content within individual cells
```

### 4. AST Node Types Needed

```python
# Musical content that gets formatted
class BarGroup:
    lines: list[BarLine]
    column_widths: list[int]

class BarLine:
    original_content: str
    cells: list[str]  # RAW content between | markers - never modified
    line_type: BarLineType  # BAR_NUMBERS, CHORDS, LYRICS

# Non-musical content preserved as-is
class TextBlock:
    content: str
    preserve_formatting: bool = True
```

### 5. Edge Cases to Handle

- **Mixed content**: Some lines have bar markers, others don't
- **Uneven columns**: Different numbers of `|` per line
- **Empty cells**: `| |` should preserve spacing
- **Timing markers**: `.` and `;` characters need proper spacing
- **Long chord names**: `Abdim7/B` vs simple `C`

### 6. Configuration Options

Consider making these configurable:
- Minimum column width
- Padding between columns (applied outside cell content)
- Whether to align bar numbers separately
- Cell content is NEVER configurable - always preserved exactly

### 7. Implementation Phases

**Phase 1**: Basic vertical alignment
- Parse bar lines into columns
- Calculate widths, apply uniform padding
- Handle simple chord/lyric combinations

**Phase 2**: Smart width calculation
- Analyze typical content types per column position
- Weight lyrics more heavily for width calculation
- Handle bar number formatting

**Phase 3**: Edge case handling
- Mixed line types within sections
- Preserve important spacing (like pickup beats `...;F`)
- Integration with existing parser

### 8. Example Processing

**Input:**
```
| F.. F9/A Abdim7/B | Am7/E |
| You've got a way | I just knew how |
```

**Analysis:**
- Column 1 content: "F.. F9/A Abdim7/B" (17 chars) vs "You've got a way" (16 chars)
- Column 2 content: "Am7/E" (5 chars) vs "I just knew how" (15 chars)
- Column widths: [17, 15]

**Output:**
```
| F.. F9/A Abdim7/B | Am7/E          |
| You've got a way  | I just knew how |
```

Note: `F..` timing is preserved exactly, only trailing spaces added for alignment.

### 9. Integration Points

- Extend existing SongML parser to identify bar groups
- Add formatting pass after parsing, before output
- Ensure round-trip compatibility (parse → format → parse)
- Consider integration with validation warnings

### 10. Testing Strategy

- Unit tests for column width calculation
- Round-trip tests (format doesn't change semantics)
- Real-world examples from `samples/youve-got-a-way.songml`
- Edge cases: empty bars, long chord names, timing markers
