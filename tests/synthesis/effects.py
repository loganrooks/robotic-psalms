import pytest
import numpy as np
import soundfile as sf
import io
import os
from pathlib import Path

# Import the class to be tested
from robotic_psalms.synthesis.effects import ReverbEffect, AudioEffect
from robotic_psalms.synthesis.base import ParameterEnum

# --- Test Fixtures ---

@pytest.fixture
def sample_rate():
    """Returns a standard sample rate."""
    return 44100

@pytest.fixture
    duration = 1.0 # 1 second
    frequency = 440.0 # A4 note
    t = np.linspace(0., duration, int(sample_rate * duration), endpoint=False)
    return 0.5 * np.sin(2 * np.pi * frequency * t)

@pytest.fixture
def stereo_audio_data(sample_rate):
    """Returns a simple stereo audio signal."""
    duration = 1.0 # 1 second
    frequency_l = 440.0 # A4
    frequency_r = 442.0 # Slightly detuned
    t = np.linspace(0., duration, int(sample_rate * duration), endpoint=False)
    left_channel = 0.5 * np.sin(2 * np.pi * frequency_l * t)
    right_channel = 0.5 * np.sin(2 * np.pi * frequency_r * t)
    # Shape needs to be (n_samples, n_channels) for pedalboard
    return np.vstack((left_channel, right_channel)).T

# --- Test AudioEffect Base Class ---

def test_audio_effect_is_abstract():
    """Verify that AudioEffect cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class AudioEffect"):
        AudioEffect()

# --- Test ReverbEffect ---

def test_reverb_effect_init_default():
    """Test ReverbEffect initialization with default parameters."""
    reverb = ReverbEffect()
    assert reverb.reverberance == 0.5
    assert reverb.damping == 0.5
    assert reverb.room_scale == 0.5
    assert reverb.stereo_depth == 1.0
    assert reverb.pre_delay == 0.0
    assert reverb.wet_gain == 0.0
    assert reverb.dry_gain == 1.0 # Default derived from wet_gain

def test_reverb_effect_init_custom():
    """Test ReverbEffect initialization with custom parameters."""
    params = {
        ParameterEnum.REVERBERANCE: 0.8,
        ParameterEnum.DAMPING: 0.2,
        ParameterEnum.ROOM_SIZE: 0.9, # Note: ParameterEnum uses ROOM_SIZE
        ParameterEnum.STEREO_WIDTH: 0.7, # Note: ParameterEnum uses STEREO_WIDTH
        ParameterEnum.PRE_DELAY: 0.1,
        ParameterEnum.WET_GAIN: 0.3,
        ParameterEnum.DRY_GAIN: 0.6, # Explicitly set dry gain
    }
    reverb = ReverbEffect(params=params)
    assert reverb.reverberance == 0.8
    assert reverb.damping == 0.2
    assert reverb.room_scale == 0.9
    assert reverb.stereo_depth == 0.7
    assert reverb.pre_delay == 0.1
    assert reverb.wet_gain == 0.3
    assert reverb.dry_gain == 0.6 # Should use the provided dry gain

@pytest.mark.parametrize("param, value, expected_value", [
    (ParameterEnum.REVERBERANCE, 0.7, 0.7),
    (ParameterEnum.REVERBERANCE, 1.2, 1.0), # Clamp above max
    (ParameterEnum.REVERBERANCE, -0.5, 0.0), # Clamp below min
    (ParameterEnum.DAMPING, 0.3, 0.3),
    (ParameterEnum.DAMPING, 1.1, 1.0),
    (ParameterEnum.DAMPING, -0.2, 0.0),
    (ParameterEnum.ROOM_SIZE, 0.8, 0.8),
    (ParameterEnum.ROOM_SIZE, 1.5, 1.0),
    (ParameterEnum.ROOM_SIZE, -0.1, 0.0),
    (ParameterEnum.STEREO_WIDTH, 0.6, 0.6),
    (ParameterEnum.STEREO_WIDTH, 1.2, 1.0),
    (ParameterEnum.STEREO_WIDTH, -0.3, 0.0),
    (ParameterEnum.PRE_DELAY, 0.05, 0.05),
    (ParameterEnum.PRE_DELAY, 0.5, 0.2), # Clamp above max (assuming max is 0.2 for pre_delay)
    (ParameterEnum.PRE_DELAY, -0.1, 0.0),
    (ParameterEnum.WET_GAIN, 0.4, 0.4),
    (ParameterEnum.WET_GAIN, 1.5, 1.0),
    (ParameterEnum.WET_GAIN, -0.2, 0.0),
    (ParameterEnum.DRY_GAIN, 0.7, 0.7),
    (ParameterEnum.DRY_GAIN, 1.1, 1.0),
    (ParameterEnum.DRY_GAIN, -0.1, 0.0),
])
def test_reverb_effect_set_parameter_clamping(param, value, expected_value):
    """Test setting parameters with clamping."""
    reverb = ReverbEffect()
    reverb.set_parameter(param, value)

    # Check the corresponding attribute in the ReverbEffect instance
    if param == ParameterEnum.REVERBERANCE:
        assert reverb.reverberance == expected_value
    elif param == ParameterEnum.DAMPING:
        assert reverb.damping == expected_value
    elif param == ParameterEnum.ROOM_SIZE:
        assert reverb.room_scale == expected_value
    elif param == ParameterEnum.STEREO_WIDTH:
        assert reverb.stereo_depth == expected_value
    elif param == ParameterEnum.PRE_DELAY:
        assert reverb.pre_delay == expected_value
    elif param == ParameterEnum.WET_GAIN:
        assert reverb.wet_gain == expected_value
    elif param == ParameterEnum.DRY_GAIN:
        assert reverb.dry_gain == expected_value

def test_reverb_effect_set_parameter_invalid_name():
    """Test setting an invalid parameter name raises an error."""
    reverb = ReverbEffect()
    with pytest.raises(AttributeError): # pedalboard.Reverb raises AttributeError
        reverb.set_parameter("invalid_param", 0.5) # type: ignore

def test_reverb_effect_apply_mono(mono_audio_data, sample_rate):
    """Test applying reverb effect to mono audio."""
    reverb = ReverbEffect(params={ParameterEnum.WET_GAIN: 0.5, ParameterEnum.DRY_GAIN: 0.5}) # Ensure effect is audible
    processed_audio = reverb.apply(mono_audio_data, sample_rate)

    assert isinstance(processed_audio, np.ndarray)
    assert processed_audio.shape == mono_audio_data.shape # Mono in -> Mono out
    assert processed_audio.dtype == np.float32
    # Check that the audio data has changed (effect was applied)
    assert not np.allclose(processed_audio, mono_audio_data)

def test_reverb_effect_apply_stereo(stereo_audio_data, sample_rate):
    """Test applying reverb effect to stereo audio."""
    reverb = ReverbEffect(params={ParameterEnum.WET_GAIN: 0.5, ParameterEnum.DRY_GAIN: 0.5}) # Ensure effect is audible
    processed_audio = reverb.apply(stereo_audio_data, sample_rate)

    assert isinstance(processed_audio, np.ndarray)
    assert processed_audio.shape == stereo_audio_data.shape # Stereo in -> Stereo out
    assert processed_audio.dtype == np.float32
    # Check that the audio data has changed
    assert not np.allclose(processed_audio, stereo_audio_data)

def test_reverb_effect_apply_no_change(mono_audio_data, sample_rate):
    """Test applying reverb with wet gain 0 results in no change."""
    reverb = ReverbEffect(params={ParameterEnum.WET_GAIN: 0.0, ParameterEnum.DRY_GAIN: 1.0})
    processed_audio = reverb.apply(mono_audio_data, sample_rate)

    assert isinstance(processed_audio, np.ndarray)
    assert processed_audio.shape == mono_audio_data.shape
    assert processed_audio.dtype == np.float32
    # Should be very close to the original
    np.testing.assert_allclose(processed_audio, mono_audio_data, atol=1e-6) # Allow for tiny floating point differences

def test_reverb_effect_apply_different_params(mono_audio_data, sample_rate):
    """Test that applying reverb with different parameters yields different results."""
    reverb1 = ReverbEffect(params={ParameterEnum.WET_GAIN: 0.2, ParameterEnum.DRY_GAIN: 0.8, ParameterEnum.ROOM_SIZE: 0.2})
    reverb2 = ReverbEffect(params={ParameterEnum.WET_GAIN: 0.8, ParameterEnum.DRY_GAIN: 0.2, ParameterEnum.ROOM_SIZE: 0.8})

    processed1 = reverb1.apply(mono_audio_data, sample_rate)
    processed2 = reverb2.apply(mono_audio_data, sample_rate)

    assert not np.allclose(processed1, processed2)

def test_reverb_effect_apply_empty_input(sample_rate):
    """Test applying reverb to an empty array."""
    reverb = ReverbEffect()
    empty_audio = np.array([], dtype=np.float32)
    processed_audio = reverb.apply(empty_audio, sample_rate)
    assert isinstance(processed_audio, np.ndarray)
    assert processed_audio.size == 0

def test_reverb_effect_apply_invalid_input_type(sample_rate):
    """Test applying reverb to invalid input type raises TypeError."""
    reverb = ReverbEffect()
    invalid_input = [1, 2, 3] # List instead of numpy array
    with pytest.raises(TypeError): # pedalboard raises TypeError
        reverb.apply(invalid_input, sample_rate) # type: ignore

# --- Test AudioEffect Base Class (Again, after defining a concrete subclass) ---

def test_audio_effect_base_class_instantiation_with_subclass():
    """Verify that a class inheriting from AudioEffect can be instantiated."""
    try:
        _ = ReverbEffect() # Instantiate the concrete subclass
    except TypeError:
        pytest.fail("Instantiation of a concrete subclass should not raise TypeError")

def test_audio_effect_has_apply_method():
    """Verify that the AudioEffect base class defines an apply method."""
    assert hasattr(AudioEffect, 'apply')
    # Check if it's abstract (though this is implicitly tested by the inability to instantiate AudioEffect directly)
