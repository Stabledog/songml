"""Tests for songml-inspect-midi CLI."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from songml_utils.midi_inspector import InstrumentInfo, MIDIInspection
from songml_utils.midi_inspector_cli import main


class TestMidiInspectorCli:
    """Tests for MIDI inspector CLI entry point."""

    def test_main_success(self, tmp_path, monkeypatch, capsys):
        """Successful inspection should display formatted output."""
        # Create a dummy MIDI file (content doesn't matter, we'll mock inspect_midi)
        input_file = tmp_path / "test.mid"
        input_file.write_bytes(b"dummy midi content")

        # Mock inspect_midi to return test data
        mock_inspection = MIDIInspection(
            filename=str(input_file),
            tempo=120.0,
            time_signature_numerator=4,
            time_signature_denominator=4,
            key_signature="C",
            total_notes=10,
            duration_seconds=5.0,
            instruments=[
                InstrumentInfo(
                    program=0, program_name="Acoustic Grand Piano", is_drum=False, note_count=10
                )
            ],
        )

        mock_inspect = Mock(return_value=mock_inspection)
        monkeypatch.setattr("songml_utils.midi_inspector_cli.inspect_midi", mock_inspect)
        monkeypatch.setattr("sys.argv", ["songml-inspect-midi", str(input_file)])

        # Call main
        main()

        # Verify inspect_midi was called with correct path
        mock_inspect.assert_called_once_with(str(input_file))

        # Verify output contains key information
        captured = capsys.readouterr()
        assert "test.mid" in captured.out
        assert "120.0 BPM" in captured.out
        assert "4/4" in captured.out
        assert "10" in captured.out  # note count
        assert "Acoustic Grand Piano" in captured.out

    def test_main_file_not_found(self, monkeypatch, capsys):
        """Should exit with error message when file doesn't exist."""
        monkeypatch.setattr("sys.argv", ["songml-inspect-midi", "nonexistent.mid"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        # FileNotFoundError gets caught by the FileNotFoundError handler
        assert "✗" in captured.err
        assert "nonexistent.mid" in captured.err

    def test_main_invalid_midi(self, tmp_path, monkeypatch, capsys):
        """Should exit with error message for invalid MIDI file."""
        # Create invalid MIDI file
        invalid_file = tmp_path / "invalid.mid"
        invalid_file.write_text("Not a MIDI file")

        monkeypatch.setattr("sys.argv", ["songml-inspect-midi", str(invalid_file)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ Inspection error" in captured.err

    def test_main_unexpected_error(self, tmp_path, monkeypatch, capsys):
        """Should handle unexpected errors gracefully."""
        input_file = tmp_path / "test.mid"
        input_file.write_bytes(b"dummy")

        # Mock inspect_midi to raise unexpected error
        mock_inspect = Mock(side_effect=RuntimeError("Unexpected problem"))
        monkeypatch.setattr("songml_utils.midi_inspector_cli.inspect_midi", mock_inspect)
        monkeypatch.setattr("sys.argv", ["songml-inspect-midi", str(input_file)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ Unexpected error" in captured.err
