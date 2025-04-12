import os
import logging
from typing import List, Tuple

import pretty_midi
import librosa
import numpy as np # librosa.midi_to_hz returns numpy float

# Configure logging
logger = logging.getLogger(__name__)

class MidiParsingError(ValueError):
    """Custom exception for errors encountered during MIDI parsing."""
    pass

def parse_midi_melody(midi_path: str, instrument_index: int = 0) -> List[Tuple[float, float]]:
    """
    Parses a MIDI file to extract a melody contour from a specific instrument/track.

    Args:
        midi_path: Path to the MIDI file.
        instrument_index: The index of the instrument (track) to parse (default: 0).

    Returns:
        A list of (pitch_hz, duration_seconds) tuples representing the melody.
        Returns an empty list if the MIDI file contains no instruments, the specified
        instrument index is out of bounds, or the selected instrument track contains no valid notes.

    Raises:
        FileNotFoundError: If the midi_path does not exist.
        MidiParsingError: If the MIDI file is invalid or cannot be parsed.
    """
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found at path: {midi_path}")

    melody: List[Tuple[float, float]] = []
    try:
        midi_data = pretty_midi.PrettyMIDI(midi_path)

        if not midi_data.instruments:
            logger.warning(f"No instruments found in MIDI file: {midi_path}")
            return []

        if instrument_index >= len(midi_data.instruments):
            logger.warning(f"Instrument index {instrument_index} out of bounds for MIDI file: {midi_path} (found {len(midi_data.instruments)} instruments)")
            return []

        instrument = midi_data.instruments[instrument_index]

        if not instrument.notes:
            logger.warning(f"No notes found in instrument {instrument_index} ('{instrument.name}') of MIDI file: {midi_path}")
            return []

        # Sort notes by start time just in case
        instrument.notes.sort(key=lambda note: note.start)

        for note in instrument.notes:
            if note.pitch <= 0: # Skip invalid pitches
                logger.debug(f"Skipping note with invalid pitch {note.pitch} at time {note.start}")
                continue

            duration_sec = note.end - note.start
            if duration_sec <= 0: # Skip zero or negative duration notes
                 logger.debug(f"Skipping note with non-positive duration {duration_sec} at time {note.start}")
                 continue

            # Convert MIDI pitch to Hz. librosa returns np.float64, cast to float.
            pitch_hz = float(librosa.midi_to_hz(note.pitch))

            melody.append((pitch_hz, duration_sec))

    except Exception as e:
        logger.error(f"Failed to parse MIDI file '{midi_path}': {e}", exc_info=True)
        raise MidiParsingError(f"Error parsing MIDI file '{midi_path}': {e}") from e

    if not melody:
         logger.warning(f"Successfully parsed MIDI file '{midi_path}' but extracted no valid notes from instrument {instrument_index}.")

    return melody