import importlib
import logging
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt
import soundfile as sf
from scipy import signal

from ..config import PsalmConfig, VocalTimbre

class ParameterEnum:
    """Mock Parameter enum for type checking"""
    RATE: int = 1
    PITCH: int = 2

@runtime_checkable
class TTSEngine(Protocol):
    """Protocol for TTS engines to ensure type safety"""
    Parameter: ParameterEnum
    def synth(self, text: str) -> list[float]: ...
    def set_voice(self, voice: str) -> None: ...
    def set_parameter(self, param: int, value: int) -> None: ...

@runtime_checkable
class FestivalEngine(Protocol):
    """Protocol for Festival TTS engine"""
    def set_language(self, lang: str) -> None: ...
    def text_to_wave(self, text: str) -> str: ...

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
        
        # Initialize TTS engines
        self.espeak: Optional[TTSEngine] = None
        self.festival: Optional[FestivalEngine] = None
        
        try:
            # Import espeak dynamically to avoid static type checking
            espeak_module = importlib.import_module('espeak')
            self.espeak = espeak_module.init()
            if not isinstance(self.espeak, TTSEngine):
                raise VoxDeiSynthesisError("eSpeak initialization failed: invalid interface")
        except ImportError as e:
            self.logger.error(f"Failed to initialize eSpeak: {e}")
            raise VoxDeiSynthesisError("eSpeak initialization failed")
            
        try:
            # Import festival dynamically to avoid static type checking
            festival_module = importlib.import_module('festival')
            self.festival = festival_module.Festival()
            if not isinstance(self.festival, FestivalEngine):
                raise VoxDeiSynthesisError("Festival initialization failed: invalid interface")
        except ImportError as e:
            self.logger.error(f"Failed to initialize Festival: {e}")
            raise VoxDeiSynthesisError("Festival initialization failed")

    def synthesize_text(self, text: str) -> npt.NDArray[np.float32]:
        """Synthesize Latin text using combined TTS engines
        
        Args:
            text: Latin text to synthesize
            
        Returns:
            numpy array of audio samples (float32)
            
        Raises:
            VoxDeiSynthesisError: If synthesis fails
        """
        try:
            # Generate raw TTS audio
            espeak_audio = self._generate_espeak(text)
            festival_audio = self._generate_festival(text)
            
            # Align and combine TTS streams
            combined = self._align_and_mix(espeak_audio, festival_audio)
            
            # Apply formant shifting
            shifted = self._apply_formant_shift(combined)
            
            # Apply timbre blending
            final = self._apply_timbre_blend(shifted)
            
            return final
            
        except Exception as e:
            self.logger.error(f"Synthesis failed: {str(e)}")
            raise VoxDeiSynthesisError(f"Failed to synthesize text: {str(e)}")

    def _generate_espeak(self, text: str) -> npt.NDArray[np.float32]:
        """Generate speech using eSpeak"""
        if not self.espeak:
            raise VoxDeiSynthesisError("eSpeak not initialized")
            
        try:
            # Configure eSpeak for Latin
            self.espeak.set_voice("la")
            self.espeak.set_parameter(self.espeak.Parameter.RATE, 130)
            self.espeak.set_parameter(self.espeak.Parameter.PITCH, 60)
            
            # Generate audio and convert to float32
            raw_audio = self.espeak.synth(text)
            return np.array(raw_audio, dtype=np.float32)
            
        except Exception as e:
            raise VoxDeiSynthesisError(f"eSpeak synthesis failed: {str(e)}")

    def _generate_festival(self, text: str) -> npt.NDArray[np.float32]:
        """Generate speech using Festival"""
        if not self.festival:
            raise VoxDeiSynthesisError("Festival not initialized")
            
        try:
            # Configure Festival for Latin
            self.festival.set_language("latin")
            
            # Generate audio
            wav_path = self.festival.text_to_wave(text)
            audio_data = sf.read(wav_path)
            Path(wav_path).unlink()  # Clean up temp file
            
            # Convert to float32
            audio = np.array(audio_data[0], dtype=np.float32)
            
            return audio
            
        except Exception as e:
            raise VoxDeiSynthesisError(f"Festival synthesis failed: {str(e)}")

    def _align_and_mix(
        self,
        esp: npt.NDArray[np.float32],
        fest: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Align and mix two audio streams"""
        # Resample to match lengths if needed
        if len(esp) != len(fest):
            resampled = signal.resample(fest, len(esp))
            fest = np.array(resampled, dtype=np.float32)
        
        # Apply cross-fade mixing
        mix_ratio = 0.6  # Favor eSpeak slightly
        return esp * mix_ratio + fest * (1 - mix_ratio)

    def _apply_formant_shift(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply formant shifting based on timbre settings"""
        timbre = self.config.vocal_timbre
        
        # Calculate shift factors based on timbre blend
        choir_shift = 1.2 * timbre.choirboy
        android_shift = 0.8 * timbre.android
        machine_shift = 0.5 * timbre.machinery
        
        # Apply multiple formant shifts
        shifted = audio.copy()
        if choir_shift > 0:
            shifted += self._formant_shift(audio, choir_shift)
        if android_shift > 0:
            shifted += self._formant_shift(audio, android_shift)
        if machine_shift > 0:
            shifted += self._formant_shift(audio, machine_shift)
            
        # Normalize
        max_val = np.max(np.abs(shifted))
        if max_val > 0:
            shifted = shifted / max_val
            
        return shifted

    def _formant_shift(
        self,
        audio: npt.NDArray[np.float32],
        factor: float
    ) -> npt.NDArray[np.float32]:
        """Apply formant shifting by factor"""
        # Use phase vocoder for formant shifting
        D = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), 1/self.sample_rate)
        
        # Shift frequency components
        shifted_freqs = freqs * factor
        shifted_D = np.interp(freqs, shifted_freqs, D)
        
        # Convert back to time domain and ensure float32
        result = np.fft.irfft(shifted_D)
        return np.array(result, dtype=np.float32)

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
        for i, delay in enumerate([0.01, 0.02, 0.03]):
            samples = int(delay * self.sample_rate)
            delayed = np.pad(audio, (samples, 0))[:-samples]
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