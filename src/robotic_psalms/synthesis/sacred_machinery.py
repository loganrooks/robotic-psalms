import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from scipy import signal

from ..config import HauntingParameters, LiturgicalMode, PsalmConfig
from .vox_dei import VoxDeiSynthesizer

@dataclass
class SynthesisResult:
    """Container for synthesis output"""
    vocals: np.ndarray
    pads: np.ndarray
    percussion: np.ndarray
    drones: np.ndarray
    combined: np.ndarray
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
        self._noise_buffer = np.random.uniform(-1, 1, self.sample_rate)
        
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

    def _generate_pads(self, duration: float) -> np.ndarray:
        """Generate glacial synthesizer pads"""
        num_samples = int(duration * self.sample_rate)
        t = np.arange(num_samples) / self.sample_rate
        
        # Get frequencies for current mode
        frequencies = self.mode_frequencies[self.config.mode]
        
        pad = np.zeros(num_samples)
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

    def _generate_percussion(self, duration: float) -> np.ndarray:
        """Generate stochastic metallic percussion"""
        num_samples = int(duration * self.sample_rate)
        result = np.zeros(num_samples)
        
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

    def _generate_metallic_hit(self, num_samples: int) -> np.ndarray:
        """Generate single metallic percussion hit"""
        # Generate metallic frequencies
        freqs = [800, 1200, 2400, 3600, 4800]
        t = np.arange(num_samples) / self.sample_rate
        
        hit = np.zeros(num_samples)
        for freq in freqs:
            # Generate sine wave with random phase
            phase = np.random.uniform(0, 2 * np.pi)
            sine = np.sin(2 * np.pi * freq * t + phase)
            
            # Apply quick decay envelope
            envelope = np.exp(-t * 20)
            hit += sine * envelope
        
        return hit

    def _generate_drones(self, duration: float) -> np.ndarray:
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
        
        return drone * 0.4

    def _fit_to_length(self, audio: np.ndarray, target_length: int) -> np.ndarray:
        """Fit audio to target length using resampling"""
        if len(audio) == target_length:
            return audio
        return signal.resample(audio, target_length)

    def _mix_components(self, vocals: np.ndarray, pads: np.ndarray, 
                       percussion: np.ndarray, drones: np.ndarray) -> np.ndarray:
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
        return mixed / np.max(np.abs(mixed))