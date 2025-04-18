import logging
import random
import librosa
import typing
from typing import Any, Optional, cast # Removed Protocol, runtime_checkable
from pathlib import Path
import soundfile as sf
import numpy as np
import numpy.typing as npt
from scipy import signal
# Type hint imports to avoid circular dependency at runtime
# Import config classes used at runtime
from ..config import PsalmConfig, HauntingParameters, LiturgicalMode
# Type hint imports to avoid circular dependency at runtime
if typing.TYPE_CHECKING:
    pass # No specific type hints needed here now
from .vox_dei import VoxDeiSynthesizer, VoxDeiSynthesisError
from .effects import (
    apply_high_quality_reverb, ReverbParameters,
    apply_complex_delay, DelayParameters,
    apply_chorus, ChorusParameters,
    apply_smooth_spectral_freeze, SpectralFreezeParameters,
    apply_refined_glitch, GlitchParameters,
    apply_saturation, SaturationParameters,
    apply_master_dynamics, MasterDynamicsParameters
)
# Removed unused import: from scipy.signal.windows import hann
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
    """
    Main synthesis engine for Robotic Psalms.

    Orchestrates vocal, pad, drone, and percussion synthesis, applies the
    configured effects chain, and mixes the final output.
    """
    # Pad Generation Constants
    _PAD_LFO_AMP_FREQ = 0.1
    _PAD_LFO_FILTER_FREQ = 0.15
    _PAD_LFO_HARMONICITY_FREQ = 0.08
    _PAD_OSC_GAIN = 0.3
    _PAD_FILTER_SEGMENT_LEN = 1024
    _PAD_FILTER_ORDER = 2
    _PAD_FILTER_MIN_CUTOFF_HZ = 500.0 # Use float
    _PAD_FILTER_MAX_CUTOFF_HZ = 8000.0 # Use float
    _PAD_FILTER_MIN_NORM_CUTOFF = 0.001 # Safety margin
    _PAD_FILTER_MAX_NORM_CUTOFF = 0.999 # Safety margin

    # Drone Generation Constants
    _DRONE_OSC_COUNT = 3
    _DRONE_BASE_FREQ_DIVISOR = 2  # Octave down
    _DRONE_LFO_AMP_FREQ = 0.05
    _DRONE_LFO_AMP_BASE = 0.6
    _DRONE_LFO_AMP_DEPTH = 0.4
    _DRONE_LFO_DETUNE_FREQ = 0.15
    _DRONE_LFO_DETUNE_MAX_HZ = 1.5
    _DRONE_LFO_DETUNE_BASE_FACTOR = 0.5 # Centered around 0.5
    _DRONE_LFO_DETUNE_DEPTH_FACTOR = 0.5 # Range [0, 1]


    def __init__(self, config: "PsalmConfig"): # Use string literal for type hint
        from ..config import PsalmConfig # Import locally to break circular dependency
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
        # --- Vocal Layering Implementation ---
        vocal_layers = []
        target_samples_for_layers = int(duration * self.sample_rate) # Pre-calculate target length for error case

        for i in range(self.config.num_vocal_layers):
            self.logger.debug(f"Synthesizing vocal layer {i+1}/{self.config.num_vocal_layers}")
            pitch_shift_semitones = 0.0
            timing_shift_samples = 0

            # Calculate variations (skip for the first layer)
            if i > 0:
                if self.config.layer_pitch_variation > 0:
                    pitch_shift_semitones = random.uniform(
                        -self.config.layer_pitch_variation, self.config.layer_pitch_variation
                    )
                    self.logger.debug(f"  Layer {i+1} pitch shift: {pitch_shift_semitones:.2f} semitones")
                if self.config.layer_timing_variation_ms > 0:
                    timing_shift_ms = random.uniform(
                        -self.config.layer_timing_variation_ms, self.config.layer_timing_variation_ms
                    )
                    timing_shift_samples = int(timing_shift_ms / 1000.0 * self.sample_rate)
                    self.logger.debug(f"  Layer {i+1} timing shift: {timing_shift_ms:.2f} ms ({timing_shift_samples} samples)")

            # Synthesize layer
            try:
                raw_layer, tts_sample_rate = self.vox_dei.synthesize_text(text)

                # Resample to engine sample rate if needed
                if tts_sample_rate != self.sample_rate:
                    self.logger.debug(f"  Resampling layer {i+1} from {tts_sample_rate}Hz to {self.sample_rate}Hz")
                    num_samples_target = int(len(raw_layer) * self.sample_rate / tts_sample_rate)
                    layer_audio = signal.resample(raw_layer, num_samples_target)
                else:
                    layer_audio = raw_layer # Keep original type for now

            except VoxDeiSynthesisError as e:
                self.logger.error(f"Vocal synthesis failed for layer {i+1}: {e}")
                layer_audio = np.zeros(target_samples_for_layers, dtype=np.float32)

            # Apply pitch shift
            # Ensure layer_audio is float32 before pitch shift
            # Explicitly cast to reassure Pylance before using numpy methods
            layer_audio = cast(npt.NDArray[Any], layer_audio).astype(np.float32)

            # Apply pitch shift using helper
            if abs(pitch_shift_semitones) > 1e-6: # Avoid processing if shift is negligible
                layer_audio = self._apply_pitch_shift(layer_audio, pitch_shift_semitones, layer_index=i+1)
            # Apply timing shift using helper
            if timing_shift_samples != 0:
                layer_audio = self._apply_timing_shift(layer_audio, timing_shift_samples)
            vocal_layers.append(layer_audio)

        # Align and mix layers
        if not vocal_layers:
             # Should not happen if num_vocal_layers >= 1, but handle defensively
            vocals = np.zeros(target_samples_for_layers, dtype=np.float32)
        else:
            max_len = max(len(layer) for layer in vocal_layers)
            aligned_layers = []
            for layer in vocal_layers:
                if len(layer) < max_len:
                    aligned_layers.append(np.pad(layer, (0, max_len - len(layer)), mode='constant'))
                else:
                    aligned_layers.append(layer[:max_len]) # Trim if longer

            # Sum layers
            mixed_vocals = np.sum(np.array(aligned_layers), axis=0)

            # Normalize the mixed result (using existing helper)
            vocals = self._normalize_audio(mixed_vocals)
            self.logger.debug(f"Mixed {len(vocal_layers)} vocal layers.")
        # --- End Vocal Layering Implementation ---

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

        # Apply refined glitch effect if configured
        if self.config.glitch_effect is not None:
            self.logger.debug("Applying refined glitch effect...")
            try:
                vocals = apply_refined_glitch(vocals, self.sample_rate, self.config.glitch_effect)
                pads = apply_refined_glitch(pads, self.sample_rate, self.config.glitch_effect)
                drones = apply_refined_glitch(drones, self.sample_rate, self.config.glitch_effect)
            except Exception as glitch_err:
                self.logger.error(f"Failed to apply refined glitch effect: {glitch_err}")
                # Continue without glitch if effect fails
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

        # Apply saturation effect if configured
        combined = self._apply_configured_saturation(combined)

        # Apply complex delay effect if configured
        # Apply chorus effect if configured
        combined = self._apply_configured_chorus(combined)

        combined = self._apply_configured_delay(combined)
        # Apply master dynamics if configured (final step)
        if self.config.master_dynamics is not None:
            self.logger.debug("Applying master dynamics...")
            try:
                # Assuming config.master_dynamics is already a validated Pydantic model instance
                master_params = self.config.master_dynamics
                combined = apply_master_dynamics(combined, self.sample_rate, master_params)
                # Ensure audio is float32 after effect
                combined = np.array(combined, dtype=np.float32)
            except Exception as master_dyn_err:
                self.logger.error(f"Failed to apply master dynamics: {master_dyn_err}")
                # Continue with un-effected audio on error

        return SynthesisResult(
            vocals=vocals.astype(np.float32),
            pads=pads.astype(np.float32),
            percussion=percussion.astype(np.float32),
            drones=drones.astype(np.float32),
            combined=combined.astype(np.float32),
            sample_rate=self.sample_rate
        )

    def _mix_components(self, vocals, pads, percussion, drones):
        """
        Mix all audio components together according to configured levels.

        Applies mix levels before padding components to the same length and summing.
        """
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
    def _apply_time_varying_lowpass(
        self,
        audio: npt.NDArray[np.float32],
        lfo_filter: npt.NDArray[np.float32],
        sample_rate: int,
        segment_len: int = _PAD_FILTER_SEGMENT_LEN, # Access class constant directly
        filter_order: int = _PAD_FILTER_ORDER,     # Access class constant directly
        min_cutoff_hz: float = _PAD_FILTER_MIN_CUTOFF_HZ, # Access class constant directly
        max_cutoff_hz: float = _PAD_FILTER_MAX_CUTOFF_HZ, # Access class constant directly
        min_norm_cutoff: float = _PAD_FILTER_MIN_NORM_CUTOFF, # Access class constant directly
        max_norm_cutoff: float = _PAD_FILTER_MAX_NORM_CUTOFF, # Access class constant directly
    ) -> npt.NDArray[np.float32]:
        """Applies a time-varying low-pass filter using segmented processing.

        The filter cutoff frequency is modulated over time based on the provided
        LFO signal (`lfo_filter`). The audio is processed in segments to
        efficiently apply different filter parameters over time. The cutoff
        frequency for each segment is determined by the average LFO value
        within that segment, mapped exponentially between `min_cutoff_hz` and
        `max_cutoff_hz`. A Butterworth filter is used.

        Args:
            audio: The input audio signal.
            lfo_filter: Low-frequency oscillator signal (range 0.0 to 1.0)
                        controlling the filter cutoff modulation.
            sample_rate: The sample rate of the audio.
            segment_len: The length of each processing segment in samples.
            filter_order: The order of the Butterworth filter.
            min_cutoff_hz: The minimum cutoff frequency in Hz.
            max_cutoff_hz: The maximum cutoff frequency in Hz.
            min_norm_cutoff: The minimum normalized cutoff frequency (safety clamp).
            max_norm_cutoff: The maximum normalized cutoff frequency (safety clamp).

        Returns:
            The audio signal with the time-varying low-pass filter applied.

        Raises:
            ValueError: If filter design fails (logged, returns unfiltered segment).
        """
        num_samples = len(audio)
        filtered_audio = np.zeros_like(audio)
        nyquist = 0.5 * sample_rate
        num_segments = num_samples // segment_len
        last_norm_cutoff = min_norm_cutoff # Initialize for the remainder block

        log_min_cutoff = np.log(min_cutoff_hz)
        log_max_cutoff = np.log(max_cutoff_hz)

        for i in range(num_segments):
            start = i * segment_len
            end = start + segment_len
            segment = audio[start:end]

            # Calculate average cutoff for this segment using exponential mapping
            segment_lfo_filter_avg = np.mean(lfo_filter[start:end])
            cutoff_freq_segment = np.exp(log_min_cutoff + segment_lfo_filter_avg * (log_max_cutoff - log_min_cutoff))

            norm_cutoff = cutoff_freq_segment / nyquist
            # Clamp normalized cutoff frequency
            norm_cutoff = np.clip(norm_cutoff, min_norm_cutoff, max_norm_cutoff)
            last_norm_cutoff = norm_cutoff # Store for the remainder

            try:
                sos = signal.butter(filter_order, norm_cutoff, btype='low', output='sos')
                filtered_segment = signal.sosfilt(sos, segment)
                filtered_audio[start:end] = filtered_segment
            except ValueError as filter_err:
                 self.logger.error(f"Failed to apply filter segment {i} (cutoff={norm_cutoff}): {filter_err}")
                 filtered_audio[start:end] = segment # Use unfiltered segment on error

        # Handle any remaining samples
        remainder_start = num_segments * segment_len
        if remainder_start < num_samples:
            segment = audio[remainder_start:]
            try:
                 # Use the cutoff from the last full segment for the remainder
                 sos = signal.butter(filter_order, last_norm_cutoff, btype='low', output='sos')
                 filtered_segment = signal.sosfilt(sos, segment)
                 filtered_audio[remainder_start:] = filtered_segment
            except ValueError as filter_err:
                 self.logger.error(f"Failed to apply final filter segment (cutoff={last_norm_cutoff}): {filter_err}")
                 filtered_audio[remainder_start:] = segment # Use unfiltered segment on error

        return filtered_audio





    def _apply_haunting_effects(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """
        Apply haunting effects using high-quality reverb and optional spectral freeze.

        Uses `apply_high_quality_reverb` with parameters from `self.haunting.reverb`.
        Conditionally applies `apply_smooth_spectral_freeze` based on `self.haunting.spectral_freeze`.
        Ensures output length matches input length after reverb application.
        """
        # Apply high-quality reverb
        reverb_params = ReverbParameters(**self.haunting.reverb.model_dump())
        reverbed = apply_high_quality_reverb(audio, self.sample_rate, reverb_params)

        # Ensure reverbed audio is trimmed/padded back to original length before spectral freeze mix
        # Note: apply_high_quality_reverb might return longer audio due to tail/pre-delay.
        # For mixing with spectral freeze, we need consistent length.
        # Ensure the reverbed audio matches the original length before mixing or further processing.
        # Reverb might add tail or pre-delay, changing the length.
        original_length = len(audio)
        if len(reverbed) > original_length:
            reverbed = reverbed[:original_length]
        elif len(reverbed) < original_length:
            reverbed = np.pad(reverbed, (0, original_length - len(reverbed)), mode='constant')

        # Apply spectral freeze effect if configured
        if isinstance(self.haunting.spectral_freeze, SpectralFreezeParameters):
            self.logger.debug("Applying smooth spectral freeze effect...")
            result = apply_smooth_spectral_freeze(
                reverbed, self.sample_rate, self.haunting.spectral_freeze
            )
        else:
            result = reverbed # No freeze configured

        # Assuming 'apply_smooth_spectral_freeze' and 'reverbed' return float32 numpy arrays
        return result


    def _generate_pads(self, duration: float) -> npt.NDArray[np.float32]:
        """Generate evolving synthesizer pads with modulated harmonicity and filter.

        This method creates ambient pad sounds by summing oscillators based on the
        current musical mode's frequencies. The timbre evolves through:
        1.  **Modulated Harmonicity:** An LFO (`_PAD_LFO_HARMONICITY_FREQ`) varies
            the mix between sine and sawtooth waveforms for each oscillator,
            scaled by `config.celestial_harmonicity`.
        2.  **Time-Varying Filter:** A low-pass filter is applied using the
            `_apply_time_varying_lowpass` helper method. The filter's cutoff
            frequency is modulated by another LFO (`_PAD_LFO_FILTER_FREQ`).
        3.  **Amplitude Modulation:** An overall amplitude LFO (`_PAD_LFO_AMP_FREQ`)
            is applied to the final pad sound.

        Internal constants (`_PAD_*`) control LFO frequencies, oscillator gain,
        and filter parameters. The final output is normalized.

        Args:
            duration: The desired duration of the pads in seconds.

        Returns:
            An array containing the generated pad audio signal.
        """
        num_samples = int(duration * self.sample_rate)
        t = np.arange(num_samples) / self.sample_rate

        # Get frequencies for current mode
        frequencies = self.mode_frequencies[self.config.mode]

        pad = np.zeros(num_samples, dtype=np.float32)

        # LFOs for modulation (using class constants)
        lfo_amp = 0.7 + 0.3 * np.sin(2 * np.pi * self._PAD_LFO_AMP_FREQ * t)
        lfo_filter = 0.5 + 0.5 * np.sin(2 * np.pi * self._PAD_LFO_FILTER_FREQ * t) # Range [0, 1]
        lfo_harmonicity = 0.5 + 0.5 * np.sin(2 * np.pi * self._PAD_LFO_HARMONICITY_FREQ * t) # Range [0, 1]

        # Base harmonicity from config, modulated by LFO
        base_harmonicity = self.config.celestial_harmonicity
        harmonicity = base_harmonicity * lfo_harmonicity # Effective range [0, base_harmonicity]

        # Generate base waveform by summing oscillators
        for freq in frequencies:
            # Mix sine and sawtooth waves based on time-varying harmonicity
            sine = np.sin(2 * np.pi * freq * t)
            saw = 2 * (t * freq - np.floor(0.5 + t * freq)) # Basic sawtooth

            # Ensure harmonicity is broadcastable if needed (should be same length as t)
            wave = sine * (1 - harmonicity) + saw * harmonicity
            pad += wave * self._PAD_OSC_GAIN # Use class constant for gain

        # Apply Time-Varying Low-Pass Filter using helper function
        pad = self._apply_time_varying_lowpass(
            audio=pad,
            lfo_filter=lfo_filter,
            sample_rate=self.sample_rate
            # Uses default constants defined in the class for other parameters
        )

        # Apply overall amplitude LFO
        pad *= lfo_amp

        # Normalize final output
        pad = self._normalize_audio(pad) # Use helper function

        return pad.astype(np.float32)

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

        return hit.astype(np.float32) # Cast to ensure correct return type

    def _generate_drones(self, duration: float) -> npt.NDArray[np.float32]:
        """Generate rich, evolving drones using multiple detuned oscillators.

        This method creates drone sounds based on the root frequency of the current
        musical mode (shifted down by `_DRONE_BASE_FREQ_DIVISOR`). It uses
        `_DRONE_OSC_COUNT` sawtooth oscillators. The richness and evolution come from:
        1.  **Detuning:** Oscillators are detuned relative to each other. The amount
            of detuning is modulated by a slow LFO (`_DRONE_LFO_DETUNE_FREQ`,
            `_DRONE_LFO_DETUNE_MAX_HZ`).
        2.  **Amplitude Modulation:** The overall amplitude is modulated by another
            slow LFO (`_DRONE_LFO_AMP_FREQ`).

        Internal constants (`_DRONE_*`) control the oscillator count, LFO parameters,
        and detuning amounts. The final output is normalized.

        Args:
            duration: The desired duration of the drone in seconds.

        Returns:
            An array containing the generated drone audio signal.
        """
        num_samples = int(duration * self.sample_rate)
        t = np.arange(num_samples) / self.sample_rate

        # Base frequency from mode, shifted down
        base_freq = self.mode_frequencies[self.config.mode][0] / self._DRONE_BASE_FREQ_DIVISOR

        # LFOs for modulation
        lfo_amp_freq = self._DRONE_LFO_AMP_FREQ
        lfo_detune_freq = self._DRONE_LFO_DETUNE_FREQ
        max_detune_hz = self._DRONE_LFO_DETUNE_MAX_HZ

        # Amplitude LFO (slow swell)
        lfo_amp = self._DRONE_LFO_AMP_BASE + self._DRONE_LFO_AMP_DEPTH * np.sin(
            2 * np.pi * lfo_amp_freq * t
        )
        # Detuning Amount LFO (slow variation, range [0, max_detune_hz])
        lfo_detune_amount = (
            self._DRONE_LFO_DETUNE_BASE_FACTOR
            + self._DRONE_LFO_DETUNE_DEPTH_FACTOR
            * np.sin(2 * np.pi * lfo_detune_freq * t)
        ) * max_detune_hz

        drone = np.zeros(num_samples, dtype=np.float32)
        num_oscillators = self._DRONE_OSC_COUNT

        for i in range(num_oscillators):
            # Calculate detuning factor for this oscillator, centered around 0.
            # Example for 3 oscillators: i=0 -> -1.0, i=1 -> 0.0, i=2 -> +1.0
            detune_factor = i - (num_oscillators - 1) / 2.0
            detune_offset = lfo_detune_amount * detune_factor

            # Calculate instantaneous frequency for this oscillator
            osc_freq = base_freq + detune_offset

            # Generate sawtooth wave using scipy.signal.sawtooth.
            # Note: Providing a time-varying frequency array `osc_freq` to the phase
            # calculation `2 * np.pi * osc_freq * t` effectively creates frequency
            # modulation (FM) of the phase, resulting in dynamic timbre shifts.
            saw_wave = signal.sawtooth(2 * np.pi * osc_freq * t)

            # Add to the mix, dividing by num_oscillators to prevent immediate clipping
            drone += saw_wave / num_oscillators

        # Apply overall amplitude LFO
        drone *= lfo_amp

        # Normalize final output
        drone = self._normalize_audio(drone)

        return drone.astype(np.float32)

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

    # --- Helper Methods for Effects ---

    def _apply_pitch_shift(
        self,
        audio: npt.NDArray[np.float32],
        semitones: float,
        layer_index: Optional[int] = None # Optional for logging context
    ) -> npt.NDArray[np.float32]:
        """Applies pitch shifting using librosa.

        Args:
            audio: The input audio array (must be float32).
            semitones: The number of semitones to shift.
            layer_index: Optional index of the layer for logging purposes.

        Returns:
            The pitch-shifted audio array, or the original if shifting fails.
        """
        try:
            shifted_audio = librosa.effects.pitch_shift(
                y=audio, sr=self.sample_rate, n_steps=semitones
            )
            return shifted_audio
        except Exception as pitch_err:
            log_prefix = f"layer {layer_index}" if layer_index is not None else "audio"
            self.logger.error(f"Pitch shift failed for {log_prefix}: {pitch_err}")
            return audio # Continue with unshifted audio on error

    def _apply_timing_shift(
        self,
        audio: npt.NDArray[np.float32],
        shift_samples: int
    ) -> npt.NDArray[np.float32]:
        """Applies a timing shift to the audio using padding and slicing.

        Args:
            audio: The input audio array.
            shift_samples: The number of samples to shift.
                           Positive shifts earlier (pads start, trims end).
                           Negative shifts later (pads end, trims start).

        Returns:
            The time-shifted audio array.
        """
        current_len = len(audio)
        if shift_samples > 0: # Shift earlier (pad start, trim end)
            pad_width = (shift_samples, 0)
            shifted_audio = np.pad(audio, pad_width, mode='constant')
            return shifted_audio[:current_len] # Trim end to original length
        elif shift_samples < 0: # Shift later (pad end, trim start)
            shift_abs = abs(shift_samples)
            pad_width = (0, shift_abs)
            shifted_audio = np.pad(audio, pad_width, mode='constant')
            return shifted_audio[shift_abs:shift_abs + current_len] # Trim start
        else: # No shift
            return audio

    def _apply_configured_saturation(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Applies the saturation effect if configured in self.config."""
        if self.config.saturation_effect is not None and self.config.saturation_effect.mix > 0:
            self.logger.debug("Applying saturation effect...")
            try:
                saturation_params = SaturationParameters(**self.config.saturation_effect.model_dump())
                processed_audio = apply_saturation(audio, self.sample_rate, saturation_params)
                # Ensure audio is float32 after effect
                return np.array(processed_audio, dtype=np.float32)
            except Exception as saturation_err:
                self.logger.error(f"Failed to apply saturation effect: {saturation_err}")
                return audio # Return original audio on error
        else:
            return audio # Return original if not configured or mix is zero

    def _apply_configured_chorus(
        self,
        audio: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Applies the chorus effect if configured in self.config."""
        if self.config.chorus_params is not None and self.config.chorus_params.wet_dry_mix > 0:
            self.logger.debug("Applying chorus effect...")
            try:
                chorus_params = ChorusParameters(**self.config.chorus_params.model_dump())
                processed_audio = apply_chorus(audio, self.sample_rate, chorus_params)
                # Ensure audio is float32 after effect
                return np.array(processed_audio, dtype=np.float32)
            except Exception as chorus_err:
                self.logger.error(f"Failed to apply chorus effect: {chorus_err}")
                return audio # Return original audio on error
        else:
            return audio # Return original if not configured or mix is zero

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
