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

import sys
from dataclasses import dataclass


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


def detect_bar_line(line: str) -> bool:
    """Check if line contains bar markers."""
    return '|' in line


def split_bar_line(line: str) -> list[str]:
    """Split line by | markers, preserving empty cells.
    
    Args:
        line: Line containing | markers
        
    Returns:
        List of cell contents (without the | markers)
        
    Example:
        "| F.. | Am |" -> ["", " F.. ", " Am ", ""]
    """
    return line.split('|')


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
    return content + ' ' * (target_width - current_len)


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
        aligned_line = '|'.join(parts)
        aligned_lines.append(aligned_line)
    
    return aligned_lines


def group_bar_lines(lines: list[str]) -> list[BarGroup | TextBlock]:
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
                blocks.append(TextBlock(
                    content=current_text_lines,
                    line_numbers=current_text_line_numbers
                ))
                current_text_lines = []
                current_text_line_numbers = []
            
            # Add to current bar group
            cells = split_bar_line(line)
            bar_line = BarLine(
                original_content=line,
                cells=cells,
                line_number=line_num
            )
            
            if not current_bar_lines:
                bar_group_start = line_num
            
            current_bar_lines.append(bar_line)
        else:
            # Flush any accumulated bar group
            if current_bar_lines:
                blocks.append(BarGroup(
                    lines=current_bar_lines,
                    start_line=bar_group_start,
                    end_line=line_num - 1
                ))
                current_bar_lines = []
                bar_group_start = -1
            
            # Add to text block
            current_text_lines.append(line)
            current_text_line_numbers.append(line_num)
    
    # Flush remaining content
    if current_bar_lines:
        blocks.append(BarGroup(
            lines=current_bar_lines,
            start_line=bar_group_start,
            end_line=len(lines) - 1
        ))
    if current_text_lines:
        blocks.append(TextBlock(
            content=current_text_lines,
            line_numbers=current_text_line_numbers
        ))
    
    return blocks


def format_songml(content: str) -> str:
    """Format SongML content with aligned bar markers.
    
    Args:
        content: SongML document text
        
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
    lines = content.split('\n')
    blocks = group_bar_lines(lines)
    
    output_lines = []
    
    for block in blocks:
        if isinstance(block, TextBlock):
            # Preserve text blocks as-is
            output_lines.extend(block.content)
        elif isinstance(block, BarGroup):
            # Align bar lines
            column_widths = calculate_column_widths(block)
            aligned = align_bar_group(block, column_widths)
            output_lines.extend(aligned)
    
    return '\n'.join(output_lines)


def main() -> None:
    """CLI entry point for songml-format command.
    
    Usage:
        songml-format INPUT.songml              # Print to stdout
        songml-format INPUT.songml -i           # Format in-place
        songml-format INPUT.songml OUTPUT.songml  # Write to OUTPUT
    
    Exit codes:
        0: Success
        1: File error or invalid arguments
    """
    if len(sys.argv) < 2:
        print("Usage: songml-format INPUT.songml              # Print to stdout", file=sys.stderr)
        print("       songml-format INPUT.songml -i|--inplace  # Format in-place", file=sys.stderr)
        print("       songml-format INPUT.songml OUTPUT.songml # Write to OUTPUT", file=sys.stderr)
        sys.exit(1)
    
    input_file = sys.argv[1]
    inplace = '-i' in sys.argv or '--inplace' in sys.argv
    
    # Determine output destination
    output_file = None
    if inplace:
        output_file = input_file
    elif len(sys.argv) > 2 and sys.argv[2] not in ['-i', '--inplace']:
        output_file = sys.argv[2]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        formatted = format_songml(content)
        
        if output_file:
            # Write to file (either in-place or to specified output)
            with open(output_file, 'w', encoding='utf-8') as f:
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
