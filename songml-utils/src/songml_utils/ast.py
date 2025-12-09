"""Abstract syntax tree definitions for SongML."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union
import json


@dataclass
class ChordToken:
    """A single chord symbol with its timing information within a bar."""
    text: str  # Opaque chord text (e.g., "C", "Dm7", "F9/A", "/Bb")
    start_beat: float  # Position within the bar (0-based)
    duration_beats: float  # Duration in beats
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {"type": "ChordToken", **asdict(self)}


@dataclass
class Bar:
    """A single bar containing chords and optional lyrics."""
    number: int  # Bar number (sequential within section)
    chords: List[ChordToken] = field(default_factory=list)  # Empty for synthesized bars
    lyrics: Optional[str] = None  # Lyric text for this bar
    line_number: int = 0  # Source line number for error reporting
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": "Bar",
            "number": self.number,
            "chords": [c.to_dict() for c in self.chords],
            "lyrics": self.lyrics,
            "line_number": self.line_number
        }


@dataclass
class Section:
    """A named section with a declared bar count and bar sequence."""
    name: str  # Section name (e.g., "Verse 1", "Chorus")
    bar_count: int  # Declared number of bars
    bars: List[Bar] = field(default_factory=list)  # Flat sequence of bars
    line_number: int = 0  # Source line number for error reporting
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": "Section",
            "name": self.name,
            "bar_count": self.bar_count,
            "bars": [b.to_dict() for b in self.bars],
            "line_number": self.line_number
        }


@dataclass
class Property:
    """A property declaration (e.g., Key: Cmaj, Tempo: 120)."""
    name: str  # Property name (e.g., "Key", "Tempo", "Title")
    value: str  # Property value as text
    line_number: int = 0  # Source line number for error reporting
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {"type": "Property", **asdict(self)}


@dataclass
class TextBlock:
    """A block of free-form text, comments, or unrecognized content."""
    lines: List[str] = field(default_factory=list)  # Lines of text
    line_number: int = 0  # Starting line number
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {"type": "TextBlock", **asdict(self)}


@dataclass
class Document:
    """Top-level document containing sequence of text blocks, properties, and sections."""
    items: List[Union[TextBlock, Property, Section]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)  # Non-fatal issues (e.g., duplicate sections)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "version": "1.0",
            "type": "Document",
            "items": [item.to_dict() for item in self.items],
            "warnings": self.warnings
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Document':
        """Deserialize from dict. Future hook for loading AST JSON."""
        # TODO: Implement deserialization when needed
        # This keeps the API ready for bidirectional conversion
        raise NotImplementedError("AST deserialization not yet implemented")


class ParseError(Exception):
    """Exception raised when parser encounters a structural error."""
    def __init__(self, message: str, line_number: int):
        self.message = message
        self.line_number = line_number
        super().__init__(f"Line {line_number}: {message}")
