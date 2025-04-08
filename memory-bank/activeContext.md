# Active Context

*This file tracks the immediate focus, ongoing tasks, and unresolved questions for the current session.*

---
### [2025-04-08 06:55:12] - Task: Create Project Specification
- **Focus:** Defining initial project specification (`project_specification.md`) for Robotic Psalms based on user request and provided context summary.
- **Status:** Drafting specification content, preparing to update Memory Bank and write file.


### [2025-04-08 06:59:45] - Task: Create Pseudocode for TTS Fix
- **Focus:** Generated pseudocode (`pseudocode.md`) outlining investigation, fix/replacement strategy for TTS, integration, and robotic effects based on `project_specification.md` and code analysis.
- **Status:** Pseudocode generated and saved. Preparing Memory Bank update and task completion.


### [2025-04-08 07:04:08] - Task: Write Initial Failing Tests (Vocal Synthesis)
- **Focus:** Created initial failing tests (Red phase) for TTS output, robotic effects, VoxDei integration, and SacredMachinery integration.
- **Files Created:** `tests/synthesis/tts/test_espeak.py`, `tests/synthesis/test_vox_dei.py`, `tests/test_sacred_machinery.py`.
- **Status:** Tests created using mock implementations. Ready for implementation phase (Green).


### [2025-04-08 09:23:33] - Task: Evaluate py-espeak-ng TTS Library
- **Focus:** Evaluated `py-espeak-ng` against functionality, robotic voice potential, cost, maintainability, and integration complexity criteria.
- **Findings:** Library meets core requirements, uses direct buffer synthesis (better than file I/O), is Apache-2.0 licensed, and was last updated Oct 2024.
- **Status:** Evaluation complete. Recommendation is to proceed with `py-espeak-ng`. Preparing Memory Bank update for Decision Log and task completion.



### [2025-04-08 09:59:00] - Task: Implement TTS Fix with py-espeak-ng (Revised)
- **Focus:** Implement vocal synthesis using `espeak-ng` via command-line wrapper after encountering persistent issues with Python libraries (`py-espeak-ng`, `espeakng`).
- **Approach:** Modified `EspeakNGWrapper` to use `subprocess.run` calling `/usr/bin/espeak-ng` with temporary files for input and capturing stdout for WAV data.
- **Files Modified:** `pyproject.toml`, `src/robotic_psalms/synthesis/tts/engines/espeak.py`, `tests/synthesis/tts/test_espeak.py`, `tests/synthesis/test_vox_dei.py`.
- **Status:** Implementation complete. Tests `tests/synthesis/tts/test_espeak.py` and `tests/synthesis/test_vox_dei.py` are passing. Preparing Memory Bank update and task completion.



### [2025-04-08 10:23:06] - Task: Resolve Pylance Issues in vox_dei.py
- **Focus:** Addressing Pylance static analysis errors/warnings in `src/robotic_psalms/synthesis/vox_dei.py`.
- **Approach:** Removed unused imports (`importlib`, `Path`, `Any`, `runtime_checkable`, `soundfile`), removed deprecated `EspeakWrapper` fallback logic, and refactored filter implementations (`_choir_filter`, `_android_filter`, `_machinery_filter`) to use `signal.butter(..., output='sos')` and `signal.sosfiltfilt` for improved stability and type inference.
- **Status:** Changes applied. Preparing Memory Bank update and verification step (running tests).



### [2025-04-08 10:41:13] - Task: Improve TTS Test Coverage
- **Focus:** Analyze test coverage for `espeak.py` and `vox_dei.py`, identify gaps, and add tests.
- **Actions:**
    - Ran coverage analysis.
    - Added tests for error handling, parameter variations, audio processing in `test_espeak.py`.
    - Added tests for initialization errors, synthesis errors, and processing edge cases in `test_vox_dei.py`.
    - Fixed test failure related to int16 scaling in `espeak.py`.
    - Resolved Pylance errors in test files and `sacred_machinery.py`.
- **Status:** Completed. Coverage increased to 94% for `espeak.py` and 95% for `vox_dei.py`. All tests passing.


### [2025-04-08 10:49:49] - Task: Improve Sacred Machinery Test Coverage (Feedback)
- **Focus:** Address feedback regarding low coverage in `sacred_machinery.py`.
- **Actions:**
    - Rewrote `test_sacred_machinery.py` with comprehensive tests using mocks.
    - Tested `process_psalm` success and error handling (`VoxDeiSynthesisError`).
    - Tested application of haunting and glitch effects.
    - Tested helper methods (`_fit_to_length`, `_mix_components`) indirectly.
    - Debugged test failures related to incorrect mocking and Pydantic validation.
- **Status:** Completed. Coverage for `sacred_machinery.py` increased from 13% to 73%. All 41 tests passing.



### [2025-04-08 11:22:10] - Task: Debug Silent Vocals in CLI Output
- **Focus:** Investigate why `output.wav` has silent vocals when running via CLI (`robotic-psalms ...`) despite unit tests passing.
- **Investigation:**
    1. Checked `cli.py`: Confirmed args parsed and config passed correctly.
    2. Checked `examples/config.yml`: Confirmed `mix_levels.vocals` is 1.0.
    3. Added logging to `sacred_machinery.py`: Confirmed `VoxDeiSynthesizer.synthesize_text` succeeds and returns audio data.
    4. Added logging to `_mix_components`: Found vocal amplitude > 7.0 before mixing, indicating severe clipping.
- **Root Cause:** Effects processing and resampling amplified vocals beyond [-1.0, 1.0], causing clipping. Final mix normalization didn't apply to individual stems saved.
- **Fix:** Added `_normalize_audio` helper and applied it to each component (vocals, pads, etc.) in `process_psalm` before mixing/returning.
- **Status:** Fix applied. Preparing Memory Bank update and task completion.



### [2025-04-08 12:19:01] - Task: Refine Specifications for "Odi et Amo" Aesthetic
- **Focus:** Analyze target aesthetic, review current capabilities (`README.md`, `project_specification.md`, `config.py`, `vox_dei.py`, `sacred_machinery.py`), identify gaps, define new artistic requirements (including melodic control), and create `artistic_specification.md`.
- **Status:** `artistic_specification.md` created. Preparing to generate pseudocode for high-priority artistic requirements (starting with REQ-ART-E01: High-Quality Reverb).



### [2025-04-08 12:31:14] - Task: Update Project Documentation (Current State & Roadmap)
- **Focus:** Update `README.md` and `src/robotic_psalms/architecture.md` to reflect the use of `espeakng` (sayak-brm wrapper) and outline future artistic goals from `artistic_specification.md`.
- **Actions:**
    - Confirmed `espeakng` dependency in `pyproject.toml`.
    - Read `artistic_specification.md` for future goals.
    - Created `docs/index.md` as a placeholder for detailed documentation.
    - Updated `README.md`: System Requirements, Python Requirements, Installation, Troubleshooting, Acknowledgments, added Development Status/Roadmap section, added link to `docs/index.md`.
    - Updated `src/robotic_psalms/architecture.md`: Technical Dependencies, added Implementation Notes on refactoring and future direction.
- **Status:** Documentation files updated. Preparing Memory Bank update and task completion.
