"""CLI tool for creating new SongML projects."""

from __future__ import annotations

import os
import re
import shutil
import sys
from typing import Dict, Tuple


def parse_key(key_input: str) -> Tuple[str, bool]:
    """Parse key input like 'C', 'F#min', 'Dbmin' into (root, is_minor).
    
    Args:
        key_input: Key specification like 'C', 'F#min', 'Bb', 'C#min'
        
    Returns:
        Tuple of (root_note, is_minor)
        
    Raises:
        ValueError: If key format is invalid
    """
    if not key_input:
        raise ValueError("Key cannot be empty")
    
    # Match pattern like C, C#, Bb, F#min, Dbmin
    match = re.match(r'^([A-G][#b]?)(min)?$', key_input)
    if not match:
        raise ValueError(f"Invalid key format: {key_input}. Expected format like 'C', 'F#min', 'Bb'")
    
    root = match.group(1)
    is_minor = match.group(2) is not None
    
    return root, is_minor


def get_chord_progression(root: str, is_minor: bool) -> Dict[str, str]:
    """Get I-vi-IV-V chord progression for given key.
    
    Args:
        root: Root note (C, F#, Bb, etc.)
        is_minor: Whether the key is minor
        
    Returns:
        Dict mapping Roman numerals to chord symbols
    """
    # Circle of fifths for major keys
    major_keys = {
        'C': ('C', 'Am', 'F', 'G'),
        'G': ('G', 'Em', 'C', 'D'),
        'D': ('D', 'Bm', 'G', 'A'),
        'A': ('A', 'F#m', 'D', 'E'),
        'E': ('E', 'C#m', 'A', 'B'),
        'B': ('B', 'G#m', 'E', 'F#'),
        'F#': ('F#', 'D#m', 'B', 'C#'),
        'Db': ('Db', 'Bbm', 'Gb', 'Ab'),
        'Ab': ('Ab', 'Fm', 'Db', 'Eb'),
        'Eb': ('Eb', 'Cm', 'Ab', 'Bb'),
        'Bb': ('Bb', 'Gm', 'Eb', 'F'),
        'F': ('F', 'Dm', 'Bb', 'C'),
        # Enharmonic equivalents
        'C#': ('C#', 'A#m', 'F#', 'G#'),
        'Gb': ('Gb', 'Ebm', 'B', 'Db'),
    }
    
    # For minor keys, the relative minor is the vi of the major key
    minor_keys = {
        'A': ('Am', 'F', 'Dm', 'Em'),      # Am relative to C major
        'E': ('Em', 'C', 'Am', 'Bm'),      # Em relative to G major  
        'B': ('Bm', 'G', 'Em', 'F#m'),     # Bm relative to D major
        'F#': ('F#m', 'D', 'Bm', 'C#m'),   # F#m relative to A major
        'C#': ('C#m', 'A', 'F#m', 'G#m'),  # C#m relative to E major
        'G#': ('G#m', 'E', 'C#m', 'D#m'),  # G#m relative to B major
        'D#': ('D#m', 'B', 'G#m', 'A#m'),  # D#m relative to F# major
        'Bb': ('Bbm', 'Gb', 'Ebm', 'Fm'),  # Bbm relative to Db major
        'F': ('Fm', 'Db', 'Bbm', 'Cm'),    # Fm relative to Ab major
        'C': ('Cm', 'Ab', 'Fm', 'Gm'),     # Cm relative to Eb major
        'G': ('Gm', 'Eb', 'Cm', 'Dm'),     # Gm relative to Bb major
        'D': ('Dm', 'Bb', 'Gm', 'Am'),     # Dm relative to F major
        # Enharmonic equivalents
        'A#': ('A#m', 'F#', 'D#m', 'E#m'), # A#m relative to C# major
        'Eb': ('Ebm', 'B', 'Abm', 'Bbm'),  # Ebm relative to Gb major
    }
    
    if is_minor:
        if root not in minor_keys:
            raise ValueError(f"Unsupported minor key: {root}min")
        i, bvi, iv, v = minor_keys[root]
        return {'I': i, 'vi': bvi, 'IV': iv, 'V': v}
    else:
        if root not in major_keys:
            raise ValueError(f"Unsupported major key: {root}")
        I, vi, IV, V = major_keys[root]
        return {'I': I, 'vi': vi, 'IV': IV, 'V': V}


def sanitize_project_name(name: str) -> str:
    """Sanitize project name for use as directory and file name.
    
    Args:
        name: Original project name
        
    Returns:
        Sanitized name safe for Windows file systems
    """
    # Replace Windows forbidden characters with dashes
    forbidden = r'[<>:"/\\|?*]'
    sanitized = re.sub(forbidden, '-', name)
    
    # Remove leading/trailing whitespace and convert to lowercase
    sanitized = sanitized.strip().lower()
    
    # Replace multiple consecutive spaces/dashes with single dash
    sanitized = re.sub(r'[-\s]+', '-', sanitized)
    
    # Remove leading/trailing dashes
    sanitized = sanitized.strip('-')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'untitled-song'
    
    return sanitized


def load_template() -> str:
    """Load the basic SongML template.
    
    Returns:
        Template content as string
        
    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = os.path.join(
        os.path.dirname(__file__), 
        'data', 
        'templates', 
        'basic.songml'
    )
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def create_project(song_name: str, key_input: str) -> None:
    """Create a new SongML project.
    
    Args:
        song_name: Name of the song
        key_input: Key specification like 'C', 'F#min', etc.
        
    Raises:
        ValueError: If key format is invalid
        FileExistsError: If project directory already exists
        FileNotFoundError: If template or chord voicings file not found
    """
    # Parse inputs
    root, is_minor = parse_key(key_input)
    chords = get_chord_progression(root, is_minor)
    sanitized_name = sanitize_project_name(song_name)
    
    # Format key for SongML (use user input directly as specified)
    key_value = key_input
    
    # Check if project directory already exists
    if os.path.exists(sanitized_name):
        raise FileExistsError(f"Project directory '{sanitized_name}' already exists")
    
    # Load template
    template = load_template()
    
    # Replace tokens with basic chord symbols (no padding - leave formatting to format command)
    content = template.replace('{{title}}', song_name)
    content = content.replace('{{key}}', key_value)
    content = content.replace('{{I}}', chords['I'])
    content = content.replace('{{vi}}', chords['vi'])
    content = content.replace('{{IV}}', chords['IV'])
    content = content.replace('{{V}}', chords['V'])
    
    # Create project directory
    os.makedirs(sanitized_name)
    
    try:
        # Write songml file
        songml_path = os.path.join(sanitized_name, f'{sanitized_name}.songml')
        with open(songml_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Copy chord voicings file
        source_voicings = os.path.join(
            os.path.dirname(__file__), 
            'data', 
            'chord_voicings.tsv'
        )
        dest_voicings = os.path.join(sanitized_name, 'chord_voicings.tsv')
        shutil.copy2(source_voicings, dest_voicings)
        
        print(f"✓ Created project '{sanitized_name}' with key {key_value}")
        print(f"  Files: {songml_path}, {dest_voicings}")
        
    except Exception:
        # Clean up directory if creation fails
        shutil.rmtree(sanitized_name, ignore_errors=True)
        raise


def main() -> None:
    """CLI entry point for songml-create command.
    
    Creates a new SongML project with templated structure.
    
    Usage:
        songml-create "Song Name" [root][min]
        
    Examples:
        songml-create "My Song" C
        songml-create "Sad Song" C#min
        songml-create "Jazz Standard" Bb
    
    Exit codes:
        0: Success
        1: Invalid arguments, file errors, or creation failure
    """
    if len(sys.argv) != 3:
        print("Usage: songml-create \"Song Name\" [root][min]", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  songml-create \"My Song\" C", file=sys.stderr)
        print("  songml-create \"Sad Song\" C#min", file=sys.stderr)
        print("  songml-create \"Jazz Standard\" Bb", file=sys.stderr)
        sys.exit(1)
    
    song_name = sys.argv[1]
    key_input = sys.argv[2]
    
    try:
        create_project(song_name, key_input)
    except ValueError as e:
        print(f"✗ Invalid key: {e}", file=sys.stderr)
        sys.exit(1)
    except FileExistsError as e:
        print(f"✗ Project exists: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"✗ Template not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Creation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
