import numpy as np
from pydantic import BaseModel, Field, ConfigDict, model_validator
from pedalboard import Delay, Reverb
from pedalboard._pedalboard import Pedalboard # Import as suggested by Pylance

# Define validation ranges based on common sense and test cases
# import librosa # Not used in reverb, delay, or formant shift sections
# import parselmouth # Not used in reverb, delay, or formant shift sections
import pyworld as pw # Use pw alias for formant shifting
from scipy.interpolate import interp1d # Used for formant shifting spectral warping

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

def apply_high_quality_reverb(audio: np.ndarray, sample_rate: int, params: ReverbParameters) -> np.ndarray:
    """
    Applies a high-quality reverb effect to an audio signal using pedalboard.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of ReverbParameters containing effect settings.

    Returns:
        The processed audio signal with reverb applied.
    """
    if audio.size == 0:
        return np.array([], dtype=audio.dtype)

    # Map ReverbParameters to pedalboard.Reverb parameters
    # Conceptual mapping: decay_time -> room_size (0-1 range)
    # Map decay_time (e.g., 0.1s-10s) linearly to pedalboard's room_size (0.1-1.0)
    normalized_decay = (params.decay_time - MIN_DECAY_S) / (MAX_DECAY_S - MIN_DECAY_S)
    room_size = np.clip(normalized_decay * (MAX_ROOM_SIZE - MIN_ROOM_SIZE) + MIN_ROOM_SIZE, 0.0, 1.0)

    # Map wet_dry_mix to wet_level and dry_level
    # Simple linear crossfade:
    wet_level = params.wet_dry_mix
    dry_level = 1.0 - params.wet_dry_mix
    # Note: Pedalboard's levels might not sum to 1 for constant power.
    # A more perceptually accurate mapping might be needed later.

    reverb_effect = Reverb( # Use direct import
        room_size=room_size,
        damping=params.damping,
        wet_level=wet_level,
        dry_level=dry_level,
        # Conceptually map diffusion (0-1) to stereo width (0-1).
        # Simple scaling, could be refined. Pedalboard's default width is 1.0.
        width=np.clip(params.diffusion, 0.0, 1.0)
        # pre_delay is not available in pedalboard.Reverb
    )

    # Pedalboard expects float32
    audio_float32 = audio.astype(np.float32)

    # Simulate pre-delay by adding silence
    pre_delay_samples = int(params.pre_delay * sample_rate)
    if pre_delay_samples > 0:
        padding_shape = (pre_delay_samples,) + audio_float32.shape[1:] # Add padding dims if stereo
        padding = np.zeros(padding_shape, dtype=audio_float32.dtype)
        audio_padded = np.concatenate((padding, audio_float32), axis=0)
    else:
        audio_padded = audio_float32

    # Apply effect
    # Pedalboard handles mono/stereo automatically if input is (samples,) or (samples, channels)
    # Apply effect using a Pedalboard instance
    reverb_board = Pedalboard([reverb_effect]) # No sample_rate here
    reverberated_signal = reverb_board(audio_padded, sample_rate=sample_rate) # Pass sample_rate here

    # The output length will be input_length + pre_delay_samples + reverb_tail
    # We need to combine the original dry signal (with pre-delay) and the wet signal correctly
    # For simplicity in this minimal implementation, let's assume the pedalboard's dry_level
    # handles mixing the original *padded* signal. The output length will naturally be longer.
    # A more complex implementation might mix the original *unpadded* dry signal with the
    # *reverberated* signal, aligning them based on pre_delay.
    wet_signal = reverberated_signal # Use the output directly for now

    # Ensure output shape matches input channel count, though length might change
    if audio.ndim == 1 and wet_signal.ndim == 2 and wet_signal.shape[1] == 1:
        # If input was mono but output is (n, 1), flatten it
        wet_signal = wet_signal.flatten()
    elif audio.ndim == 2 and wet_signal.ndim == 1 and audio.shape[1] == 1:
         # If input was (n, 1) and output is mono, reshape it
         wet_signal = wet_signal.reshape(-1, 1)


    # Pedalboard might change the length slightly, the tests allow for this (>=)
    # Return in original dtype if possible, though effects usually work best in float
    # For now, return float32 as pedalboard outputs
    return wet_signal


# --- Formant Shifting --- 

class FormantShiftParameters(BaseModel):
    """Parameters for the robust formant shifting effect."""
    shift_factor: float = Field(..., gt=0.0, description="Factor by which to shift formants. >1 shifts up, <1 shifts down.")

    model_config = ConfigDict(extra='forbid')

def apply_robust_formant_shift(audio: np.ndarray, sample_rate: int, params: FormantShiftParameters) -> np.ndarray:
    """
    Applies formant shifting while preserving pitch using the WORLD vocoder.

    Analyzes the audio into F0, spectral envelope (SP), and aperiodicity (AP).
    Warps the spectral envelope's frequency axis according to the shift_factor.
    Resynthesizes the audio using the original F0, original AP, and the warped SP.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of FormantShiftParameters containing effect settings.

    Returns:
        The processed audio signal with formants shifted.
    """
    if audio.size == 0:
        return np.array([], dtype=audio.dtype)

    # If shift_factor is 1.0, no change is needed.
    if np.isclose(params.shift_factor, 1.0):
        return audio.copy()

    original_dtype = audio.dtype
    # pyworld expects float64
    audio_float64 = audio.astype(np.float64)

    # Handle stereo by processing channels independently
    if audio_float64.ndim == 2:
        shifted_channels = []
        for i in range(audio_float64.shape[1]):
            channel_audio = np.ascontiguousarray(audio_float64[:, i]) # Ensure contiguous
            shifted_channel = _apply_formant_shift_mono(channel_audio, sample_rate, params.shift_factor)
            shifted_channels.append(shifted_channel)
        # Stack channels back together
        shifted_audio = np.stack(shifted_channels, axis=-1)
    elif audio_float64.ndim == 1:
        audio_float64 = np.ascontiguousarray(audio_float64) # Ensure contiguous
        shifted_audio = _apply_formant_shift_mono(audio_float64, sample_rate, params.shift_factor)
    else:
        raise ValueError("Input audio must be 1D (mono) or 2D (stereo)")

    # Convert back to original dtype if needed, though float is often preferred for effects
    # Let's return float64 for now, consistent with pyworld output
    # return shifted_audio.astype(original_dtype)
    return shifted_audio


def _apply_formant_shift_mono(x: np.ndarray, fs: int, shift_factor: float) -> np.ndarray:
    """Helper function to apply formant shift to a mono float64 signal."""
    # Ensure input is float64 and contiguous (redundant check, but safe)
    x = np.ascontiguousarray(x, dtype=np.float64)

    # --- WORLD Analysis ---
    # Use default DIO/Harvest parameters for F0 estimation
    f0, t = pw.dio(x, fs) # type: ignore
    # Refine F0 using Stonemask
    f0 = pw.stonemask(x, f0, t, fs) # type: ignore
    # Estimate spectral envelope using CheapTrick
    sp = pw.cheaptrick(x, f0, t, fs) # type: ignore
    # Estimate aperiodicity using D4C
    ap = pw.d4c(x, f0, t, fs) # type: ignore

    # --- Warp Spectral Envelope ---
    sp_warped = _warp_spectral_envelope(sp, fs, shift_factor)

    # --- WORLD Synthesis ---
    # Ensure f0 is C-contiguous double array for synthesis
    f0_cont = np.ascontiguousarray(f0, dtype=np.float64)
    # Ensure sp_warped and ap are also contiguous float64 (should be from warping/analysis)
    sp_warped_cont = np.ascontiguousarray(sp_warped, dtype=np.float64)
    ap_cont = np.ascontiguousarray(ap, dtype=np.float64)

    # Synthesize using original F0, warped SP, original AP
    y = pw.synthesize(f0_cont, sp_warped_cont, ap_cont, fs) # type: ignore

    # Ensure output length matches input length (synthesis might slightly alter it)
    if len(y) > len(x):
        y = y[:len(x)]
    elif len(y) < len(x):
        padding = np.zeros(len(x) - len(y), dtype=np.float64)
        y = np.concatenate((y, padding))

    return y.astype(np.float64) # Return float64


# Helper function for spectral warping based on research report
def _warp_spectral_envelope(sp: np.ndarray, fs: int, formant_shift_ratio: float) -> np.ndarray:
    """
    Warps the spectral envelope frequency axis using interpolation.

    Args:
        sp: Spectral envelope from pyworld (frames x frequency_bins), float64.
        fs: Sample rate.
        formant_shift_ratio: Factor to shift formants (>1 up, <1 down).

    Returns:
        Warped spectral envelope, float64.
    """
    num_frames, num_bins = sp.shape
    # CheapTrick uses fft_size / 2 + 1 bins. Calculate fft_size from num_bins.
    fft_size = (num_bins - 1) * 2
    original_freqs = np.linspace(0, fs / 2, num_bins)
    # Frequencies from which to sample the *original* envelope
    warped_freqs = original_freqs / formant_shift_ratio

    sp_warped = np.zeros_like(sp)

    for i in range(num_frames):
        # Create interpolation function based on original envelope values at warped frequencies
        interp_func = interp1d(
            warped_freqs, sp[i], kind='linear', bounds_error=False,
            # Extrapolate using edge values of the original envelope
            fill_value="extrapolate" # type: ignore
        )
        # Evaluate the interpolation function at the original frequencies to get the warped envelope
        sp_warped[i] = interp_func(original_freqs)

    # Ensure non-negative values (numerical precision might cause small negatives)
    # Use a small positive floor based on pyworld examples/recommendations
    sp_warped[sp_warped < 1e-16] = 1e-16

    # Ensure output is float64 for pyworld synthesis
    return sp_warped.astype(np.float64)


# --- Complex Delay ---

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
        if self.filter_low_hz > self.filter_high_hz:
            raise ValueError("filter_low_hz cannot be greater than filter_high_hz")
        return self


def apply_complex_delay(audio: np.ndarray, sample_rate: int, params: DelayParameters) -> np.ndarray:
    """
    Applies a complex delay effect to an audio signal using pedalboard.Delay.
    Focuses on delay_time, feedback, and mix for initial TDD green phase.
    Other parameters (spread, LFO, filters) are ignored in this implementation.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of DelayParameters containing effect settings.

    Returns:
        The processed audio signal with delay applied.
    """
    if audio.size == 0:
        return np.array([], dtype=audio.dtype)

    # Map parameters from DelayParameters to pedalboard.Delay arguments
    delay_seconds = params.delay_time_ms / 1000.0
    feedback = params.feedback
    mix = params.wet_dry_mix # pedalboard.Delay uses 'mix' (0=dry, 1=wet)

    # Instantiate the delay effect
    delay_effect = Delay( # Use direct import
        delay_seconds=delay_seconds,
        feedback=feedback, # Note: Known upstream issue in pedalboard.Delay may affect feedback behavior.
        mix=mix
        # Note: stereo_spread, LFO parameters, and filter parameters from
        # DelayParameters are not directly supported by pedalboard.Delay
        # and are ignored in this implementation.
    )

    # Create a Pedalboard instance with the delay effect
    board = Pedalboard([delay_effect]) # No sample_rate here

    # Process the audio (pedalboard expects float32)
    audio_float32 = audio.astype(np.float32)
    delayed_signal = board(audio_float32, sample_rate=sample_rate) # Pass sample_rate here

    # Ensure output shape matches input channel count, though length might change
    if audio.ndim == 1 and delayed_signal.ndim == 2 and delayed_signal.shape[1] == 1:
        # If input was mono but output is (n, 1), flatten it
        delayed_signal = delayed_signal.flatten()
    elif audio.ndim == 2 and delayed_signal.ndim == 1 and audio.shape[1] == 1:
         # If input was (n, 1) and output is mono, reshape it
         delayed_signal = delayed_signal.reshape(-1, 1)

    # Return float32 as pedalboard outputs
    return delayed_signal
