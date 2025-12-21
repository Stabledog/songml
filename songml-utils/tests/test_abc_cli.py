"""Tests for songml-to-abc CLI."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

from songml_utils.abc_cli import main


class TestAbcCli:
    """Tests for ABC export CLI entry point."""

    def test_main_write_file_success(self, tmp_path, monkeypatch, capsys):
        """Successful ABC export to file."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.abc"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        fake_doc = MagicMock()
        fake_doc.warnings = []
        mock_parse = Mock(return_value=fake_doc)
        mock_to_abc_string = Mock(return_value="X:1\nT:Test\n")

        monkeypatch.setattr("songml_utils.abc_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.abc_exporter.to_abc_string", mock_to_abc_string)
        monkeypatch.setattr("sys.argv", ["songml-to-abc", str(input_file), str(output_file)])

        main()

        # Verify output file was written
        assert output_file.exists()
        assert output_file.read_text() == "X:1\nT:Test\n"

        # Verify success message in stderr
        captured = capsys.readouterr()
        assert "✓ Exported to" in captured.err
        assert str(output_file) in captured.err

        # Verify stdout is empty (not printing to stdout for file write)
        assert "X:1" not in captured.out

    def test_main_stdout_output_dash(self, tmp_path, monkeypatch, capsys):
        """ABC export to stdout when output is '-'."""
        input_file = tmp_path / "song.songml"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        fake_doc = MagicMock()
        fake_doc.warnings = []
        mock_parse = Mock(return_value=fake_doc)
        abc_text = "X:1\nT:Test\nK:C\n"
        mock_to_abc_string = Mock(return_value=abc_text)

        monkeypatch.setattr("songml_utils.abc_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.abc_exporter.to_abc_string", mock_to_abc_string)
        monkeypatch.setattr("sys.argv", ["songml-to-abc", str(input_file), "-"])

        main()

        # Verify output to stdout
        captured = capsys.readouterr()
        assert abc_text in captured.out

        # Verify success message NOT in stderr (not for stdout)
        assert "✓ Exported to" not in captured.err

    def test_main_with_options(self, tmp_path, monkeypatch, capsys):
        """ABC export with unit-length and chord-style options."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.abc"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        fake_doc = MagicMock()
        fake_doc.warnings = []
        mock_parse = Mock(return_value=fake_doc)
        mock_to_abc_string = Mock(return_value="X:1\nT:Test\n")

        monkeypatch.setattr("songml_utils.abc_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.abc_exporter.to_abc_string", mock_to_abc_string)
        monkeypatch.setattr(
            "sys.argv",
            [
                "songml-to-abc",
                str(input_file),
                str(output_file),
                "--unit-length",
                "1/8",
                "--chord-style",
                "inline",
            ],
        )

        main()

        # Verify to_abc_string was called with correct options
        mock_to_abc_string.assert_called_once()
        kwargs = mock_to_abc_string.call_args[1]
        assert kwargs["unit_note_length"] == "1/8"
        assert kwargs["chord_style"] == "inline"
        assert kwargs["transpose"] == 0  # default transpose

    def test_main_parse_error_exits_1(self, tmp_path, monkeypatch, capsys):
        """ParseError causes exit with code 1."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.abc"
        input_file.write_text("invalid")

        from songml_utils.ast import ParseError

        mock_parse = Mock(side_effect=ParseError("Invalid syntax", 1))
        monkeypatch.setattr("songml_utils.abc_cli.parse_songml", mock_parse)
        monkeypatch.setattr("sys.argv", ["songml-to-abc", str(input_file), str(output_file)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ Parse error:" in captured.err

    def test_main_export_value_error_exits_1(self, tmp_path, monkeypatch, capsys):
        """ValueError from to_abc_string causes exit with code 1."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.abc"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        fake_doc = MagicMock()
        fake_doc.warnings = []
        mock_parse = Mock(return_value=fake_doc)
        mock_to_abc_string = Mock(side_effect=ValueError("Bad export"))

        monkeypatch.setattr("songml_utils.abc_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.abc_exporter.to_abc_string", mock_to_abc_string)
        monkeypatch.setattr("sys.argv", ["songml-to-abc", str(input_file), str(output_file)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ Export error:" in captured.err

    def test_main_input_file_not_found(self, monkeypatch, capsys):
        """FileNotFoundError when input file doesn't exist."""
        nonexistent = "/nonexistent/path/song.songml"
        output_file = "/tmp/song.abc"

        monkeypatch.setattr("sys.argv", ["songml-to-abc", nonexistent, output_file])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ File error:" in captured.err

    def test_main_with_warnings(self, tmp_path, monkeypatch, capsys):
        """Warnings from parser are printed to stderr."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.abc"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        fake_doc = MagicMock()
        fake_doc.warnings = ["Warning 1: something", "Warning 2: something else"]
        mock_parse = Mock(return_value=fake_doc)
        mock_to_abc_string = Mock(return_value="X:1\nT:Test\n")

        monkeypatch.setattr("songml_utils.abc_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.abc_exporter.to_abc_string", mock_to_abc_string)
        monkeypatch.setattr("sys.argv", ["songml-to-abc", str(input_file), str(output_file)])

        main()

        captured = capsys.readouterr()
        assert "Warning 1: something" in captured.err
        assert "Warning 2: something else" in captured.err

    def test_main_with_transpose_flag(self, tmp_path, monkeypatch, capsys):
        """Transpose flag is passed to to_abc_string."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.abc"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        fake_doc = MagicMock()
        fake_doc.warnings = []
        mock_parse = Mock(return_value=fake_doc)
        mock_to_abc_string = Mock(return_value="X:1\nT:Test\n")

        monkeypatch.setattr("songml_utils.abc_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.abc_exporter.to_abc_string", mock_to_abc_string)
        monkeypatch.setattr(
            "sys.argv", ["songml-to-abc", str(input_file), str(output_file), "-t", "7"]
        )

        main()

        # Verify to_abc_string was called with transpose=7
        mock_to_abc_string.assert_called_once()
        kwargs = mock_to_abc_string.call_args[1]
        assert kwargs["transpose"] == 7

    def test_main_with_transpose_long_form(self, tmp_path, monkeypatch, capsys):
        """Long form --transpose flag works correctly."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.abc"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        fake_doc = MagicMock()
        fake_doc.warnings = []
        mock_parse = Mock(return_value=fake_doc)
        mock_to_abc_string = Mock(return_value="X:1\nT:Test\n")

        monkeypatch.setattr("songml_utils.abc_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.abc_exporter.to_abc_string", mock_to_abc_string)
        monkeypatch.setattr(
            "sys.argv", ["songml-to-abc", str(input_file), str(output_file), "--transpose", "-5"]
        )

        main()

        # Verify to_abc_string was called with transpose=-5
        mock_to_abc_string.assert_called_once()
        kwargs = mock_to_abc_string.call_args[1]
        assert kwargs["transpose"] == -5
