import importlib
import logging
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt
import soundfile as sf
from scipy import signal

from ..config import PsalmConfig, VocalTimbre
from .tts.engines.espeak import EspeakNGWrapper # Remove EspeakWrapper import
from .tts.base import TTSEngine, ParameterEnum


class VoxDeiSynthesisError(Exception):
    """Raised when vocal synthesis fails"""
    pass

class VoxDeiSynthesizer:
    """Core vocal synthesis engine combining TTS and sample processing"""
    
    def __init__(self, config: PsalmConfig, sample_rate: int = 48000):
        """Initialize the vocal synthesizer
        
        Args:
            config: Main configuration object
            sample_rate: Audio sample rate (default 48kHz)
        """
        self.config = config
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        
        # Internal buffers
        self._tts_buffer: Optional[npt.NDArray[np.float32]] = None
        self._formant_buffer: Optional[npt.NDArray[np.float32]] = None
        
        # Initialize TTS engine
        self.espeak: Optional[TTSEngine] = None
        
        # Try espeak-ng first
        try:
            self.espeak = EspeakNGWrapper()
            if not isinstance(self.espeak, TTSEngine):
                raise VoxDeiSynthesisError("Invalid eSpeak interface")
        except Exception as e:
            # Fallback logic for legacy EspeakWrapper removed as it's deprecated
            # except Exception as e2:
                self.logger.warning("No eSpeak engine available")
                self.logger.error(f"Failed to initialize any functional eSpeak wrapper: {e}")
                self.espeak = None

        if self.espeak:
            # Configure TTS engine based on settings
            self.espeak.set_parameter(ParameterEnum.RATE, 
                                    int(150 * self.config.tempo_scale))
            self.espeak.set_parameter(ParameterEnum.PITCH, 
                                    int(50 + self.config.vocal_timbre.choirboy * 30))
            
            # Apply articulation settings
            phoneme_rate = int(200 * self.config.robotic_articulation.phoneme_spacing)
            self.espeak.set_parameter(ParameterEnum.VOLUME,
                                    int(200 * self.config.robotic_articulation.consonant_harshness))
            self.espeak.set_parameter(ParameterEnum.RATE, phoneme_rate)

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
            pitch_value = int(50 * (base_freq / 130.81))
            self.logger.debug(f"Setting base pitch to {pitch_value}")
            self.espeak.set_parameter(ParameterEnum.PITCH, pitch_value)
            
            # Apply formant shifting for voice character
            self.formant_shift_factor = self.config.voice_range.formant_shift

    def synthesize_text(self, text: str) -> npt.NDArray[np.float32]:
        """Synthesize text using TTS engine"""
        if not self.espeak:
            raise VoxDeiSynthesisError("No TTS engine available")
            
        try:
            # Update parameters before synthesis
            self.espeak.set_parameter(ParameterEnum.RATE, 
                                    int(150 * self.config.tempo_scale))
            self.espeak.set_parameter(ParameterEnum.VOLUME,
                                    int(100 * self.config.robotic_articulation.consonant_harshness))
            
            self.logger.debug("Synthesizing text with eSpeak...")
            audio = self.espeak.synth(text)
            
            if len(audio) == 0:
                raise VoxDeiSynthesisError("Empty audio data")
            
            self.logger.debug(f"Pre-processing max amplitude: {np.max(np.abs(audio))}")

            # Apply formant shift and timbre blend
            audio = self._apply_formant_shift(audio)
            audio = self._apply_timbre_blend(audio)

             # Boost vocal output
            audio = np.tanh(audio * 2.0)  # Double gain with soft clipping
            
            self.logger.debug(f"Post-processing max amplitude: {np.max(np.abs(audio))}")
                
            return audio
            
        except Exception as e:
            raise VoxDeiSynthesisError(f"TTS synthesis failed: {str(e)}")

    def _apply_formant_shift(self, audio: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        """Apply formant shifting based on timbre and voice range settings"""
        timbre: VocalTimbre = self.config.vocal_timbre
        
        # Apply base formant shift for voice range
        shifted = self._formant_shift(audio, self.formant_shift_factor)
        
        # Calculate additional shifts based on timbre blend
        choir_shift = 1.2 * timbre.choirboy
        android_shift = 0.8 * timbre.android
        machine_shift = 0.5 * timbre.machinery
        
        # Layer additional formant shifts
        if choir_shift > 0:
            shifted += self._formant_shift(audio, choir_shift * self.formant_shift_factor)
        if android_shift > 0:
            shifted += self._formant_shift(audio, android_shift * self.formant_shift_factor)
        if machine_shift > 0:
            shifted += self._formant_shift(audio, machine_shift * self.formant_shift_factor)
            
        return shifted

    def _formant_shift(self, audio: npt.NDArray[np.float32], factor: float) -> npt.NDArray[np.float32]:
        """Apply formant shifting"""
        # Ensure even length for FFT
        if len(audio) % 2 != 0:
            audio = np.pad(audio, (0, 1), mode='constant')
        
        # Get frequency spectrum    
        D = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1/self.sample_rate)
        
        # Shift frequency components
        shifted_freqs = freqs * factor
        shifted_D = np.interp(freqs, shifted_freqs, np.abs(D)) * np.exp(1j * np.angle(D))
        
        # Inverse transform
        result = np.fft.irfft(shifted_D)
        
        # Ensure output matches input length
        if len(result) > len(audio):
            result = result[:len(audio)]
        elif len(result) < len(audio):
            result = np.pad(result, (0, len(audio) - len(result)), mode='constant')
            
        return result.astype(np.float32)

    def _apply_timbre_blend(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply final timbre adjustments"""
        timbre = self.config.vocal_timbre
        
        # Apply different filters based on timbre settings
        result = np.zeros_like(audio)
        
        if timbre.choirboy > 0:
            result += self._choir_filter(audio) * timbre.choirboy
        if timbre.android > 0:
            result += self._android_filter(audio) * timbre.android
        if timbre.machinery > 0:
            result += self._machinery_filter(audio) * timbre.machinery
            
        return result.astype(np.float32)

    def _choir_filter(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply angelic choir characteristics"""
        # Gentle lowpass + subtle chorus
        b, a = signal.butter(4, 0.6)
        filtered = signal.filtfilt(b, a, audio)
        
        # Add chorus effect
        chorus = np.zeros_like(audio)
        max_delay = int(0.03 * self.sample_rate)  # Maximum delay samples
        padded_audio = np.pad(audio, (max_delay, 0), mode='constant')
        
        for i, delay in enumerate([0.01, 0.02, 0.03]):
            samples = int(delay * self.sample_rate)
            # Use pre-padded audio slice
            delayed = padded_audio[max_delay-samples:len(padded_audio)-samples]
            chorus += delayed * 0.3
            
        return np.array(filtered + chorus, dtype=np.float32)

    def _android_filter(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply android voice characteristics"""
        # Bandpass filter + ring modulation
        b, a = signal.butter(6, [0.1, 0.7], btype='band')
        filtered = signal.filtfilt(b, a, audio)
        
        # Add subtle ring modulation
        t = np.arange(len(audio)) / self.sample_rate
        carrier = np.sin(2 * np.pi * 2000 * t)
        
        # Ensure float32 output
        result = filtered * (1 + 0.2 * carrier)
        return np.array(result, dtype=np.float32)

    def _machinery_filter(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply machinery characteristics"""
        # Highpass + distortion
        b, a = signal.butter(6, 0.3, btype='high')
        filtered = signal.filtfilt(b, a, audio)
        
        # Add metallic resonance
        resonance = np.zeros_like(audio)
        t = np.arange(len(audio)) / self.sample_rate
        for freq in [1200, 2400, 3600]:
            resonance += np.sin(2 * np.pi * freq * t) * 0.1
            
        # Ensure float32 output
        result = np.clip(filtered + resonance, -1, 1)
        return np.array(result, dtype=np.float32)