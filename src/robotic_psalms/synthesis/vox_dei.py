import logging
from typing import Optional, cast # Removed Protocol

import numpy as np
import numpy.typing as npt
# soundfile and Path moved into debug blocks later
# soundfile is used implicitly by EspeakNGWrapper, but not directly here.
from scipy import signal

from ..config import PsalmConfig, VocalTimbre
# Corrected imports for TTS engines and base class
from .tts.base import TTSEngine, ParameterEnum
from .effects import FormantShiftParameters, apply_robust_formant_shift, ResonantFilterParameters, BandpassFilterParameters, apply_rbj_lowpass_filter, apply_bandpass_filter
from .tts.engines.espeak import EspeakNGWrapper


# Constant for minimum length required by sosfiltfilt in this context
_MIN_SOSFILTFILT_LEN = 15


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


    def synthesize_text(self, text: str) -> tuple[npt.NDArray[np.float32], int]:
        """Synthesize text using TTS engine and return audio data and sample rate"""
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
            audio: npt.NDArray[np.float32] = audio_data
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

            return audio, synth_sample_rate

        except Exception as e:
            # Log the full traceback for better debugging
            self.logger.exception(f"TTS synthesis failed: {e}")
            raise VoxDeiSynthesisError(f"TTS synthesis failed: {str(e)}") from e

    def _apply_formant_shift(self, audio: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
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
            return shifted_audio.astype(np.float32)
        except Exception as e:
            self.logger.error(f"Robust formant shifting failed: {e}", exc_info=True)
            # Return original audio on error to avoid breaking the chain
            return audio

