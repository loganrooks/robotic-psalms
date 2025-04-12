import pytest
import numpy as np
import logging
from unittest.mock import patch, MagicMock, ANY
from typing import List, Tuple, Optional


from robotic_psalms.synthesis.vox_dei import VoxDeiSynthesisError
from robotic_psalms.synthesis.tts.engines.espeak import EspeakNGWrapper
from robotic_psalms.synthesis.effects import FormantShiftParameters # Added import

# Attempt to import the non-existent MIDI parser function and error for patching
# Import the actual MIDI parser function and error class
from robotic_psalms.utils.midi_parser import parse_midi_melody, MidiParsingError

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

# Note: The test 'test_synthesize_text_invalid_bandpass_range' was removed
# as it tested a warning from the old _android_filter which is now obsolete.
# Filter parameter validation is handled within the effects functions and their tests.

# Note: Testing internal normalization/padding logic via public interface is complex.
# Coverage for those specific lines might remain lower without direct private method tests.

# --- Melodic Contour Tests (REQ-ART-MEL-01) ---

@pytest.fixture
def sample_melody() -> List[Tuple[float, float]]:
    """Provides a simple ascending scale melody."""
    # (Pitch in Hz, Duration in seconds)
    return [
        (261.63, 0.5), # C4
        (293.66, 0.5), # D4
        (329.63, 0.5), # E4
        (349.23, 0.5), # F4
    ]

# Removed obsolete test: test_synthesize_text_accepts_melody_argument
# Removed obsolete test: test_synthesize_text_applies_melody_contour

def test_synthesize_text_handles_no_melody():
    """Test that synthesize_text works normally without a melody argument."""
    config = PsalmConfig()
    synthesizer = VoxDeiSynthesizer(config=config)
    text_input = "Test"
    base_audio = np.random.rand(100).astype(np.float32)
    sample_rate = 22050

    # Mock the base TTS synthesis and the (currently non-existent) melody application
    with patch.object(EspeakNGWrapper, 'synth', return_value=(base_audio, sample_rate)), \
         patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_melody_contour') as mock_apply_melody:

        # Call without the melody argument
        audio_output, sr_output = synthesizer.synthesize_text(text_input)

    # Assert basic synthesis worked
    assert isinstance(audio_output, np.ndarray)
    assert sr_output == sample_rate
    assert audio_output.size > 0

    # Assert that melody application was NOT called
    mock_apply_melody.assert_not_called()


# --- MIDI Input Tests (REQ-ART-MEL-02 - Red Phase) ---

# Placeholder path for a dummy MIDI file
TEST_MIDI_PATH = "tests/fixtures/simple_melody.mid"

# Removed obsolete test: test_synthesize_text_accepts_midi_path_argument

@patch('robotic_psalms.synthesis.vox_dei.parse_midi_melody')
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_melody_contour')
def test_synthesize_text_calls_midi_parser_when_path_provided(mock_apply_contour, mock_parse_midi, sample_melody):
    """Test that parse_midi_melody is called when midi_path is provided."""
    config = PsalmConfig()
    synthesizer = VoxDeiSynthesizer(config=config)
    text_input = "MIDI Melody"
    base_audio = np.random.rand(100).astype(np.float32)
    sample_rate = 22050

    # Configure the mock parser to return a sample melody
    mock_parse_midi.return_value = sample_melody

    # Mock the base TTS synthesis
    with patch.object(EspeakNGWrapper, 'synth', return_value=(base_audio, sample_rate)):
        # Call synthesize_text with the midi_path
        synthesizer.synthesize_text(text_input, midi_path=TEST_MIDI_PATH)


    # Assert that the MIDI parser was called correctly
    # This will fail with AttributeError if parse_midi_melody is not imported/used,
    # or AssertionError if not called.
    mock_parse_midi.assert_called_once_with(TEST_MIDI_PATH, instrument_index=0)

    # Assert that the contour application was called with the result from the parser
    mock_apply_contour.assert_called_once_with(ANY, sample_rate, sample_melody)


@patch('robotic_psalms.synthesis.vox_dei.parse_midi_melody')
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_melody_contour')
def test_synthesize_text_no_midi_calls_when_path_is_none(mock_apply_contour, mock_parse_midi):
    """Test that MIDI parser and contour application are not called if midi_path is None."""
    config = PsalmConfig()
    synthesizer = VoxDeiSynthesizer(config=config)
    text_input = "No MIDI"
    base_audio = np.random.rand(100).astype(np.float32)
    sample_rate = 22050

    # Mock the base TTS synthesis
    with patch.object(EspeakNGWrapper, 'synth', return_value=(base_audio, sample_rate)):
        # Call without midi_path (it should default to None)
        synthesizer.synthesize_text(text_input)
        # Explicitly call with midi_path=None
        synthesizer.synthesize_text(text_input, midi_path=None)

    # Assert that neither the parser nor the contour application were called
    mock_parse_midi.assert_not_called()
    mock_apply_contour.assert_not_called()

# TODO: Add test case where BOTH melody and midi_path are provided (define expected behavior - e.g., midi_path takes precedence?)



def test_apply_melody_contour_shifts_pitch(sample_melody):
    """Directly test if _apply_melody_contour shifts pitch as expected (XFAIL)."""
    config = PsalmConfig()
    synthesizer = VoxDeiSynthesizer(config=config)
    sample_rate = 22050
    duration = sum(d for _, d in sample_melody) # Total duration from melody
    original_freq = 220.0 # A3

    # Create a simple sine wave as input
    t = np.linspace(0., duration, int(sample_rate * duration), endpoint=False)
    input_audio = (0.5 * np.sin(2. * np.pi * original_freq * t)).astype(np.float32)

    # Apply the melody contour directly
    output_audio = synthesizer._apply_melody_contour(input_audio, sample_rate, sample_melody)

    # --- Verification (Complex Part - XFAIL) ---
    # Ideally, we'd analyze the pitch contour of output_audio.
    # This requires robust pitch detection (like pyin) and segmenting the output
    # according to the melody durations to check the average pitch in each segment.

    # Example using pyin (simplified - likely needs refinement)
    import librosa
    segment_start_sample = 0
    detected_pitches = []
    for target_pitch_hz, duration_sec in sample_melody:
        segment_end_sample = min(segment_start_sample + int(duration_sec * sample_rate), len(output_audio))
        segment = output_audio[segment_start_sample:segment_end_sample]

        if len(segment) > int(0.1 * sample_rate): # Min duration for pyin
            f0, voiced_flag, _ = librosa.pyin(
                segment.astype(np.float32),
                fmin=float(librosa.note_to_hz('C2')), # Cast to float
                fmax=float(librosa.note_to_hz('C7')), # Cast to float
                sr=sample_rate
            )
            voiced_f0 = f0[voiced_flag]
            if np.any(voiced_flag) and not np.all(np.isnan(voiced_f0)):
                detected_pitch = np.nanmean(voiced_f0)
                detected_pitches.append(detected_pitch)
                # Basic assertion (likely too strict for real-world pyin results)
                # Use absolute tolerance of 10 Hz as per REQ-STAB-04
                assert np.isclose(detected_pitch, target_pitch_hz, atol=10.0), \
                    f"Segment expected {target_pitch_hz:.1f} Hz (+/- 10 Hz), detected ~{detected_pitch:.1f} Hz"
            else:
                pytest.fail(f"Could not detect voiced pitch in segment for target {target_pitch_hz:.1f} Hz")
        else:
             pytest.fail(f"Output segment too short for pitch analysis (target {target_pitch_hz:.1f} Hz)")

        segment_start_sample = segment_end_sample

    assert len(detected_pitches) == len(sample_melody), "Mismatch between number of melody segments and detected pitches"
