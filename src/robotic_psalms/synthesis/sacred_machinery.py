import logging
from typing import Any, Optional, Protocol, runtime_checkable, cast
from pathlib import Path
import soundfile as sf
import numpy as np
import numpy.typing as npt
from scipy import signal
from ..config import PsalmConfig, HauntingParameters, LiturgicalMode
from .vox_dei import VoxDeiSynthesizer, VoxDeiSynthesisError
from .effects import apply_high_quality_reverb, ReverbParameters
from .effects import apply_complex_delay, DelayParameters
from scipy.signal.windows import hann
from dataclasses import dataclass

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

        # Extract effect parameters for direct access
        self.haunting: HauntingParameters = config.haunting_intensity

        # Modulation state
        self._lfo_phase = 0.0
        self._noise_buffer: npt.NDArray[np.float32] = np.random.uniform(
            -1, 1, self.sample_rate
        ).astype(np.float32)

        # Modal frequencies for each liturgical mode
        self.mode_frequencies = {
            LiturgicalMode.DORIAN: [146.83, 220.00, 293.66],
            LiturgicalMode.PHRYGIAN: [164.81, 220.00, 329.63],
            LiturgicalMode.LYDIAN: [174.61, 261.63, 349.23],
            LiturgicalMode.MIXOLYDIAN: [196.00, 293.66, 392.00],
            LiturgicalMode.AEOLIAN: [220.00, 293.66, 440.00],
        }

    def process_psalm(self, text: str, duration: float) -> SynthesisResult:
        """
        Process a complete psalm text, generating all audio components and applying effects.

        Args:
            text: The Latin psalm text.
            duration: The target duration of the output audio in seconds.

        Returns:
            A SynthesisResult object containing individual stems and the combined mix.
        """
        # Generate base components
        try:
            # Synthesize and get actual sample rate
            raw_vocals, tts_sample_rate = self.vox_dei.synthesize_text(text)

            # Resample to engine sample rate *immediately* if needed
            if tts_sample_rate != self.sample_rate:
                self.logger.debug(f"Resampling vocals from {tts_sample_rate}Hz to {self.sample_rate}Hz")
                num_samples_target = int(len(raw_vocals) * self.sample_rate / tts_sample_rate)
                vocals = signal.resample(raw_vocals, num_samples_target)
                # --- DEBUG: Save resampled vocals (Step 04) ---
                if self.logger.isEnabledFor(logging.DEBUG):
                    try:
                        resampled_path = Path("debug_vocals_04_resampled.wav")
                        sf.write(resampled_path, vocals, self.sample_rate)
                        self.logger.debug(f"Saved resampled vocals to {resampled_path}")
                    except Exception as write_err:
                        self.logger.error(f"Failed to save resampled vocals: {write_err}")
                # --- END DEBUG ---
            else:
                vocals = raw_vocals
        except VoxDeiSynthesisError as e:
            self.logger.error(f"Vocal synthesis failed: {e}")
            vocals = np.zeros(int(duration * self.sample_rate), dtype=np.float32)

        pads = self._generate_pads(duration)
        percussion = self._generate_percussion(duration)
        drones = self._generate_drones(duration)

        # Apply effects
        vocals_typed = cast(npt.NDArray[np.float32], vocals) # Assure type checker
        vocals = self._apply_haunting_effects(vocals_typed)
        pads = self._apply_haunting_effects(pads)
        drones = self._apply_haunting_effects(drones)
        # --- DEBUG: Save vocals after haunting effects (Step 05) ---
        if self.logger.isEnabledFor(logging.DEBUG):
            try:
                haunting_path = Path("debug_vocals_05_after_haunting.wav")
                sf.write(haunting_path, vocals, self.sample_rate)
                self.logger.debug(f"Saved vocals after haunting effects to {haunting_path}")
            except Exception as write_err:
                self.logger.error(f"Failed to save vocals after haunting effects: {write_err}")
        # --- END DEBUG ---

        # Apply glitch effects
        if self.config.glitch_density > 0:
            vocals = self._apply_glitch_effect(vocals)
            pads = self._apply_glitch_effect(pads)
            drones = self._apply_glitch_effect(drones)
            # --- DEBUG: Save vocals after glitch effects (Step 06) ---
            if self.logger.isEnabledFor(logging.DEBUG):
                try:
                    glitch_path = Path("debug_vocals_06_after_glitch.wav")
                    sf.write(glitch_path, vocals, self.sample_rate)
                    self.logger.debug(f"Saved vocals after glitch effects to {glitch_path}")
                except Exception as write_err:
                    self.logger.error(f"Failed to save vocals after glitch effects: {write_err}")
            # --- END DEBUG ---

        # Align lengths using sample count instead of duration
        target_samples = int(duration * self.sample_rate)
        vocals = self._fit_to_length(vocals, target_samples)
        pads = self._fit_to_length(pads, target_samples)
        percussion = self._fit_to_length(percussion, target_samples)
        drones = self._fit_to_length(drones, target_samples)

        # Mix components with levels applied before any final processing
        combined = self._mix_components(vocals, pads, percussion, drones)
        # --- DEBUG: Save vocals after length fitting (Step 07) ---
        if self.logger.isEnabledFor(logging.DEBUG):
            try:
                fitted_path = Path("debug_vocals_07_after_fitting.wav")
                sf.write(fitted_path, vocals, self.sample_rate)
                self.logger.debug(f"Saved vocals after length fitting to {fitted_path}")
            except Exception as write_err:
                self.logger.error(f"Failed to save vocals after length fitting: {write_err}")
        # --- END DEBUG ---

        # Normalize individual components before mixing
        vocals = self._normalize_audio(vocals)
        pads = self._normalize_audio(pads)
        percussion = self._normalize_audio(percussion)
        drones = self._normalize_audio(drones)
        # --- DEBUG: Save vocals after normalization (Step 08) ---
        if self.logger.isEnabledFor(logging.DEBUG):
            try:
                normalized_path = Path("debug_vocals_08_after_normalization.wav")
                sf.write(normalized_path, vocals, self.sample_rate)
                self.logger.debug(f"Saved vocals after normalization to {normalized_path}")
            except Exception as write_err:
                self.logger.error(f"Failed to save vocals after normalization: {write_err}")
        # --- END DEBUG ---

        # Apply complex delay effect if configured
        combined = self._apply_configured_delay(combined)
        return SynthesisResult(
            vocals=vocals.astype(np.float32),
            pads=pads.astype(np.float32),
            percussion=percussion.astype(np.float32),
            drones=drones.astype(np.float32),
            combined=combined.astype(np.float32),
            sample_rate=self.sample_rate
        )

    def _mix_components(self, vocals, pads, percussion, drones):
        """Mix all audio components together"""
        max_len = max(len(vocals), len(pads), len(percussion), len(drones))

        # Apply mix levels before padding
        vocals = vocals * self.config.mix_levels.vocals
        pads = pads * self.config.mix_levels.pads
        percussion = percussion * self.config.mix_levels.percussion
        drones = drones * self.config.mix_levels.drones

        # Pad to same length
        vocals = np.pad(vocals, (0, max_len - len(vocals)), mode='constant')
        pads = np.pad(pads, (0, max_len - len(pads)), mode='constant')
        percussion = np.pad(percussion, (0, max_len - len(percussion)), mode='constant')
        drones = np.pad(drones, (0, max_len - len(drones)), mode='constant')

        # Simple sum with protection against clipping
        mixed = vocals + pads + percussion + drones
        peak = np.max(np.abs(mixed))
        if peak > 1.0:
            mixed /= peak
        return mixed

    def _generate_backup_vocals(
            self,
            text: str,
            duration: float
        ) -> npt.NDArray[np.float32]:
            """Generate fallback robotic vocals when TTS fails

            This creates a synthetic vocal-like sound using formant synthesis
            and robotic modulation, maintaining the rhythmic structure of the text.

            Args:
                text: Latin text to synthesize
                duration: Target duration in seconds

            Returns:
                Synthesized backup vocals as float32 array
            """
            # Estimate number of syllables (rough approximation for Latin)
            syllables = len([c for c in text.lower() if c in 'aeiouy'])
            if syllables == 0:
                syllables = len(text) // 3  # Fallback approximation

            # Calculate timing
            samples_per_syllable = int(self.sample_rate * duration / syllables)
            num_samples = int(duration * self.sample_rate)
            result = np.zeros(num_samples, dtype=np.float32)

            # Generate carrier frequencies (typical vocal formants)
            formants = [500, 1500, 2500]  # Hz
            t = np.arange(samples_per_syllable) / self.sample_rate

            # Generate base formant waves
            formant_waves = []
            for freq in formants:
                wave = np.sin(2 * np.pi * freq * t)
                # Add slight frequency modulation for more natural sound
                mod = np.sin(2 * np.pi * 5 * t)  # 5 Hz modulation
                wave *= (1 + 0.1 * mod)  # 10% modulation depth
                formant_waves.append(wave)

            # Combine formants with different amplitudes
            syllable = formant_waves[0] * 1.0 + formant_waves[1] * 0.5 + formant_waves[2] * 0.25

            # Create amplitude envelope
            envelope = np.exp(-t * 10)  # Quick decay
            envelope = envelope / np.max(envelope)
            syllable *= envelope

            # Place syllables in output buffer with random timing variations
            time_index = 0
            for i in range(syllables):
                if time_index >= num_samples:
                    break

                # Add random timing variation (±10%)
                variation = int(samples_per_syllable * np.random.uniform(-0.1, 0.1))
                actual_length = min(len(syllable), num_samples - time_index)

                # Add syllable with random pitch variation
                pitch_var = np.random.uniform(0.95, 1.05)
                pitched = signal.resample(
                    syllable,
                    int(actual_length * pitch_var)
                )[:actual_length]

                # Add to result with crossfade
                if len(pitched) > 0:
                    result[time_index:time_index + len(pitched)] += pitched

                # Move to next syllable position with spacing
                time_index += int(samples_per_syllable * 1.2)  # 20% gap between syllables

            # Apply robotic effects
            # 1. Ring modulation
            t_full = np.arange(len(result)) / self.sample_rate
            carrier = np.sin(2 * np.pi * 2000 * t_full)  # 2kHz carrier
            result *= (1 + 0.5 * carrier)  # 50% modulation depth

            # 2. Frequency shifter
            D = np.fft.rfft(result)
            freqs = np.fft.rfftfreq(len(result))
            shift = 100  # Hz shift up
            shifted_freqs = freqs + shift / (self.sample_rate / 2)
            shifted_D = np.interp(freqs, shifted_freqs, np.abs(D))
            shifted_D = shifted_D * np.exp(1j * np.angle(D))
            result = np.fft.irfft(shifted_D)

            # 3. Bitcrushing effect for digital character
            bits = 8
            steps = 2**bits
            result = np.round(result * steps) / steps

            # Normalize
            max_val = np.max(np.abs(result))
            if max_val > 0:
                result /= max_val

            return result.astype(np.float32)


    def _apply_glitch_effect(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Apply glitch effects based on glitch_density parameter"""
        density = self.config.glitch_density
        result = audio.copy()

        # Calculate number of glitch points based on density
        num_glitches = int(len(audio) * density * 0.01)  # 1% max glitch points
        if num_glitches == 0:
            return result

        # Generate random glitch points
        glitch_points = np.random.randint(0, len(audio), num_glitches)

        for point in glitch_points:
            # Random glitch length between 100-1000 samples
            glitch_length = np.random.randint(100, 1000)
            if point + glitch_length > len(audio):
                continue

            # Apply random glitch effects
            effect_type = np.random.choice(['repeat', 'reverse', 'bitcrush', 'dropout'])

            if effect_type == 'repeat':
                # Repeat a small segment
                seg_length = glitch_length // 4
                segment = result[point:point + seg_length]
                for i in range(4):
                    if point + (i+1)*seg_length <= len(result):
                        result[point + i*seg_length:point + (i+1)*seg_length] = segment

            elif effect_type == 'reverse':
                # Reverse a segment
                result[point:point + glitch_length] = np.flip(
                    result[point:point + glitch_length]
                )

            elif effect_type == 'bitcrush':
                # Reduce bit depth effect
                segment = result[point:point + glitch_length]
                bits = np.random.randint(2, 8)
                steps = 2**bits
                segment = np.round(segment * steps) / steps
                result[point:point + glitch_length] = segment

            else:  # dropout
                # Random audio dropout
                result[point:point + glitch_length] = 0

        return result

    def _apply_haunting_effects(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """
        Apply haunting effects using high-quality reverb and spectral freeze.

        Uses `apply_high_quality_reverb` with parameters from `self.haunting.reverb`.
        """
        # Apply high-quality reverb
        reverb_params = ReverbParameters(**self.haunting.reverb.model_dump())
        reverbed = apply_high_quality_reverb(audio, self.sample_rate, reverb_params)

        # Ensure reverbed audio is trimmed/padded back to original length before spectral freeze mix
        # Note: apply_high_quality_reverb might return longer audio due to tail/pre-delay.
        # For mixing with spectral freeze, we need consistent length.
        original_length = len(audio)
        if len(reverbed) > original_length:
            reverbed = reverbed[:original_length]
        elif len(reverbed) < original_length:
            reverbed = np.pad(reverbed, (0, original_length - len(reverbed)), mode='constant')

        # Apply spectral freeze effect
        freeze_amount = self.haunting.spectral_freeze  # Using direct HauntingParameters
        if freeze_amount > 0:
            frozen = self._spectral_freeze(audio, freeze_amount)
            result = reverbed * (1 - freeze_amount) + frozen * freeze_amount
        else:
            result = reverbed

        return np.array(result, dtype=np.float32)


    def _spectral_freeze(
        self,
        audio: npt.NDArray[np.float32],
        freeze_amount: float
    ) -> npt.NDArray[np.float32]:
        """Apply spectral freeze effect"""
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


    def _normalize_audio(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Normalize audio to [-1.0, 1.0] range."""
        peak = np.max(np.abs(audio))
        if peak > 1.0:
            return audio / peak
        return audio


    def _apply_configured_delay(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Applies the complex delay effect if configured in self.config."""
        if self.config.delay_effect is not None and self.config.delay_effect.wet_dry_mix > 0:
            self.logger.debug("Applying complex delay effect...")
            try:
                delay_params = DelayParameters(**self.config.delay_effect.model_dump())
                processed_audio = apply_complex_delay(audio, self.sample_rate, delay_params)
                # Ensure audio is float32 after effect
                return np.array(processed_audio, dtype=np.float32)
            except Exception as delay_err:
                self.logger.error(f"Failed to apply complex delay effect: {delay_err}")
                return audio # Return original audio on error
        else:
            return audio # Return original if not configured or mix is zero
