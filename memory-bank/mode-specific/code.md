# Auto-Coder Specific Memory

*This file stores context, notes, and decisions specific to the Auto-Coder mode.*

---



### Implementation: TTS Fix (eSpeak-NG Command-Line Wrapper) - 2025-04-08 09:59:00
- **Approach**: Replaced Python library wrappers (`py-espeak-ng`, `espeakng`) with a direct command-line call to `/usr/bin/espeak-ng` using `subprocess.run`. Input text is passed via a temporary file (`-f`), and WAV audio is captured from stdout (`--stdout`). This bypasses library integration issues.
- **Key Files Modified/Created**: `src/robotic_psalms/synthesis/tts/engines/espeak.py`: Rewritten `EspeakNGWrapper`.
- **Notes**: This approach proved necessary after persistent failures with Python library wrappers returning empty audio data. The command-line tool was verified to work independently. Tests `test_espeak.py` and `test_vox_dei.py` now pass with this implementation.
## Current Implementation Focus
<!-- Describe the code being worked on -->

## Code Snippets & Logic
<!-- Store relevant code blocks or logic notes -->

## Refactoring Notes
<!-- Track potential refactoring opportunities -->


### Dependency: py-espeak-ng - 2025-04-08 09:29:40
- **Version**: >=0.1.0
- **Purpose**: Initial attempt to wrap eSpeak-NG library.
- **Used by**: `EspeakNGWrapper` (initially).
- **Config notes**: Removed from `pyproject.toml` due to persistent runtime issues (empty audio output).


### Dependency: espeakng - 2025-04-08 09:55:31
- **Version**: >=1.0
- **Purpose**: Alternative attempt to wrap eSpeak-NG library.
- **Used by**: `EspeakNGWrapper` (briefly considered).
- **Config notes**: Added to `pyproject.toml` but ultimately not used in the final implementation; the library required file export, leading back to the command-line wrapper approach. Removed from `pyproject.toml`.



### Dependency: pedalboard - 2025-04-08 14:47:14
- **Version**: >=0.7.1
- **Purpose**: Provides high-quality audio effects, specifically used for `pedalboard.Reverb` in the initial implementation of `apply_high_quality_reverb`.
- **Used by**: `src/robotic_psalms/synthesis/effects.py`
- **Config notes**: Added to main dependencies in `pyproject.toml`.

### Implementation: Pylance Fixes for vox_dei.py - 2025-04-08 10:23:06
- **Approach**: Resolved Pylance static analysis issues in `src/robotic_psalms/synthesis/vox_dei.py`. Removed unused imports and deprecated `EspeakWrapper` fallback. Refactored filter methods (`_choir_filter`, `_android_filter`, `_machinery_filter`) to use `signal.butter(..., output='sos')` and `signal.sosfiltfilt` for improved stability and type inference, resolving errors related to `signal.butter` return types.
- **Key Files Modified/Created**: `src/robotic_psalms/synthesis/vox_dei.py`: Applied fixes.
- **Notes**: The use of SOS format for filters resolved the Pylance errors related to tuple unpacking and potential `None` values from `signal.butter` with `output='ba'`. `sosfiltfilt` maintains zero-phase filtering.


### Implementation: Minimal High-Quality Reverb (REQ-ART-E01) - 2025-04-08 14:47:14
- **Approach**: Implemented `apply_high_quality_reverb` using `pedalboard.Reverb`. Created `ReverbParameters` Pydantic model. Mapped parameters conceptually (e.g., `decay_time` to `room_size`). Simulated `pre_delay` using `np.concatenate` with zero padding. Updated tests to use Pydantic v2 `.model_copy()` and adjusted assertions to account for length changes caused by reverb tail and pre-delay padding.
- **Key Files Modified/Created**: `src/robotic_psalms/synthesis/effects.py` (Created), `tests/synthesis/test_effects.py` (Modified), `pyproject.toml` (Modified).
- **Notes**: The implementation successfully passes all tests in `tests/synthesis/test_effects.py`. The parameter mapping and pre-delay simulation are basic and may need refinement. A Pylance warning regarding `model_config` in the Pydantic model persists but doesn't affect functionality.