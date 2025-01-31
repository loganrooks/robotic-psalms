import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import numpy.typing as npt
from scipy import signal
from scipy.signal.windows import hann

from ..config import HauntingParameters, LiturgicalMode, PsalmConfig
from .vox_dei import VoxDeiSynthesizer

@dataclass
class SynthesisResult:
    """Container for synthesis output"""
    vocals: npt.NDArray[np.float32]
    pads: npt.NDArray[np.float32]
    percussion: npt.NDArray[np.float32]
    drones: npt.NDArray[np.float32]
    combined: npt.NDArray[np.float32]
    sample_rate: int

class SacredMachineryEngine:
    """Main synthesis engine combining all sound elements"""
    
    def __init__(self, config: PsalmConfig):
        """Initialize the sacred machinery engine
        
        Args:
            config: Main configuration object
        """
        self.config = config
        self.sample_rate = 48000
        self.logger = logging.getLogger(__name__)
        
        # Initialize component synthesizers
        self.vox_dei = VoxDeiSynthesizer(config, self.sample_rate)
        
        # Modulation state
        self._lfo_phase = 0.0
        self._noise_buffer: npt.NDArray[np.float32] = np.random.uniform(
            -1, 1, self.sample_rate
        ).astype(np.float32)
        
        # Modal frequencies for each liturgical mode
        self.mode_frequencies = {
            LiturgicalMode.DORIAN: [146.83, 220.00, 293.66],      # D3, A3, D4
            LiturgicalMode.PHRYGIAN: [164.81, 220.00, 329.63],    # E3, A3, E4
            LiturgicalMode.LYDIAN: [174.61, 261.63, 349.23],      # F3, C4, F4
            LiturgicalMode.MIXOLYDIAN: [196.00, 293.66, 392.00],  # G3, D4, G4
            LiturgicalMode.AEOLIAN: [220.00, 293.66, 440.00],     # A3, D4, A4
        }

    def process_psalm(self, text: str, duration: float) -> SynthesisResult:
        """Process a complete psalm
        
        Args:
            text: Latin psalm text
            duration: Total duration in seconds
            
        Returns:
            SynthesisResult containing all audio components
        """
        # Generate base components
        vocals = self.vox_dei.synthesize_text(text)
        pads = self._generate_pads(duration)
        percussion = self._generate_percussion(duration)
        drones = self._generate_drones(duration)
        
        # Apply haunting effects
        vocals = self._apply_haunting_effects(vocals)
        pads = self._apply_haunting_effects(pads)
        drones = self._apply_haunting_effects(drones)
        
        # Align lengths
        target_length = int(duration * self.sample_rate)
        vocals = self._fit_to_length(vocals, target_length)
        pads = self._fit_to_length(pads, target_length)
        percussion = self._fit_to_length(percussion, target_length)
        drones = self._fit_to_length(drones, target_length)
        
        # Mix components
        combined = self._mix_components(vocals, pads, percussion, drones)
        
        return SynthesisResult(
            vocals=vocals,
            pads=pads,
            percussion=percussion,
            drones=drones,
            combined=combined,
            sample_rate=self.sample_rate
        )

    def _apply_haunting_effects(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply haunting effects using reverb and spectral freeze
        
        Args:
            audio: Input audio array
            
        Returns:
            Processed audio with haunting effects
        """
        haunting = self.config.haunting_intensity
        
        # Apply reverb based on decay time
        reverb_time = haunting.reverb_decay
        impulse_response = self._generate_reverb_ir(reverb_time)
        reverbed = signal.fftconvolve(audio, impulse_response)[:len(audio)]
        
        # Apply spectral freeze effect
        if haunting.spectral_freeze > 0:
            frozen = self._spectral_freeze(audio, haunting.spectral_freeze)
            result = reverbed * (1 - haunting.spectral_freeze) + frozen * haunting.spectral_freeze
        else:
            result = reverbed
            
        return np.array(result, dtype=np.float32)

    def _generate_reverb_ir(self, decay_time: float) -> npt.NDArray[np.float32]:
        """Generate reverb impulse response
        
        Args:
            decay_time: Reverb decay time in seconds
            
        Returns:
            Impulse response array
        """
        ir_length = int(decay_time * self.sample_rate)
        t = np.arange(ir_length) / self.sample_rate
        
        # Generate exponential decay
        decay = np.exp(-t * (6.0 / decay_time))
        
        # Add some early reflections
        reflections = np.zeros_like(decay)
        for i, offset in enumerate([0.01, 0.02, 0.03, 0.05]):
            idx = int(offset * self.sample_rate)
            if idx < len(reflections):
                reflections[idx] = 0.5 / (i + 1)
        
        ir = decay * (reflections + np.random.uniform(0, 0.1, len(decay)))
        return np.array(ir, dtype=np.float32)

    def _spectral_freeze(
        self,
        audio: npt.NDArray[np.float32],
        freeze_amount: float
    ) -> npt.NDArray[np.float32]:
        """Apply spectral freeze effect
        
        Args:
            audio: Input audio array
            freeze_amount: Amount of freezing (0-1)
            
        Returns:
            Spectrally frozen audio
        """
        # Get spectral representation
        D = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio))
        
        # Generate frozen spectrum by smoothing
        window_size = int(len(freqs) * freeze_amount * 0.1)
        if window_size > 1:
            window = hann(window_size, sym=False)
            frozen_D = signal.convolve(np.abs(D), window/window.sum(), mode='same')
            frozen_D = frozen_D * np.exp(1j * np.angle(D))
        else:
            frozen_D = D
            
        # Convert back to time domain
        result = np.fft.irfft(frozen_D)
        return np.array(result[:len(audio)], dtype=np.float32)

    def _generate_pads(self, duration: float) -> npt.NDArray[np.float32]:
        """Generate glacial synthesizer pads"""
        num_samples = int(duration * self.sample_rate)
        t = np.arange(num_samples) / self.sample_rate
        
        # Get frequencies for current mode
        frequencies = self.mode_frequencies[self.config.mode]
        
        pad = np.zeros(num_samples, dtype=np.float32)
        harmonicity = self.config.celestial_harmonicity
        
        for freq in frequencies:
            # Mix sine and sawtooth waves based on harmonicity
            sine = np.sin(2 * np.pi * freq * t)
            saw = 2 * (t * freq - np.floor(0.5 + t * freq))
            
            wave = sine * (1 - harmonicity) + saw * harmonicity
            pad += wave * 0.3
        
        # Apply slow evolution
        lfo = np.sin(2 * np.pi * 0.1 * t)
        pad *= 0.7 + 0.3 * lfo
        
        return pad

    def _generate_percussion(self, duration: float) -> npt.NDArray[np.float32]:
        """Generate stochastic metallic percussion"""
        num_samples = int(duration * self.sample_rate)
        result = np.zeros(num_samples, dtype=np.float32)
        
        # Generate random timing for percussion hits
        hit_probability = 0.1  # hits per second
        hit_times = np.random.uniform(0, duration, int(duration * hit_probability))
        
        for time in hit_times:
            # Generate metallic sound for each hit
            hit_samples = int(0.1 * self.sample_rate)  # 100ms per hit
            hit_start = int(time * self.sample_rate)
            
            if hit_start + hit_samples > num_samples:
                continue
                
            hit = self._generate_metallic_hit(hit_samples)
            result[hit_start:hit_start + hit_samples] += hit
        
        return result * 0.3  # Reduce volume

    def _generate_metallic_hit(self, num_samples: int) -> npt.NDArray[np.float32]:
        """Generate single metallic percussion hit"""
        # Generate metallic frequencies
        freqs = [800, 1200, 2400, 3600, 4800]
        t = np.arange(num_samples) / self.sample_rate
        
        hit = np.zeros(num_samples, dtype=np.float32)
        for freq in freqs:
            # Generate sine wave with random phase
            phase = np.random.uniform(0, 2 * np.pi)
            sine = np.sin(2 * np.pi * freq * t + phase)
            
            # Apply quick decay envelope
            envelope = np.exp(-t * 20)
            hit += sine * envelope
        
        return hit

    def _generate_drones(self, duration: float) -> npt.NDArray[np.float32]:
        """Generate frequency modulated drones"""
        num_samples = int(duration * self.sample_rate)
        t = np.arange(num_samples) / self.sample_rate
        
        # Base frequency from mode
        base_freq = self.mode_frequencies[self.config.mode][0] / 2  # One octave down
        
        # Generate main drone
        mod_freq = 0.1  # Slow modulation
        mod_depth = 0.01 * base_freq  # Small frequency deviation
        
        # FM synthesis
        modulator = np.sin(2 * np.pi * mod_freq * t)
        instantaneous_freq = base_freq + mod_depth * modulator
        phase = np.cumsum(instantaneous_freq) / self.sample_rate
        drone = np.sin(2 * np.pi * phase)
        
        # Add harmonics
        for harmonic in [2, 3, 4]:
            harmonic_freq = base_freq * harmonic
            harmonic_mod_depth = mod_depth * harmonic
            
            instantaneous_freq = harmonic_freq + harmonic_mod_depth * modulator
            phase = np.cumsum(instantaneous_freq) / self.sample_rate
            drone += np.sin(2 * np.pi * phase) * (0.3 / harmonic)
        
        return np.array(drone * 0.4, dtype=np.float32)

    def _fit_to_length(
        self,
        audio: npt.NDArray[np.float32],
        target_length: int
    ) -> npt.NDArray[np.float32]:
        """Fit audio to target length using resampling"""
        if len(audio) == target_length:
            return audio
        resampled = signal.resample(audio, target_length)
        return np.array(resampled, dtype=np.float32)

    def _mix_components(
        self,
        vocals: npt.NDArray[np.float32],
        pads: npt.NDArray[np.float32],
        percussion: npt.NDArray[np.float32],
        drones: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Mix all components with proper levels"""
        # Mix levels
        vocal_level = 0.8
        pad_level = 0.6
        percussion_level = 0.4
        drone_level = 0.5
        
        # Combine components
        mixed = (vocals * vocal_level + 
                pads * pad_level + 
                percussion * percussion_level + 
                drones * drone_level)
        
        # Normalize
        max_val = np.max(np.abs(mixed))
        if max_val > 0:
            mixed = mixed / max_val
        
        return mixed