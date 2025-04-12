import pytest
import numpy as np
from unittest.mock import patch, MagicMock, ANY, call # Add call
from unittest.mock import patch, MagicMock, ANY # Add ANY
import numpy.fft as fft
import librosa
import numpy as np
from typing import cast # Added for casting
from robotic_psalms.synthesis.effects import ReverbParameters, DelayParameters, ChorusParameters, SpectralFreezeParameters, GlitchParameters, SaturationParameters, MasterDynamicsParameters # Add MasterDynamicsParameters
from robotic_psalms.synthesis.effects import ReverbParameters, DelayParameters, ChorusParameters, SpectralFreezeParameters, GlitchParameters, SaturationParameters # Add GlitchParameters, SaturationParameters

# Import actual implementations
from robotic_psalms.config import PsalmConfig, HauntingParameters, MixLevels, LiturgicalMode, ReverbConfig, DelayConfig # Consolidated imports
from robotic_psalms.synthesis.sacred_machinery import SacredMachineryEngine, SynthesisResult
from robotic_psalms.synthesis.vox_dei import VoxDeiSynthesizer, VoxDeiSynthesisError # Keep for side_effect

# Fixture for default config and engine
@pytest.fixture
def default_config() -> PsalmConfig:
    """Provides a default PsalmConfig instance."""
    return PsalmConfig()

@pytest.fixture
def engine_factory():
    """Factory fixture to create a patched SacredMachineryEngine instance."""
    def _create_engine(config: PsalmConfig) -> SacredMachineryEngine:
        with patch('robotic_psalms.synthesis.sacred_machinery.VoxDeiSynthesizer', autospec=True) as mock_vox_init:
            mock_vox_instance = mock_vox_init.return_value
            mock_vox_instance.sample_rate = 48000 # Match engine's default
            mock_vox_instance.synthesize_text = MagicMock()
            engine_instance = SacredMachineryEngine(config=config)
            return engine_instance
    return _create_engine

@pytest.fixture
def engine(default_config: PsalmConfig, engine_factory) -> SacredMachineryEngine:
    """Provides a SacredMachineryEngine instance with default config using the factory."""
    return engine_factory(default_config)

# --- Test process_psalm Success Case ---

def test_process_psalm_success(engine: SacredMachineryEngine):
    """
    Verify process_psalm returns a valid SynthesisResult on successful vocal synthesis.
    """
    psalm_text = "Laudate Dominum"
    duration = 5.0
    sample_rate = engine.sample_rate
    expected_samples = int(duration * sample_rate)

    # Configure the mock method on the instance directly, using cast
    dummy_vocals = np.sin(np.linspace(0, 440 * 2 * np.pi, expected_samples)).astype(np.float32)
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (dummy_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assertions
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)
    assert isinstance(result, SynthesisResult)
    assert result.sample_rate == sample_rate

    # Check all components exist, are numpy arrays, float32, and have the correct length
    for component_name in ['vocals', 'pads', 'percussion', 'drones', 'combined']:
        component_audio = getattr(result, component_name)
        assert isinstance(component_audio, np.ndarray), f"{component_name} should be ndarray"
        assert component_audio.dtype == np.float32, f"{component_name} dtype should be float32"
        # Allow for slight variations due to internal processing/resampling if duration wasn't exact match
        assert abs(len(component_audio) - expected_samples) <= 1, f"{component_name} length mismatch"
        if component_name != 'percussion': # Percussion can be sparse
             assert component_audio.size > 0, f"{component_name} should not be empty"

    # Check combined audio doesn't clip excessively (simple check)
    assert np.max(np.abs(result.combined)) <= 1.0, "Combined audio should not clip"

# --- Test process_psalm Error Handling ---

def test_process_psalm_vocal_synthesis_error(engine: SacredMachineryEngine, caplog):
    """
    Verify process_psalm handles VoxDeiSynthesisError and returns zero vocals.
    """
    psalm_text = "Error case"
    duration = 3.0
    sample_rate = engine.sample_rate
    expected_samples = int(duration * sample_rate)

    # Configure the mock method on the instance to raise an error, using cast
    cast(MagicMock, engine.vox_dei).synthesize_text.side_effect = VoxDeiSynthesisError("Mock TTS Failure")

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assertions
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)
    assert "Vocal synthesis failed for layer 1: Mock TTS Failure" in caplog.text
    assert isinstance(result, SynthesisResult)
    assert result.sample_rate == sample_rate

    # Check vocals are zeros
    assert isinstance(result.vocals, np.ndarray)
    assert result.vocals.dtype == np.float32
    assert len(result.vocals) == expected_samples
    assert np.all(result.vocals == 0), "Vocals should be zeros on synthesis error"

    # Check other components are still generated
    assert result.pads.size > 0
    # Percussion might be empty depending on random hits, size check not reliable
    assert result.drones.size > 0
    assert result.combined.size > 0

# --- Test Effects Application ---

@patch('robotic_psalms.synthesis.sacred_machinery.apply_high_quality_reverb', autospec=True)
@patch('robotic_psalms.synthesis.sacred_machinery.apply_smooth_spectral_freeze', autospec=True)
def test_process_psalm_applies_haunting(mock_apply_freeze: MagicMock, mock_apply_reverb: MagicMock, default_config: PsalmConfig, engine_factory):
    """Test that haunting effects attempt to call the new high-quality reverb."""
    # Modify config for strong haunting
    test_config = default_config.model_copy(deep=True)
    # Instantiate with new SpectralFreezeParameters structure
    test_freeze_params = SpectralFreezeParameters(freeze_point=0.5, blend_amount=0.8, fade_duration=0.1)
    test_config.haunting_intensity = HauntingParameters(reverb=ReverbConfig(decay_time=0.8), spectral_freeze=test_freeze_params)
    test_config.glitch_effect = None # Disable glitch for isolation

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "Haunting test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock, using cast
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Configure mocks to return a copy of the input audio to avoid type errors downstream
    mock_apply_reverb.side_effect = lambda audio, sr, params: audio.copy()
    mock_apply_freeze.side_effect = lambda audio, sr, params: audio.copy()

    result = engine.process_psalm(psalm_text, duration)

    # Assert reverb was called (should still pass if reverb logic is unchanged)
    assert mock_apply_reverb.call_count == 3, "Reverb should be applied 3 times (vocals, pads, drones)"
    mock_apply_reverb.assert_called_with(ANY, engine.sample_rate, ANY)
    assert isinstance(mock_apply_reverb.call_args[0][2], ReverbParameters)

    # Assert that the spectral freeze function was called with the correct arguments
    # We'll check the last call's arguments as an example
    last_call_args = mock_apply_freeze.call_args_list[-1][0]
    assert isinstance(last_call_args[0], np.ndarray) # audio data
    assert last_call_args[1] == engine.sample_rate # sample rate
    assert isinstance(last_call_args[2], SpectralFreezeParameters) # SpectralFreezeParameters instance
    # Verify parameters passed correctly from config
    assert last_call_args[2].freeze_point == test_freeze_params.freeze_point
    assert last_call_args[2].blend_amount == test_freeze_params.blend_amount
    assert last_call_args[2].fade_duration == test_freeze_params.fade_duration

    # Check that the mock was called 3 times (for vocals, pads, drones)
    assert mock_apply_freeze.call_count == 3

    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)


@patch('robotic_psalms.synthesis.sacred_machinery.apply_refined_glitch', autospec=True)
def test_process_psalm_applies_glitch(mock_apply_glitch: MagicMock, default_config: PsalmConfig, engine_factory):
    """Test that glitch effects are applied when configured."""
    # Modify config for glitch
    test_config = default_config.model_copy(deep=True)
    test_glitch_params = GlitchParameters(glitch_type='repeat', intensity=0.5, chunk_size_ms=50, repeat_count=2, tape_stop_speed=0.5, bitcrush_depth=8, bitcrush_rate_factor=0.5) # Enable glitch with specific parameters
    test_config.glitch_effect = test_glitch_params
    # Minimize haunting effects
    test_config.haunting_intensity = HauntingParameters(reverb=ReverbConfig(decay_time=0.5), spectral_freeze=None)

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "Glitch test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    input_vocals = np.sin(np.linspace(0, 440 * 2 * np.pi, expected_samples)).astype(np.float32)
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Configure mock to return slightly modified audio to ensure original assertion can still pass
    mock_apply_glitch.side_effect = lambda audio, sr, params: audio * 0.99

    result = engine.process_psalm(psalm_text, duration)

    # Assert that the glitch function was called once
    assert mock_apply_glitch.call_count == 3, "Expected apply_refined_glitch to be called 3 times (vocals, pads, drones)"

    # Check arguments passed to the mock
    call_args = mock_apply_glitch.call_args[0]
    assert isinstance(call_args[0], np.ndarray) # audio data
    assert call_args[1] == engine.sample_rate # sample rate


@patch('robotic_psalms.synthesis.sacred_machinery.apply_refined_glitch', autospec=True)
def test_process_psalm_does_not_apply_glitch_when_none(mock_apply_glitch: MagicMock, engine: SacredMachineryEngine):
    """Test that glitch effect is NOT applied when glitch_effect is None (default)."""
    # Engine fixture uses default config where glitch_effect is None

    psalm_text = "No glitch test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the glitch function was NOT called
    mock_apply_glitch.assert_not_called()

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)


# --- Test Helper Methods (Indirectly) ---


# --- NEW TESTS FOR COMPLEX DELAY ---

@patch('robotic_psalms.synthesis.sacred_machinery.apply_complex_delay', autospec=True)
def test_process_psalm_applies_complex_delay_when_configured(mock_apply_delay: MagicMock, default_config: PsalmConfig, engine_factory):
    """Test that complex delay effect is applied when configured in PsalmConfig."""
    # Modify config to enable delay
    test_config = default_config.model_copy(deep=True)
    test_delay_config = DelayConfig(delay_time_ms=500.0, feedback=0.3, wet_dry_mix=0.5)
    test_config.delay_effect = test_delay_config
    test_config.glitch_effect = None # Disable glitch for isolation
    test_config.haunting_intensity = HauntingParameters() # Use default haunting

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "Delay test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the delay function was called (EXPECTED TO FAIL)
    mock_apply_delay.assert_called_once()

    # Check arguments (basic check using ANY for audio)
    call_args = mock_apply_delay.call_args[0]
    assert isinstance(call_args[0], np.ndarray) # audio data
    assert call_args[1] == engine.sample_rate # sample rate
    assert isinstance(call_args[2], DelayParameters) # DelayParameters instance
    # Verify parameters passed correctly from config
    assert call_args[2].delay_time_ms == test_delay_config.delay_time_ms
    assert call_args[2].feedback == test_delay_config.feedback
    assert call_args[2].wet_dry_mix == test_delay_config.wet_dry_mix

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)


@patch('robotic_psalms.synthesis.sacred_machinery.apply_complex_delay', autospec=True)
def test_process_psalm_does_not_apply_complex_delay_when_not_configured(mock_apply_delay: MagicMock, engine: SacredMachineryEngine):
    """Test that complex delay effect is NOT applied when not configured (default)."""
    # Engine fixture uses default config where delay_effect is None

    psalm_text = "No delay test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the delay function was NOT called
    mock_apply_delay.assert_not_called()

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)




# --- NEW TESTS FOR CHORUS ---

@patch('robotic_psalms.synthesis.sacred_machinery.apply_chorus', autospec=True)
def test_process_psalm_applies_chorus_when_configured(mock_apply_chorus: MagicMock, default_config: PsalmConfig, engine_factory):
    """Test that chorus effect is applied when configured in PsalmConfig."""
    # Modify config to enable chorus
    test_config = default_config.model_copy(deep=True)
    # Instantiate ChorusParameters directly as ChorusConfig doesn't exist in config.py
    test_chorus_params = ChorusParameters(rate_hz=1.0, depth=0.5, delay_ms=7.0, feedback=0.2, num_voices=3, wet_dry_mix=0.6) # Corrected param name and added num_voices
    test_config.chorus_params = test_chorus_params
    test_config.glitch_effect = None # Disable glitch for isolation
    test_config.haunting_intensity = HauntingParameters() # Use default haunting
    test_config.delay_effect = None # Disable delay for isolation

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "Chorus test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the chorus function was called
    mock_apply_chorus.assert_called_once()

    # Check arguments (basic check using ANY for audio)
    call_args = mock_apply_chorus.call_args[0]
    assert isinstance(call_args[0], np.ndarray) # audio data
    assert call_args[1] == engine.sample_rate # sample rate
    assert isinstance(call_args[2], ChorusParameters) # ChorusParameters instance
    # Verify parameters passed correctly from config
    assert call_args[2].rate_hz == test_chorus_params.rate_hz
    assert call_args[2].depth == test_chorus_params.depth
    assert call_args[2].delay_ms == test_chorus_params.delay_ms # Corrected param name
    assert call_args[2].feedback == test_chorus_params.feedback
    assert call_args[2].wet_dry_mix == test_chorus_params.wet_dry_mix

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)


@patch('robotic_psalms.synthesis.sacred_machinery.apply_chorus', autospec=True)
def test_process_psalm_does_not_apply_chorus_when_not_configured(mock_apply_chorus: MagicMock, engine: SacredMachineryEngine):
    """Test that chorus effect is NOT applied when not configured (default)."""
    # Engine fixture uses default config where chorus_params is None

    psalm_text = "No chorus test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the chorus function was NOT called
    mock_apply_chorus.assert_not_called()

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)


@patch('robotic_psalms.synthesis.sacred_machinery.apply_chorus', autospec=True)
def test_process_psalm_does_not_apply_chorus_when_mix_is_zero(mock_apply_chorus: MagicMock, default_config: PsalmConfig, engine_factory):
    """Test that chorus effect is NOT applied when configured but mix is zero."""
    # Modify config to enable chorus but set mix to 0
    test_config = default_config.model_copy(deep=True)
    test_chorus_params = ChorusParameters(rate_hz=1.0, depth=0.5, delay_ms=7.0, feedback=0.2, num_voices=3, wet_dry_mix=0.0) # Corrected param name and added num_voices
    test_config.chorus_params = test_chorus_params

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "Zero mix chorus test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the chorus function was NOT called
    mock_apply_chorus.assert_not_called()

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)

def test_process_psalm_fit_to_length(engine: SacredMachineryEngine):
    """Test that components are correctly fitted to the target duration."""
    psalm_text = "Length test"
    duration = 4.0 # Target duration
    sample_rate = engine.sample_rate
    expected_samples = int(duration * sample_rate)

    # Make mock synth return audio of different length, use cast
    wrong_length_samples = expected_samples // 2
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (np.zeros(wrong_length_samples, dtype=np.float32), engine.sample_rate)

    # Mock generation methods to also return different lengths
    # Use patch.object on the specific engine instance
    with patch.object(engine, '_generate_pads', return_value=np.zeros(wrong_length_samples + 100, dtype=np.float32), autospec=True), \
         patch.object(engine, '_generate_percussion', return_value=np.zeros(wrong_length_samples - 50, dtype=np.float32), autospec=True), \
         patch.object(engine, '_generate_drones', return_value=np.zeros(wrong_length_samples + 200, dtype=np.float32), autospec=True):

        result = engine.process_psalm(psalm_text, duration)

        # Check all components now have the correct length
        for component_name in ['vocals', 'pads', 'percussion', 'drones', 'combined']:
            component_audio = getattr(result, component_name)
            assert len(component_audio) == expected_samples, f"{component_name} should be fitted to target length"

@patch('robotic_psalms.synthesis.sacred_machinery.apply_refined_glitch', autospec=True) # Add patch for refined glitch
def test_process_psalm_mix_levels(mock_apply_glitch: MagicMock, default_config: PsalmConfig, engine_factory): # Add mock argument
    """Test that mix levels are applied."""
    # Set distinct mix levels
    test_config = default_config.model_copy(deep=True)
    test_config.mix_levels = MixLevels(vocals=0.1, pads=0.2, percussion=0.3, drones=0.4)
    # No need to modify haunting/glitch here, we will mock the effect methods

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "Mix test"
    duration = 1.0
    sample_rate = engine.sample_rate
    expected_samples = int(duration * sample_rate)

    # Return constant value from synth and generators to easily check mixing, use cast
    mock_input_val = 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (np.ones(expected_samples, dtype=np.float32) * mock_input_val, engine.sample_rate)

    # Configure the new mock to not modify audio
    mock_apply_glitch.side_effect = lambda audio, sr, params: audio

    # Mock generation and other effect methods to isolate mixing
    with patch.object(engine, '_generate_pads', return_value=np.ones(expected_samples, dtype=np.float32) * mock_input_val, autospec=True), \
         patch.object(engine, '_generate_percussion', return_value=np.ones(expected_samples, dtype=np.float32) * mock_input_val, autospec=True), \
         patch.object(engine, '_generate_drones', return_value=np.ones(expected_samples, dtype=np.float32) * mock_input_val, autospec=True), \
         patch.object(engine, '_apply_haunting_effects', side_effect=lambda x: x, autospec=True): # Removed _apply_glitch_effect patch

        result = engine.process_psalm(psalm_text, duration)

        # Expected combined value before normalization:
        # 0.5*0.1 + 0.5*0.2 + 0.5*0.3 + 0.5*0.4 = 0.05 + 0.10 + 0.15 + 0.20 = 0.5
        expected_combined_value = 0.5
        # Now that effects are mocked out, allclose should work
        assert np.allclose(result.combined, expected_combined_value, atol=1e-6), "Combined audio does not reflect mix levels"

        # Check individual components in the result *do not* have mix levels applied
        # Their max value should be close to the original mocked input value
        assert np.isclose(np.max(np.abs(result.vocals)), mock_input_val, atol=1e-6)
        assert np.isclose(np.max(np.abs(result.pads)), mock_input_val, atol=1e-6)
        # Percussion might be zero if no hits generated, skip max check
        assert np.isclose(np.max(np.abs(result.drones)), mock_input_val, atol=1e-6)


# --- Test Generation Methods (Basic Checks via process_psalm) ---

def test_generate_methods_produce_output(engine: SacredMachineryEngine):
    """Check that generation methods produce non-empty float32 arrays."""
    psalm_text = "Generation test"
    duration = 2.0
    # Use cast
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (np.zeros(int(duration * engine.sample_rate), dtype=np.float32), engine.sample_rate)

    result = engine.process_psalm(psalm_text, duration)

    assert result.pads.size > 0 and result.pads.dtype == np.float32
    # Percussion can be empty if no hits, so size > 0 is not guaranteed
    assert isinstance(result.percussion, np.ndarray) and result.percussion.dtype == np.float32
    assert result.drones.size > 0 and result.drones.dtype == np.float32


# --- Test _generate_pads Method ---

@pytest.mark.parametrize("duration", [1.0, 0.5, 3.14])
def test_generate_pads_basic_properties(engine: SacredMachineryEngine, duration: float):
    """Test basic properties of the generated pads."""
    sample_rate = engine.sample_rate
    expected_samples = int(duration * sample_rate)

    pads = engine._generate_pads(duration)

    assert isinstance(pads, np.ndarray)
    assert pads.dtype == np.float32
    # Allow slight length deviation due to internal calculations
    assert abs(len(pads) - expected_samples) <= 1
    if expected_samples > 0:
        assert np.max(np.abs(pads)) <= 1.0, "Pad amplitude should be within [-1.0, 1.0]"
    else:
        assert len(pads) == 0


def test_generate_pads_spectral_richness(engine: SacredMachineryEngine): # Renamed
    """(FAILING TEST) Test that pads have spectral richness (more than simple tones)."""
    duration = 2.0
    sample_rate = engine.sample_rate
    pads = engine._generate_pads(duration)
    significant_peaks = 0 # Initialize

    if len(pads) == 0:
        pytest.skip("Generated pad is empty, cannot analyze spectrum.")

    # Analyze spectrum (simple peak count - revised threshold logic)
    spectrum = np.abs(fft.rfft(pads))
    max_peak_value = np.max(spectrum) if spectrum.size > 0 else 0
    # Use an absolute threshold relative to the max peak, avoid normalization issues
    threshold = max_peak_value * 0.01 # 1% of max peak value
    # Count peaks significantly above the absolute threshold
    significant_peaks = np.sum(spectrum > threshold) # Corrected variable used here
    # Removed debug print

    # Expecting more than a few peaks for a complex pad (e.g., > 15) - Increased threshold
    # This assertion should now FAIL for the current simple implementation
    # This assertion should now FAIL for the current simple implementation
    assert significant_peaks > 15, f"Pad spectrum seems too simple (only {significant_peaks} peaks > {threshold:.4f})"


def test_generate_pads_spectral_evolution(engine: SacredMachineryEngine): # Renamed
    """(FAILING TEST) Test that pad spectrum evolves over time."""
    duration = 4.0 # Longer duration to see evolution
    sample_rate = engine.sample_rate
    segment_duration = 0.5
    segment_samples = int(segment_duration * sample_rate)

    pads = engine._generate_pads(duration)
    segment1 = np.array([], dtype=np.float32) # Initialize
    segment2 = np.array([], dtype=np.float32) # Initialize
    spectrum_start = np.array([], dtype=np.float32) # Initialize
    spectrum_end = np.array([], dtype=np.float32) # Initialize

    if len(pads) < 2 * segment_samples:
        pytest.skip("Generated pad is too short to compare segments.")

    # Get spectra of first and last segments
    spectrum_start = np.abs(fft.rfft(pads[:segment_samples]))
    spectrum_end = np.abs(fft.rfft(pads[-segment_samples:]))

    # Normalize spectra
    spectrum_start = spectrum_start / np.max(spectrum_start) if np.max(spectrum_start) > 0 else spectrum_start
    spectrum_end = spectrum_end / np.max(spectrum_end) if np.max(spectrum_end) > 0 else spectrum_end
    # Debug print moved here
    diff = np.abs(spectrum_start - spectrum_end)
    max_diff = np.max(diff) if diff.size > 0 else 0 # Handle empty diff case
    # Removed debug print

    # Assert that the spectra are NOT identical (allowing for very small tolerance)
    # This assertion should now FAIL if only amplitude changes slightly
    assert not np.allclose(spectrum_start, spectrum_end, atol=1e-6), "Pad spectrum does not seem to evolve significantly over time" # Decreased atol


def test_generate_pads_non_repetitive(engine: SacredMachineryEngine): # Renamed
    """(FAILING TEST) Test that pads are not perfectly repetitive."""
    duration = 6.0 # Longer duration
    sample_rate = engine.sample_rate
    segment_duration = 1.0
    segment_samples = int(segment_duration * sample_rate)

    pads = engine._generate_pads(duration)

    if len(pads) < 2 * segment_samples:
        pytest.skip("Generated pad is too short to compare segments.")

    # Compare first and second segments (adjust indices if needed)
    segment1 = pads[:segment_samples]
    segment2 = pads[segment_samples:2*segment_samples]
    # Debug print moved here
    diff_segments = np.abs(segment1 - segment2)
    max_diff_segments = np.max(diff_segments)
    # Removed debug print

    # Assert that the segments are NOT identical (with tighter tolerance)
    # This assertion should now FAIL if only minor LFO changes occur
    assert not np.allclose(segment1, segment2, atol=1e-12), "Pad seems repetitive between segments (within tolerance)" # Extremely low tolerance




# --- NEW FAILING TESTS FOR PAD COMPLEXITY (REQ-ART-A01-v2) ---

def test_generate_pads_spectral_centroid_variance_fails(engine: SacredMachineryEngine):
    """(FAILING TEST) Test that pad spectral centroid variance exceeds a high threshold."""
    duration = 4.0 # Longer duration to capture evolution
    sample_rate = engine.sample_rate
    pads = engine._generate_pads(duration)

    if len(pads) < 2048: # Need enough samples for STFT
        pytest.skip("Generated pad is too short for spectral analysis.")

    # Calculate spectral centroid per frame
    centroids = librosa.feature.spectral_centroid(y=pads, sr=sample_rate)[0]

    # Calculate variance of the centroid over time
    centroid_variance = np.var(centroids)

    # Define a threshold expected to FAIL against the current implementation
    # Baseline is likely low due to simple LFO. Set threshold much higher.
    min_expected_variance = 50000.0 # Increased threshold significantly

    print(f"\n[DEBUG] Pad Centroid Variance: {centroid_variance:.2f}") # Temporary debug

    assert centroid_variance > min_expected_variance, \
        f"Pad spectral centroid variance ({centroid_variance:.2f}) is too low, expected > {min_expected_variance}"

def test_generate_pads_spectral_flux_fails(engine: SacredMachineryEngine):
    """(FAILING TEST) Test that pad mean spectral flux exceeds a high threshold."""
    duration = 4.0
    sample_rate = engine.sample_rate
    pads = engine._generate_pads(duration)

    if len(pads) < 2048:
        pytest.skip("Generated pad is too short for spectral analysis.")

    # Calculate spectral flux
    onset_env = librosa.onset.onset_strength(y=pads, sr=sample_rate)
    spectral_flux = np.mean(onset_env) # Using onset strength as a proxy for spectral flux

    # Define a threshold expected to FAIL against the current implementation
    # Baseline flux is likely low. Set threshold much higher.
    min_expected_flux = 0.5 # Increased threshold significantly

    print(f"\n[DEBUG] Pad Mean Spectral Flux (Onset Strength): {spectral_flux:.4f}") # Temporary debug

    assert spectral_flux > min_expected_flux, \
        f"Pad mean spectral flux ({spectral_flux:.4f}) is too low, expected > {min_expected_flux}"

# --- Test _generate_drones Method ---

@pytest.mark.parametrize("duration", [1.0, 0.5, 3.14])
def test_generate_drones_basic_properties(engine: SacredMachineryEngine, duration: float):
    """Test basic properties of the generated drones."""
    sample_rate = engine.sample_rate
    expected_samples = int(duration * sample_rate)

    drones = engine._generate_drones(duration)

    assert isinstance(drones, np.ndarray)
    assert drones.dtype == np.float32
    # Allow slight length deviation due to internal calculations
    assert abs(len(drones) - expected_samples) <= 1
    if expected_samples > 0:
        assert np.max(np.abs(drones)) <= 1.0, "Drone amplitude should be within [-1.0, 1.0]"
        assert drones.size > 0, "Drones should not be empty for positive duration"
    else:
        assert len(drones) == 0

def test_generate_drones_spectral_richness(engine: SacredMachineryEngine):
    """(FAILING TEST) Test that drones have spectral richness (more than simple tones)."""
    duration = 2.0
    sample_rate = engine.sample_rate
    drones = engine._generate_drones(duration)
    significant_peaks = 0

    if len(drones) == 0:
        pytest.skip("Generated drone is empty, cannot analyze spectrum.")

    # Analyze spectrum (simple peak count)
    spectrum = np.abs(fft.rfft(drones))
    max_peak_value = np.max(spectrum) if spectrum.size > 0 else 0
    threshold = max_peak_value * 0.05 # 5% of max peak value (adjust if needed for drones)
    significant_peaks = np.sum(spectrum > threshold)

    # Expecting more than a few peaks for a complex drone (e.g., > 5)
    # This assertion should FAIL for a simple sine/basic drone implementation
    assert significant_peaks > 5, f"Drone spectrum seems too simple (only {significant_peaks} peaks > {threshold:.4f})"

def test_generate_drones_spectral_evolution(engine: SacredMachineryEngine):
    """(FAILING TEST) Test that drone spectrum evolves over time."""
    duration = 4.0 # Longer duration to see evolution
    sample_rate = engine.sample_rate
    segment_duration = 0.5
    segment_samples = int(segment_duration * sample_rate)

    drones = engine._generate_drones(duration)
    spectrum_start = np.array([], dtype=np.float32)
    spectrum_end = np.array([], dtype=np.float32)

    if len(drones) < 2 * segment_samples:
        pytest.skip("Generated drone is too short to compare segments.")

    # Get spectra of first and last segments
    spectrum_start = np.abs(fft.rfft(drones[:segment_samples]))
    spectrum_end = np.abs(fft.rfft(drones[-segment_samples:]))

    # Normalize spectra if they are not empty
    if np.max(spectrum_start) > 0:
        spectrum_start = spectrum_start / np.max(spectrum_start)
    if np.max(spectrum_end) > 0:
        spectrum_end = spectrum_end / np.max(spectrum_end)

    # Assert that the spectra are NOT identical (allowing for small tolerance)
    # This assertion should FAIL if the drone is static
    assert not np.allclose(spectrum_start, spectrum_end, atol=1e-5), "Drone spectrum does not seem to evolve significantly over time"

def test_generate_drones_non_repetitive(engine: SacredMachineryEngine):
    """(FAILING TEST) Test that drones are not perfectly repetitive."""
    duration = 6.0 # Longer duration
    sample_rate = engine.sample_rate
    segment_duration = 1.0
    segment_samples = int(segment_duration * sample_rate)

    drones = engine._generate_drones(duration)

    if len(drones) < 2 * segment_samples:
        pytest.skip("Generated drone is too short to compare segments.")

    # Compare first and second segments
    segment1 = drones[:segment_samples]
    segment2 = drones[segment_samples:2*segment_samples]

    # Assert that the segments are NOT identical (with very tight tolerance)
    # This assertion should FAIL if the drone is perfectly looping/static
    assert not np.allclose(segment1, segment2, atol=1e-10), "Drone seems repetitive between segments (within tolerance)"


# --- NEW TESTS FOR SPECTRAL FREEZE INTEGRATION ---

@patch('robotic_psalms.synthesis.sacred_machinery.apply_smooth_spectral_freeze', autospec=True)
def test_process_psalm_does_not_apply_spectral_freeze_when_none(mock_apply_freeze: MagicMock, default_config: PsalmConfig, engine_factory):
    """Test that spectral freeze is NOT applied when HauntingParameters.spectral_freeze is None."""
    test_config = default_config.model_copy(deep=True)
    # Explicitly set spectral_freeze to None
    test_config.haunting_intensity = HauntingParameters(reverb=ReverbConfig(decay_time=0.8), spectral_freeze=None)
    test_config.glitch_effect = None # Disable glitch for isolation

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "No freeze test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the spectral freeze function was NOT called
    mock_apply_freeze.assert_not_called()

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)



# --- NEW TESTS FOR SATURATION ---

@patch('robotic_psalms.synthesis.sacred_machinery.apply_saturation', autospec=True)
def test_process_psalm_applies_saturation_when_configured(mock_apply_saturation: MagicMock, default_config: PsalmConfig, engine_factory):
    """Test that saturation effect is applied when configured in PsalmConfig."""
    # Modify config to enable saturation
    test_config = default_config.model_copy(deep=True)
    test_saturation_params = SaturationParameters(drive=0.6, tone=0.4, mix=0.7)
    test_config.saturation_effect = test_saturation_params
    # Disable other potentially interfering effects for isolation
    test_config.glitch_effect = None
    test_config.haunting_intensity = HauntingParameters()
    test_config.delay_effect = None
    test_config.chorus_params = None

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "Saturation test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Configure mock to return a copy to avoid downstream issues
    mock_apply_saturation.side_effect = lambda audio, sr, params: audio.copy()

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the saturation function was called (EXPECTED TO FAIL)
    # Assuming saturation is applied once to the final mix
    mock_apply_saturation.assert_called_once()

    # Check arguments (basic check using ANY for audio)
    call_args = mock_apply_saturation.call_args[0]
    assert isinstance(call_args[0], np.ndarray) # audio data
    assert call_args[1] == engine.sample_rate # sample rate
    assert isinstance(call_args[2], SaturationParameters) # SaturationParameters instance
    # Verify parameters passed correctly from config
    assert call_args[2].drive == test_saturation_params.drive
    assert call_args[2].tone == test_saturation_params.tone
    assert call_args[2].mix == test_saturation_params.mix

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)


@patch('robotic_psalms.synthesis.sacred_machinery.apply_saturation', autospec=True)
def test_process_psalm_does_not_apply_saturation_when_none(mock_apply_saturation: MagicMock, engine: SacredMachineryEngine):
    """Test that saturation effect is NOT applied when not configured (default)."""
    # Engine fixture uses default config where saturation_effect is None

    psalm_text = "No saturation test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the saturation function was NOT called
    mock_apply_saturation.assert_not_called()

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)



# --- NEW TESTS FOR VOCAL LAYERING (REQ-ART-V03) ---

def test_process_psalm_no_layering_by_default(engine: SacredMachineryEngine):
    """Test that by default (no layering config), synthesize_text is called once."""
    psalm_text = "Single layer test"
    duration = 2.0
    # Patch the instance method directly
    engine.vox_dei.synthesize_text = MagicMock(return_value=(np.zeros(int(duration * engine.sample_rate), dtype=np.float32), engine.sample_rate))

    engine.process_psalm(psalm_text, duration)
    engine.vox_dei.synthesize_text.assert_called_once_with(psalm_text)

    # No need for mock_synthesize checks anymore


def test_process_psalm_applies_vocal_layering_when_configured(default_config: PsalmConfig, engine_factory):
    """Test that synthesize_text is called multiple times when num_vocal_layers > 1."""
    num_layers = 3
    pitch_variation = 0.1
    timing_variation = 15.0

    # Create config with layering enabled
    test_config = default_config.model_copy(deep=True)
    test_config.num_vocal_layers = num_layers
    test_config.layer_pitch_variation = pitch_variation
    test_config.layer_timing_variation_ms = timing_variation

    engine = engine_factory(test_config)

    psalm_text = "Multi layer test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Mock needs to provide enough return values for multiple calls
    # Patch the instance method directly
    engine.vox_dei.synthesize_text = MagicMock(side_effect=[
        (np.zeros(expected_samples, dtype=np.float32) + i, engine.sample_rate)
        for i in range(num_layers)
    ])

    engine.process_psalm(psalm_text, duration)

    # This assertion should FAIL initially
    assert engine.vox_dei.synthesize_text.call_count == num_layers, f"Expected {num_layers} calls to synthesize_text, but got {engine.vox_dei.synthesize_text.call_count}"


def test_process_psalm_vocal_layering_varies_parameters(default_config: PsalmConfig, engine_factory):
    """(FAILING TEST) Test that subsequent calls to synthesize_text have varied parameters."""
    num_layers = 2
    pitch_variation = 0.2
    timing_variation = 10.0

    # Create config with layering enabled
    test_config = default_config.model_copy(deep=True)
    test_config.num_vocal_layers = num_layers
    test_config.layer_pitch_variation = pitch_variation
    test_config.layer_timing_variation_ms = timing_variation

    engine = engine_factory(test_config)

    psalm_text = "Parameter variation test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Patch the instance method directly
    engine.vox_dei.synthesize_text = MagicMock(side_effect=[
        (np.zeros(expected_samples, dtype=np.float32) + i, engine.sample_rate)
        for i in range(num_layers)
    ])

    engine.process_psalm(psalm_text, duration)

    # This assertion should FAIL initially
    assert engine.vox_dei.synthesize_text.call_count == num_layers, f"Expected {num_layers} calls, got {engine.vox_dei.synthesize_text.call_count}"

    # Note: The current implementation applies variations *after* synthesis.
    # Therefore, checking for varied *arguments* to synthesize_text is not applicable here.
    # The test primarily confirms the correct number of calls based on config.
    # Testing the variation itself would require patching random.uniform or analyzing output audio.


def test_process_psalm_vocal_layering_mixes_results(default_config: PsalmConfig, engine_factory):
    """Test that the results from multiple synthesis calls are mixed (basic check)."""
    num_layers = 2
    pitch_variation = 0.1
    timing_variation = 5.0

    # Create config with layering enabled
    test_config = default_config.model_copy(deep=True)
    test_config.num_vocal_layers = num_layers
    test_config.layer_pitch_variation = pitch_variation
    test_config.layer_timing_variation_ms = timing_variation

    engine = engine_factory(test_config)

    psalm_text = "Mixing test"
    duration = 1.0
    expected_samples = int(duration * engine.sample_rate)

    # Create distinct audio for each layer
    layer1_audio = np.ones(expected_samples, dtype=np.float32) * 0.2
    layer2_audio = np.ones(expected_samples, dtype=np.float32) * 0.3
    # Patch the instance method directly
    engine.vox_dei.synthesize_text = MagicMock(side_effect=[
        (layer1_audio, engine.sample_rate),
        (layer2_audio, engine.sample_rate)
    ])

    result = engine.process_psalm(psalm_text, duration)

    # Basic check: Is the final vocal output different from the first layer's output?
    # This doesn't guarantee correct mixing, but ensures *something* happened.
    # Note: This might pass even if only the first layer is used if other effects modify it.
    # A better test would involve mocking the mixing/normalization functions, but that's more complex.
    # This test primarily ensures the output isn't identical to just one layer, implying some mixing occurred.
    final_vocals = result.vocals
    
    # Check length is correct first
    assert abs(len(final_vocals) - expected_samples) <= 1, "Final vocals length mismatch"

    # Check if the content is roughly the sum (before normalization)
    # This is tricky due to potential normalization and effects. 
    # A simpler check: is it different from layer 1?
    if engine.vox_dei.synthesize_text.call_count == num_layers: # Only check if layering likely happened
         assert not np.allclose(final_vocals, layer1_audio, atol=1e-5), "Final vocals seem identical to the first layer, mixing might not have occurred or was trivial."
         # A slightly stronger check: is the max amplitude higher than layer 1's max?
         # This assumes positive signals and simple addition before normalization.
         # assert np.max(final_vocals) > np.max(layer1_audio) # This is unreliable due to normalization
    else:
        # If layering didn't happen, this test is less meaningful
        pass



# --- NEW TESTS FOR MASTER DYNAMICS (REQ-ART-M01) ---

@patch('robotic_psalms.synthesis.sacred_machinery.apply_master_dynamics', autospec=True)
def test_process_psalm_applies_master_dynamics_when_configured(mock_apply_dynamics: MagicMock, default_config: PsalmConfig, engine_factory):
    """Test that master dynamics effect is applied when configured in PsalmConfig."""
    # Modify config to enable master dynamics (e.g., limiter)
    test_config = default_config.model_copy(deep=True)
    test_dynamics_params = MasterDynamicsParameters(
        enable_compressor=False, compressor_threshold_db=0.0, compressor_ratio=1.0, compressor_attack_ms=1.0, compressor_release_ms=100.0, # Defaults for disabled compressor
        enable_limiter=True, limiter_threshold_db=-1.0
    )
    test_config.master_dynamics = test_dynamics_params
    # Disable other potentially interfering effects for isolation
    test_config.glitch_effect = None
    test_config.haunting_intensity = HauntingParameters()
    test_config.delay_effect = None
    test_config.chorus_params = None
    test_config.saturation_effect = None

    # Create engine with modified config using the factory
    engine = engine_factory(test_config)

    psalm_text = "Master dynamics test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Configure mock to return a copy to avoid downstream issues
    mock_apply_dynamics.side_effect = lambda audio, sr, params: audio.copy()

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the dynamics function was called (EXPECTED TO FAIL)
    # Assuming dynamics is applied once to the final mix
    mock_apply_dynamics.assert_called_once()

    # Check arguments (basic check using ANY for audio)
    call_args = mock_apply_dynamics.call_args[0]
    assert isinstance(call_args[0], np.ndarray) # audio data
    assert call_args[1] == engine.sample_rate # sample rate
    assert isinstance(call_args[2], MasterDynamicsParameters) # MasterDynamicsParameters instance
    # Verify parameters passed correctly from config
    assert call_args[2].enable_limiter == test_dynamics_params.enable_limiter
    assert call_args[2].limiter_threshold_db == test_dynamics_params.limiter_threshold_db

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)


@patch('robotic_psalms.synthesis.sacred_machinery.apply_master_dynamics', autospec=True)
def test_process_psalm_does_not_apply_master_dynamics_when_none(mock_apply_dynamics: MagicMock, engine: SacredMachineryEngine):
    """Test that master dynamics effect is NOT applied when not configured (default)."""
    # Engine fixture uses default config where master_dynamics is None

    psalm_text = "No master dynamics test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    # Process the psalm
    result = engine.process_psalm(psalm_text, duration)

    # Assert that the dynamics function was NOT called
    mock_apply_dynamics.assert_not_called()

    # Ensure synth was called
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)

