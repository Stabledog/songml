"""Tests for songml-to-midi CLI."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

from songml_utils.midi_cli import main


class TestMidiCli:
    """Tests for midi CLI entry point."""

    def test_main_success_no_local_voicings(self, tmp_path, monkeypatch, capsys):
        """Successful export when no local chord_voicings.tsv exists."""
        # Setup temp files
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.mid"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        # Mock external dependencies
        fake_doc = MagicMock()
        mock_parse = Mock(return_value=fake_doc)
        mock_export = Mock()

        monkeypatch.setattr("songml_utils.midi_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.midi_cli.export_midi", mock_export)
        monkeypatch.setattr("sys.argv", ["songml-to-midi", str(input_file), str(output_file)])

        # Call main
        main()

        # Verify parse was called
        mock_parse.assert_called_once()
        assert input_file.read_text() in mock_parse.call_args[0]

        # Verify export was called with voicings_path=None (no local file)
        mock_export.assert_called_once()
        args = mock_export.call_args[0]
        assert args[0] == fake_doc  # doc
        assert args[1] == str(output_file)  # output path
        assert mock_export.call_args[1] == {} or (
            mock_export.call_args[0][2] is None
        )  # voicings_path=None

        # Verify success message in stderr
        captured = capsys.readouterr()
        assert "✓ Exported to" in captured.err
        assert str(output_file) in captured.err

    def test_main_success_with_local_voicings(self, tmp_path, monkeypatch, capsys):
        """Export uses local chord_voicings.tsv when it exists."""
        # Setup temp files and local voicings file
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.mid"
        local_voicings = tmp_path / "chord_voicings.tsv"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")
        local_voicings.write_text("C\tC\t0,4,7")

        # Mock external dependencies
        fake_doc = MagicMock()
        mock_parse = Mock(return_value=fake_doc)
        mock_export = Mock()

        monkeypatch.setattr("songml_utils.midi_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.midi_cli.export_midi", mock_export)
        monkeypatch.setattr("sys.argv", ["songml-to-midi", str(input_file), str(output_file)])

        # Call main
        main()

        # Verify export was called with the local voicings path
        mock_export.assert_called_once()
        args = mock_export.call_args[0]
        assert args[2] == str(local_voicings)  # voicings_path should be local file

    def test_main_parse_error_exits_1(self, tmp_path, monkeypatch, capsys):
        """ParseError causes exit with code 1."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.mid"
        input_file.write_text("invalid")

        from songml_utils.ast import ParseError

        mock_parse = Mock(side_effect=ParseError("Invalid syntax", 1))
        monkeypatch.setattr("songml_utils.midi_cli.parse_songml", mock_parse)
        monkeypatch.setattr("sys.argv", ["songml-to-midi", str(input_file), str(output_file)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ Parse error:" in captured.err

    def test_main_export_value_error_exits_1(self, tmp_path, monkeypatch, capsys):
        """ValueError from export_midi causes exit with code 1."""
        input_file = tmp_path / "song.songml"
        output_file = tmp_path / "song.mid"
        input_file.write_text("Title: Test\n\n[Verse - 1 bars]\n| C |")

        fake_doc = MagicMock()
        mock_parse = Mock(return_value=fake_doc)
        mock_export = Mock(side_effect=ValueError("Bad chord"))

        monkeypatch.setattr("songml_utils.midi_cli.parse_songml", mock_parse)
        monkeypatch.setattr("songml_utils.midi_cli.export_midi", mock_export)
        monkeypatch.setattr("sys.argv", ["songml-to-midi", str(input_file), str(output_file)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ Export error:" in captured.err

    def test_main_input_file_not_found(self, monkeypatch, capsys):
        """FileNotFoundError when input file doesn't exist."""
        nonexistent = "/nonexistent/path/song.songml"
        output_file = "/tmp/song.mid"

        monkeypatch.setattr("sys.argv", ["songml-to-midi", nonexistent, output_file])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ File error:" in captured.err
