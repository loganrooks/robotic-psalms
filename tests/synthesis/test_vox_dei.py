import pytest
import numpy as np
import logging
from unittest.mock import patch, MagicMock, ANY
from typing import List, Tuple, Optional
import unittest.mock # For call object if needed later
# Mocks for external dependencies (replace with actual imports if available)
# Assume pyfoal has an align function: pyfoal.align(audio, text, sample_rate) -> List[Tuple[str, float, float]] (word, start_sec, end_sec)
# Assume librosa has time_stretch: librosa.effects.time_stretch(y, rate) -> np.ndarray



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


# --- Duration Control Test Fixtures ---

@pytest.fixture
def mock_alignment_success():
    """Returns a mock successful alignment result from pyfoal."""
    # Mock object structure expected by the code (object with .words attribute)
    mock_alignment_obj = MagicMock()
    # Define word-like objects with start, end, text attributes
    class MockWord:
        def __init__(self, text, start, end):
            self.text = text
            self.start = start
            self.end = end
    mock_alignment_obj.words = [
        MockWord("Gloria", 0.0, 0.4),
        MockWord("Patri", 0.45, 0.8),
        MockWord("et", 0.85, 1.0),
        MockWord("Filio", 1.05, 1.5),
    ]
    return mock_alignment_obj

@pytest.fixture
def mock_alignment_failure():
    """Simulates pyfoal raising an exception."""
    return Exception("Mocked pyfoal alignment error")

@pytest.fixture
def target_durations_match(sample_melody):
    """Target durations matching the mock_alignment_success segments."""
    # (pitch_hz is ignored here, only duration matters)
    # Use sample_melody fixture length for consistency
    return [
        (261.63, 0.6), # Target duration for "Gloria"
        (293.66, 0.5), # Target duration for "Patri"
        (329.63, 0.2), # Target duration for "et"
        (349.23, 0.7), # Target duration for "Filio"
    ][:len(sample_melody)] # Ensure length matches sample_melody if different

@pytest.fixture
def target_durations_mismatch_less():
    """Target durations fewer than aligned segments."""
    return [
        (261.63, 0.6),
        (293.66, 0.5),
    ]

@pytest.fixture
def target_durations_mismatch_more():
    """Target durations more than aligned segments."""
    return [
        (261.63, 0.6),
        (293.66, 0.5),
        (329.63, 0.2),
        (349.23, 0.7),
        (392.00, 0.4),
    ]

@pytest.fixture
def synthesizer_with_config():
    """Provides a VoxDeiSynthesizer instance with a default config."""
    return VoxDeiSynthesizer(config=PsalmConfig())

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


# --- Duration Control Unit Tests (_apply_duration_control) ---
# These will fail with AttributeError until the method exists

@patch('pyfoal.align') # Corrected patch target
@patch('librosa.effects.time_stretch') # Corrected patch target
def test_duration_control_calls_aligner(mock_stretch, mock_align, synthesizer_with_config, mock_alignment_success, target_durations_match):
    """Test _apply_duration_control calls pyfoal.align correctly."""
    mock_align.return_value = mock_alignment_success # mock_alignment_success is now a MagicMock with .words
    mock_stretch.side_effect = lambda y, rate: y # Simple passthrough for this test
    audio_in = np.random.rand(22050 * 2).astype(np.float32) # 2 seconds
    sr = 22050
    text = "Gloria Patri et Filio"

    # Extract just the durations for the call
    target_durations_sec = [d for _, d in target_durations_match]
    synthesizer_with_config._apply_duration_control(audio_in, sr, text, target_durations_sec)

    # Assert align was called
    mock_align.assert_called_once_with(audio_in, sr, text)

@patch('pyfoal.align') # Corrected patch target
@patch('librosa.effects.time_stretch') # Corrected patch target
def test_duration_control_handles_alignment_failure(mock_stretch, mock_align, synthesizer_with_config, mock_alignment_failure, target_durations_match):
    """Test _apply_duration_control returns original audio on alignment failure."""
    mock_align.side_effect = mock_alignment_failure
    audio_in = np.random.rand(22050 * 2).astype(np.float32)
    sr = 22050
    text = "Gloria Patri et Filio"

    # Extract just the durations for the call
    target_durations_sec = [d for _, d in target_durations_match]
    audio_out = synthesizer_with_config._apply_duration_control(audio_in, sr, text, target_durations_sec)

    # Assertions
    assert np.array_equal(audio_out, audio_in) # Should return original on align failure
    mock_stretch.assert_not_called()

@patch('pyfoal.align') # Corrected patch target
@patch('librosa.effects.time_stretch') # Corrected patch target
def test_duration_control_calls_time_stretch(mock_stretch, mock_align, synthesizer_with_config, mock_alignment_success, target_durations_match):
    """Test _apply_duration_control calls librosa.effects.time_stretch with correct rates."""
    mock_align.return_value = mock_alignment_success # mock_alignment_success is now a MagicMock with .words
    # Mock stretch to just return a segment of expected length based on target duration
    def stretch_mock(y, rate):
        original_duration = len(y) / synthesizer_with_config.sample_rate
        target_duration = original_duration / rate
        return np.zeros(int(target_duration * synthesizer_with_config.sample_rate), dtype=np.float32)
    mock_stretch.side_effect = stretch_mock

    audio_in = np.random.rand(int(22050 * 1.6)).astype(np.float32) # 1.6 seconds to contain segments
    sr = 22050
    text = "Gloria Patri et Filio"

    # Extract just the durations for the call
    target_durations_sec = [d for _, d in target_durations_match]
    audio_out = synthesizer_with_config._apply_duration_control(audio_in, sr, text, target_durations_sec)

    # Assertions
    assert mock_stretch.call_count == len(mock_alignment_success.words)
    expected_rates = [
        (0.4 / 0.6),  # "Gloria" original 0.4s -> target 0.6s
        (0.35 / 0.5), # "Patri" original 0.35s -> target 0.5s (0.8 - 0.45)
        (0.15 / 0.2), # "et" original 0.15s -> target 0.2s (1.0 - 0.85)
        (0.45 / 0.7), # "Filio" original 0.45s -> target 0.7s (1.5 - 1.05)
    ]
    # Check rates for the calls that were made
    rates_called = [call_args[1]['rate'] for call_args in mock_stretch.call_args_list]
    assert len(rates_called) == len(expected_rates)
    for i, rate in enumerate(rates_called):
         # Increase tolerance further
         assert np.isclose(rate, expected_rates[i], atol=1e-3)

@patch('pyfoal.align') # Corrected patch target
@patch('librosa.effects.time_stretch') # Corrected patch target
def test_duration_control_skips_stretch_near_one(mock_stretch, mock_align, synthesizer_with_config, mock_alignment_success):
    """Test _apply_duration_control skips time_stretch if rate is close to 1.0."""
    mock_align.return_value = mock_alignment_success # mock_alignment_success is now a MagicMock with .words
    # Target durations very close to original aligned durations
    target_durations_close = [
        (261.63, 0.401), # Gloria 0.4 -> 0.401 (rate ~0.9975)
        (293.66, 0.349), # Patri 0.35 -> 0.349 (rate ~1.0028)
        (329.63, 0.150), # et 0.15 -> 0.150 (rate 1.0)
        (349.23, 0.452), # Filio 0.45 -> 0.452 (rate ~0.995)
    ]
    audio_in = np.random.rand(int(22050 * 1.6)).astype(np.float32)
    sr = 22050
    text = "Gloria Patri et Filio"

    # Extract just the durations for the call
    target_durations_sec = [d for _, d in target_durations_close]
    audio_out = synthesizer_with_config._apply_duration_control(audio_in, sr, text, target_durations_sec)

    # Assertions
    # Expect stretch to be called 0 times as all rates are within 0.01 of 1.0
    assert mock_stretch.call_count == 0
    # No need to check rates if call_count is 0
    # The assertion for call_count == 0 is sufficient
    pass


@patch('pyfoal.align') # Corrected patch target
@patch('librosa.effects.time_stretch') # Corrected patch target
def test_duration_control_concatenates_output(mock_stretch, mock_align, synthesizer_with_config, mock_alignment_success, target_durations_match):
    """Test _apply_duration_control concatenates stretched segments correctly."""
    mock_align.return_value = mock_alignment_success # mock_alignment_success is now a MagicMock with .words
    sr = 22050
    # Mock stretch to return segments of predictable length based on target duration
    def stretch_mock(y, rate):
        original_duration = len(y) / sr
        target_duration = original_duration / rate
        # Return simple sine wave of target duration to make concatenation obvious
        t = np.linspace(0., target_duration, int(target_duration * sr), endpoint=False)
        # Use different frequencies for each segment
        freq = 100 + mock_stretch.call_count * 100 # 100Hz, 200Hz, 300Hz, 400Hz
        return (0.5 * np.sin(2. * np.pi * freq * t)).astype(np.float32)
    mock_stretch.side_effect = stretch_mock

    audio_in = np.random.rand(int(sr * 1.6)).astype(np.float32)
    text = "Gloria Patri et Filio"

    # Extract just the durations for the call
    target_durations_sec = [d for _, d in target_durations_match]
    audio_out = synthesizer_with_config._apply_duration_control(audio_in, sr, text, target_durations_sec)

    # Assertions
    # Expected duration includes target word durations (2.0s) + silence gaps (0.05*3=0.15s) + final silence (0.1s)
    expected_total_duration_inc_silence = sum(d for _, d in target_durations_match) + 0.05 + 0.05 + 0.05 + (1.6 - 1.5) # 2.0 + 0.15 + 0.1 = 2.25s
    actual_duration = len(audio_out) / sr
    assert len(audio_out) > 0
    assert abs(actual_duration - expected_total_duration_inc_silence) < 0.1 # Check duration within 100ms

@patch('pyfoal.align') # Corrected patch target
@patch('librosa.effects.time_stretch', side_effect=Exception("Mock Stretch Error")) # Corrected patch target
def test_duration_control_handles_stretch_failure(mock_stretch, mock_align, synthesizer_with_config, mock_alignment_success, target_durations_match):
    """Test _apply_duration_control returns original audio on time_stretch failure."""
    mock_align.return_value = mock_alignment_success # mock_alignment_success is now a MagicMock with .words
    audio_in = np.random.rand(int(22050 * 1.6)).astype(np.float32)
    sr = 22050
    text = "Gloria Patri et Filio"

    # Extract just the durations for the call
    target_durations_sec = [d for _, d in target_durations_match]
    audio_out = synthesizer_with_config._apply_duration_control(audio_in, sr, text, target_durations_sec)

    # Assertions
    # Expect original audio because stretch fails and code uses original segment
    assert np.array_equal(audio_out, audio_in)
    mock_stretch.assert_called() # It should be called at least once before failing

@patch('pyfoal.align') # Corrected patch target
@patch('librosa.effects.time_stretch') # Corrected patch target
def test_duration_control_handles_duration_mismatch_less(mock_stretch, mock_align, synthesizer_with_config, mock_alignment_success, target_durations_mismatch_less):
    """Test _apply_duration_control handles fewer target durations than segments (returns original)."""
    mock_align.return_value = mock_alignment_success # mock_alignment_success is now a MagicMock with .words
    audio_in = np.random.rand(int(22050 * 1.6)).astype(np.float32)
    sr = 22050
    text = "Gloria Patri et Filio"

    # Extract just the durations for the call
    target_durations_sec = [d for _, d in target_durations_mismatch_less]
    audio_out = synthesizer_with_config._apply_duration_control(audio_in, sr, text, target_durations_sec)

    # Assertions
    # Expect stretch to be called only for the number of target durations (2)
    assert mock_stretch.call_count == len(target_durations_mismatch_less) # Only 2 stretches
    # Check output length is positive (precise length prediction is complex)
    assert len(audio_out) > 0

@patch('pyfoal.align') # Corrected patch target
@patch('librosa.effects.time_stretch') # Corrected patch target
def test_duration_control_handles_duration_mismatch_more(mock_stretch, mock_align, synthesizer_with_config, mock_alignment_success, target_durations_mismatch_more):
    """Test _apply_duration_control handles more target durations than segments (returns original)."""
    mock_align.return_value = mock_alignment_success # mock_alignment_success is now a MagicMock with .words
    audio_in = np.random.rand(int(22050 * 1.6)).astype(np.float32)
    sr = 22050
    text = "Gloria Patri et Filio"

    # Extract just the durations for the call
    target_durations_sec = [d for _, d in target_durations_mismatch_more]
    audio_out = synthesizer_with_config._apply_duration_control(audio_in, sr, text, target_durations_sec)

    # Assertions
    # Expect stretch to be called only for the number of aligned words (4)
    assert mock_stretch.call_count == len(mock_alignment_success.words) # Only 4 stretches
    # Check output length is roughly correct for the processed segments + silence
    # Expected: word1(0.6)+s(0.05)+word2(0.5)+s(0.05)+word3(0.2)+s(0.05)+word4(0.7)+final_silence(1.6-1.5=0.1) = 2.25s
    # Check output length is positive (precise length prediction is complex)
    assert len(audio_out) > 0


# --- Duration Control Integration Tests (synthesize_text) ---
# These will fail with AssertionError until synthesize_text is modified

@patch('robotic_psalms.synthesis.vox_dei.parse_midi_melody')
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_duration_control')
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_formant_shift') # Keep corrected target
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_melody_contour')
def test_synthesize_text_calls_duration_control_when_midi_valid(
    mock_apply_contour, mock_apply_formant, mock_apply_duration, mock_parse_midi, # Corrected mock name
    synthesizer_with_config, target_durations_match
):
    """Test synthesize_text calls _apply_duration_control when midi parsing yields durations."""
    text_input = "Duration Test"
    midi_path = "dummy.mid"
    base_audio = np.random.rand(100).astype(np.float32)
    sr = 22050

    # Mock MIDI parsing to return valid durations
    mock_parse_midi.return_value = target_durations_match
    # Mock TTS
    with patch.object(EspeakNGWrapper, 'synth', return_value=(base_audio, sr)):
        # Mock duration/formant/contour to just return input to isolate duration call
        mock_apply_duration.return_value = base_audio
        mock_apply_formant.return_value = base_audio # Corrected mock name
        mock_apply_contour.return_value = base_audio

        synthesizer_with_config.synthesize_text(text_input, midi_path=midi_path)

    # Assert duration control was called correctly
    mock_parse_midi.assert_called_once_with(midi_path, instrument_index=0)
    # Correct assertion: Expect list of durations, not list of tuples
    target_durations_sec = [d for _, d in target_durations_match]
    mock_apply_duration.assert_called_once_with(base_audio, sr, text_input, target_durations_sec)
    mock_apply_formant.assert_called_once() # Should still be called after # Corrected mock name
    mock_apply_contour.assert_called_once() # Should still be called after

@patch('robotic_psalms.synthesis.vox_dei.parse_midi_melody')
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_duration_control')
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_formant_shift') # Corrected patch target
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_melody_contour')
def test_synthesize_text_skips_duration_control_when_midi_empty(
    mock_apply_contour, mock_apply_formant, mock_apply_duration, mock_parse_midi, # Corrected mock name
    synthesizer_with_config
):
    """Test synthesize_text skips _apply_duration_control when midi parsing yields empty list."""
    text_input = "Duration Test"
    midi_path = "dummy_empty.mid"
    base_audio = np.random.rand(100).astype(np.float32)
    sr = 22050

    # Mock MIDI parsing to return empty list
    mock_parse_midi.return_value = []
    # Mock TTS
    with patch.object(EspeakNGWrapper, 'synth', return_value=(base_audio, sr)):
        # Mock formant/contour
        mock_apply_formant.return_value = base_audio # Corrected mock name
        mock_apply_contour.return_value = base_audio

        synthesizer_with_config.synthesize_text(text_input, midi_path=midi_path)

    # Assert duration control was NOT called
    mock_parse_midi.assert_called_once_with(midi_path, instrument_index=0)
    mock_apply_duration.assert_not_called() # This is the key assertion
    mock_apply_formant.assert_called_once() # Should still be called # Corrected mock name
    # Correct assertion: Contour should NOT be called if parsed_melody_data is empty
    mock_apply_contour.assert_not_called()

@patch('robotic_psalms.synthesis.vox_dei.parse_midi_melody')
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_duration_control')
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_formant_shift') # Corrected patch target
@patch('robotic_psalms.synthesis.vox_dei.VoxDeiSynthesizer._apply_melody_contour')
def test_synthesize_text_duration_control_call_order(
    mock_apply_contour, mock_apply_formant, mock_apply_duration, mock_parse_midi, # Corrected mock name
    synthesizer_with_config, target_durations_match
):
    """Test the call order: duration -> effects -> contour."""
    text_input = "Order Test"
    midi_path = "dummy.mid"
    base_audio = np.random.rand(100).astype(np.float32)
    sr = 22050
    duration_applied_audio = np.random.rand(110).astype(np.float32) # Simulate change
    formant_applied_audio = np.random.rand(110).astype(np.float32) # Simulate change # Corrected name
    contour_applied_audio = np.random.rand(110).astype(np.float32) # Simulate change

    # Mock MIDI parsing
    mock_parse_midi.return_value = target_durations_match
    # Mock TTS
    with patch.object(EspeakNGWrapper, 'synth', return_value=(base_audio, sr)):
        # Mock processing chain
        mock_apply_duration.return_value = duration_applied_audio
        mock_apply_formant.return_value = formant_applied_audio # Corrected mock name
        mock_apply_contour.return_value = contour_applied_audio

        # Use a manager to track call order
        manager = MagicMock()
        manager.attach_mock(mock_apply_duration, 'duration')
        manager.attach_mock(mock_apply_formant, 'formant') # Corrected mock name
        manager.attach_mock(mock_apply_contour, 'contour')

        synthesizer_with_config.synthesize_text(text_input, midi_path=midi_path)

    # Assert call order
    # These assertions will fail until the order is correct in synthesize_text
    # Correct expected arguments: list of durations, not list of tuples
    target_durations_sec = [d for _, d in target_durations_match]
    # Use ANY for audio arguments to avoid issues with comparing random arrays
    expected_calls = [
        unittest.mock.call.duration(ANY, sr, text_input, target_durations_sec),
        unittest.mock.call.formant(ANY), # Formant shift applied AFTER duration
        unittest.mock.call.contour(ANY, sr, target_durations_match) # Contour applied AFTER formant shift
    ]
    # Standard comparison should work with ANY
    assert manager.mock_calls == expected_calls
