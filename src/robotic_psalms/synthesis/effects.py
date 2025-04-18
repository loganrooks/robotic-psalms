"""Audio effect implementations for Robotic Psalms."""

import numpy as np
from pydantic import BaseModel, Field, ConfigDict, model_validator
from pedalboard import Pedalboard, Delay, Reverb #type: ignore # Importing pedalboard effects
from scipy import signal # Added for filters
import math # Added for RBJ filter calculations
from scipy.interpolate import interp1d # Used for formant shifting spectral warping
import pyworld as pw # Use pw alias for formant shifting
import librosa # Added for spectral freeze
from typing import Literal
from typing import Literal, cast
import random # For glitch probability
from pedalboard import Distortion, LowpassFilter, Compressor, Limiter # Added for saturation and dynamics
# Removed module-level seed

# Pedalboard's Reverb defaults: room_size=0.5, damping=0.5, wet_level=0.33, dry_level=0.4, width=1.0, freeze_mode=0.0
# We'll map our params where possible. Pedalboard doesn't have direct decay_time, pre_delay, diffusion.
# We'll use room_size for decay_time (larger room = longer decay), wet_level/dry_level for wet_dry_mix, and damping.
# Pre-delay and diffusion are not directly available in pedalboard.Reverb, so we'll omit them for this minimal implementation
# or map them conceptually if possible (e.g., width might relate to diffusion).
# For minimalism, let's stick to what maps directly: room_size, damping, wet/dry.

# Constants for decay_time to room_size mapping
MIN_DECAY_S = 0.1
MAX_DECAY_S = 10.0
MIN_ROOM_SIZE = 0.1
MAX_ROOM_SIZE = 1.0

class ReverbParameters(BaseModel):
    """Parameters for the high-quality reverb effect."""
    decay_time: float = Field(..., ge=0.0, description="Conceptual reverb decay time (maps to room size). Larger values mean longer reverb.")
    pre_delay: float = Field(..., ge=0.0, description="Pre-delay in seconds before reverb starts. (Note: Not directly used by pedalboard.Reverb)")
    diffusion: float = Field(..., ge=0.0, le=1.0, description="Diffusion of the reverb tail. (Note: Not directly used by pedalboard.Reverb)")
    damping: float = Field(..., ge=0.0, le=1.0, description="High-frequency damping of the reverb tail (0=none, 1=max).")
    wet_dry_mix: float = Field(..., ge=0.0, le=1.0, description="Mix between wet (reverb) and dry (original) signal (0=dry, 1=wet).")

    model_config = ConfigDict(extra='forbid') # Ensure no unexpected parameters are passed


class DelayParameters(BaseModel):
    """Parameters for the complex delay effect."""
    delay_time_ms: float = Field(..., ge=0.0, description="Delay time in milliseconds.")
    feedback: float = Field(..., ge=0.0, le=1.0, description="Feedback amount (0.0 to 1.0).")
    wet_dry_mix: float = Field(..., ge=0.0, le=1.0, description="Mix between wet (delay) and dry (original) signal (0=dry, 1=wet).")
    stereo_spread: float = Field(..., ge=0.0, le=1.0, description="Stereo spread of the delay taps (0.0 to 1.0). [IGNORED by current pedalboard.Delay implementation]")
    lfo_rate_hz: float = Field(..., ge=0.0, description="Rate of the Low-Frequency Oscillator (LFO) modulating the delay time, in Hz. [IGNORED by current pedalboard.Delay implementation]")
    lfo_depth: float = Field(..., ge=0.0, le=1.0, description="Depth of the LFO modulation (0.0 to 1.0). [IGNORED by current pedalboard.Delay implementation]")
    filter_low_hz: float = Field(..., ge=0.0, description="Low-cut filter frequency for the feedback path, in Hz. [IGNORED by current pedalboard.Delay implementation]")
    filter_high_hz: float = Field(..., ge=0.0, description="High-cut filter frequency for the feedback path, in Hz. [IGNORED by current pedalboard.Delay implementation]")

    model_config = ConfigDict(extra='forbid')

    @model_validator(mode='after')
    def check_filter_range(self) -> 'DelayParameters':
        """Validates that filter_low_hz is not greater than filter_high_hz."""
        if self.filter_low_hz > self.filter_high_hz:
            raise ValueError("filter_low_hz cannot be greater than filter_high_hz")
        return self


class FormantShiftParameters(BaseModel):
    """Parameters for the robust formant shifting effect."""
    shift_factor: float = Field(..., gt=0.0, description="Factor by which to shift formants. >1 shifts up, <1 shifts down.")

    model_config = ConfigDict(extra='forbid')


class ResonantFilterParameters(BaseModel):
    """Parameters for the resonant low-pass filter effect (RBJ Biquad implementation)."""
    cutoff_hz: float = Field(..., gt=0.0, description="Cutoff frequency in Hz.")
    q: float = Field(..., gt=0.0, description="Resonance factor (Q). Higher values mean a sharper peak at the cutoff frequency.") # Renamed from resonance

    model_config = ConfigDict(extra='forbid')


class BandpassFilterParameters(BaseModel):
    """Parameters for the bandpass filter effect (Butterworth implementation)."""
    center_hz: float = Field(..., gt=0.0, description="Center frequency of the bandpass filter in Hz.")
    q: float = Field(..., gt=0.0, description="Quality factor (Q) of the bandpass filter. Higher values mean a narrower bandwidth.")
    order: int = Field(2, gt=0, description="Order of the Butterworth filter. Higher orders provide steeper rolloff.") # Added order parameter

    model_config = ConfigDict(extra='forbid')
    # Removed validator check_filter_range, handled in apply_bandpass_filter




class ChorusParameters(BaseModel):
    """Parameters for the chorus effect."""
    rate_hz: float = Field(..., gt=0.0, description="Rate of the LFO modulating the delay time in Hz.")
    depth: float = Field(..., ge=0.0, le=1.0, description="Depth of the LFO modulation (0.0 to 1.0).")
    delay_ms: float = Field(..., gt=0.0, description="Base delay time in milliseconds.")
    feedback: float = Field(..., ge=0.0, le=1.0, description="Feedback amount (0.0 to 1.0).")
    num_voices: int = Field(..., ge=2, description="Number of chorus voices. [Note: Ignored by current pedalboard.Chorus implementation]")
    wet_dry_mix: float = Field(..., ge=0.0, le=1.0, description="Mix between wet (chorus) and dry (original) signal (0=dry, 1=wet).")

    model_config = ConfigDict(extra='forbid')


class SpectralFreezeParameters(BaseModel):
    """Parameters for the smooth spectral freeze effect."""
    freeze_point: float = Field(..., ge=0.0, le=1.0, description="Normalized time point (0.0 to 1.0) in the audio to capture the spectrum from.")
    blend_amount: float = Field(..., ge=0.0, le=1.0, description="Blend between the original and frozen spectrum (0.0=original, 1.0=frozen).")
    fade_duration: float = Field(..., ge=0.0, description="Duration in seconds over which to fade the blend amount.")

    model_config = ConfigDict(extra='forbid')



class GlitchParameters(BaseModel):
    """Parameters for the refined glitch effect."""
    glitch_type: Literal['repeat', 'stutter', 'tape_stop', 'bitcrush'] = Field(..., description="Type of glitch effect to apply.")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Probability (0.0 to 1.0) of applying the glitch to any given chunk.")
    chunk_size_ms: float = Field(..., gt=0.0, description="Size of audio chunks affected by the glitch in milliseconds.")
    # Type-specific parameters
    repeat_count: int = Field(..., ge=2, description="Number of times to repeat a chunk for 'repeat' or 'stutter' glitches (minimum 2).") # Updated validation to ge=2
    tape_stop_speed: float = Field(..., gt=0.0, lt=1.0, description="Final speed factor for the 'tape_stop' effect (e.g., 0.5 for half speed). Speed ramps down towards this value. Must be > 0.0 and < 1.0.") # Updated validation to lt=1.0
    bitcrush_depth: int = Field(..., ge=1, le=16, description="Target bit depth for the 'bitcrush' effect (1 to 16).")
    bitcrush_rate_factor: float = Field(..., ge=0.0, le=1.0, description="Controls sample rate reduction via sample holding. 1.0 = no reduction, 0.0 = max reduction.")
    model_config = ConfigDict(extra='forbid')



class SaturationParameters(BaseModel):
    """Parameters for the saturation/distortion effect."""
    drive: float = Field(..., ge=0.0, description="Amount of drive/gain applied before saturation. Higher values increase distortion.")
    tone: float = Field(..., ge=0.0, le=1.0, description="Tone control (0.0=dark, 1.0=bright). Maps to a lowpass filter cutoff frequency.")
    mix: float = Field(..., ge=0.0, le=1.0, description="Wet/dry mix (0.0=dry, 1.0=wet).")

    model_config = ConfigDict(extra='forbid')



class MasterDynamicsParameters(BaseModel):
    """Parameters for the master dynamics processing (compressor, limiter)."""
    enable_compressor: bool = Field(False, description="Enable the master compressor.")
    compressor_threshold_db: float = Field(-20.0, description="Compressor threshold in dB.")
    compressor_ratio: float = Field(4.0, ge=1.0, description="Compressor ratio (>= 1.0).")
    compressor_attack_ms: float = Field(5.0, gt=0.0, description="Compressor attack time in milliseconds (> 0.0).")
    compressor_release_ms: float = Field(100.0, gt=0.0, description="Compressor release time in milliseconds (> 0.0).")
    enable_limiter: bool = Field(True, description="Enable the master limiter.")
    limiter_threshold_db: float = Field(-1.0, le=0.0, description="Limiter threshold in dB (<= 0.0).")

    model_config = ConfigDict(extra='forbid')
# --- Effect Functions ---

def apply_high_quality_reverb(audio: np.ndarray, sample_rate: int, params: ReverbParameters) -> np.ndarray:
    """
    Applies a high-quality reverb effect using pedalboard.Reverb.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of ReverbParameters containing effect settings.

    Returns:
        The processed audio signal with reverb applied (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32) # Return float32 for consistency

    # Map ReverbParameters to pedalboard.Reverb parameters
    normalized_decay = np.clip((params.decay_time - MIN_DECAY_S) / (MAX_DECAY_S - MIN_DECAY_S), 0.0, 1.0)
    room_size = normalized_decay * (MAX_ROOM_SIZE - MIN_ROOM_SIZE) + MIN_ROOM_SIZE

    wet_level = params.wet_dry_mix
    dry_level = 1.0 - params.wet_dry_mix
    width = np.clip(params.diffusion, 0.0, 1.0) # Map diffusion to width

    reverb_effect = Reverb(
        room_size=room_size,
        damping=params.damping,
        wet_level=wet_level,
        dry_level=dry_level,
        width=width
    )

    # Pedalboard expects float32
    audio_float32 = audio.astype(np.float32)

    # Simulate pre-delay by adding silence (if any)
    pre_delay_samples = int(params.pre_delay * sample_rate)
    if pre_delay_samples > 0:
        padding_shape = (pre_delay_samples,) + audio_float32.shape[1:] if audio_float32.ndim > 1 else (pre_delay_samples,)
        padding = np.zeros(padding_shape, dtype=np.float32)
        audio_padded = np.concatenate((padding, audio_float32), axis=0)
    else:
        audio_padded = audio_float32

    # Apply effect using a Pedalboard instance
    reverb_board = Pedalboard([reverb_effect])
    reverberated_signal = reverb_board(audio_padded, sample_rate=sample_rate)

    # Ensure output shape matches input channel count if possible
    # Output length will be longer due to reverb tail and pre-delay padding
    if audio.ndim == 1 and reverberated_signal.ndim == 2 and reverberated_signal.shape[1] == 1:
        reverberated_signal = reverberated_signal.flatten()
    elif audio.ndim == 2 and reverberated_signal.ndim == 1 and audio.shape[1] == 1:
        # If input was stereo (shape like (n, 1)) and output is mono (shape like (m,)), reshape output
        reverberated_signal = reverberated_signal.reshape(-1, 1)
    # Note: If input is stereo (n, 2) and output is mono (m,), this code doesn't handle it.
    # Pedalboard.Reverb typically preserves channel count, so this is unlikely.

    return reverberated_signal.astype(np.float32) # Return float32


def apply_complex_delay(audio: np.ndarray, sample_rate: int, params: DelayParameters) -> np.ndarray:
    """
    Applies a complex delay effect using pedalboard.Delay.
    Focuses on delay_time, feedback, and mix. Other parameters are ignored.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of DelayParameters containing effect settings.

    Returns:
        The processed audio signal with delay applied (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32)

    delay_seconds = params.delay_time_ms / 1000.0

    # Instantiate the delay effect
    delay_effect = Delay(
        delay_seconds=delay_seconds,
        feedback=params.feedback,
        mix=params.wet_dry_mix # pedalboard.Delay uses 'mix' (0=dry, 1=wet)
    )

    # Create a Pedalboard instance with the delay effect
    board = Pedalboard([delay_effect])

    # Process the audio (pedalboard expects float32)
    audio_float32 = audio.astype(np.float32)
    delayed_signal = board(audio_float32, sample_rate=sample_rate)

    # Ensure output shape matches input channel count if possible
    if audio.ndim == 1 and delayed_signal.ndim == 2 and delayed_signal.shape[1] == 1:
        delayed_signal = delayed_signal.flatten()
    elif audio.ndim == 2 and delayed_signal.ndim == 1 and audio.shape[1] == 1:
         delayed_signal = delayed_signal.reshape(-1, 1)

    return delayed_signal.astype(np.float32) # Return float32


def _apply_formant_shift_mono(x: np.ndarray, fs: int, shift_factor: float) -> np.ndarray:
    """Helper function to apply formant shift to a mono float64 signal using WORLD."""
    x = np.ascontiguousarray(x, dtype=np.float64) # Ensure input is float64 and contiguous

    # --- WORLD Analysis ---
    # Use default DIO/Harvest parameters for F0 estimation
    f0, t = pw.dio(x, fs) # type: ignore # Fundamental frequency
    f0 = pw.stonemask(x, f0, t, fs) # type: ignore # Refine F0
    sp = pw.cheaptrick(x, f0, t, fs) # type: ignore # Spectral envelope
    ap = pw.d4c(x, f0, t, fs) # type: ignore # Aperiodicity

    # --- Warp Spectral Envelope ---
    sp_warped = _warp_spectral_envelope(sp, fs, shift_factor)

    # --- WORLD Synthesis ---
    # Ensure arrays are C-contiguous double for synthesis
    f0_cont = np.ascontiguousarray(f0, dtype=np.float64)
    sp_warped_cont = np.ascontiguousarray(sp_warped, dtype=np.float64)
    ap_cont = np.ascontiguousarray(ap, dtype=np.float64)

    y = pw.synthesize(f0_cont, sp_warped_cont, ap_cont, fs) # type: ignore

    # Ensure output length matches input length
    if len(y) > len(x):
        y = y[:len(x)]
    elif len(y) < len(x):
        padding = np.zeros(len(x) - len(y), dtype=np.float64)
        y = np.concatenate((y, padding))

    return y.astype(np.float64) # Return float64 as per pyworld's output


def _warp_spectral_envelope(sp: np.ndarray, fs: int, formant_shift_ratio: float) -> np.ndarray:
    """
    Warps the spectral envelope frequency axis using linear interpolation.
    Used internally by apply_robust_formant_shift.

    Args:
        sp: Spectral envelope from pyworld (frames x frequency_bins), float64.
        fs: Sample rate.
        formant_shift_ratio: Factor to shift formants (>1 shifts up, <1 shifts down).

    Returns:
        Warped spectral envelope, float64.
    """
    num_frames, num_bins = sp.shape
    fft_size = (num_bins - 1) * 2 # Calculate FFT size from number of bins

    original_freqs = np.linspace(0, fs / 2, num_bins) # Frequencies corresponding to the bins
    # Frequencies from which to sample the *original* envelope to create the *warped* envelope
    warped_freqs = original_freqs / formant_shift_ratio

    sp_warped = np.zeros_like(sp) # Initialize warped envelope

    # Iterate through each frame (time slice) of the spectrogram
    for i in range(num_frames):
        # Create an interpolation function based on the original envelope's values at the warped frequencies
        interp_func = interp1d(
            warped_freqs, sp[i], kind='linear', bounds_error=False,
            # Use 'extrapolate' to handle frequencies outside the original range
            # This uses the edge values of the original envelope for extrapolation
            fill_value="extrapolate" # type: ignore # Pylance doesn't recognize 'extrapolate' string
        )
        # Evaluate the interpolation function at the original frequencies
        # This maps the values from the warped frequency scale back onto the original frequency scale
        sp_warped[i] = interp_func(original_freqs)

    # Ensure non-negative values (numerical precision might cause small negatives)
    # Use a small positive floor based on pyworld examples/recommendations
    sp_warped[sp_warped < 1e-16] = 1e-16

    return sp_warped.astype(np.float64) # Ensure output is float64


def apply_robust_formant_shift(audio: np.ndarray, sample_rate: int, params: FormantShiftParameters) -> np.ndarray:
    """
    Applies formant shifting while preserving pitch using the WORLD vocoder.
    Handles mono or stereo input.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of FormantShiftParameters containing effect settings.

    Returns:
        The processed audio signal with formants shifted (float64).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float64)

    # If shift_factor is 1.0, no change is needed. Return a copy.
    if np.isclose(params.shift_factor, 1.0):
        return audio.astype(np.float64).copy() # Return float64 copy

    original_dtype = audio.dtype # Keep original dtype info if needed later
    audio_float64 = audio.astype(np.float64)

    if audio_float64.ndim == 1: # Mono input
        shifted_audio = _apply_formant_shift_mono(audio_float64, sample_rate, params.shift_factor)
    elif audio_float64.ndim == 2: # Stereo input
        # Process each channel independently
        shifted_channels = []
        for i in range(audio_float64.shape[1]):
            channel_audio = np.ascontiguousarray(audio_float64[:, i])
            shifted_channel = _apply_formant_shift_mono(channel_audio, sample_rate, params.shift_factor)
            shifted_channels.append(shifted_channel)
        # Stack channels back together
        shifted_audio = np.stack(shifted_channels, axis=-1)
    else:
        raise ValueError("Input audio must be 1D (mono) or 2D (stereo)")

    # Return float64 as per _apply_formant_shift_mono's output
    return shifted_audio


def apply_rbj_lowpass_filter(audio: np.ndarray, sample_rate: int, params: ResonantFilterParameters) -> np.ndarray:
    """
    Applies a resonant low-pass filter using RBJ Biquad design (zero-phase).

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of ResonantFilterParameters containing cutoff frequency and Q.

    Returns:
        The processed audio signal with the filter applied (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32) # Return float32 for consistency

    nyquist = sample_rate / 2.0
    # Clip cutoff frequency to be slightly below Nyquist to avoid issues with filter design
    cutoff_hz = np.clip(params.cutoff_hz, 0.01, nyquist * 0.999) # Ensure cutoff is positive and below Nyquist
    # Ensure Q is positive and reasonably small if zero/negative provided (avoids instability)
    q = max(0.1, params.q) # Use 0.1 as a minimum Q

    # RBJ Lowpass Filter coefficient calculation (from RBJ Audio EQ Cookbook)
    w0 = 2 * math.pi * cutoff_hz / sample_rate
    alpha = math.sin(w0) / (2 * q)
    cos_w0 = math.cos(w0)

    b0 = (1 - cos_w0) / 2
    b1 = 1 - cos_w0
    b2 = (1 - cos_w0) / 2
    a0 = 1 + alpha
    a1 = -2 * cos_w0
    a2 = 1 - alpha

    # Normalize coefficients so a0 = 1
    b = np.array([b0, b1, b2]) / a0
    a = np.array([a0, a1, a2]) / a0 # a[0] is now 1

    # Convert to second-order sections (SOS) for numerical stability
    sos = signal.tf2sos(b, a)

    # Apply filter using sosfiltfilt (zero-phase filtering)
    # Process in float32 for consistency
    audio_float = audio.astype(np.float32)
    filtered_audio = signal.sosfiltfilt(sos, audio_float, axis=0)

    # Ensure output shape matches input channel count
    if audio.ndim == 1 and filtered_audio.ndim == 2 and filtered_audio.shape[1] == 1:
        filtered_audio = filtered_audio.flatten()
    elif audio.ndim == 2 and filtered_audio.ndim == 1 and audio.shape[1] == 1:
         filtered_audio = filtered_audio.reshape(-1, 1)

    # Return float32
    return filtered_audio.astype(np.float32)


def apply_bandpass_filter(audio: np.ndarray, sample_rate: int, params: BandpassFilterParameters) -> np.ndarray:
    """
    Applies a bandpass filter effect using a Butterworth filter (sosfiltfilt, zero-phase).

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of BandpassFilterParameters containing center frequency, Q, and order.

    Returns:
        The processed audio signal with the filter applied (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32) # Return float32 for consistency

    nyquist = sample_rate / 2.0

    # Ensure Q is positive to avoid division by zero or negative bandwidth
    q = max(0.01, params.q) # Use a small positive minimum Q

    # Calculate bandwidth from center frequency and Q
    bandwidth = params.center_hz / q

    # Calculate lower and upper cutoff frequencies
    low_cutoff = params.center_hz - bandwidth / 2.0
    high_cutoff = params.center_hz + bandwidth / 2.0

    # Clip frequencies to be within the valid Nyquist range [0, nyquist]
    # Also ensure low_cutoff is slightly above 0 for stability
    low_cutoff_clipped = max(0.01, low_cutoff)
    high_cutoff_clipped = min(high_cutoff, nyquist * 0.999) # Use a slightly smaller factor than 1.0

    # Check if the resulting frequency range is valid (low < high)
    if low_cutoff_clipped >= high_cutoff_clipped:
        # If clipping results in an invalid range (e.g., Q is too small, or center_hz is too close to 0 or nyquist)
        # Try to create a minimal valid band around the intended center_hz, or return original if impossible
        center_freq_clipped = np.clip(params.center_hz, 0.01, nyquist * 0.998)
        min_bw_hz = 0.01 # Define a minimum bandwidth in Hz to prevent zero or negative bandwidth

        # Recalculate low and high cutoffs based on the clipped center and minimum bandwidth
        low_cutoff_clipped = max(0.01, center_freq_clipped - min_bw_hz / 2)
        high_cutoff_clipped = min(nyquist * 0.999, center_freq_clipped + min_bw_hz / 2)

        # Final check: if still invalid, return original audio with a warning
        if low_cutoff_clipped >= high_cutoff_clipped:
            print(f"Warning: Bandpass filter parameters (center={params.center_hz}, Q={params.q}, order={params.order}) "
                  f"result in invalid frequency range [{low_cutoff_clipped:.2f}, {high_cutoff_clipped:.2f}] "
                  f"after clipping. Returning original audio.")
            return audio.astype(np.float32).copy() # Return float32 copy
        else:
             print(f"Warning: Bandpass filter parameters resulted in invalid range. "
                   f"Using adjusted range: [{low_cutoff_clipped:.2f}, {high_cutoff_clipped:.2f}]")

    # Normalize frequencies to Nyquist frequency (0 to 1 range)
    low_normalized = low_cutoff_clipped / nyquist
    high_normalized = high_cutoff_clipped / nyquist

    # Design the Butterworth bandpass filter using second-order sections (SOS)
    # Use the order specified in params
    sos = signal.butter(N=params.order, Wn=[low_normalized, high_normalized], btype='bandpass', output='sos')

    # Apply the filter using sosfiltfilt (zero-phase filtering)
    # Process in float32 for consistency
    audio_float = audio.astype(np.float32)
    filtered_audio = signal.sosfiltfilt(sos, audio_float, axis=0)

    # Ensure output shape matches input channel count
    if audio.ndim == 1 and filtered_audio.ndim == 2 and filtered_audio.shape[1] == 1:
        filtered_audio = filtered_audio.flatten()
    elif audio.ndim == 2 and filtered_audio.ndim == 1 and audio.shape[1] == 1:
         filtered_audio = filtered_audio.reshape(-1, 1)

    # Return float32
    return filtered_audio.astype(np.float32)


def apply_chorus(audio: np.ndarray, sample_rate: int, params: ChorusParameters) -> np.ndarray:
    """
    Applies a multi-voice chorus effect manually using modulated delay lines and feedback.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of ChorusParameters containing effect settings.

    Returns:
        The processed audio signal with chorus applied (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32)

    audio_float32 = audio.astype(np.float32)
    num_samples = audio_float32.shape[0]
    is_stereo = audio_float32.ndim == 2 and audio_float32.shape[1] == 2
    num_channels = 2 if is_stereo else 1

    # --- Parameters ---
    num_voices = max(1, params.num_voices)
    base_delay_sec = params.delay_ms / 1000.0
    base_delay_samples = base_delay_sec * sample_rate
    # Max variation based on depth, ensuring it doesn't exceed base delay
    max_variation_samples = min(params.depth * base_delay_samples, base_delay_samples - 1)
    max_variation_samples = max(0, max_variation_samples) # Ensure non-negative

    rate_hz = params.rate_hz
    feedback = np.clip(params.feedback, 0.0, 0.98) # Clip feedback slightly below 1 for stability
    mix = np.clip(params.wet_dry_mix, 0.0, 1.0)

    # --- LFO Generation ---
    t = np.arange(num_samples) / sample_rate
    # Use a sine LFO for smooth modulation
    lfo = np.sin(2 * np.pi * rate_hz * t)

    # --- Static Delay Offsets per Voice ---
    if num_voices > 1:
        # Static offsets spread around 0, scaled by max_variation_samples
        static_offsets = np.linspace(-max_variation_samples, max_variation_samples, num_voices, endpoint=True)
    else:
        static_offsets = np.array([0.0])

    # --- Delay Line Initialization ---
    # Determine max possible delay for buffer sizing
    max_dynamic_delay = base_delay_samples + max_variation_samples
    buffer_size = int(np.ceil(max_dynamic_delay)) + 2 # Add margin for interpolation

    # Create delay buffers (one per voice per channel)
    delay_buffers_shape = (num_voices, num_channels, buffer_size)
    delay_buffers = np.zeros(delay_buffers_shape, dtype=np.float32)
    write_pointers = np.zeros(num_voices, dtype=int)

    # --- Output Signal Initialization ---
    wet_signal = np.zeros_like(audio_float32)

    # --- Sample-by-Sample Processing ---
    for n in range(num_samples):
        current_input = audio_float32[n] # Shape: (,) or (2,)
        if not is_stereo:
            current_input = np.array([current_input]) # Ensure shape (1,) for consistent indexing

        total_delayed_sample_channels = np.zeros(num_channels, dtype=np.float32)

        for i in range(num_voices):
            # Calculate time-varying delay for this voice
            lfo_modulation = static_offsets[i] + max_variation_samples * lfo[n]
            current_delay_samples = base_delay_samples + lfo_modulation
            current_delay_samples = np.clip(current_delay_samples, 1.0, buffer_size - 2) # Ensure valid delay

            # Calculate read position (fractional)
            read_pos_frac = write_pointers[i] - current_delay_samples
            read_idx_0 = int(np.floor(read_pos_frac))
            read_idx_1 = read_idx_0 + 1
            frac = read_pos_frac - read_idx_0

            # Wrap buffer indices
            read_idx_0 = (read_idx_0 % buffer_size + buffer_size) % buffer_size
            read_idx_1 = (read_idx_1 % buffer_size + buffer_size) % buffer_size

            # Linear interpolation for each channel
            delayed_sample_channels = np.zeros(num_channels, dtype=np.float32)
            for ch in range(num_channels):
                y0 = delay_buffers[i, ch, read_idx_0]
                y1 = delay_buffers[i, ch, read_idx_1]
                delayed_sample_channels[ch] = y0 + frac * (y1 - y0)

            # Accumulate delayed samples for the wet mix
            total_delayed_sample_channels += delayed_sample_channels

            # Calculate feedback input and write to buffer for each channel
            for ch in range(num_channels):
                 buffer_input = current_input[ch] + feedback * delayed_sample_channels[ch]
                 # Clip buffer input to prevent extreme values with high feedback
                 buffer_input = np.clip(buffer_input, -1.0, 1.0)
                 delay_buffers[i, ch, write_pointers[i]] = buffer_input

            # Increment write pointer for this voice
            write_pointers[i] = (write_pointers[i] + 1) % buffer_size

        # Average the delayed samples across voices
        avg_delayed_sample = total_delayed_sample_channels / num_voices

        # Store the averaged wet sample (shape (1,) or (2,))
        if is_stereo:
            wet_signal[n] = avg_delayed_sample
        else:
            wet_signal[n] = avg_delayed_sample[0]

    # --- Mix wet and dry signals ---
    output_signal = (audio_float32 * (1.0 - mix)) + (wet_signal * mix)

    # Ensure output length matches original input length (should already match)
    if output_signal.shape[0] != num_samples:
        print(f"Warning: Final output signal length mismatch ({output_signal.shape[0]} vs {num_samples}). Truncating.")
        output_signal = output_signal[:num_samples, ...]

    # Ensure output shape matches input channel count (should already match)
    if audio.ndim == 1 and output_signal.ndim == 2 and output_signal.shape[1] == 1:
        output_signal = output_signal.flatten()
    elif audio.ndim == 2 and output_signal.ndim == 1 and audio.shape[1] == 1:
         output_signal = output_signal.reshape(-1, 1)

    return output_signal.astype(np.float32)


# --- Spectral Freeze Constants ---
N_FFT = 2048
HOP_LENGTH = 512


# --- Spectral Freeze Helper Functions ---

def _prepare_audio_for_librosa(audio_float32: np.ndarray) -> tuple[np.ndarray, int, tuple]:
    """Prepares audio array shape for librosa STFT (channels first)."""
    original_ndim = audio_float32.ndim
    original_shape = audio_float32.shape

    if original_ndim == 1:
        # Mono: add channel dimension
        audio_proc = audio_float32[np.newaxis, :]
    elif original_ndim == 2:
        # Stereo: ensure channels are the first dimension
        if original_shape[0] > original_shape[1]: # samples x channels
            audio_proc = audio_float32.T
        else: # channels x samples
            audio_proc = audio_float32
    else:
        raise ValueError("Input audio must be 1D (mono) or 2D (stereo)")

    return audio_proc, original_ndim, original_shape


def _create_blend_mask(params: SpectralFreezeParameters, sample_rate: int, hop_length: int, n_frames: int) -> np.ndarray:
    """Creates the time-varying blend mask for spectral freeze."""
    fade_frames = int(round(params.fade_duration * sample_rate / hop_length))
    fade_frames = min(fade_frames, n_frames) # Clamp fade duration

    if fade_frames <= 0 or params.blend_amount == 0 or n_frames == 0:
        blend_mask = np.full(n_frames, params.blend_amount)
    else:
        ramp = np.linspace(0, params.blend_amount, fade_frames)
        # Ensure plateau length is not negative
        plateau_len = max(0, n_frames - fade_frames)
        plateau = np.full(plateau_len, params.blend_amount)
        blend_mask = np.concatenate((ramp, plateau))
        # Ensure blend_mask length matches n_frames exactly if concatenation resulted in different length due to rounding
        if len(blend_mask) != n_frames:
             blend_mask = np.resize(blend_mask, n_frames)
             if n_frames > 0: # Ensure last element is correct if resized
                 blend_mask[-1] = params.blend_amount
    return blend_mask


def _restore_audio_shape(processed_audio: np.ndarray, original_ndim: int, original_shape: tuple) -> np.ndarray:
    """Restores the processed audio array to its original shape."""
    if original_ndim == 1 and processed_audio.shape[0] == 1:
        # Input mono, output has channel dim -> flatten
        output_audio = processed_audio[0]
    elif original_ndim == 2 and original_shape[0] > original_shape[1]: # Input was samples x channels
        # Output is channels x samples -> transpose back
        output_audio = processed_audio.T
    else: # Input was mono/channels x samples, output is channels x samples
        output_audio = processed_audio

    # Ensure final output shape is consistent if possible (e.g., handle potential squeeze)
    # Check if output_audio is valid before accessing shape
    if isinstance(output_audio, np.ndarray):
        if output_audio.shape != original_shape and original_ndim == 1 and output_audio.ndim == 0:
             # If input was mono and output somehow became scalar, reshape
             output_audio = output_audio.reshape(original_shape)
        elif output_audio.shape != original_shape and original_ndim == 2:
             # If shapes mismatch for stereo, this might indicate an issue
             # Attempt to reshape if total size matches
             if output_audio.size == np.prod(original_shape):
                 try:
                     output_audio = output_audio.reshape(original_shape)
                 except ValueError:
                     print(f"Warning: Could not reshape processed audio {output_audio.shape} to original shape {original_shape}")
             else:
                  print(f"Warning: Processed audio size {output_audio.size} differs from original {np.prod(original_shape)}")
    else: # If something went wrong, return an empty array matching original dtype
        print("Warning: Audio processing failed during shape restoration.")
        # Return original audio copy instead of empty array to be safer
        # This requires passing original audio or handling failure differently.
        # For now, returning empty array as before.
        return np.array([], dtype=processed_audio.dtype)

    return output_audio


# --- Main Effect Function ---
def apply_smooth_spectral_freeze(audio: np.ndarray, sample_rate: int, params: SpectralFreezeParameters) -> np.ndarray:
    """
    Applies a smooth spectral freeze effect using STFT.

    Freezes the spectrum at a specified point and blends it with the original
    audio over time, controlled by a fade-in duration.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
               Expected shapes: (n_samples,) for mono, or (n_channels, n_samples)
               or (n_samples, n_channels) for stereo.
        sample_rate: Sample rate of the audio signal.
        params: An instance of SpectralFreezeParameters containing effect settings.

    Returns:
        The processed audio signal with the spectral freeze effect applied (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32)

    audio_float32 = audio.astype(np.float32)

    # --- Prepare audio shape for librosa (channels first) ---
    audio_proc, original_ndim, original_shape = _prepare_audio_for_librosa(audio_float32)
    n_channels, n_samples = audio_proc.shape

    # --- STFT Parameters ---
    n_fft = N_FFT
    hop_length = HOP_LENGTH

    # --- Calculate STFT ---
    stft_result = librosa.stft(y=audio_proc, n_fft=n_fft, hop_length=hop_length)
    # Result shape is (n_channels, n_freq_bins, n_frames)
    if stft_result.ndim == 2: # Handle case where librosa might return 2D for mono
        stft_result = stft_result[np.newaxis, :, :]
        n_channels = 1 # Ensure n_channels is 1

    n_freq_bins, n_frames = stft_result.shape[1:]


    # --- Determine Freeze Frame ---
    # Ensure index is within bounds [0, n_frames - 1]
    target_frame_index = min(int(round(params.freeze_point * (n_frames - 1))), n_frames - 1) if n_frames > 0 else 0


    # --- Extract Magnitudes and Phase ---
    magnitude = np.abs(stft_result)
    phase = np.angle(stft_result)
    frozen_magnitude = magnitude[:, :, target_frame_index] if n_frames > 0 else np.zeros((n_channels, n_freq_bins)) # Shape: (n_channels, n_freq_bins)


    # --- Create Time-Varying Blend Mask ---
    blend_mask = _create_blend_mask(params, sample_rate, hop_length, n_frames)


    # Expand mask for broadcasting: (1, 1, n_frames)
    blend_mask_expanded = blend_mask[np.newaxis, np.newaxis, :]
    # Expand frozen magnitude for broadcasting: (n_channels, n_freq_bins, 1)
    frozen_magnitude_expanded = frozen_magnitude[:, :, np.newaxis]

    # --- Interpolate Magnitudes ---
    # Ensure broadcasting works even if n_frames is 0 or 1
    if n_frames > 0:
        interpolated_magnitude = (1.0 - blend_mask_expanded) * magnitude + \
                                 blend_mask_expanded * frozen_magnitude_expanded
    else: # Handle case with no frames
         interpolated_magnitude = np.zeros((n_channels, n_freq_bins, 0))


    # --- Reconstruct STFT ---
    final_stft = interpolated_magnitude * np.exp(1j * phase)

    # --- Inverse STFT ---
    # Ensure output length matches original input length
    processed_audio = librosa.istft(final_stft, hop_length=hop_length, length=n_samples, win_length=n_fft) # Specify win_length

    # --- Restore Original Shape ---
    output_audio = _restore_audio_shape(processed_audio, original_ndim, original_shape)

    # Final check for dtype and return
    if not isinstance(output_audio, np.ndarray): # If something went wrong during restoration
        print("Warning: Spectral freeze processing failed, returning original audio.")
        return audio.astype(np.float32).copy()

    return output_audio.astype(np.float32)


# --- Glitch Helper Functions ---

def _apply_repeat_glitch(audio_chunk: np.ndarray, sample_rate: int, params: GlitchParameters) -> np.ndarray:
    """
    Applies repeat or stutter glitch to an audio chunk.
    'repeat': Repeats the initial segment of length chunk_len / repeat_count, repeat_count times.
    'stutter': Repeats the initial 10ms segment multiple times.
    Ensures output length matches input length.
    """
    if audio_chunk.size == 0:
        return audio_chunk

    chunk_len = audio_chunk.shape[0]

    if params.glitch_type == 'repeat':
        if params.repeat_count <= 1:
             return audio_chunk # No repetition needed
        # Calculate the length of the initial segment to repeat
        segment_len = max(1, chunk_len // params.repeat_count)
        segment_to_repeat = audio_chunk[:segment_len, ...]
        # Tile this segment `repeat_count` times
        num_tiles = params.repeat_count
        repeated_chunk = np.tile(segment_to_repeat, (num_tiles,) + (1,) * (audio_chunk.ndim - 1))

    elif params.glitch_type == 'stutter':
        # Repeat a small initial part of the chunk (hardcoded 10ms stutter length).
        stutter_len_ms = 10.0
        stutter_len_samples = max(1, int(round(stutter_len_ms / 1000.0 * sample_rate)))
        stutter_len_samples = min(stutter_len_samples, chunk_len)

        if stutter_len_samples > 0:
            stutter_part = audio_chunk[:stutter_len_samples, ...]
            # Calculate how many times to tile to approximately fill the chunk
            num_tiles = (chunk_len + stutter_len_samples - 1) // stutter_len_samples # Ceiling division
            repeated_chunk = np.tile(stutter_part, (num_tiles,) + (1,) * (audio_chunk.ndim - 1))
        else:
            repeated_chunk = audio_chunk # Should not happen if chunk_len > 0
    else:
        # Should not happen if called correctly from main function
        return audio_chunk

    # Ensure the output length matches the input chunk length by truncating or padding
    if repeated_chunk.shape[0] > chunk_len:
        repeated_chunk = repeated_chunk[:chunk_len, ...]
    elif repeated_chunk.shape[0] < chunk_len:
        padding_shape = (chunk_len - repeated_chunk.shape[0],) + audio_chunk.shape[1:]
        padding = np.zeros(padding_shape, dtype=audio_chunk.dtype)
        repeated_chunk = np.concatenate((repeated_chunk, padding), axis=0)

    return repeated_chunk.astype(audio_chunk.dtype) # Ensure output dtype matches input

def _apply_tape_stop_glitch(audio_chunk: np.ndarray, sample_rate: int, params: GlitchParameters) -> np.ndarray:
    """Applies tape stop simulation to an audio chunk using resampling."""
    if audio_chunk.size == 0:
        return audio_chunk

    num_samples = audio_chunk.shape[0]

    # Create a time-varying resampling factor (speed)
    # Linearly decrease speed from 1.0 down to a minimum speed (e.g., 0.01 or params.tape_stop_speed)
    # Using 0.01 as minimum speed to avoid zero length output from resample.
    # Assume params.tape_stop_speed is the target speed factor (e.g., 0.5 = half speed).
    # The speed ramps down linearly from 1.0 to target_speed over the chunk duration.
    target_speed = max(0.01, params.tape_stop_speed) # Ensure speed is at least slightly positive
    # speeds = np.linspace(1.0, target_speed, num_samples) # This line is unused.
    # Calculate the new number of samples based on the integral of the inverse speed
    # This is complex. Simpler approach: Resample to a target length based on average speed?
    # Or, even simpler for now: just resample based on a fixed final speed?
    # Let's try resampling to a length proportional to the average speed.
    # avg_speed = (1.0 + min_speed) / 2.0
    # target_samples = int(round(num_samples * avg_speed))

    # Alternative: Use librosa's time stretch? No, that preserves pitch.
    # Let's try scipy.signal.resample with a fixed target length based on final speed.
    # This simulates slowing down *to* that speed over the chunk duration.
    target_samples = int(round(num_samples * target_speed))
    if target_samples <= 0:
        return np.zeros_like(audio_chunk) # Return silence if target is zero

    try:
        # resample needs float64 for precision
        # Cast the result to ndarray to help Pylance with type inference
        resampled_chunk = cast(np.ndarray, signal.resample(audio_chunk.astype(np.float64), target_samples, axis=0))
    except ValueError as e:
        print(f"Warning: Resampling failed for tape stop: {e}. Returning original chunk.")
        return audio_chunk

    # Pad or truncate the resampled chunk to match the original chunk length
    output_chunk = np.zeros_like(audio_chunk, dtype=np.float32)
    current_len = resampled_chunk.shape[0]
    original_len = audio_chunk.shape[0]

    if current_len > 0:
        copy_len = min(current_len, original_len)
        output_chunk[:copy_len, ...] = resampled_chunk[:copy_len, ...]

    return output_chunk.astype(np.float32)

def _apply_bitcrush_glitch(audio_chunk: np.ndarray, sample_rate: int, params: GlitchParameters) -> np.ndarray:
    """Applies bitcrush (quantization and sample rate reduction) to an audio chunk."""
    if audio_chunk.size == 0:
        return audio_chunk

    processed_chunk = audio_chunk.astype(np.float32).copy() # Ensure we work on a float32 copy
    num_samples = processed_chunk.shape[0]

    # --- Bit Depth Reduction ---
    if params.bitcrush_depth < 16: # Apply only if depth is less than typical float precision
        num_levels = 2**params.bitcrush_depth
        # Scale to [0, levels-1], round, scale back to [-1, 1]
        # Assuming audio is in [-1, 1] range
        processed_chunk = np.round((processed_chunk + 1.0) / 2.0 * (num_levels - 1))
        processed_chunk = (processed_chunk / (num_levels - 1) * 2.0) - 1.0
        # Clip just in case of precision issues
        processed_chunk = np.clip(processed_chunk, -1.0, 1.0)

    # --- Sample Rate Reduction (Downsampling simulation by holding samples) ---
    if params.bitcrush_rate_factor < 1.0:
        # Calculate how many samples to hold each value for.
        # factor=1.0 -> hold=1 (no change). factor=0.0 -> hold=inf (effectively hold first sample).
        # Let's map factor 0.0 -> large hold, factor near 1.0 -> hold=1
        # A simple approach: hold_samples = max(1, int(round(1.0 / (params.bitcrush_rate_factor + 1e-9))))
        # Let's try mapping factor to step size directly: step = 1 / factor
        step_size = max(1, int(round(1.0 / (params.bitcrush_rate_factor + 1e-9)))) # Add epsilon for factor=0
        step_size = min(step_size, num_samples) # Cannot step more than chunk size

        if step_size > 1:
            for i in range(0, num_samples, step_size):
                # Value to hold is the first sample in the step
                hold_value = processed_chunk[i, ...]
                # Apply this value to the whole step (or until the end of the chunk)
                end_index = min(i + step_size, num_samples)
                processed_chunk[i:end_index, ...] = hold_value

    return processed_chunk.astype(np.float32)


# Removed duplicate function definition

def apply_refined_glitch(audio: np.ndarray, sample_rate: int, params: GlitchParameters) -> np.ndarray:
    """
    Applies a refined glitch effect based on the specified parameters.
    Randomly applies glitches to chunks of the audio based on intensity.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of GlitchParameters containing effect settings.

    Returns:
        The processed audio signal with glitches applied (float32).
    """
    if audio.size == 0 or params.intensity == 0.0:
        return audio.astype(np.float32).copy()

    audio_out = audio.astype(np.float32).copy()
    num_samples = audio_out.shape[0]

    # Calculate chunk size in samples, ensure it's at least 1
    chunk_size_samples = max(1, int(round(params.chunk_size_ms / 1000.0 * sample_rate)))

    # Iterate through the audio in chunks
    for i in range(0, num_samples, chunk_size_samples):
        # Check probability based on intensity
        if random.random() < params.intensity:
            # print(f"DEBUG: Applying glitch type {params.glitch_type} to chunk {i // chunk_size_samples}") # DEBUG - Removed
            print(f"DEBUG: Applying glitch type {params.glitch_type} to chunk {i // chunk_size_samples}") # DEBUG
            start_sample = i
            end_sample = min(i + chunk_size_samples, num_samples)
            current_chunk = audio_out[start_sample:end_sample, ...]

            # Apply the selected glitch type
            if params.glitch_type in ('repeat', 'stutter'):
                glitched_chunk = _apply_repeat_glitch(current_chunk, sample_rate, params)
            elif params.glitch_type == 'tape_stop':
                glitched_chunk = _apply_tape_stop_glitch(current_chunk, sample_rate, params)
            elif params.glitch_type == 'bitcrush':
                glitched_chunk = _apply_bitcrush_glitch(current_chunk, sample_rate, params)
            else:
                # Should not happen due to Pydantic validation, but handle defensively
                glitched_chunk = current_chunk

            # print(f"DEBUG: Chunk {i // chunk_size_samples} modified by helper: {not np.allclose(current_chunk, glitched_chunk)}") # DEBUG - Removed

            # Place the glitched chunk back into the output audio
            # Ensure the glitched chunk fits (it should if helpers maintain length)
            if glitched_chunk.shape[0] == (end_sample - start_sample):
                audio_out[start_sample:end_sample, ...] = glitched_chunk
            else:
                # This might happen if a glitch changes length significantly and wasn't padded/truncated correctly
                print(f"Warning: Glitched chunk length mismatch ({glitched_chunk.shape[0]} vs {end_sample - start_sample}). Skipping application for this chunk.")

    return audio_out
# Removed duplicate minimal implementation


def apply_saturation(audio: np.ndarray, sample_rate: int, params: SaturationParameters) -> np.ndarray:
    """
    Applies a saturation/distortion effect using pedalboard.Distortion and a tone filter.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of SaturationParameters containing effect settings.

    Returns:
        The processed audio signal with saturation applied (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32)

    audio_float32 = audio.astype(np.float32)
    dry_signal = audio_float32.copy() # Keep original for mixing

    # 1. Apply Drive (Distortion)
    # Map drive (0.0+) linearly to drive_db. The scaling factor (10.0) is arbitrary and might need tuning.
    # Clip the result to a practical maximum (e.g., 60dB) to avoid extreme distortion.
    MAX_DRIVE_DB = 60.0
    drive_db = np.clip(params.drive * 10.0, 0.0, MAX_DRIVE_DB)
    distortion_effect = Distortion(drive_db=drive_db)
    board_dist = Pedalboard([distortion_effect])
    wet_signal = board_dist(audio_float32, sample_rate=sample_rate)

    # 2. Apply Tone (Lowpass Filter)
    TONE_MIN_FREQ = 200.0
    TONE_MAX_FREQ = 10000.0
    # Ensure tone is clipped 0-1
    tone_clipped = np.clip(params.tone, 0.0, 1.0)
    # Logarithmic mapping for tone control (0=dark -> min_freq, 1=bright -> max_freq)
    cutoff_hz = TONE_MIN_FREQ * (TONE_MAX_FREQ / TONE_MIN_FREQ)**tone_clipped
    nyquist = sample_rate / 2.0
    # Clip cutoff frequency to be within valid range [min_freq, nyquist * 0.99]
    cutoff_hz = np.clip(cutoff_hz, TONE_MIN_FREQ, nyquist * 0.99)

    # Only apply filter if tone is not max (1.0), otherwise keep full spectrum
    if tone_clipped < 1.0:
        tone_filter = LowpassFilter(cutoff_frequency_hz=cutoff_hz)
        board_tone = Pedalboard([tone_filter])
        # Apply filter to the distorted signal
        wet_signal = board_tone(wet_signal, sample_rate=sample_rate)

    # 3. Apply Mix
    mix_clipped = np.clip(params.mix, 0.0, 1.0)

    # Ensure shapes match for broadcasting before mixing.
    # Pedalboard effects can sometimes change channel count (e.g., mono input -> stereo output).
    if dry_signal.ndim != wet_signal.ndim or dry_signal.shape[1:] != wet_signal.shape[1:]:
         # Handle potential mono->stereo conversion by pedalboard
         if dry_signal.ndim == 1 and wet_signal.ndim == 2 and wet_signal.shape[1] > 1:
             # Tile dry signal to match wet signal channels
             dry_signal = np.tile(dry_signal[:, np.newaxis], (1, wet_signal.shape[1]))
         elif dry_signal.ndim == 2 and wet_signal.ndim == 1 and dry_signal.shape[1] == 1:
             wet_signal = wet_signal.reshape(-1, 1)
         # If shapes still don't match after attempting common fixes, log warning and return dry
         if dry_signal.shape[1:] != wet_signal.shape[1:]:
              print(f"Warning: Shape mismatch between dry ({dry_signal.shape}) and wet ({wet_signal.shape}) signals after saturation/tone. Returning dry signal.")
              # Ensure length matches original before returning
              if dry_signal.shape[0] != audio.shape[0]:
                   dry_signal = np.resize(dry_signal, audio.shape) # Resize to original shape
              return dry_signal.astype(np.float32)

    # Ensure lengths match before mixing (pedalboard effects generally preserve length, but be safe).
    min_len = min(dry_signal.shape[0], wet_signal.shape[0])
    dry_signal = dry_signal[:min_len, ...]
    wet_signal = wet_signal[:min_len, ...]

    output_signal = (dry_signal * (1.0 - mix_clipped)) + (wet_signal * mix_clipped)

    # Ensure final output length matches original input length.
    # This handles cases where intermediate processing might have slightly altered length.
    if output_signal.shape[0] != audio.shape[0]:
        target_len = audio.shape[0]
        current_len = output_signal.shape[0]
        if current_len > target_len:
            output_signal = output_signal[:target_len, ...]
        else:
            padding_shape = (target_len - current_len,) + output_signal.shape[1:]
            padding = np.zeros(padding_shape, dtype=output_signal.dtype)
            output_signal = np.concatenate((output_signal, padding), axis=0)


    return output_signal.astype(np.float32)




def apply_master_dynamics(audio: np.ndarray, sample_rate: int, params: MasterDynamicsParameters) -> np.ndarray:
    """
    Applies master dynamics processing (compression and limiting) to the audio signal
    using pedalboard.Compressor and pedalboard.Limiter.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of MasterDynamicsParameters containing effect settings.

    Returns:
        The processed audio signal (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32)

    board = Pedalboard()

    # Add Compressor if enabled
    if params.enable_compressor:
        compressor = Compressor(
            threshold_db=params.compressor_threshold_db,
            ratio=params.compressor_ratio,
            attack_ms=params.compressor_attack_ms,
            release_ms=params.compressor_release_ms
        )
        board.append(compressor)

    # Add Limiter if enabled (typically after compressor)
    if params.enable_limiter:
        limiter = Limiter(
            threshold_db=params.limiter_threshold_db,
            release_ms=1.0 # Set a fast release time for potentially better impulse response
        )
        board.append(limiter)

    # Process audio only if effects were added
    if len(board) > 0:
        audio_float32 = audio.astype(np.float32)
        processed_audio = board(audio_float32, sample_rate=sample_rate)

        # Ensure output shape matches input channel count if possible
        if audio.ndim == 1 and processed_audio.ndim == 2 and processed_audio.shape[1] == 1:
            processed_audio = processed_audio.flatten()
        elif audio.ndim == 2 and processed_audio.ndim == 1 and audio.shape[1] == 1:
             processed_audio = processed_audio.reshape(-1, 1)

        # Ensure length matches original input length (pedalboard dynamics shouldn't change length)
        if processed_audio.shape[0] != audio.shape[0]:
            target_len = audio.shape[0]
            current_len = processed_audio.shape[0]
            if current_len > target_len:
                processed_audio = processed_audio[:target_len, ...]
            else:
                padding_shape = (target_len - current_len,) + processed_audio.shape[1:]
                padding = np.zeros(padding_shape, dtype=processed_audio.dtype)
                processed_audio = np.concatenate((processed_audio, padding), axis=0)

        return processed_audio.astype(np.float32)
    else:
        # No effects enabled, return original audio as float32
        return audio.astype(np.float32).copy()
