"""SongML formatter - formats SongML files with consistent style.

Aligns bar markers (|) vertically within sections while preserving the original
format of free-form text blocks. This creates readable, tabular-like alignment
for musical content.

Key principles:
- Vertical bar alignment within section groups
- Preserve cell content exactly (spacing has timing semantics)
- Only add padding outside cells for alignment
- Preserve non-musical content (comments, blank lines, properties)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from .ast import ParseError, Section
from .parser import parse_songml


@dataclass
class BarLine:
    """A single line containing | markers."""

    original_content: str
    cells: list[str]  # Content between | markers (preserved exactly)
    line_number: int


@dataclass
class BarGroup:
    """Consecutive lines with | markers that should be aligned together."""

    lines: list[BarLine]
    start_line: int
    end_line: int


@dataclass
class TextBlock:
    """Non-musical content preserved as-is."""

    content: list[str]  # Lines of text
    line_numbers: list[int]


type BarGroupOrTextBlock = BarGroup | TextBlock
type BarRenumberingMap = dict[int, list[int]]


def detect_bar_line(line: str) -> bool:
    """Check if line contains bar markers."""
    return "|" in line


def split_bar_line(line: str) -> list[str]:
    """Split line by | markers, preserving empty cells.

    Args:
        line: Line containing | markers

    Returns:
        List of cell contents (without the | markers)

    Example:
        "| F.. | Am |" -> ["", " F.. ", " Am ", ""]
    """
    return line.split("|")


def calculate_column_widths(bar_group: BarGroup) -> list[int]:
    """Calculate optimal column widths for alignment.

    Simply finds the maximum width needed for each column across all lines.

    Args:
        bar_group: Group of bar lines to align

    Returns:
        List of column widths
    """
    if not bar_group.lines:
        return []

    # Find max number of columns
    max_cols = max(len(line.cells) for line in bar_group.lines)

    # Calculate width needed for each column (just use max length)
    widths = [0] * max_cols

    for line in bar_group.lines:
        for col_idx, cell in enumerate(line.cells):
            widths[col_idx] = max(widths[col_idx], len(cell))

    return widths


def pad_cell(content: str, target_width: int) -> str:
    """Add trailing spaces without modifying internal content.

    CRITICAL: Never modify spacing within content as it has timing semantics.
    Only add padding at the end.

    Args:
        content: Cell content (preserved exactly)
        target_width: Target width for this column

    Returns:
        Content with trailing spaces to reach target width
    """
    current_len = len(content)
    if current_len >= target_width:
        return content
    return content + " " * (target_width - current_len)


def align_bar_group(bar_group: BarGroup, column_widths: list[int]) -> list[str]:
    """Convert BarGroup to list of aligned text lines.

    Args:
        bar_group: Group of bar lines to align
        column_widths: Width for each column

    Returns:
        List of formatted lines with aligned | markers
    """
    aligned_lines = []

    for line in bar_group.lines:
        # Build aligned line
        parts = []
        for col_idx, cell in enumerate(line.cells):
            if col_idx < len(column_widths):
                # Pad to column width
                padded = pad_cell(cell, column_widths[col_idx])
                parts.append(padded)
            else:
                # No width info, use as-is
                parts.append(cell)

        # Join with | markers
        aligned_line = "|".join(parts)
        aligned_lines.append(aligned_line)

    return aligned_lines


def group_bar_lines(lines: list[str]) -> list[BarGroupOrTextBlock]:
    """Identify consecutive bar lines vs. other content.

    Args:
        lines: All lines from document

    Returns:
        List of BarGroup and TextBlock objects
    """
    blocks: list[BarGroup | TextBlock] = []
    current_bar_lines: list[BarLine] = []
    current_text_lines: list[str] = []
    current_text_line_numbers: list[int] = []
    bar_group_start = -1

    for line_num, line in enumerate(lines):
        if detect_bar_line(line):
            # Flush any accumulated text block
            if current_text_lines:
                blocks.append(
                    TextBlock(content=current_text_lines, line_numbers=current_text_line_numbers)
                )
                current_text_lines = []
                current_text_line_numbers = []

            # Add to current bar group
            cells = split_bar_line(line)
            bar_line = BarLine(original_content=line, cells=cells, line_number=line_num)

            if not current_bar_lines:
                bar_group_start = line_num

            current_bar_lines.append(bar_line)
        else:
            # Flush any accumulated bar group
            if current_bar_lines:
                blocks.append(
                    BarGroup(
                        lines=current_bar_lines, start_line=bar_group_start, end_line=line_num - 1
                    )
                )
                current_bar_lines = []
                bar_group_start = -1

            # Add to text block
            current_text_lines.append(line)
            current_text_line_numbers.append(line_num)

    # Flush remaining content
    if current_bar_lines:
        blocks.append(
            BarGroup(lines=current_bar_lines, start_line=bar_group_start, end_line=len(lines) - 1)
        )
    if current_text_lines:
        blocks.append(TextBlock(content=current_text_lines, line_numbers=current_text_line_numbers))

    return blocks


def format_songml(content: str, parsed_doc=None) -> str:
    """Format SongML content with aligned bar markers.

    Args:
        content: SongML document text
        parsed_doc: Optional pre-parsed document (used for bar renumbering)

    Returns:
        Formatted SongML text with aligned | markers

    Example:
        Input:
            | F.. | Am |
            | You've got a way | I just knew |

        Output:
            | F..              | Am          |
            | You've got a way | I just knew |
    """
    lines = content.split("\n")

    # Build bar renumbering map from parsed document if provided
    bar_renumbering = {}
    if parsed_doc:
        bar_renumbering = _extract_bar_renumbering(parsed_doc)

    blocks = group_bar_lines(lines)

    output_lines = []

    for block in blocks:
        if isinstance(block, TextBlock):
            # Preserve text blocks as-is
            output_lines.extend(block.content)
        elif isinstance(block, BarGroup):
            # Apply bar renumbering if available
            if bar_renumbering:
                block = _apply_bar_renumbering(block, bar_renumbering)

            # Align bar lines
            column_widths = calculate_column_widths(block)
            aligned = align_bar_group(block, column_widths)
            output_lines.extend(aligned)

    return "\n".join(output_lines)


def _fix_bar_numbers_in_ast(doc) -> None:
    """Fix bar numbers in the AST to be sequential across all sections.

    Modifies the document in-place.
    """
    expected_bar = 1

    for item in doc.items:
        if not isinstance(item, Section):
            continue

        for bar in item.bars:
            bar.number = expected_bar
            expected_bar += 1


def _extract_bar_renumbering(doc) -> BarRenumberingMap:
    """Extract the corrected bar numbers from AST, organized by line number.

    Returns:
        Dict mapping line_number -> list of corrected bar numbers for that line
    """
    bar_map: BarRenumberingMap = {}

    for item in doc.items:
        if not isinstance(item, Section):
            continue

        if not item.bars:
            continue

        # Group bars by their line number (bar number rows)
        line_to_bars = {}
        for bar in item.bars:
            if bar.line_number not in line_to_bars:
                line_to_bars[bar.line_number] = []
            line_to_bars[bar.line_number].append(bar.number)

        bar_map.update(line_to_bars)

    return bar_map


def _apply_bar_renumbering(bar_group: BarGroup, bar_map: BarRenumberingMap) -> BarGroup:
    """Apply corrected bar numbers to a bar group.

    Args:
        bar_group: Group of bar lines
        bar_map: Mapping from line_number -> list of correct bar numbers

    Returns:
        New BarGroup with updated bar numbers
    """
    if not bar_group.lines:
        return bar_group

    # Check if first line is a bar number row
    first_line = bar_group.lines[0]
    if not _is_bar_number_row(first_line):
        return bar_group

    # Look up correct bar numbers for this line
    # Note: AST uses 1-indexed line numbers, formatter uses 0-indexed
    correct_bars = bar_map.get(first_line.line_number + 1)
    if not correct_bars:
        return bar_group

    # Replace bar numbers in first line
    new_first_line = _replace_bar_numbers(first_line, correct_bars)

    new_lines = [new_first_line]
    new_lines.extend(bar_group.lines[1:])  # Keep other lines unchanged

    return BarGroup(lines=new_lines, start_line=bar_group.start_line, end_line=bar_group.end_line)


def _is_bar_number_row(bar_line: BarLine) -> bool:
    """Check if this line is a bar number row (has digits in cells)."""
    for cell in bar_line.cells:
        cell_text = cell.strip()
        if cell_text and cell_text[0].isdigit():
            return True
    return False


def _replace_bar_numbers(bar_line: BarLine, correct_bars: list[int]) -> BarLine:
    """Replace bar numbers in a line with correct sequential numbers.

    Args:
        bar_line: Line containing bar numbers
        correct_bars: List of correct bar numbers in order

    Returns:
        New BarLine with corrected numbers
    """
    new_cells = []
    bar_index = 0

    for cell in bar_line.cells:
        cell_text = cell.strip()

        # Check if this cell contains a bar number
        if cell_text and cell_text.isdigit():
            if bar_index < len(correct_bars):
                # Replace with correct bar number, preserving spacing
                old_num = cell_text
                new_num = str(correct_bars[bar_index])
                new_cell = cell.replace(old_num, new_num)
                new_cells.append(new_cell)
                bar_index += 1
            else:
                # Shouldn't happen, but keep original
                new_cells.append(cell)
        else:
            # Not a number or empty - keep as-is
            new_cells.append(cell)

    return BarLine(
        original_content=bar_line.original_content,
        cells=new_cells,
        line_number=bar_line.line_number,
    )


def main() -> None:
    """CLI entry point for songml-format command."""
    parser = argparse.ArgumentParser(
        description="Format SongML files by aligning bar markers (|) vertically.",
        epilog="""Examples:
  %(prog)s song.songml              # Print to stdout
  %(prog)s song.songml -i           # Format in-place
  %(prog)s song.songml out.songml   # Write to output file""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", metavar="INPUT", help="input SongML file")
    parser.add_argument("output", metavar="OUTPUT", nargs="?", help="output file (default: stdout)")
    parser.add_argument("-i", "--inplace", action="store_true", help="format file in-place")

    args = parser.parse_args()
    input_file = args.input

    # Determine output destination
    output_file = None
    if args.inplace:
        output_file = input_file
    elif args.output:
        output_file = args.output

    try:
        with open(input_file, encoding="utf-8") as f:
            content = f.read()

        # Parse and validate
        try:
            doc = parse_songml(content)

            # Fix bar numbers in the AST
            _fix_bar_numbers_in_ast(doc)

            if doc.warnings:
                print(f"Validation warnings ({len(doc.warnings)}):", file=sys.stderr)
                for warning in doc.warnings:
                    print(f"  {warning}", file=sys.stderr)
                print("", file=sys.stderr)  # Blank line for readability
        except ParseError as e:
            print(f"✗ Validation failed: {e}", file=sys.stderr)
            sys.exit(1)

        formatted = format_songml(content, parsed_doc=doc)

        if output_file:
            # Write to file (either in-place or to specified output)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(formatted)
            print(f"✓ Formatted to {output_file}", file=sys.stderr)
        else:
            # Print to stdout (default behavior)
            print(formatted)

    except FileNotFoundError as e:
        print(f"✗ File error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
