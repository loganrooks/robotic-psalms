import logging
import typing  # Add typing import
from typing import Optional, cast, List, Tuple, TypedDict, ClassVar # Added ClassVar

import numpy as np
import numpy.typing as npt
import librosa
import librosa.effects
import pyfoal
# Removed incorrect 'from pyfoal import Word'
# soundfile and Path moved into debug blocks later
# soundfile is used implicitly by EspeakNGWrapper, but not directly here.
from scipy import signal

# Removed top-level config import causing circular dependency

# Type hint import to avoid circular dependency at runtime
if typing.TYPE_CHECKING:
    from ..config import PsalmConfig
# Corrected imports for TTS engines and base class
from .tts.base import TTSEngine, ParameterEnum
from .effects import (
    FormantShiftParameters, apply_robust_formant_shift,
    ResonantFilterParameters, BandpassFilterParameters,
    apply_rbj_lowpass_filter, apply_bandpass_filter
)
# Import the MIDI parser function and error
from ..utils.midi_parser import parse_midi_melody, MidiParsingError
from .tts.engines.espeak import EspeakNGWrapper


# Constants
_MIN_SOSFILTFILT_LEN = 15 # Minimum length required by sosfiltfilt
_MIN_PYIN_DURATION_SEC = 0.1 # Minimum duration for reliable pyin pitch estimation
_MIN_SEMITONE_SHIFT = 1e-3  # Minimum semitone shift to apply (avoids tiny shifts)
# _STRETCH_RATE_THRESHOLD moved inside the class

# --- Type Definitions ---
class AlignedWord(TypedDict):
    """Structure representing a word from pyfoal alignment."""
    start: float
    end: float
    text: str
    # confidence: Optional[float] # Add other fields if known/needed

class VoxDeiSynthesisError(Exception):
    """Raised when vocal synthesis fails"""
    pass


class VoxDeiSynthesizer:
    """Core vocal synthesis engine combining TTS and sample processing"""

    # --- Constants ---
    _STRETCH_RATE_THRESHOLD: ClassVar[float] = 0.01 # Threshold for applying time stretch

    # Explicitly type internal buffers and the espeak engine instance
    _tts_buffer: Optional[npt.NDArray[np.float32]]
    _formant_buffer: Optional[npt.NDArray[np.float32]]
    espeak: Optional[TTSEngine]
    formant_shift_factor: float # Added type hint

    def __init__(self, config: "PsalmConfig", sample_rate: int = 48000): # Use string literal for type hint
        from ..config import PsalmConfig # Import locally for runtime use
        """Initialize the vocal synthesizer

        Args:
            config: Main configuration object
            sample_rate: Audio sample rate (default 48kHz)
        """
        self.config = config
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)

        # Initialize internal buffers
        self._tts_buffer = None
        self._formant_buffer = None

        # Initialize TTS engine - explicitly None initially
        self.espeak = None
        self.formant_shift_factor = 1.0 # Default value

        # Try espeak-ng first
        try:
            espeak_ng_engine = EspeakNGWrapper()
            # Ensure the instance conforms to the protocol
            if isinstance(espeak_ng_engine, TTSEngine):
                self.espeak = espeak_ng_engine
            else:
                 # This path shouldn't be hit if EspeakNGWrapper implements TTSEngine
                 raise VoxDeiSynthesisError("EspeakNGWrapper does not conform to TTSEngine")
        except Exception as e:
            # Log the error if EspeakNGWrapper fails
            self.logger.error(f"eSpeak-NG initialization failed: {e}")
            self.espeak = None # Ensure it remains None if initialization fails

        if self.espeak:
            # Configure TTS engine based on settings
            # Use cast to inform type checker that self.espeak is not None here
            espeak_instance = cast(TTSEngine, self.espeak)
            espeak_instance.set_parameter(ParameterEnum.RATE,
                                    int(150 * self.config.tempo_scale))
            espeak_instance.set_parameter(ParameterEnum.PITCH,
                                    int(50 + self.config.vocal_timbre.choirboy * 30))

            # Apply articulation settings
            phoneme_rate = int(200 * self.config.robotic_articulation.phoneme_spacing)
            espeak_instance.set_parameter(ParameterEnum.VOLUME,
                                    int(100 * self.config.robotic_articulation.consonant_harshness)) # Corrected default volume
            espeak_instance.set_parameter(ParameterEnum.RATE, phoneme_rate)

            # Configure voice range
            base_freqs = {
                "C2": 65.41, "G2": 98.00,  # Bass
                "A2": 110.00, "D3": 146.83,  # Baritone
                "C3": 130.81, "G3": 196.00,  # Tenor
                "E3": 164.81, "C4": 261.63   # Counter-tenor
            }

            # Get base frequency or default to C3
            base_freq = base_freqs.get(self.config.voice_range.base_pitch, 130.81)

            # Set pitch based on voice range with proper scaling
            pitch_value = int(50 * (base_freq / 130.81)) # Assuming 50 is the baseline pitch for C3
            self.logger.debug(f"Setting base pitch to {pitch_value}")
            espeak_instance.set_parameter(ParameterEnum.PITCH, pitch_value)

            # Apply formant shifting for voice character
            self.formant_shift_factor = self.config.voice_range.formant_shift
        else:
             self.logger.error("No functional eSpeak engine could be initialized.")
             # Consider raising an error here if TTS is essential


    def synthesize_text(self, text: str, midi_path: Optional[str] = None) -> tuple[npt.NDArray[np.float32], int]: # Reverted type hint
        """Synthesize text using TTS, optionally apply duration/melody, return audio.

        Uses the configured TTS engine (eSpeak-NG) to synthesize the input text.
        If `midi_path` is provided, it attempts to:
        1. Parse the MIDI file for note durations and pitches.
        2. Apply duration control: Aligns the synthesized audio to the text using
           `pyfoal`, maps aligned words to MIDI durations, and time-stretches
           segments using `librosa.effects.time_stretch` via the
           `_apply_duration_control` method.
        3. Apply melodic contour: Estimates the original pitch of audio segments
           and shifts them to match the MIDI pitches using `librosa.effects.pitch_shift`
           via the `_apply_melody_contour` method.
        Finally, applies configured formant shifting and atmospheric filters.

        Args:
            text (str): The text to synthesize.
            midi_path (Optional[str]): Path to a MIDI file. If provided, enables
                duration control and melodic contour application based on the
                first instrument track's notes. Defaults to None.

        Returns:
            tuple[npt.NDArray[np.float32], int]: Synthesized audio data and sample rate.

        Raises:
            VoxDeiSynthesisError: If the TTS engine is unavailable or synthesis fails.
            FileNotFoundError: If the provided `midi_path` does not exist.
            MidiParsingError: If the MIDI file cannot be parsed correctly.
        """
        if not self.espeak:
            raise VoxDeiSynthesisError("No TTS engine available for synthesis")

        # Use cast to assure type checker self.espeak is not None
        espeak_instance = cast(TTSEngine, self.espeak)

        try:
            # Update parameters before synthesis
            espeak_instance.set_parameter(ParameterEnum.RATE,
                                    int(150 * self.config.tempo_scale))
            espeak_instance.set_parameter(ParameterEnum.VOLUME,
                                    int(100 * self.config.robotic_articulation.consonant_harshness))

            self.logger.debug("Synthesizing text with eSpeak...")
            # Call synth and unpack the audio data and sample rate
            audio_data, synth_sample_rate = espeak_instance.synth(text)
            # Rename audio_data to audio for consistency with the rest of the function
            audio: npt.NDArray[np.float32] = audio_data # Reverted type hint
            # --- DEBUG: Save raw TTS output ---
            if self.logger.isEnabledFor(logging.DEBUG):
                import soundfile as sf # Import moved here
                from pathlib import Path # Import moved here
                try:
                    raw_output_path = Path("debug_vocals_01_raw_tts.wav") # Numbered filename
                    sf.write(raw_output_path, audio, synth_sample_rate)
                    self.logger.debug(f"Saved raw TTS output to {raw_output_path}")
                except Exception as write_err:
                    self.logger.error(f"Failed to save raw TTS output: {write_err}")
            # --- END DEBUG ---
            if audio.size == 0: # Check size instead of len for numpy arrays
                raise VoxDeiSynthesisError("TTS returned empty audio data")

            self.logger.debug(f"Pre-processing max amplitude: {np.max(np.abs(audio))}")

            # --- Parse MIDI once if path is provided ---
            parsed_melody_data: Optional[List[Tuple[float, float]]] = None
            if midi_path:
                self.logger.info(f"MIDI path provided: {midi_path}. Attempting to parse melody.")
                try:
                    # Assuming default instrument index 0 for now
                    parsed_melody_data = parse_midi_melody(midi_path, instrument_index=0)
                    if not parsed_melody_data:
                         self.logger.warning(f"MIDI parsing resulted in an empty melody for path: {midi_path}")
                except FileNotFoundError:
                    self.logger.error(f"MIDI file not found at path: {midi_path}.")
                    parsed_melody_data = None # Ensure it's None on error
                except MidiParsingError as e:
                    self.logger.error(f"Failed to parse MIDI file '{midi_path}': {e}.")
                    parsed_melody_data = None # Ensure it's None on error
                except Exception as e: # Catch any other unexpected errors during parsing
                    self.logger.exception(f"Unexpected error parsing MIDI file '{midi_path}': {e}.")
                    parsed_melody_data = None # Ensure it's None on error
            # --- End MIDI Parsing ---

            # --- Apply Duration Control from MIDI ---
            # Use the pre-parsed MIDI data
            if parsed_melody_data:
                target_durations_sec = [duration for _, duration in parsed_melody_data]
                self.logger.debug(f"Applying duration control based on parsed MIDI ({len(target_durations_sec)} target durations)...")
                try:
                    audio = self._apply_duration_control(audio, synth_sample_rate, text, target_durations_sec)
                    # --- DEBUG: Save audio after duration control ---
                    if self.logger.isEnabledFor(logging.DEBUG):
                        import soundfile as sf
                        from pathlib import Path
                        try:
                            duration_path = Path("debug_vocals_01b_after_duration_control.wav")
                            sf.write(duration_path, audio, synth_sample_rate)
                            self.logger.debug(f"Saved audio after duration control to {duration_path}")
                        except Exception as write_err:
                            self.logger.error(f"Failed to save audio after duration control: {write_err}")
                    # --- END DEBUG ---
                except Exception as duration_err:
                     self.logger.exception(f"Error applying duration control: {duration_err}. Proceeding without duration control.")
            else:
                self.logger.debug("No valid MIDI melody provided or parsed for duration control, skipping.")
            # --- End Duration Control ---


            # Apply formant shift and timbre blend
            audio = self._apply_formant_shift(audio)
            # --- DEBUG: Save audio after formant shift ---
            if self.logger.isEnabledFor(logging.DEBUG):
                import soundfile as sf # Import moved here
                from pathlib import Path # Import moved here
                try:
                    formant_shift_path = Path("debug_vocals_02_after_formant_shift.wav")
                    sf.write(formant_shift_path, audio, synth_sample_rate)
                    self.logger.debug(f"Saved audio after formant shift to {formant_shift_path}")
                except Exception as write_err:
                    self.logger.error(f"Failed to save audio after formant shift: {write_err}")
            # --- END DEBUG ---
            # Apply atmospheric filters based on config (Bandpass takes precedence)
            if self.config.bandpass_filter_params:
                self.logger.debug("Applying bandpass filter...")
                audio = apply_bandpass_filter(audio, self.sample_rate, params=self.config.bandpass_filter_params)
            elif self.config.resonant_filter_params:
                self.logger.debug("Applying resonant low-pass filter...")
                audio = apply_rbj_lowpass_filter(audio, self.sample_rate, params=self.config.resonant_filter_params)
            else:
                self.logger.debug("No atmospheric filter configured.")

            # --- DEBUG: Save audio after atmospheric filter ---
            if self.logger.isEnabledFor(logging.DEBUG):
                import soundfile as sf
                from pathlib import Path
                try:
                    filter_path = Path("debug_vocals_03_after_filter.wav")
                    sf.write(filter_path, audio, synth_sample_rate)
                    self.logger.debug(f"Saved audio after atmospheric filter to {filter_path}")
                except Exception as write_err:
                    self.logger.error(f"Failed to save audio after atmospheric filter: {write_err}")
            # --- END DEBUG ---

            # Boost vocal output - ensure float32
            audio = np.tanh(audio * 2.0).astype(np.float32)

            self.logger.debug(f"Post-processing max amplitude: {np.max(np.abs(audio))}")

            # --- Apply Melody Contour from MIDI ---
            # Use the pre-parsed MIDI data
            if parsed_melody_data:
                self.logger.debug(f"Applying melody contour from parsed MIDI ({len(parsed_melody_data)} notes)...")
                try:
                    audio = self._apply_melody_contour(audio, synth_sample_rate, parsed_melody_data)
                    # --- DEBUG: Save audio after melody contour ---
                    if self.logger.isEnabledFor(logging.DEBUG):
                        import soundfile as sf
                        from pathlib import Path
                        try:
                            contour_path = Path("debug_vocals_04_after_contour.wav")
                            sf.write(contour_path, audio, synth_sample_rate)
                            self.logger.debug(f"Saved audio after melody contour to {contour_path}")
                        except Exception as write_err:
                            self.logger.error(f"Failed to save audio after melody contour: {write_err}")
                    # --- END DEBUG ---
                except Exception as contour_err:
                     self.logger.exception(f"Error applying melody contour: {contour_err}. Proceeding without contour.")
            else:
                self.logger.debug("No valid MIDI melody provided or parsed, skipping contour application.")
            # --- End Melody Contour ---

            return audio, synth_sample_rate

        except Exception as e:
            # Log the full traceback for better debugging
            self.logger.exception(f"TTS synthesis failed: {e}")
            raise VoxDeiSynthesisError(f"TTS synthesis failed: {str(e)}") from e

    def _apply_formant_shift(self, audio: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]: # Reverted type hint
        """Apply robust formant shifting using the dedicated effects function."""
        if abs(self.formant_shift_factor - 1.0) < 1e-6:
            # Skip shifting if factor is effectively 1.0
            return audio

        self.logger.debug(f"Applying robust formant shift with factor: {self.formant_shift_factor}")
        params = FormantShiftParameters(shift_factor=self.formant_shift_factor)
        try:
            # Pass sample_rate explicitly
            shifted_audio = apply_robust_formant_shift(audio, self.sample_rate, params=params)
            # Ensure output is float32
            return shifted_audio.astype(np.float32) # Ensure float32 output
        except Exception as e:
            self.logger.error(f"Robust formant shifting failed: {e}", exc_info=True)
            # Return original audio on error to avoid breaking the chain
            return audio.astype(np.float32) # Ensure float32 output on error

    def _apply_melody_contour(self, audio: npt.NDArray[np.float32], sample_rate: int, melody: List[Tuple[float, float]]) -> npt.NDArray[np.float32]: # Reverted type hint
        """Apply a target melodic contour to the synthesized audio using pitch shifting.

        This method iterates through the provided `melody` (a list of pitch/duration tuples).
        For each target segment in the melody:
        1. It extracts the corresponding segment from the input `audio`.
        2. It estimates the original fundamental frequency (F0) of the audio segment using
           `librosa.pyin`. Handles segments too short for reliable estimation.
        3. It calculates the required pitch shift in semitones to match the target pitch.
        4. It applies the pitch shift using `librosa.effects.pitch_shift`.
        5. Segments are concatenated, and the final audio is adjusted to match the original length.

        Args:
            audio (npt.NDArray[np.float32]): The input audio waveform.
            sample_rate (int): The sample rate of the audio.
            melody (List[Tuple[float, float]]): The target melodic contour, where each
                tuple is (pitch_in_hz, duration_in_seconds).

        Returns:
            npt.NDArray[np.float32]: The audio waveform with the melodic contour applied.
                Returns the original audio if errors occur during processing.
        """
        # librosa import moved to top

        self.logger.debug(f"Applying melody contour with {len(melody)} segments to audio of length {len(audio)}.")
        processed_segments = []
        current_sample = 0
        total_samples = len(audio) # Original audio length

        for i, (target_pitch_hz, duration_sec) in enumerate(melody):
            start_sample = current_sample # Start sample index for this segment
            # Calculate end sample, ensuring it doesn't exceed total audio length
            end_sample = min(start_sample + int(duration_sec * sample_rate), total_samples)
            segment_len_samples = end_sample - start_sample # Actual length of this segment

            # Skip processing if segment length is zero or negative
            if segment_len_samples <= 0:
                self.logger.warning(f"Skipping zero/negative length melody segment {i+1}/{len(melody)}.")
                continue

            segment = audio[start_sample:end_sample]

            # --- Pitch Estimation ---
            # Estimate original pitch of the segment using pyin.
            # pyin requires a minimum duration; handle short segments gracefully.
            min_pyin_duration_samples = int(_MIN_PYIN_DURATION_SEC * sample_rate)
            original_pitch_hz = target_pitch_hz # Default/fallback if estimation fails or segment is too short
            semitone_shift = 0.0 # Default shift if estimation fails or target==original

            if segment_len_samples < min_pyin_duration_samples:
                self.logger.warning(f"Segment {i+1}/{len(melody)} too short ({segment_len_samples / sample_rate:.3f}s < {_MIN_PYIN_DURATION_SEC}s) for pyin pitch estimation, skipping shift.")
                # Keep default original_pitch_hz = target_pitch_hz and semitone_shift = 0.0
            else:
                # Attempt pyin pitch estimation
                try:
                    f0, voiced_flag, voiced_probs = librosa.pyin(segment.astype(np.float32), # Ensure float32 for pyin
                                                                 fmin=float(librosa.note_to_hz('C2')),
                                                                 fmax=float(librosa.note_to_hz('C7')),
                                                                 sr=sample_rate,
                                                                 frame_length=2048, # Default, adjust if needed
                                                                 hop_length=512) # Default, adjust if needed
                    # Calculate average pitch of voiced frames, ignoring NaNs
                    voiced_f0 = f0[voiced_flag]
                    if np.any(voiced_flag) and not np.all(np.isnan(voiced_f0)):
                        original_pitch_hz = np.nanmean(voiced_f0)
                    else:
                        self.logger.warning(f"Segment {i+1}/{len(melody)}: No voiced frames detected or all NaNs in pyin output, using target pitch ({target_pitch_hz:.2f} Hz) as original.")
                        # Keep default original_pitch_hz = target_pitch_hz
                except Exception as pyin_err:
                    self.logger.error(f"Error during pyin pitch estimation for segment {i+1}/{len(melody)}: {pyin_err}. Skipping shift.")
                    # Keep default original_pitch_hz = target_pitch_hz and semitone_shift = 0.0

            # --- Pitch Shift Calculation ---
            # Calculate pitch shift in semitones, handling potential invalid pitch values.
            if original_pitch_hz > 0 and target_pitch_hz > 0:
                # Avoid log2(0) or division by zero if pitches are valid
                try:
                    semitone_shift = 12 * np.log2(target_pitch_hz / original_pitch_hz)
                except (ValueError, ZeroDivisionError) as calc_err:
                    self.logger.warning(f"Segment {i+1}/{len(melody)}: Error calculating semitone shift ({calc_err}). Original: {original_pitch_hz:.2f}, Target: {target_pitch_hz:.2f}. Skipping shift.")
                    semitone_shift = 0.0
            else:
                # Log warning if either pitch is invalid (<= 0) and ensure no shift happens
                self.logger.warning(f"Segment {i+1}/{len(melody)}: Invalid original ({original_pitch_hz:.2f} Hz) or target ({target_pitch_hz:.2f} Hz) pitch, skipping shift.")
                semitone_shift = 0.0

            # --- Pitch Shift Application ---
            # Apply pitch shift using librosa if the shift is significant.
            if abs(semitone_shift) > _MIN_SEMITONE_SHIFT:
                try:
                    self.logger.debug(f"Segment {i+1}/{len(melody)}: Original ~{original_pitch_hz:.2f} Hz, Target {target_pitch_hz:.2f} Hz -> Shifting {semitone_shift:.2f} semitones.")
                    # Ensure input to pitch_shift is float32
                    segment_float32 = segment.astype(np.float32)
                    shifted_segment = librosa.effects.pitch_shift(y=segment_float32,
                                                                  sr=sample_rate,
                                                                  n_steps=semitone_shift)
                    processed_segments.append(shifted_segment)
                except Exception as e:
                    self.logger.error(f"Error pitch shifting segment {i+1}/{len(melody)}: {e}. Using original segment.", exc_info=True)
                    processed_segments.append(segment.astype(np.float32)) # Append original on error, ensure float32
            else:
                self.logger.debug(f"Segment {i+1}/{len(melody)}: No significant pitch shift needed ({semitone_shift:.2f} semitones).")
                processed_segments.append(segment.astype(np.float32)) # Append original if no shift needed, ensure float32

            current_sample = end_sample # Move to the start of the next segment
            # Exit loop if we've processed the entire audio array
            if current_sample >= total_samples:
                break # Correctly indented break statement

        # --- Final Concatenation & Length Adjustment ---
        # Handle any remaining audio if the melody duration was shorter than the audio.
        if current_sample < total_samples:
            remaining_samples = total_samples - current_sample
            self.logger.debug(f"Melody duration shorter than audio. Appending remaining {remaining_samples} samples ({remaining_samples/sample_rate:.3f}s) unchanged.")
            processed_segments.append(audio[current_sample:].astype(np.float32)) # Ensure float32

        # Concatenate processed segments.
        if not processed_segments:
             # This should ideally not happen if input audio is non-empty, but handle defensively.
             self.logger.warning("No segments were processed or collected for melody contour. Returning original audio.")
             return audio.astype(np.float32) # Ensure float32 return

        try:
            final_audio = np.concatenate(processed_segments)
        except ValueError as concat_err:
             self.logger.error(f"Error concatenating processed segments: {concat_err}. Returning original audio.", exc_info=True)
             return audio.astype(np.float32) # Ensure float32 return

        # Ensure final audio length matches original, as pitch shifting might cause minor length changes.
        if len(final_audio) != total_samples:
             self.logger.warning(f"Melody processed audio length ({len(final_audio)}) differs from original ({total_samples}). Adjusting length by padding/truncating.")
             if len(final_audio) > total_samples:
                 # Truncate if too long
                 final_audio = final_audio[:total_samples]
             else:
                 # Pad with zeros if too short
                 padding = np.zeros(total_samples - len(final_audio), dtype=np.float32)
                 final_audio = np.concatenate([final_audio, padding])

        return final_audio.astype(np.float32) # Ensure float32 return



    def _perform_alignment(self, audio: npt.NDArray[np.float32], sample_rate: int, text: str) -> Optional[List[AlignedWord]]:
        """Performs forced alignment using pyfoal.

        Uses the `pyfoal.align` function to generate word-level timestamps for
        the input audio and text.

        Args:
            audio (npt.NDArray[np.float32]): The input audio waveform.
            sample_rate (int): The sample rate of the audio.
            text (str): The text corresponding to the audio.

        Returns:
            Optional[List[AlignedWord]]: A list of aligned word objects, each
                containing 'start', 'end', and 'text', or None if alignment fails
                or returns no words.

        Raises:
            Exception: Can propagate exceptions from `pyfoal.align`.
        """
        try:
            self.logger.debug("Performing forced alignment with pyfoal...")
            # Assuming pyfoal.align returns an object with a .words attribute
            # which is a list of objects matching the AlignedWord structure.
            alignment_result = pyfoal.align(audio, sample_rate, text)

            if not alignment_result:
                self.logger.warning("pyfoal alignment returned no result. Skipping duration control.")
                return None

            # Access the .words attribute/method and cast to the expected type
            try:
                # Try accessing as a method first, then attribute, and cast
                words_data = alignment_result.words
                if callable(words_data):
                    words_data = words_data() # Call if it's a function

                aligned_words_list = cast(List[AlignedWord], words_data)
                if not aligned_words_list:
                    self.logger.warning("pyfoal alignment result's .words is empty or cast failed. Skipping duration control.")
                    return None
                self.logger.debug(f"Alignment successful, found {len(aligned_words_list)} words.")
                return aligned_words_list
            except AttributeError:
                self.logger.error("pyfoal alignment result does not have a '.words' attribute. Skipping duration control.", exc_info=True)
                return None
            except Exception as e: # Catch other potential errors accessing words
                self.logger.error(f"Error accessing words from pyfoal alignment result: {e}. Skipping duration control.", exc_info=True)
                return None

        except Exception as align_err:
            self.logger.error(f"pyfoal alignment failed: {align_err}. Skipping duration control.", exc_info=True)
            return None

    def _stretch_segment_if_needed(
        self,
        audio_segment: npt.NDArray[np.float32],
        sample_rate: int,
        original_duration: float,
        target_duration: float,
        word_text: str, # For logging - text already extracted by caller
        segment_index: int, # For logging
        total_segments: int # For logging
    ) -> npt.NDArray[np.float32]:
        """Stretches an audio segment if its duration differs significantly from target.

        Calculates the required time stretch rate (`original_duration / target_duration`).
        If the absolute difference between the rate and 1.0 exceeds a threshold
        (`_STRETCH_RATE_THRESHOLD`), it applies time stretching using
        `librosa.effects.time_stretch`.

        Args:
            audio_segment (npt.NDArray[np.float32]): The audio segment to process.
            sample_rate (int): The sample rate of the audio.
            original_duration (float): The original duration of the segment in seconds.
            target_duration (float): The desired target duration in seconds.
            word_text (str): The text of the word (for logging).
            segment_index (int): The index of the segment (for logging).
            total_segments (int): The total number of segments (for logging).

        Returns:
            npt.NDArray[np.float32]: The stretched audio segment, or the original
                segment if stretching is not needed or fails. Returns float32 type.

        Notes:
            Time stretching can introduce audio artifacts, especially with large
            stretch rates. Handles invalid (<=0) durations by returning the original segment.
        """
        # Validate durations
        if original_duration <= 0 or target_duration <= 0:
            self.logger.warning(f"Word '{word_text}' ({segment_index+1}/{total_segments}): Invalid original ({original_duration:.3f}s) or target ({target_duration:.3f}s) duration. Using original segment.")
            return audio_segment.astype(np.float32)

        # Calculate stretch rate
        stretch_rate = original_duration / target_duration
        self.logger.debug(f"Word '{word_text}' ({segment_index+1}/{total_segments}): Orig Dur={original_duration:.3f}s, Target Dur={target_duration:.3f}s, Rate={stretch_rate:.3f}")

        # Apply time stretching if rate is significantly different from 1.0
        if abs(stretch_rate - 1.0) > self._STRETCH_RATE_THRESHOLD:
            try:
                # librosa time_stretch expects float32
                stretched_segment = librosa.effects.time_stretch(y=audio_segment.astype(np.float32),
                                                                 rate=stretch_rate)
                return stretched_segment
            except Exception as stretch_err:
                self.logger.error(f"Error time stretching word '{word_text}' ({segment_index+1}/{total_segments}): {stretch_err}. Using original segment.", exc_info=True)
                return audio_segment.astype(np.float32)
        else:
            # Use original segment if stretch rate is close to 1.0
            return audio_segment.astype(np.float32)

    def _apply_duration_control(self, audio: npt.NDArray[np.float32], sample_rate: int, text: str, target_durations_sec: Optional[List[float]]) -> npt.NDArray[np.float32]:
        """Applies duration control based on target durations using alignment and stretching.

        This method orchestrates the duration control process:
        1. Performs forced alignment using `_perform_alignment` (`pyfoal`) to get
           word boundaries for the input audio and text.
        2. Maps the aligned words to the provided `target_durations_sec` list
           (typically from MIDI). Handles mismatches by processing up to the
           minimum length of the two lists.
        3. Iterates through aligned words:
           - Preserves silence gaps between words.
           - Extracts the audio segment for the word.
           - Calls `_stretch_segment_if_needed` to apply time stretching
             (`librosa.effects.time_stretch`) if the original duration differs
             significantly from the target duration.
        4. Concatenates the processed (potentially stretched) segments and silence gaps.

        Args:
            audio (npt.NDArray[np.float32]): The input audio waveform.
            sample_rate (int): The sample rate of the audio.
            text (str): The original text corresponding to the audio.
            target_durations_sec (Optional[List[float]]): A list of target durations
                in seconds. If None or empty, the original audio is returned.

        Returns:
            npt.NDArray[np.float32]: The audio waveform with duration control applied,
                or the original audio if alignment/stretching fails, is skipped,
                or no target durations are provided. Returns float32 type.

        Dependencies:
            - `pyfoal`: For forced alignment (`_perform_alignment`).
            - `librosa`: For time stretching (`_stretch_segment_if_needed`).

        Potential Issues:
            - Alignment failure (`_perform_alignment` returns None).
            - Mismatch between number of aligned words and target durations.
            - Errors during time stretching (`_stretch_segment_if_needed`).
            - Audio artifacts introduced by time stretching.
        """
        if not target_durations_sec:
            self.logger.debug("No target durations provided for duration control, skipping.")
            return audio.copy().astype(np.float32)

        self.logger.info("Applying duration control...")

        # 1. Forced Alignment (using helper)
        aligned_words_list = self._perform_alignment(audio, sample_rate, text)
        if aligned_words_list is None:
            return audio.copy().astype(np.float32) # Return original if alignment failed

        # 2. Map Segments to Durations
        num_words = len(aligned_words_list)
        num_targets = len(target_durations_sec)
        if num_words != num_targets:
            self.logger.warning(f"Mismatch between aligned words ({num_words}) and target durations ({num_targets}). Mapping 1:1 up to the shorter length.")
            min_len = min(num_words, num_targets)
            aligned_words_list = aligned_words_list[:min_len]
            target_durations_sec = target_durations_sec[:min_len]
            num_words = min_len # Update count for iteration

        # 3. Time Stretching
        stretched_pieces = []
        last_word_end_sample = 0

        for i, word_obj in enumerate(aligned_words_list): # Rename loop variable
            # Cast to Any to satisfy Pylance while using attribute access for mocks
            word = cast(typing.Any, word_obj)
            target_duration = target_durations_sec[i]
            # Use attribute access for compatibility with test mocks
            start_sample = int(word.start * sample_rate)
            end_sample = int(word.end * sample_rate)
            word_text = getattr(word, 'text', 'UNKNOWN') # Use getattr for mocks

            # Handle silence/gap before the current word
            if start_sample > last_word_end_sample:
                silence_segment = audio[last_word_end_sample:start_sample]
                stretched_pieces.append(silence_segment.astype(np.float32))
                self.logger.debug(f"Preserving silence segment from {last_word_end_sample/sample_rate:.3f}s to {start_sample/sample_rate:.3f}s")

            # Extract and stretch the word segment using the helper
            audio_segment = audio[start_sample:end_sample]
            original_duration = (end_sample - start_sample) / sample_rate

            # Pass word_text obtained via getattr
            stretched_segment = self._stretch_segment_if_needed(
                audio_segment, sample_rate, original_duration, target_duration,
                word_text, i, num_words
            )
            stretched_pieces.append(stretched_segment)

            last_word_end_sample = end_sample

        # Handle potential silence after the last word
        if last_word_end_sample < len(audio):
            final_silence = audio[last_word_end_sample:]
            stretched_pieces.append(final_silence.astype(np.float32))
            self.logger.debug(f"Preserving final silence segment from {last_word_end_sample/sample_rate:.3f}s onwards")

        # 4. Concatenate
        if not stretched_pieces:
            self.logger.warning("No segments were processed or collected during duration control. Returning original audio.")
            return audio.copy().astype(np.float32)

        try:
            final_audio = np.concatenate(stretched_pieces)
            self.logger.info("Duration control applied successfully.")
            return final_audio.astype(np.float32)
        except ValueError as concat_err:
            self.logger.error(f"Error concatenating duration-controlled segments: {concat_err}. Returning original audio.", exc_info=True)
            return audio.copy().astype(np.float32)

