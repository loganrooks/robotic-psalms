import pytest
import numpy as np
from dataclasses import dataclass, field

from robotic_psalms.synthesis.sacred_machinery import SacredMachineryEngine, SynthesisResult
from robotic_psalms.config import PsalmConfig # Use PsalmConfig
# TODO: Uncomment imports above once the classes/structures exist

# Remove Mock classes

# TDD: Test SacredMachineryEngine includes vocals
def test_sacred_machinery_engine_includes_vocals():
    """
    Verify that SacredMachineryEngine.process_psalm produces a SynthesisResult
    with non-empty vocal audio data.
    """
    # Use actual implementations
    try:
        config = PsalmConfig() # Use default config
        engine = SacredMachineryEngine(config=config)
    except Exception as e:
        pytest.fail(f"Failed to initialize SacredMachineryEngine: {e}")
    psalm_input = "Dominus regit me"

    # Process the psalm (assuming default duration or handling within the method)
    # The actual method might require duration, adjust if needed.
    # Based on src/robotic_psalms/cli.py, it seems duration is needed. Let's add a default.
    default_duration = 1.0 # seconds
    result = engine.process_psalm(psalm_input, duration=default_duration)

    # Assertions
    assert isinstance(result, SynthesisResult), "Output should be a SynthesisResult"
    assert hasattr(result, 'vocals'), "Result should have a 'vocals' attribute"
    assert isinstance(result.vocals, np.ndarray), "Vocals attribute should be a NumPy array"
    assert result.vocals.dtype == np.float32, "Vocals data type should be float32"
    assert result.vocals.size > 0, "Vocals audio data should not be empty"
    # Add check for other components if relevant
    assert result.combined.size > 0, "Combined audio data should not be empty"
    assert result.sample_rate > 0, "Sample rate should be positive"