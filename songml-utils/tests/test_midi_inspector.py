"""Tests for MIDI inspector core functionality."""

from __future__ import annotations

import mido
import pytest

from songml_utils.midi_inspector import (
    InstrumentInfo,
    MIDIInspection,
    _key_number_to_string,
    format_inspection,
    inspect_midi,
)


class TestKeyNumberToString:
    """Tests for _key_number_to_string helper."""

    def test_c_major(self):
        """Key number 0 should be C major."""
        assert _key_number_to_string(0) == "C"

    def test_g_major(self):
        """Key number 1 should be G major."""
        assert _key_number_to_string(1) == "G"

    def test_f_major(self):
        """Key number -1 should be F major."""
        assert _key_number_to_string(-1) == "F"

    def test_flats(self):
        """Flat keys should be represented correctly."""
        assert _key_number_to_string(-2) == "Bb"
        assert _key_number_to_string(-7) == "Cb"

    def test_sharps(self):
        """Sharp keys should be represented correctly."""
        assert _key_number_to_string(2) == "D"
        assert _key_number_to_string(7) == "C#"

    def test_out_of_range_returns_c(self):
        """Out of range key numbers should default to C."""
        assert _key_number_to_string(100) == "C"
        assert _key_number_to_string(-100) == "C"


class TestInspectMidi:
    """Tests for inspect_midi function."""

    def test_basic_midi_inspection(self, tmp_path):
        """Should extract basic properties from a simple MIDI file."""
        # Create a simple MIDI file using mido
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        # Set tempo to 120 BPM
        track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120)))

        # Set time signature to 4/4
        track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4))

        # Add some notes
        track.append(mido.Message("program_change", program=0, time=0))
        track.append(mido.Message("note_on", note=60, velocity=64, time=0))
        track.append(mido.Message("note_off", note=60, velocity=64, time=480))
        track.append(mido.Message("note_on", note=64, velocity=64, time=0))
        track.append(mido.Message("note_off", note=64, velocity=64, time=480))

        midi_path = tmp_path / "test.mid"
        midi.save(str(midi_path))

        # Inspect the file
        result = inspect_midi(str(midi_path))

        assert isinstance(result, MIDIInspection)
        assert result.filename == str(midi_path)
        assert result.tempo == pytest.approx(120.0, rel=0.1)
        assert result.time_signature_numerator == 4
        assert result.time_signature_denominator == 4
        assert result.key_signature == "C"  # Default when not set
        assert result.total_notes == 2
        assert result.duration_seconds > 0
        assert len(result.instruments) == 1

    def test_instrument_info(self, tmp_path):
        """Should extract instrument information correctly."""
        # Create MIDI with a piano instrument
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(100)))
        track.append(mido.Message("program_change", program=0, time=0))  # Acoustic Grand Piano
        track.append(mido.Message("note_on", note=60, velocity=64, time=0))
        track.append(mido.Message("note_off", note=60, velocity=64, time=480))

        midi_path = tmp_path / "test.mid"
        midi.save(str(midi_path))

        result = inspect_midi(str(midi_path))

        assert len(result.instruments) == 1
        inst = result.instruments[0]
        assert inst.program == 0
        assert "Piano" in inst.program_name
        assert inst.is_drum is False
        assert inst.note_count == 1

    def test_missing_file_raises_error(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            inspect_midi("nonexistent.mid")

    def test_invalid_midi_raises_error(self, tmp_path):
        """Should raise ValueError for invalid MIDI file."""
        invalid_file = tmp_path / "invalid.mid"
        invalid_file.write_text("This is not a MIDI file")

        with pytest.raises(ValueError, match="Failed to load MIDI file"):
            inspect_midi(str(invalid_file))


class TestFormatInspection:
    """Tests for format_inspection function."""

    def test_format_basic_inspection(self):
        """Should format inspection results into readable text."""
        inspection = MIDIInspection(
            filename="test.mid",
            tempo=120.0,
            time_signature_numerator=4,
            time_signature_denominator=4,
            key_signature="C",
            total_notes=10,
            duration_seconds=5.5,
            instruments=[
                InstrumentInfo(
                    program=0, program_name="Acoustic Grand Piano", is_drum=False, note_count=10
                )
            ],
        )

        result = format_inspection(inspection)

        assert "test.mid" in result
        assert "120.0 BPM" in result
        assert "4/4" in result
        assert "C" in result
        assert "10" in result  # total notes
        assert "5.50 seconds" in result
        assert "Acoustic Grand Piano" in result

    def test_format_multiple_instruments(self):
        """Should list multiple instruments."""
        inspection = MIDIInspection(
            filename="multi.mid",
            tempo=100.0,
            time_signature_numerator=3,
            time_signature_denominator=4,
            key_signature="G",
            total_notes=20,
            duration_seconds=10.0,
            instruments=[
                InstrumentInfo(program=0, program_name="Piano", is_drum=False, note_count=10),
                InstrumentInfo(program=33, program_name="Bass", is_drum=False, note_count=10),
            ],
        )

        result = format_inspection(inspection)

        assert "Instruments: 2" in result
        assert "Piano" in result
        assert "Bass" in result
        assert "10 notes" in result

    def test_format_drum_track(self):
        """Should mark drum tracks."""
        inspection = MIDIInspection(
            filename="drums.mid",
            tempo=120.0,
            time_signature_numerator=4,
            time_signature_denominator=4,
            key_signature="C",
            total_notes=50,
            duration_seconds=8.0,
            instruments=[
                InstrumentInfo(program=0, program_name="Drums", is_drum=True, note_count=50)
            ],
        )

        result = format_inspection(inspection)

        assert "(drums)" in result
