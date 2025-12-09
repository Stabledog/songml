"""SongML parser - reads and validates SongML files.

Intentionally forgiving - focuses on extracting meaning rather than strict validation.
"""

import re
from typing import Dict, List, Optional, Tuple
from .ast import (
    Document, TextBlock, Property, Section, Bar, ChordToken, ParseError
)


def parse_songml(content: str) -> Document:
    """Parse SongML content into an AST.
    
    Single-pass parser with persistent property state.
    Properties have defaults: Time: 4/4, Key: Cmaj, Tempo: 100, Title: Untitled
    """
    lines = content.split('\n')
    
    # Initialize property state with defaults
    property_state: Dict[str, str] = {
        'Time': '4/4',
        'Key': 'Cmaj',
        'Tempo': '100',
        'Title': 'Untitled'
    }
    
    document = Document()
    current_text_block: Optional[TextBlock] = None
    current_section: Optional[Section] = None
    section_names_seen: set = set()
    
    line_num = 0
    while line_num < len(lines):
        line = lines[line_num]
        
        # Try to parse as property
        prop_match = re.match(r'^([A-Z][A-Za-z]*)\s*:\s*(.+)$', line.strip())
        if prop_match:
            # Properties terminate sections
            if current_section:
                _finalize_section(current_section, document)
                current_section = None
            
            # Flush text block
            if current_text_block:
                document.items.append(current_text_block)
                current_text_block = None
            
            # Create property and update state
            prop_name = prop_match.group(1)
            prop_value = prop_match.group(2).strip()
            property_state[prop_name] = prop_value
            document.items.append(Property(prop_name, prop_value, line_num + 1))
            line_num += 1
            continue
        
        # Try to parse as section header
        section_match = re.match(r'^\[(.+?)\s*-\s*(\d+)\s*bars?\s*\]$', line.strip(), re.IGNORECASE)
        if section_match:
            # Flush current section
            if current_section:
                _finalize_section(current_section, document)
            
            # Flush text block
            if current_text_block:
                document.items.append(current_text_block)
                current_text_block = None
            
            # Start new section
            section_name = section_match.group(1).strip()
            bar_count = int(section_match.group(2))
            
            # Warn on duplicate section names
            if section_name in section_names_seen:
                document.warnings.append(f"Line {line_num + 1}: Duplicate section name '{section_name}'")
            section_names_seen.add(section_name)
            
            current_section = Section(section_name, bar_count, [], line_num + 1)
            line_num += 1
            continue
        
        # Check if we're inside a section and this looks like a bar-delimited row
        if current_section and '|' in line:
            # Parse section content starting from this line
            line_num = _parse_section_content(lines, line_num, current_section, property_state)
            continue
        
        # Otherwise, accumulate as text block
        if current_section:
            # This shouldn't happen - section without bars?
            # We'll let _finalize_section catch this
            pass
        
        if not current_text_block:
            current_text_block = TextBlock([], line_num + 1)
        current_text_block.lines.append(line)
        line_num += 1
    
    # Finalize any remaining blocks
    if current_section:
        _finalize_section(current_section, document)
    if current_text_block:
        document.items.append(current_text_block)
    
    return document


def _finalize_section(section: Section, document: Document) -> None:
    """Finalize section: validate bars exist, synthesize empty bars if needed."""
    if len(section.bars) == 0:
        raise ParseError(f"Section '{section.name}' has no bars", section.line_number)
    
    # Synthesize empty bars if declared count > parsed count
    if len(section.bars) < section.bar_count:
        last_bar_num = section.bars[-1].number if section.bars else -1
        num_to_synthesize = section.bar_count - len(section.bars)
        for i in range(num_to_synthesize):
            section.bars.append(Bar(
                number=last_bar_num + 1 + i,
                chords=[],
                lyrics=None,
                line_number=section.line_number
            ))
    elif len(section.bars) > section.bar_count:
        raise ParseError(
            f"Section '{section.name}' declares {section.bar_count} bars but has {len(section.bars)}",
            section.line_number
        )
    
    document.items.append(section)


def _parse_section_content(lines: List[str], start_line: int, section: Section, property_state: Dict[str, str]) -> int:
    """Parse section content (multi-group bar-number/chord/lyric rows).
    
    Returns the line number to continue parsing from.
    """
    line_num = start_line
    
    while line_num < len(lines):
        line = lines[line_num]
        
        # Check if this line ends the section
        if not line.strip():
            line_num += 1
            continue
        
        # Property line terminates section
        if re.match(r'^([A-Z][A-Za-z]*)\s*:\s*(.+)$', line.strip()):
            break
        
        # New section header terminates current section
        if re.match(r'^\[(.+?)\s*-\s*(\d+)\s*bars?\s*\]$', line.strip(), re.IGNORECASE):
            break
        
        # Not a bar-delimited row - might be text between groups, or end of section
        if '|' not in line:
            line_num += 1
            continue
        
        # Parse a row group: bar-numbers, chords, optional lyrics
        line_num = _parse_row_group(lines, line_num, section, property_state)
    
    return line_num


def _parse_row_group(lines: List[str], start_line: int, section: Section, property_state: Dict[str, str]) -> int:
    """Parse one group of rows: bar-number row, chord row, optional lyric row."""
    line_num = start_line
    
    # First row: must be bar-numbers or chords
    first_row = lines[line_num]
    cells = _split_bar_row(first_row)
    
    # Check if first cell starts with digit = bar-number row
    if cells and cells[0].strip() and cells[0].strip()[0].isdigit():
        # This is a bar-number row
        bar_numbers = _parse_bar_number_row(cells, line_num + 1)
        line_num += 1
        
        # Next row must be chords
        if line_num >= len(lines):
            raise ParseError("Bar-number row without following chord row", line_num)
        
        chord_row = lines[line_num]
        if '|' not in chord_row:
            raise ParseError("Expected chord row after bar-number row", line_num + 1)
        
        chord_cells = _split_bar_row(chord_row)
        if len(chord_cells) != len(bar_numbers):
            raise ParseError(
                f"Bar-number row has {len(bar_numbers)} cells, chord row has {len(chord_cells)}",
                line_num + 1
            )
        
        line_num += 1
        
        # Optional lyric row
        lyric_cells = None
        if line_num < len(lines) and '|' in lines[line_num]:
            next_row = lines[line_num]
            next_cells = _split_bar_row(next_row)
            
            # Check if this is a lyric row (first cell doesn't start with digit)
            if not (next_cells and next_cells[0].strip() and next_cells[0].strip()[0].isdigit()):
                lyric_cells = next_cells
                if len(lyric_cells) != len(bar_numbers):
                    raise ParseError(
                        f"Lyric row has {len(lyric_cells)} cells, expected {len(bar_numbers)}",
                        line_num + 1
                    )
                line_num += 1
        
        # Create bars with timing inference
        _create_bars(section, bar_numbers, chord_cells, lyric_cells, property_state, start_line + 1)
    else:
        # No bar-number row - error for now (could auto-number in future)
        raise ParseError("Section must start with bar-number row (first cell must contain digit)", line_num + 1)
    
    return line_num


def _split_bar_row(line: str) -> List[str]:
    """Split a bar-delimited row into cells."""
    # Remove leading/trailing pipes and split
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return line.split('|')


def _parse_bar_number_row(cells: List[str], line_number: int) -> List[int]:
    """Parse bar-number row: first cell sets counter, auto-increment, validate cells with numbers."""
    if not cells or not cells[0].strip():
        raise ParseError("Bar-number row: first cell must contain a number", line_number)
    
    first_num_text = cells[0].strip()
    if not first_num_text.isdigit():
        raise ParseError(f"Bar-number row: first cell must be a number, got '{first_num_text}'", line_number)
    
    bar_numbers = []
    current_num = int(first_num_text)
    bar_numbers.append(current_num)
    
    for i, cell in enumerate(cells[1:], start=1):
        cell_text = cell.strip()
        if cell_text:
            # Cell has content - must be a number and must match expected
            if not cell_text.isdigit():
                raise ParseError(f"Bar-number row: cell {i+1} must be a number, got '{cell_text}'", line_number)
            actual_num = int(cell_text)
            expected_num = current_num + 1
            if actual_num != expected_num:
                raise ParseError(
                    f"Bar-number row: gap detected. Expected {expected_num}, got {actual_num}",
                    line_number
                )
            current_num = actual_num
        else:
            # Empty cell - auto-increment
            current_num += 1
        bar_numbers.append(current_num)
    
    return bar_numbers


def _create_bars(section: Section, bar_numbers: List[int], chord_cells: List[str], 
                 lyric_cells: Optional[List[str]], property_state: Dict[str, str], line_number: int) -> None:
    """Create Bar objects with timing inference."""
    time_sig = property_state.get('Time', '4/4')
    beats_per_bar = _parse_time_signature(time_sig, line_number)
    
    for i, bar_num in enumerate(bar_numbers):
        chord_text = chord_cells[i].strip()
        lyric_text = lyric_cells[i].strip() if lyric_cells else None
        
        # Parse chords and infer timing
        chord_tokens = _parse_chord_tokens(chord_text, beats_per_bar, line_number)
        
        bar = Bar(
            number=bar_num,
            chords=chord_tokens,
            lyrics=lyric_text if lyric_text else None,
            line_number=line_number
        )
        section.bars.append(bar)


def _parse_time_signature(time_sig: str, line_number: int) -> int:
    """Parse time signature and return beats per bar."""
    match = re.match(r'^(\d+)/(\d+)$', time_sig.strip())
    if not match:
        raise ParseError(f"Invalid time signature format: '{time_sig}'", line_number)
    
    numerator = int(match.group(1))
    denominator = int(match.group(2))
    
    if denominator not in [4, 8]:
        raise ParseError(f"Time signature denominator must be 4 or 8, got {denominator}", line_number)
    
    return numerator


def _parse_chord_tokens(chord_text: str, beats_per_bar: int, line_number: int) -> List[ChordToken]:
    """Parse chord tokens with timing inference.
    
    Timing rules:
    - '.' = 1 beat (can be prefix, suffix, or standalone)
    - ';' after dots = +0.5 (e.g., '...;F' = 3.5 beats rest then F)
    - Formats: '...;F' (prefix), 'F....' (suffix), 'F . .' (separated)
    - Unmarked chords: first N-1 get 1 beat each, last fills remaining
    """
    if not chord_text:
        return []
    
    # Split on whitespace
    tokens = chord_text.split()
    if not tokens:
        return []
    
    chord_tokens = []
    current_beat = 0.0
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        # Check if this is a pure dot token or timing marker
        if token == '.':
            # Standalone dot = 1 beat rest
            current_beat += 1.0
            i += 1
            continue
        
        # Parse timing markers and extract chord text
        # Format 1: [.]*[;]?<chord>[.]* (prefix dots, optional semicolon, chord, suffix dots)
        prefix_dots = 0
        has_semicolon = False
        chord_start_idx = 0
        
        # Scan for prefix dots
        while chord_start_idx < len(token) and token[chord_start_idx] == '.':
            prefix_dots += 1
            chord_start_idx += 1
        
        # Check for semicolon after prefix dots
        if chord_start_idx < len(token) and token[chord_start_idx] == ';':
            has_semicolon = True
            chord_start_idx += 1
        
        # Extract chord text and count suffix dots
        chord_end_idx = len(token)
        while chord_end_idx > chord_start_idx and token[chord_end_idx - 1] == '.':
            chord_end_idx -= 1
        
        suffix_dots = len(token) - chord_end_idx
        chord_text_part = token[chord_start_idx:chord_end_idx]
        
        # Calculate beat advancement from prefix timing markers
        prefix_beat_advance = prefix_dots + (0.5 if has_semicolon else 0.0)
        
        if chord_text_part:
            # This token has a chord
            # Advance position by prefix timing markers
            current_beat += prefix_beat_advance
            
            # Check for overflow
            if current_beat > beats_per_bar:
                raise ParseError(
                    f"Beat overflow: accumulated {current_beat} beats exceeds {beats_per_bar}",
                    line_number
                )
            
            # Duration is determined by suffix dots or by last-chord-fills rule
            if suffix_dots > 0:
                # Explicit duration from suffix dots
                duration = float(suffix_dots)
            else:
                # Check if this is the last chord token (not counting standalone dots)
                is_last_chord = True
                for j in range(i + 1, len(tokens)):
                    next_token = tokens[j]
                    if next_token != '.':
                        # Check if next token has a chord (not just timing markers)
                        temp_idx = 0
                        while temp_idx < len(next_token) and next_token[temp_idx] in '.;':
                            temp_idx += 1
                        if temp_idx < len(next_token):
                            is_last_chord = False
                            break
                
                if is_last_chord:
                    # Last chord fills remaining (after accounting for any standalone dots ahead)
                    # Count standalone dots that follow
                    dots_ahead = sum(1 for j in range(i + 1, len(tokens)) if tokens[j] == '.')
                    duration = beats_per_bar - current_beat - dots_ahead
                else:
                    # Not last chord: gets 1 beat by default
                    duration = 1.0
            
            chord_tokens.append(ChordToken(
                text=chord_text_part,
                start_beat=current_beat,
                duration_beats=duration
            ))
            
            current_beat += duration
        else:
            # Pure rest notation (like '...;' without chord)
            current_beat += prefix_beat_advance
            if suffix_dots > 0:
                current_beat += suffix_dots
        
        i += 1
    
    return chord_tokens
