import numpy as np
from pydantic import BaseModel, Field, ConfigDict, model_validator
from pedalboard import Delay, Reverb
from pedalboard._pedalboard import Pedalboard # Import as suggested by Pylance
from scipy import signal # Added for filters
import math # Added for RBJ filter calculations
from scipy.interpolate import interp1d # Used for formant shifting spectral warping
import pyworld as pw # Use pw alias for formant shifting

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
    Applies a chorus effect using pedalboard.Chorus.

    Args:
        audio: Input audio signal as a NumPy array (mono or stereo).
        sample_rate: Sample rate of the audio signal.
        params: An instance of ChorusParameters containing effect settings.

    Returns:
        The processed audio signal with chorus applied (float32).
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32)

    # Import Chorus here to avoid potential circular imports if effects were split
    try:
        from pedalboard import Chorus
    except ImportError:
        raise ImportError("Pedalboard library is required for the chorus effect. Please install it.")

    # Instantiate the chorus effect
    # Note: pedalboard.Chorus does not have a 'num_voices' parameter.
    chorus_effect = Chorus(
        rate_hz=params.rate_hz,
        depth=params.depth,
        centre_delay_ms=params.delay_ms, # Map delay_ms to centre_delay_ms
        feedback=params.feedback,
        mix=params.wet_dry_mix # Map wet_dry_mix to mix
    )

    # Create a Pedalboard instance with the chorus effect
    board = Pedalboard([chorus_effect])

    # Process the audio (pedalboard expects float32)
    audio_float32 = audio.astype(np.float32)
    chorused_signal = board(audio_float32, sample_rate=sample_rate)

    # Ensure output shape matches input channel count if possible
    # Pedalboard Chorus usually outputs stereo, even for mono input
    if audio.ndim == 1 and chorused_signal.ndim == 2:
        # If input was mono, decide if output should be mono (average channels) or keep stereo
        # For now, let's keep the stereo output as it's characteristic of chorus
        pass # Keep stereo output
    elif audio.ndim == 2 and chorused_signal.ndim == 1 and audio.shape[1] == 1:
         # This case is unlikely with Chorus but handle defensively
         chorused_signal = chorused_signal.reshape(-1, 1)

    # Ensure output length matches input length (pedalboard chorus shouldn't change length)
    if chorused_signal.shape[0] != audio.shape[0]:
        # This shouldn't happen with Chorus, but handle defensively
        target_len = audio.shape[0]
        current_len = chorused_signal.shape[0]
        if current_len > target_len:
            chorused_signal = chorused_signal[:target_len, ...]
        else:
            padding_shape = (target_len - current_len,) + chorused_signal.shape[1:]
            padding = np.zeros(padding_shape, dtype=chorused_signal.dtype)
            chorused_signal = np.concatenate((chorused_signal, padding), axis=0)

    return chorused_signal.astype(np.float32) # Return float32

