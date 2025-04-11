import pytest
import numpy as np
import logging
from unittest.mock import patch, MagicMock
import soundfile as sf
import io
import os

from robotic_psalms.synthesis.tts.base import ParameterEnum
from robotic_psalms.synthesis.tts.engines.espeak import EspeakWrapper # For deprecated tests

# Import the actual TTS engine wrapper
from robotic_psalms.synthesis.tts.engines.espeak import EspeakNGWrapper
# Mock class removed

# TDD: Test TTS engine generates audio data
def test_tts_engine_generates_audio_data():
    """
    Verify that the TTS engine produces a non-empty NumPy array of float32 audio data and sample rate.
    """
    # Use the actual EspeakNGWrapper
    tts_engine = EspeakNGWrapper()
    text_input = "Laudate Dominum"

    # Synthesize audio
    # Call the correct method name 'synth' and unpack the tuple
    audio_output, sample_rate = tts_engine.synth(text_input)

    # Assertions
    assert isinstance(audio_output, np.ndarray), "Audio output should be a NumPy array"
    assert isinstance(sample_rate, int) and sample_rate > 0, "Sample rate should be a positive integer"
    assert audio_output.dtype == np.float32, "Audio data type should be float32"
    assert audio_output.size > 0, "Audio data should not be empty"


# --- Initialization Tests ---

def test_espeak_ng_wrapper_init_file_not_found():
    """Test FileNotFoundError is raised if espeak-ng command doesn't exist."""
    with patch('os.path.exists', return_value=False):
        with pytest.raises(FileNotFoundError, match="espeak-ng command not found"):
            EspeakNGWrapper()

# --- Synthesis Error Handling Tests ---

@patch('robotic_psalms.synthesis.tts.engines.espeak.subprocess.run')
def test_synth_subprocess_error(mock_run):
    """Test synth returns empty array and 0 rate if subprocess fails."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = b'espeak error'
    mock_run.return_value = mock_result

    tts_engine = EspeakNGWrapper()
    # Unpack the tuple
    audio_output, sample_rate = tts_engine.synth("Test")

    assert isinstance(audio_output, np.ndarray) # Check the audio part
    assert audio_output.size == 0 # Should be empty on error
    assert sample_rate == 0 # Sample rate should be 0 on error
    mock_run.assert_called_once()

@patch('robotic_psalms.synthesis.tts.engines.espeak.subprocess.run')
def test_synth_empty_stdout(mock_run):
    """Test synth returns empty array and 0 rate if subprocess succeeds but stdout is empty."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b''
    mock_run.return_value = mock_result

    tts_engine = EspeakNGWrapper()
    # Unpack the tuple
    audio_output, sample_rate = tts_engine.synth("Test")

    assert isinstance(audio_output, np.ndarray) # Check the audio part
    assert audio_output.size == 0 # Should be empty on error
    assert sample_rate == 0 # Sample rate should be 0 on error
    mock_run.assert_called_once()

@patch('robotic_psalms.synthesis.tts.engines.espeak.subprocess.run')
@patch('robotic_psalms.synthesis.tts.engines.espeak.sf.read', side_effect=Exception("Mock soundfile error"))
def test_synth_soundfile_read_error(mock_sf_read, mock_run):
    """Test synth returns empty array and 0 rate if soundfile.read fails."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    # Simulate some valid WAV header but sf.read will fail
    mock_result.stdout = b'RIFF\x00\x00\x00\x00WAVEfmt '
    mock_run.return_value = mock_result

    tts_engine = EspeakNGWrapper()
    # Unpack the tuple
    audio_output, sample_rate = tts_engine.synth("Test")

    assert isinstance(audio_output, np.ndarray) # Check the audio part
    assert audio_output.size == 0 # Should be empty on error
    assert sample_rate == 0 # Sample rate should be 0 on error
    mock_run.assert_called_once()
    mock_sf_read.assert_called_once()

@patch('robotic_psalms.synthesis.tts.engines.espeak.subprocess.run')
@patch('robotic_psalms.synthesis.tts.engines.espeak.os.remove', side_effect=OSError("Mock remove error"))
def test_synth_cleanup_error(mock_os_remove, mock_run, caplog):
    """Test synth still proceeds (and logs error) if temp file cleanup fails."""
    # Simulate successful synthesis first
    mock_result = MagicMock()
    mock_result.returncode = 0
    # Create dummy WAV data
    dummy_wav_data = io.BytesIO()
    expected_rate = 22050
    expected_audio = np.array([0.1, 0.2], dtype=np.float32)
    sf.write(dummy_wav_data, expected_audio, expected_rate, format='WAV')
    mock_result.stdout = dummy_wav_data.getvalue()
    mock_run.return_value = mock_result

    tts_engine = EspeakNGWrapper()
    with caplog.at_level(logging.ERROR):
        # Unpack the tuple
        audio_output, sample_rate = tts_engine.synth("Test cleanup")

    # Check audio output is still generated correctly
    assert isinstance(audio_output, np.ndarray) # Check the audio part
    assert sample_rate == expected_rate # Check the sample rate part
    assert audio_output.size > 0
    assert audio_output.dtype == np.float32
    # Add tolerance to account for minor float precision differences in WAV write/read simulation
    # Increased tolerance to 1e-4 based on previous failure
    np.testing.assert_allclose(audio_output, expected_audio, atol=1e-4) # Increased tolerance

    # Check that os.remove was called (it's mocked to raise error)
    mock_os_remove.assert_called_once()
    # Check that the error was logged
    assert "Error removing temporary file" in caplog.text
    assert "Mock remove error" in caplog.text

# --- Parameter Handling Tests ---

def test_set_parameter_unsupported(caplog):
    """Test setting an unsupported parameter logs a warning."""
    tts_engine = EspeakNGWrapper()
    invalid_param_value = 999 # Use an integer value not corresponding to any enum member
    with caplog.at_level(logging.WARNING):
        # Pass the integer directly. Python's runtime won't strictly enforce the type hint,
        # allowing the value to reach the `else` block in `set_parameter`.
        tts_engine.set_parameter(invalid_param_value, 100) # type: ignore

    # Check that the warning was logged
    assert "Unsupported parameter: 999" in caplog.text

@pytest.mark.parametrize("param, value, expected", [
    (ParameterEnum.RATE, 50, 80),      # Below min
    (ParameterEnum.RATE, 200, 200),    # Within range
    (ParameterEnum.PITCH, -10, 0),     # Below min
    (ParameterEnum.PITCH, 50, 50),     # Within range
    (ParameterEnum.PITCH, 150, 99),    # Above max
    (ParameterEnum.VOLUME, -50, 0),    # Below min
    (ParameterEnum.VOLUME, 100, 100),  # Within range
    (ParameterEnum.VOLUME, 250, 200),  # Above max
])
def test_set_parameter_clamping(param, value, expected):
    """Test that parameters are correctly clamped to their valid ranges."""
    tts_engine = EspeakNGWrapper()
    tts_engine.set_parameter(param, value)
    if param == ParameterEnum.RATE:
        assert tts_engine.rate == expected
    elif param == ParameterEnum.PITCH:
        assert tts_engine.pitch == expected
    elif param == ParameterEnum.VOLUME:
        assert tts_engine.volume == expected

def test_set_voice():
    """Test setting the voice parameter."""
    tts_engine = EspeakNGWrapper()
    new_voice = "fr"
    tts_engine.set_voice(new_voice)
    assert tts_engine.voice == new_voice

# --- Audio Processing Tests ---

@patch('robotic_psalms.synthesis.tts.engines.espeak.subprocess.run')
@patch('robotic_psalms.synthesis.tts.engines.espeak.sf.read')
def test_synth_handles_multichannel(mock_sf_read, mock_run):
    """Test synth correctly averages multi-channel audio."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b'dummy_wav_data'
    mock_run.return_value = mock_result

    # Simulate stereo float32 input
    stereo_data = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    expected_rate = 22050
    mock_sf_read.return_value = (stereo_data, expected_rate)

    tts_engine = EspeakNGWrapper()
    # Unpack the tuple
    audio_output, sample_rate = tts_engine.synth("Test stereo")

    assert isinstance(audio_output, np.ndarray) # Check the audio part
    assert sample_rate == expected_rate # Check the sample rate part
    assert audio_output.ndim == 1, "Output should be mono"
    assert audio_output.dtype == np.float32
    np.testing.assert_allclose(audio_output, np.array([0.15, 0.35], dtype=np.float32))
    mock_run.assert_called_once()
    mock_sf_read.assert_called_once()

@patch('robotic_psalms.synthesis.tts.engines.espeak.subprocess.run')
@patch('robotic_psalms.synthesis.tts.engines.espeak.sf.read')
def test_synth_handles_int16(mock_sf_read, mock_run):
    """Test synth correctly converts int16 audio to float32."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b'dummy_wav_data'
    mock_run.return_value = mock_result

    # Simulate mono int16 input
    int16_data = np.array([1638, -3276], dtype=np.int16)
    expected_rate = 22050
    mock_sf_read.return_value = (int16_data, expected_rate)

    tts_engine = EspeakNGWrapper()
    # Unpack the tuple
    audio_output, sample_rate = tts_engine.synth("Test int16")

    assert isinstance(audio_output, np.ndarray) # Check the audio part
    assert sample_rate == expected_rate # Check the sample rate part
    assert audio_output.ndim == 1
    assert audio_output.dtype == np.float32
    # Check if values are roughly scaled (exact conversion depends on sf.read behavior)
    # For int16, max is 32767. So 1638/32767 is approx 0.05
    # Check scaling: 1638 / 32767.0 (max int16) should be approx 0.05
    assert abs(audio_output[0] - (1638 / 32767.0)) < 1e-4 # Use 32767 for max int16
    mock_run.assert_called_once()
    mock_sf_read.assert_called_once()

# --- Deprecated Wrapper Tests ---

def test_deprecated_espeak_wrapper_init_raises():
    """Test initializing the deprecated EspeakWrapper raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="deprecated and non-functional"):
        EspeakWrapper()

@pytest.mark.parametrize("method_name, args", [
    ("set_voice", ("en",)),
    ("set_parameter", (ParameterEnum.RATE, 100)),
    ("synth", ("test",))
])
def test_deprecated_espeak_wrapper_methods_raise(method_name, args):
    """Test calling methods on the deprecated EspeakWrapper raises NotImplementedError."""
    # We can't instantiate it, so we patch __init__ to bypass the raise
    with patch.object(EspeakWrapper, '__init__', return_value=None):
        wrapper_instance = EspeakWrapper()
        method_to_call = getattr(wrapper_instance, method_name)
        with pytest.raises(NotImplementedError, match="deprecated"):
            method_to_call(*args)
