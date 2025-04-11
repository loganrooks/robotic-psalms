import pytest
import numpy as np
from unittest.mock import patch, MagicMock, ANY # Add ANY
from typing import cast # Added for casting
from robotic_psalms.synthesis.effects import ReverbParameters # Add ReverbParameters

# Import actual implementations
from robotic_psalms.config import PsalmConfig, HauntingParameters, MixLevels, LiturgicalMode, ReverbConfig
from robotic_psalms.synthesis.sacred_machinery import SacredMachineryEngine, SynthesisResult
from robotic_psalms.synthesis.vox_dei import VoxDeiSynthesizer, VoxDeiSynthesisError # Keep for side_effect

# Fixture for default config and engine
@pytest.fixture
def default_config() -> PsalmConfig:
    """Provides a default PsalmConfig instance."""
    return PsalmConfig()

@pytest.fixture
def engine(default_config: PsalmConfig) -> SacredMachineryEngine:
    """Provides a SacredMachineryEngine instance with default config."""
    # Patch VoxDeiSynthesizer during engine init to avoid real TTS calls
    with patch('robotic_psalms.synthesis.sacred_machinery.VoxDeiSynthesizer', autospec=True) as mock_vox_init:
        # Configure the mock instance created by the patch
        mock_vox_instance = mock_vox_init.return_value
        mock_vox_instance.sample_rate = 48000 # Match engine's default
        # Ensure synthesize_text exists on the mock spec
        mock_vox_instance.synthesize_text = MagicMock()

        engine_instance = SacredMachineryEngine(config=default_config)
        # engine_instance.vox_dei is now the mock_vox_instance
        return engine_instance

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
    assert "Vocal synthesis failed: Mock TTS Failure" in caplog.text
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

@patch('robotic_psalms.synthesis.sacred_machinery.apply_high_quality_reverb', autospec=True) # Add patch
def test_process_psalm_applies_haunting(mock_apply_reverb: MagicMock, default_config: PsalmConfig): # Add mock arg
    """Test that haunting effects attempt to call the new high-quality reverb."""
    # Modify config for strong haunting
    default_config.haunting_intensity = HauntingParameters(reverb=ReverbConfig(decay_time=0.8), spectral_freeze=0.5)
    default_config.glitch_density = 0.0 # Disable glitch for isolation

    # Re-init engine with modified config, patching VoxDei again
    with patch('robotic_psalms.synthesis.sacred_machinery.VoxDeiSynthesizer', autospec=True) as mock_vox_init:
        mock_vox_instance = mock_vox_init.return_value
        mock_vox_instance.sample_rate = 48000
        engine = SacredMachineryEngine(config=default_config)

    psalm_text = "Haunting test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    # Provide simple input audio via the mock, using cast
    input_vocals = np.ones(expected_samples, dtype=np.float32) * 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    result = engine.process_psalm(psalm_text, duration)

    # Assert that the new reverb function was called (EXPECTED TO FAIL)
    assert mock_apply_reverb.call_count == 3, f"Expected 3 calls, but got {mock_apply_reverb.call_count}"
    # Check arguments (basic check using ANY for audio and params)
    # We expect reverb params derived from config.haunting_intensity
    mock_apply_reverb.assert_called_with(
        ANY, # The audio data passed to reverb
        engine.sample_rate,
        ANY # Expecting ReverbParameters instance
        # isinstance(mock_apply_reverb.call_args[0][2], ReverbParameters) # More specific check if needed later
    )

    # Original assertion (commented out/removed as focus shifts to the call)
    # assert not np.allclose(result.vocals, input_vocals, atol=1e-6), "Vocals should be modified by haunting effects"
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)


def test_process_psalm_applies_glitch(default_config: PsalmConfig):
    """Test that glitch effects are applied when configured."""
    # Modify config for glitch
    default_config.glitch_density = 0.8 # High density
    # Minimize haunting effects by setting to minimum allowed values
    default_config.haunting_intensity = HauntingParameters(reverb=ReverbConfig(decay_time=0.5), spectral_freeze=0.0)

    # Re-init engine with modified config
    with patch('robotic_psalms.synthesis.sacred_machinery.VoxDeiSynthesizer', autospec=True) as mock_vox_init:
        mock_vox_instance = mock_vox_init.return_value
        mock_vox_instance.sample_rate = 48000
        engine = SacredMachineryEngine(config=default_config)

    psalm_text = "Glitch test"
    duration = 2.0
    expected_samples = int(duration * engine.sample_rate)
    input_vocals = np.sin(np.linspace(0, 440 * 2 * np.pi, expected_samples)).astype(np.float32)
    # Use cast
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (input_vocals, engine.sample_rate)

    result = engine.process_psalm(psalm_text, duration)

    # Check that vocals are different from the input
    assert not np.allclose(result.vocals, input_vocals, atol=1e-6), "Vocals should be modified by glitch effects"
    # Use cast
    cast(MagicMock, engine.vox_dei).synthesize_text.assert_called_once_with(psalm_text)

# --- Test Helper Methods (Indirectly) ---

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

def test_process_psalm_mix_levels(default_config: PsalmConfig):
    """Test that mix levels are applied."""
    # Set distinct mix levels
    default_config.mix_levels = MixLevels(vocals=0.1, pads=0.2, percussion=0.3, drones=0.4)
    # No need to modify haunting/glitch here, we will mock the effect methods

    # Re-init engine
    with patch('robotic_psalms.synthesis.sacred_machinery.VoxDeiSynthesizer', autospec=True) as mock_vox_init:
        mock_vox_instance = mock_vox_init.return_value
        mock_vox_instance.sample_rate = 48000
        engine = SacredMachineryEngine(config=default_config)

    psalm_text = "Mix test"
    duration = 1.0
    sample_rate = engine.sample_rate
    expected_samples = int(duration * sample_rate)

    # Return constant value from synth and generators to easily check mixing, use cast
    mock_input_val = 0.5
    cast(MagicMock, engine.vox_dei).synthesize_text.return_value = (np.ones(expected_samples, dtype=np.float32) * mock_input_val, engine.sample_rate)

    # Mock generation and effect methods to isolate mixing
    with patch.object(engine, '_generate_pads', return_value=np.ones(expected_samples, dtype=np.float32) * mock_input_val, autospec=True), \
         patch.object(engine, '_generate_percussion', return_value=np.ones(expected_samples, dtype=np.float32) * mock_input_val, autospec=True), \
         patch.object(engine, '_generate_drones', return_value=np.ones(expected_samples, dtype=np.float32) * mock_input_val, autospec=True), \
         patch.object(engine, '_apply_haunting_effects', side_effect=lambda x: x, autospec=True), \
         patch.object(engine, '_apply_glitch_effect', side_effect=lambda x: x, autospec=True):

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