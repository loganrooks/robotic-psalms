import numpy as np
from pydantic import BaseModel, Field, ConfigDict
import pedalboard

# Define validation ranges based on common sense and test cases
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

    reverb_effect = pedalboard.Reverb(
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
    reverberated_signal = reverb_effect(audio_padded, sample_rate=sample_rate)

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