"""Tests for songml-create CLI tool."""

import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from songml_utils.create import (
    create_project,
    get_chord_progression,
    load_template,
    main,
    parse_key,
    sanitize_project_name,
)


class TestParseKey:
    """Test key parsing functionality."""

    def test_major_keys(self):
        """Test parsing major keys."""
        assert parse_key("C") == ("C", False)
        assert parse_key("F#") == ("F#", False)
        assert parse_key("Bb") == ("Bb", False)
        assert parse_key("Db") == ("Db", False)

    def test_minor_keys(self):
        """Test parsing minor keys."""
        assert parse_key("Amin") == ("A", True)
        assert parse_key("C#min") == ("C#", True)
        assert parse_key("Bbmin") == ("Bb", True)
        assert parse_key("Fmin") == ("F", True)

    def test_invalid_keys(self):
        """Test invalid key formats."""
        with pytest.raises(ValueError, match="Invalid key format"):
            parse_key("H")

        with pytest.raises(ValueError, match="Invalid key format"):
            parse_key("C#major")

        with pytest.raises(ValueError, match="Invalid key format"):
            parse_key("Xyz")

        with pytest.raises(ValueError, match="Key cannot be empty"):
            parse_key("")


class TestChordProgression:
    """Test chord progression generation."""

    def test_major_key_progressions(self):
        """Test I-vi-IV-V progressions in major keys."""
        # C major
        chords = get_chord_progression("C", False)
        assert chords == {"I": "C", "vi": "Am", "IV": "F", "V": "G"}

        # F major
        chords = get_chord_progression("F", False)
        assert chords == {"I": "F", "vi": "Dm", "IV": "Bb", "V": "C"}

        # G major
        chords = get_chord_progression("G", False)
        assert chords == {"I": "G", "vi": "Em", "IV": "C", "V": "D"}

    def test_minor_key_progressions(self):
        """Test chord progressions in minor keys."""
        # A minor
        chords = get_chord_progression("A", True)
        assert chords == {"I": "Am", "vi": "F", "IV": "Dm", "V": "Em"}

        # C minor
        chords = get_chord_progression("C", True)
        assert chords == {"I": "Cm", "vi": "Ab", "IV": "Fm", "V": "Gm"}

        # F# minor
        chords = get_chord_progression("F#", True)
        assert chords == {"I": "F#m", "vi": "D", "IV": "Bm", "V": "C#m"}

    def test_unsupported_keys(self):
        """Test error handling for unsupported keys."""
        with pytest.raises(ValueError, match="Unsupported major key"):
            get_chord_progression("X", False)

        with pytest.raises(ValueError, match="Unsupported minor key"):
            get_chord_progression("X", True)


class TestSanitizeProjectName:
    """Test project name sanitization."""

    def test_basic_sanitization(self):
        """Test basic name sanitization."""
        assert sanitize_project_name("My Song") == "my-song"
        assert sanitize_project_name("Another Song Title") == "another-song-title"
        assert sanitize_project_name("  Spaces  ") == "spaces"

    def test_forbidden_characters(self):
        """Test removal of Windows forbidden characters."""
        assert sanitize_project_name("Song <with> forbidden:chars") == "song-with-forbidden-chars"
        assert sanitize_project_name("File/Path\\Name") == "file-path-name"
        assert sanitize_project_name("Question?Mark*") == "question-mark"

    def test_multiple_separators(self):
        """Test handling of multiple consecutive separators."""
        assert sanitize_project_name("Song---With--Many-Dashes") == "song-with-many-dashes"
        assert sanitize_project_name("Song   With   Spaces") == "song-with-spaces"

    def test_edge_cases(self):
        """Test edge cases in name sanitization."""
        assert sanitize_project_name("") == "untitled-song"
        assert sanitize_project_name("   ") == "untitled-song"
        assert sanitize_project_name("---") == "untitled-song"
        assert sanitize_project_name("-Song-") == "song"


class TestLoadTemplate:
    """Test template loading."""

    def test_load_template(self):
        """Test that template loads successfully."""
        template = load_template()
        assert isinstance(template, str)
        assert len(template) > 0
        assert "{{title}}" in template
        assert "{{key}}" in template
        assert "{{I}}" in template
        assert "{{vi}}" in template
        assert "{{IV}}" in template
        assert "{{V}}" in template


class TestCreateProject:
    """Test project creation functionality."""

    def setUp(self):
        """Set up test directory."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test directory."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_major_project(self):
        """Test creating project in major key."""
        self.setUp()
        try:
            create_project("Test Song", "C")

            # Check project directory exists
            assert os.path.exists("test-song")

            # Check songml file exists
            songml_path = os.path.join("test-song", "test-song.songml")
            assert os.path.exists(songml_path)

            # Check chord voicings file exists
            voicings_path = os.path.join("test-song", "chord_voicings.tsv")
            assert os.path.exists(voicings_path)

            # Check songml content
            with open(songml_path, encoding="utf-8") as f:
                content = f.read()

            assert "Title: Test Song" in content
            assert "Key: C" in content
            # Check that chords are present (formatted with padding)
            assert "| C " in content  # I chord (with padding)
            assert "| Am " in content  # vi chord (with padding)
            assert "| F " in content  # IV chord (with padding)
            assert "| G " in content  # V chord (with padding)
        finally:
            self.tearDown()

    def test_create_minor_project(self):
        """Test creating project in minor key."""
        self.setUp()
        try:
            create_project("Sad Song", "Amin")

            # Check project exists
            assert os.path.exists("sad-song")

            songml_path = os.path.join("sad-song", "sad-song.songml")
            with open(songml_path, encoding="utf-8") as f:
                content = f.read()

            assert "Title: Sad Song" in content
            assert "Key: Amin" in content
            # Check that chords are present (formatted with padding)
            assert "| Am " in content  # i chord (with padding)
            assert "| F " in content  # bVI chord (with padding)
            assert "| Dm " in content  # iv chord (with padding)
            assert "| Em " in content  # v chord (with padding)
        finally:
            self.tearDown()

    def test_output_is_formatted(self):
        """Test that created file is formatted with aligned bars."""
        self.setUp()
        try:
            create_project("Format Test", "C")

            songml_path = os.path.join("format-test", "format-test.songml")
            with open(songml_path, encoding="utf-8") as f:
                content = f.read()

            # Check that bars are aligned (formatter pads to make columns align)
            lines = content.split("\n")

            # Find lines with bar markers
            bar_lines = [line for line in lines if "|" in line and line.strip().startswith("|")]

            # At least some bar lines should exist
            assert len(bar_lines) > 0

            # Check that within a section, bar positions align vertically
            # For example, in the Intro section:
            # |   1   |   2   |   3   |   4   |
            # | C     | Am    | F     | G     |
            # The | markers should be at the same positions

            intro_section_start = content.find("[Intro - 4 bars]")
            assert intro_section_start != -1

            # Get lines after the intro header, filtering for bar lines only
            intro_content = content[intro_section_start:].split("\n")
            intro_bar_lines = [line for line in intro_content if line.strip().startswith("|")]

            # Check that we have at least 2 bar lines to compare
            if len(intro_bar_lines) >= 2:
                # Compare the first two bar lines (typically bar numbers and chords)
                line1_bars = [i for i, c in enumerate(intro_bar_lines[0]) if c == "|"]
                line2_bars = [i for i, c in enumerate(intro_bar_lines[1]) if c == "|"]

                # If both lines have bars, they should align
                if line1_bars and line2_bars:
                    assert line1_bars == line2_bars, "Bar markers should be vertically aligned"
        finally:
            self.tearDown()

    def test_project_exists_error(self):
        """Test error when project directory already exists."""
        self.setUp()
        try:
            # Create directory first
            os.makedirs("test-song")

            with pytest.raises(FileExistsError, match="already exists"):
                create_project("Test Song", "C")
        finally:
            self.tearDown()

    def test_invalid_key_error(self):
        """Test error handling for invalid keys."""
        self.setUp()
        try:
            with pytest.raises(ValueError):
                create_project("Test Song", "InvalidKey")
        finally:
            self.tearDown()


class TestMainCLI:
    """Test main CLI function."""

    @patch("sys.argv", ["songml-create", "Test Song", "C"])
    @patch("songml_utils.create.create_project")
    def test_main_success(self, mock_create):
        """Test successful CLI execution."""
        main()
        mock_create.assert_called_once_with("Test Song", "C")

    @patch("sys.argv", ["songml-create"])
    def test_main_insufficient_args(self):
        """Test CLI with insufficient arguments."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2  # argparse returns 2 for usage errors

    @patch("sys.argv", ["songml-create", "Song", "C", "extra"])
    def test_main_too_many_args(self):
        """Test CLI with too many arguments."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2  # argparse returns 2 for usage errors

    @patch("sys.argv", ["songml-create", "Test Song", "InvalidKey"])
    @patch("songml_utils.create.create_project", side_effect=ValueError("Invalid key"))
    def test_main_invalid_key(self, mock_create):
        """Test CLI error handling for invalid keys."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch("sys.argv", ["songml-create", "Test Song", "C"])
    @patch("songml_utils.create.create_project", side_effect=FileExistsError("Project exists"))
    def test_main_project_exists(self, mock_create):
        """Test CLI error handling when project exists."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
