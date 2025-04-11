import pytest
import numpy as np
import logging
from unittest.mock import patch, MagicMock, ANY

from robotic_psalms.synthesis.vox_dei import VoxDeiSynthesisError
from robotic_psalms.synthesis.tts.engines.espeak import EspeakNGWrapper
from robotic_psalms.synthesis.effects import FormantShiftParameters # Added import

# Import the actual synthesizer and config
from robotic_psalms.config import PsalmConfig # Import config
from robotic_psalms.synthesis.vox_dei import VoxDeiSynthesizer
# Mock class removed

# TDD: Test robotic effects modify audio, including formant shift call
@patch('robotic_psalms.synthesis.vox_dei.apply_robust_formant_shift') # Patch the target function
def test_robotic_effects_modify_audio(mock_apply_robust_formant_shift): # Add mock argument
    """
    Verify that applying robotic effects changes the input audio data.
    """
    # Use the actual VoxDeiSynthesizer with a config that triggers formant shift
    config = PsalmConfig() # Create default config
    config.voice_range.formant_shift = 1.2 # Ensure formant shift is not 1.0
    synthesizer = VoxDeiSynthesizer(config=config)
    # Create some dummy input audio to be returned by the mock synth
    sample_rate = 22050 # Expected sample rate
    duration = 1.0
    frequency = 440
    t = np.linspace(0., duration, int(sample_rate * duration), endpoint=False)
    mock_synth_output_audio = 0.5 * np.sin(2. * np.pi * frequency * t)
    mock_synth_output_audio = mock_synth_output_audio.astype(np.float32)

    # Configure the mock to return a valid numpy array (e.g., the input audio)
    # This prevents TypeErrors in subsequent processing steps like filters
    mock_apply_robust_formant_shift.return_value = mock_synth_output_audio

    # Apply effects by calling synthesize_text
    # Mock the underlying synth call to return the simple sine wave
    with patch.object(EspeakNGWrapper, 'synth', return_value=(mock_synth_output_audio, sample_rate)) as mock_synth:
        # Unpack the tuple returned by synthesize_text
        output_audio, output_sample_rate = synthesizer.synthesize_text("Test effects")

    # Assertions
    assert isinstance(output_audio, np.ndarray), "Output audio should be a NumPy array"
    assert isinstance(output_sample_rate, int) and output_sample_rate > 0, "Output sample rate should be a positive integer"
    assert output_sample_rate == sample_rate, "Output sample rate should match expected"
    assert output_audio.dtype == np.float32, "Audio data type should be float32"
    assert output_audio.size > 0, "Output audio data should not be empty"
    # Check that the output is different from the raw input (effects were applied)
    # Use a tolerance due to float precision
    assert not np.allclose(mock_synth_output_audio, output_audio, atol=1e-6), "Output audio should be different from the raw synth output after applying effects"

    # --- Assertions for formant shift call ---
    # This assertion WILL FAIL until vox_dei.py is updated
    mock_apply_robust_formant_shift.assert_called_once()

    # Check arguments passed to the mocked function
    call_args_tuple, call_kwargs_dict = mock_apply_robust_formant_shift.call_args
    called_audio, called_sr = call_args_tuple # Unpack positional args
    called_params = call_kwargs_dict.get('params') # Get keyword arg

    assert np.array_equal(called_audio, mock_synth_output_audio), "Formant shift called with incorrect audio data"
    assert called_sr == synthesizer.sample_rate, "Formant shift called with incorrect sample rate" # Check against synthesizer's rate
    assert isinstance(called_params, FormantShiftParameters), "Formant shift not called with FormantShiftParameters instance"
    assert called_params.shift_factor == config.voice_range.formant_shift, "Formant shift called with incorrect shift_factor"

# TDD: Test VoxDeiSynthesizer returns audio
def test_vox_dei_synthesizer_returns_audio():
    """
    Verify that VoxDeiSynthesizer.synthesize_text returns non-empty audio data and sample rate.
    """
    # Use the actual VoxDeiSynthesizer with default config
    config = PsalmConfig() # Create default config
    synthesizer = VoxDeiSynthesizer(config=config)
    text_input = "Gloria Patri"
    # sample_rate = 22050 # Sample rate is returned by the function now

    # Synthesize
    # synthesize_text returns a tuple (audio_data, sample_rate)
    audio_output, output_sample_rate = synthesizer.synthesize_text(text_input)

    # Assertions
    assert isinstance(audio_output, np.ndarray), "Output audio should be a NumPy array"
    assert isinstance(output_sample_rate, int) and output_sample_rate > 0, "Output sample rate should be a positive integer"
    assert audio_output.dtype == np.float32, "Audio data type should be float32"
    assert audio_output.size > 0, "Synthesized audio data should not be empty"


# --- Initialization Error Tests ---

@patch('robotic_psalms.synthesis.vox_dei.EspeakNGWrapper', side_effect=Exception("Mock Espeak Init Fail"))
def test_vox_dei_init_espeak_fails(mock_espeak_init, caplog):
    """Test VoxDei handles EspeakNGWrapper initialization failure gracefully."""
    config = PsalmConfig()
    with caplog.at_level(logging.ERROR):
        synthesizer = VoxDeiSynthesizer(config=config)
    assert synthesizer.espeak is None
    assert "eSpeak-NG initialization failed: Mock Espeak Init Fail" in caplog.text
    mock_espeak_init.assert_called_once()

# --- Synthesis Error Tests ---

@patch('robotic_psalms.synthesis.vox_dei.EspeakNGWrapper', side_effect=Exception("Mock Espeak Init Fail"))
def test_synthesize_text_no_tts_engine(mock_espeak_init):
    """Test synthesize_text raises error if no TTS engine was initialized."""
    config = PsalmConfig()
    synthesizer = VoxDeiSynthesizer(config=config) # Espeak init will fail here
    assert synthesizer.espeak is None
    with pytest.raises(VoxDeiSynthesisError, match="No TTS engine available"):
        synthesizer.synthesize_text("Test")

# Mock the synth method to return empty array and 0 sample rate, simulating failure
@patch.object(EspeakNGWrapper, 'synth', return_value=(np.array([], dtype=np.float32), 0))
def test_synthesize_text_empty_tts_output(mock_synth):
    """Test synthesize_text raises error if TTS returns empty audio."""
    config = PsalmConfig()
    synthesizer = VoxDeiSynthesizer(config=config)
    assert synthesizer.espeak is not None # Ensure espeak was initialized
    # Expect VoxDeiSynthesisError because the underlying synth call returned an empty array
    with pytest.raises(VoxDeiSynthesisError, match="TTS returned empty audio data"):
        synthesizer.synthesize_text("Test")
    mock_synth.assert_called_once_with("Test")

@patch.object(EspeakNGWrapper, 'synth', side_effect=Exception("Mock Synth Error"))
def test_synthesize_text_synth_exception(mock_synth, caplog):
    """Test synthesize_text raises VoxDeiSynthesisError on underlying synth exception."""
    config = PsalmConfig()
    synthesizer = VoxDeiSynthesizer(config=config)
    assert synthesizer.espeak is not None
    with caplog.at_level(logging.ERROR):
        with pytest.raises(VoxDeiSynthesisError, match="TTS synthesis failed: Mock Synth Error"):
            synthesizer.synthesize_text("Test")
    mock_synth.assert_called_once_with("Test")
    assert "TTS synthesis failed: Mock Synth Error" in caplog.text

# --- Processing Edge Case Tests (via synthesize_text) ---

# Test for invalid bandpass range warning in android filter
@patch.object(EspeakNGWrapper, 'synth') # Mock synth
def test_synthesize_text_invalid_bandpass_range(mock_synth, caplog):
    """Test warning logged for invalid bandpass range in android filter."""
    # Return some valid audio and sample rate from mock synth
    sample_rate = 22050 # Use a standard rate here; the synthesizer's rate is overridden later
    mock_synth.return_value = (np.sin(np.linspace(0, 440 * 2 * np.pi, 1000)).astype(np.float32), sample_rate) # Short audio

    config = PsalmConfig()
    config.vocal_timbre.android = 1.0 # Ensure android filter is active
    config.vocal_timbre.choirboy = 0.0
    config.vocal_timbre.machinery = 0.0

    # Use a very low sample rate to force an invalid range [300, 3400] Hz
    low_sample_rate = 4000
    synthesizer = VoxDeiSynthesizer(config=config, sample_rate=low_sample_rate)

    with caplog.at_level(logging.WARNING):
        synthesizer.synthesize_text("Test bandpass")

    assert "Invalid bandpass range" in caplog.text
    mock_synth.assert_called_once()

# Note: Testing internal normalization/padding logic via public interface is complex.
# Coverage for those specific lines might remain lower without direct private method tests.
