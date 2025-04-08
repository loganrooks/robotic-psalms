import pytest
import numpy as np

from robotic_psalms.synthesis.tts.engines.espeak import EspeakNGWrapper

# Remove Mock class

# TDD: Test TTS engine generates audio data
def test_tts_engine_generates_audio_data():
    """
    Verify that the TTS engine produces a non-empty NumPy array of float32 audio data.
    """
    # Use the actual EspeakNGWrapper
    try:
        tts_engine = EspeakNGWrapper()
    except Exception as e:
        pytest.fail(f"Failed to initialize EspeakNGWrapper: {e}")
    text_input = "Laudate Dominum"

    # Synthesize audio
    audio_output = tts_engine.synth(text_input)

    # Assertions
    assert isinstance(audio_output, np.ndarray), "Output should be a NumPy array"
    assert audio_output.dtype == np.float32, "Audio data type should be float32"
    assert audio_output.size > 0, "Audio data should not be empty"