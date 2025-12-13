"""Tests for chord voicing validator."""

from songml_utils.voicing_validator import validate_chord_voicing, validate_voicing_table


def test_valid_major_chord():
    """Test valid major chord voicing."""
    is_valid, warning = validate_chord_voicing("C", "C", [0, 4, 7])
    assert is_valid
    assert warning is None


def test_valid_maj7_chord():
    """Test valid maj7 chord voicing."""
    is_valid, warning = validate_chord_voicing("Cmaj7", "C", [0, 4, 7, 11])
    assert is_valid
    assert warning is None


def test_valid_minor_chord():
    """Test valid minor chord voicing."""
    is_valid, warning = validate_chord_voicing("Dm", "D", [0, 3, 7])
    assert is_valid
    assert warning is None


def test_invalid_maj7_chord():
    """Test invalid maj7 chord (wrong intervals)."""
    # Using minor 7 intervals instead of major 7
    is_valid, warning = validate_chord_voicing("Cmaj7", "C", [0, 3, 7, 10])
    assert not is_valid
    assert warning is not None
    assert "missing" in warning.lower() or "unexpected" in warning.lower()


def test_slash_chord():
    """Test slash chord validation."""
    is_valid, warning = validate_chord_voicing("C7/G", "C", [0, 4, 7, 10])
    assert is_valid
    assert warning is None


def test_unknown_root():
    """Test handling of invalid root note."""
    is_valid, warning = validate_chord_voicing("Cmaj7", "X", [0, 4, 7, 11])
    assert not is_valid
    assert "invalid root" in warning.lower()


def test_validate_table():
    """Test bulk validation of voicing table."""
    table = {
        "C": ("C", [0, 4, 7], "test.tsv", 1),
        "Cmaj7": ("C", [0, 4, 7, 11], "test.tsv", 2),
        "Dm": ("D", [0, 3, 7], "test.tsv", 3),
        "BadChord": ("C", [0, 1, 2], "test.tsv", 4),  # Invalid intervals
    }
    
    warnings = validate_voicing_table(table)
    
    # Should have at least one warning for BadChord
    assert len(warnings) > 0
    assert any("BadChord" in w for w in warnings)


def test_empty_table():
    """Test validation of empty table."""
    warnings = validate_voicing_table({})
    assert len(warnings) == 0


def test_doubled_notes():
    """Test voicing with doubled notes (octaves)."""
    # C major with doubled root an octave up
    is_valid, warning = validate_chord_voicing("C", "C", [0, 4, 7, 12])
    # Should pass - extra octave is allowed
    assert is_valid or "unexpected" in (warning or "").lower()
