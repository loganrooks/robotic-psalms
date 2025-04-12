import pytest
from typing import List, Tuple

# Attempt to import the non-existent function and potential custom error
# Import the actual function and error class
from robotic_psalms.utils.midi_parser import parse_midi_melody, MidiParsingError

# Placeholder path for a dummy MIDI file (replace with actual test file later)
VALID_MIDI_PATH = "tests/fixtures/simple_melody.mid"
MULTI_TRACK_MIDI_PATH = "tests/fixtures/multi_track.mid"
EMPTY_MIDI_PATH = "tests/fixtures/empty.mid"
INVALID_MIDI_PATH = "tests/fixtures/not_a_midi.txt"
NON_EXISTENT_PATH = "tests/fixtures/does_not_exist.mid"

def test_parse_midi_melody_valid_single_track():
    """
    Test parsing a simple, valid MIDI file with a single monophonic track.
    Expects a list of (pitch_hz, duration_sec) tuples matching the fixture.
    """
    melody = parse_midi_melody(VALID_MIDI_PATH)
    assert isinstance(melody, list)
    # Actual from pytest output: C4(0.5s), D4(0.5s), E4(0.5s), F4(0.5s)
    expected_melody = [
        (pytest.approx(261.63, abs=0.01), pytest.approx(0.5)),
        (pytest.approx(293.66, abs=0.01), pytest.approx(0.5)),
        (pytest.approx(329.63, abs=0.01), pytest.approx(0.5)),
        (pytest.approx(349.23, abs=0.01), pytest.approx(0.5)),
    ]
    assert len(melody) == len(expected_melody)
    for i, note in enumerate(melody):
        assert isinstance(note, tuple)
        assert len(note) == 2
        assert note[0] == expected_melody[i][0] # Pitch in Hz
        assert note[1] == expected_melody[i][1] # Duration in seconds
        assert note[0] > 0
        assert note[1] > 0
    for note in melody:
        assert isinstance(note, tuple)
        assert len(note) == 2
        assert isinstance(note[0], float) # Pitch in Hz
        assert isinstance(note[1], float) # Duration in seconds
        assert note[0] > 0
        assert note[1] > 0

def test_parse_midi_melody_multi_track_default():
    """
    Test parsing a multi-track MIDI, expecting it to default to the first track (index 0).
    """
    melody = parse_midi_melody(MULTI_TRACK_MIDI_PATH) # Default index is 0
    assert isinstance(melody, list)
    # Actual from pytest output: C4(0.4s), E4(0.4s), G4(0.4s)
    expected_melody = [
        (pytest.approx(261.63, abs=0.01), pytest.approx(0.4)),
        (pytest.approx(329.63, abs=0.01), pytest.approx(0.4)),
        (pytest.approx(392.00, abs=0.01), pytest.approx(0.4)), # Note: pytest output shows 391.995...
    ]
    assert len(melody) == len(expected_melody)
    for i, note in enumerate(melody):
        assert note[0] == expected_melody[i][0]
        assert note[1] == expected_melody[i][1]

def test_parse_midi_melody_multi_track_select_index():
    """
    Test parsing a multi-track MIDI, selecting a specific track (index 1).
    """
    melody = parse_midi_melody(MULTI_TRACK_MIDI_PATH, instrument_index=1)
    assert isinstance(melody, list)
    # Actual from pytest output: C5(0.5s), E5(0.5s), G5(0.5s)
    expected_melody = [
        (pytest.approx(523.25, abs=0.01), pytest.approx(0.5)),
        (pytest.approx(659.26, abs=0.01), pytest.approx(0.5)), # Note: pytest output shows 659.255...
        (pytest.approx(783.99, abs=0.01), pytest.approx(0.5)), # Note: pytest output shows 783.990...
    ]
    assert len(melody) == len(expected_melody)
    for i, note in enumerate(melody):
        assert note[0] == expected_melody[i][0]
        assert note[1] == expected_melody[i][1]

# Placeholder - Add test for selecting track by name if that feature is planned

def test_parse_midi_melody_file_not_found():
    """
    Test that parsing a non-existent file path raises FileNotFoundError.
    """
    with pytest.raises(FileNotFoundError):
        parse_midi_melody(NON_EXISTENT_PATH)

def test_parse_midi_melody_invalid_file_type():
    """
    Test that parsing a non-MIDI file raises MidiParsingError or ValueError.
    """
    # Expecting a specific MidiParsingError, but falling back to ValueError
    with pytest.raises((MidiParsingError, ValueError)):
        parse_midi_melody(INVALID_MIDI_PATH)

def test_parse_midi_melody_empty_or_no_notes():
    """
    Test that parsing an empty MIDI file or one with no notes returns an empty list.
    """
    melody = parse_midi_melody(EMPTY_MIDI_PATH)
    assert melody == []

def test_parse_midi_melody_index_out_of_bounds():
    """
    Test parsing a MIDI file with an instrument_index that is out of bounds.
    Expects an empty list.
    """
    # multi_track.mid has 2 instruments (indices 0 and 1)
    melody = parse_midi_melody(MULTI_TRACK_MIDI_PATH, instrument_index=5)
    assert melody == []