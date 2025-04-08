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


### Implementation: Pylance Fixes for vox_dei.py - 2025-04-08 10:23:06
- **Approach**: Resolved Pylance static analysis issues in `src/robotic_psalms/synthesis/vox_dei.py`. Removed unused imports and deprecated `EspeakWrapper` fallback. Refactored filter methods (`_choir_filter`, `_android_filter`, `_machinery_filter`) to use `signal.butter(..., output='sos')` and `signal.sosfiltfilt` for improved stability and type inference, resolving errors related to `signal.butter` return types.
- **Key Files Modified/Created**: `src/robotic_psalms/synthesis/vox_dei.py`: Applied fixes.
- **Notes**: The use of SOS format for filters resolved the Pylance errors related to tuple unpacking and potential `None` values from `signal.butter` with `output='ba'`. `sosfiltfilt` maintains zero-phase filtering.