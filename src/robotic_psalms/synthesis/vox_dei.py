import logging
from typing import Optional, cast, List, Tuple # Removed Protocol

import numpy as np
import numpy.typing as npt
import librosa # Moved import to top level
# soundfile and Path moved into debug blocks later
# soundfile is used implicitly by EspeakNGWrapper, but not directly here.
from scipy import signal

from ..config import PsalmConfig, VocalTimbre
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
_MIN_SEMITONE_SHIFT = 1e-3 # Minimum semitone shift to apply (avoids tiny shifts)


class VoxDeiSynthesisError(Exception):
    """Raised when vocal synthesis fails"""
    pass


class VoxDeiSynthesizer:
    """Core vocal synthesis engine combining TTS and sample processing"""

    # Explicitly type internal buffers and the espeak engine instance
    _tts_buffer: Optional[npt.NDArray[np.float32]]
    _formant_buffer: Optional[npt.NDArray[np.float32]]
    espeak: Optional[TTSEngine]
    formant_shift_factor: float # Added type hint

    def __init__(self, config: PsalmConfig, sample_rate: int = 48000):
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
        """Synthesize text using TTS engine, optionally applying melody contour, and return audio data and sample rate.

        Args:
            text (str): The text to synthesize.
            midi_path (Optional[str]): An optional path to a MIDI file containing a melody.
                If provided, the synthesizer will parse the MIDI using
                `robotic_psalms.utils.midi_parser.parse_midi_melody` and apply the
                resulting melodic contour (List[Tuple[float, float]]) to the synthesized speech.
                Defaults to None (no MIDI contour applied).

        Returns:
            tuple[npt.NDArray[np.float32], int]: A tuple containing the synthesized audio
                data as a NumPy array and the sample rate.

        Raises:
            VoxDeiSynthesisError: If the TTS engine is unavailable or synthesis fails.
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
            parsed_melody: Optional[List[Tuple[float, float]]] = None
            if midi_path:
                self.logger.info(f"MIDI path provided: {midi_path}. Attempting to parse melody.")
                try:
                    # Assuming default instrument index 0 for now
                    parsed_melody = parse_midi_melody(midi_path, instrument_index=0)
                    if not parsed_melody:
                         self.logger.warning(f"MIDI parsing resulted in an empty melody for path: {midi_path}")
                except FileNotFoundError:
                    self.logger.error(f"MIDI file not found at path: {midi_path}. Skipping contour application.")
                except MidiParsingError as e:
                    self.logger.error(f"Failed to parse MIDI file '{midi_path}': {e}. Skipping contour application.")
                except Exception as e: # Catch any other unexpected errors during parsing
                    self.logger.exception(f"Unexpected error parsing MIDI file '{midi_path}': {e}. Skipping contour application.")

            # Check if parsing was successful and yielded notes before applying contour
            if parsed_melody:
                self.logger.debug(f"Applying melody contour from parsed MIDI ({len(parsed_melody)} notes)...")
                try:
                    audio = self._apply_melody_contour(audio, synth_sample_rate, parsed_melody)
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


