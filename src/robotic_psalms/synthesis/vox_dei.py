import logging
from typing import Optional, Protocol, cast

import numpy as np
import numpy.typing as npt
import soundfile as sf
from pathlib import Path
# soundfile is used implicitly by EspeakNGWrapper, but not directly here.
from scipy import signal

from ..config import PsalmConfig, VocalTimbre
# Corrected imports for TTS engines and base class
from .tts.base import TTSEngine, ParameterEnum
from .tts.engines.espeak import EspeakNGWrapper


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
        """Apply formant shifting based on timbre and voice range settings"""
        timbre: VocalTimbre = self.config.vocal_timbre

        # Apply base formant shift for voice range
        shifted_audio = self._formant_shift(audio, self.formant_shift_factor)

        # Calculate additional shifts based on timbre blend
        # Ensure factors are floats
        choir_shift_factor = 1.2 * float(timbre.choirboy)
        android_shift_factor = 0.8 * float(timbre.android)
        machine_shift_factor = 0.5 * float(timbre.machinery)

        # Layer additional formant shifts only if factor > 0
        if choir_shift_factor > 1e-6: # Use small epsilon for float comparison
            shifted_audio += self._formant_shift(audio, choir_shift_factor * self.formant_shift_factor)
        if android_shift_factor > 1e-6:
            shifted_audio += self._formant_shift(audio, android_shift_factor * self.formant_shift_factor)
        if machine_shift_factor > 1e-6:
            shifted_audio += self._formant_shift(audio, machine_shift_factor * self.formant_shift_factor)

        # Normalize potentially increased amplitude
        max_amp = np.max(np.abs(shifted_audio))
        if max_amp > 1.0:
             shifted_audio /= max_amp

        return shifted_audio.astype(np.float32)

    def _formant_shift(self, audio: npt.NDArray[np.float32], factor: float) -> npt.NDArray[np.float32]:
        """Apply formant shifting using FFT"""
        n = len(audio)
        # Ensure even length for rfft
        if n % 2 != 0:
            audio = np.pad(audio, (0, 1), mode='constant')
            n += 1 # Update length

        # Get frequency spectrum
        D = np.fft.rfft(audio)
        # Frequencies for rfft output
        freqs = np.fft.rfftfreq(n, 1.0 / self.sample_rate)

        # Shift frequency components
        shifted_freqs = freqs * factor
        # Ensure shifted_freqs is monotonically increasing for interpolation
        if factor <= 0:
             # Handle non-positive factor - maybe return original or raise error
             self.logger.warning("Formant shift factor must be positive. Returning original audio.")
             return audio

        # Interpolate magnitudes onto original frequency bins
        # Use absolute value for magnitude interpolation
        shifted_magnitudes = np.interp(freqs, shifted_freqs, np.abs(D))

        # Combine interpolated magnitudes with original phases
        # Ensure phase array matches magnitude array length
        phases = np.angle(D)
        if len(phases) < len(shifted_magnitudes):
             # This case might happen with certain FFT lengths, pad phases
             phases = np.pad(phases, (0, len(shifted_magnitudes) - len(phases)), mode='constant')
        elif len(phases) > len(shifted_magnitudes):
             # Truncate phases if necessary
             phases = phases[:len(shifted_magnitudes)]

        shifted_D = shifted_magnitudes * np.exp(1j * phases)

        # Inverse transform
        result = np.fft.irfft(shifted_D, n=n) # Specify original length 'n'

        # Ensure output matches original input length (before potential padding)
        original_length = len(audio) if n == len(audio) else len(audio) - 1
        if len(result) > original_length:
            result = result[:original_length]
        elif len(result) < original_length:
            # This shouldn't happen with irfft(n=n) but handle defensively
            result = np.pad(result, (0, original_length - len(result)), mode='constant')

        return result.astype(np.float32)

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
