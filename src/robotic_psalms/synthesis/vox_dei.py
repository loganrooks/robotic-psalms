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
from .effects import FormantShiftParameters, apply_robust_formant_shift
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
            audio = self._apply_timbre_blend(audio)
            # --- DEBUG: Save audio after timbre blend ---
            if self.logger.isEnabledFor(logging.DEBUG):
                import soundfile as sf # Import moved here
                from pathlib import Path # Import moved here
                try:
                    timbre_blend_path = Path("debug_vocals_03_after_timbre_blend.wav")
                    sf.write(timbre_blend_path, audio, synth_sample_rate)
                    self.logger.debug(f"Saved audio after timbre blend to {timbre_blend_path}")
                except Exception as write_err:
                    self.logger.error(f"Failed to save audio after timbre blend: {write_err}")
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

    def _apply_timbre_blend(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply final timbre adjustments based on blend settings"""
        timbre: VocalTimbre = self.config.vocal_timbre
        result = np.zeros_like(audio, dtype=np.float32) # Initialize with float32

        # Apply filters based on timbre weights
        if timbre.choirboy > 1e-6: # Use epsilon for float comparison
            result += self._choir_filter(audio) * float(timbre.choirboy)
        if timbre.android > 1e-6:
            result += self._android_filter(audio) * float(timbre.android)
        if timbre.machinery > 1e-6:
            result += self._machinery_filter(audio) * float(timbre.machinery)

        # Normalize if sum of weights exceeds 1 or amplitudes clip
        total_weight = float(timbre.choirboy + timbre.android + timbre.machinery)
        max_amp = np.max(np.abs(result))

        # Normalize if total weight is significant and clipping occurs, or if total weight > 1
        if max_amp > 1.0 or (total_weight > 1.0 and max_amp > 1e-6):
             # Normalize by the maximum potential amplitude based on weights, or actual max amp
             norm_factor = max(total_weight, max_amp)
             if norm_factor > 1e-6: # Avoid division by zero
                 result /= norm_factor

        return result.astype(np.float32) # Ensure final type

    def _choir_filter(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply angelic choir characteristics (lowpass + chorus)"""
        # sosfiltfilt requires input length > padlen (default is often related to filter order, seems to be 15 here)
        if audio.shape[0] <= _MIN_SOSFILTFILT_LEN:
            self.logger.warning(f"Audio length ({audio.shape[0]}) too short for choir filter (needs > {_MIN_SOSFILTFILT_LEN}). Skipping.")
            return audio

        # Gentle lowpass filter (adjust cutoff frequency as needed)
        # Cutoff relative to Nyquist frequency (sample_rate / 2)
        cutoff_norm = 8000 / (self.sample_rate / 2)
        # Use SOS format for stability
        sos = signal.butter(4, min(cutoff_norm, 0.99), btype='low', output='sos')
        filtered = signal.sosfiltfilt(sos, audio)

        # Simple chorus effect
        chorus = np.zeros_like(audio)
        delays_ms = [15, 25, 35] # Delays in milliseconds
        max_delay_samples = int(max(delays_ms) * self.sample_rate / 1000)
        padded_audio = np.pad(filtered, (max_delay_samples, 0), mode='constant')
        depth = 0.3 # Chorus depth

        for delay_ms in delays_ms:
            delay_samples = int(delay_ms * self.sample_rate / 1000)
            # Ensure slicing is correct
            delayed_signal = padded_audio[max_delay_samples - delay_samples : len(padded_audio) - delay_samples]
            # Add delayed signal (lengths should match due to padding and slicing)
            chorus += delayed_signal * (depth / len(delays_ms)) # Average contribution
        # Combine original filtered signal with chorus
        # Ensure lengths match
        final_output = filtered + chorus

        return final_output.astype(np.float32)

    def _android_filter(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply android voice characteristics (bandpass + ring mod)"""
        # sosfiltfilt requires input length > padlen (default is often related to filter order, seems to be 15 here)
        if audio.shape[0] <= _MIN_SOSFILTFILT_LEN:
            self.logger.warning(f"Audio length ({audio.shape[0]}) too short for android filter (needs > {_MIN_SOSFILTFILT_LEN}). Skipping.")
            return audio

        # Bandpass filter (adjust frequencies as needed)
        low_cut_norm = 300 / (self.sample_rate / 2)
        high_cut_norm = 3400 / (self.sample_rate / 2)
        # Ensure valid frequency range
        if low_cut_norm >= high_cut_norm or low_cut_norm <= 0 or high_cut_norm >= 1.0:
             self.logger.warning(f"Invalid bandpass range: {low_cut_norm*self.sample_rate/2:.1f}-{high_cut_norm*self.sample_rate/2:.1f} Hz. Skipping filter.")
             return audio # Return original if range is invalid

        # Use SOS format for stability
        sos = signal.butter(6, [low_cut_norm, high_cut_norm], btype='band', output='sos')
        filtered = signal.sosfiltfilt(sos, audio)

        # Subtle ring modulation
        t = np.arange(len(filtered)) / self.sample_rate
        carrier_freq = 50 # Lower frequency for more subtle effect
        carrier = np.sin(2 * np.pi * carrier_freq * t)
        modulation_index = 0.2 # Keep it subtle

        result = filtered * (1 + modulation_index * carrier)
        return result.astype(np.float32)

    def _machinery_filter(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply machinery characteristics (highpass + distortion/resonance)"""
        # sosfiltfilt requires input length > padlen (default is often related to filter order, seems to be 15 here)
        if audio.shape[0] <= _MIN_SOSFILTFILT_LEN:
            self.logger.warning(f"Audio length ({audio.shape[0]}) too short for machinery filter (needs > {_MIN_SOSFILTFILT_LEN}). Skipping.")
            return audio

        # Highpass filter
        cutoff_norm = 1000 / (self.sample_rate / 2) # Higher cutoff for metallic feel
        # Use SOS format for stability
        sos = signal.butter(6, min(cutoff_norm, 0.99), btype='high', output='sos')
        filtered = signal.sosfiltfilt(sos, audio)

        # Add metallic resonance (simulated comb filter or distortion)
        # Simple soft clipping distortion
        distortion_level = 1.5
        distorted = np.tanh(filtered * distortion_level)

        # Normalize amplitude after distortion
        max_amp = np.max(np.abs(distorted))
        if max_amp > 1e-6:
             distorted /= max_amp

        return distorted.astype(np.float32)
