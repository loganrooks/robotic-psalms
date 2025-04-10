# Global Context

*This file stores long-term project information, decisions, and patterns.*

---

## Product Context
*High-level goals, user stories, constraints.*

#### [2025-04-08 06:55:34] - Robotic Psalms Initial Goal
- **Goal:** Generate ethereal, computerized vocal arrangements of traditional Latin psalms by combining synthesized robotic voices with ambient pads, drones, and subtle percussion.
- **Initial State:** Existing codebase is non-functional, primarily due to issues in the vocal synthesis pipeline.
- **Phase 1 Focus:** Fix vocal synthesis using a free, robotic-sounding TTS engine with minimal changes to other components.

---

## System Patterns
*Architectural diagrams, component relationships, data flows.*

---

## Decision Log
*Key technical choices, justifications, alternatives considered.*

#### [2025-04-08 07:00:24] - Decision: TTS Fix/Replacement Strategy
- **Context:** Initial analysis of `espeak.py` and `espeakmodulecore.cpp` revealed a fragile file-based communication mechanism (hardcoded `/tmp` paths, polling) likely causing the TTS failure.
- **Decision:** Generated pseudocode (`pseudocode.md`) outlining a multi-step approach:
    1.  **Investigate:** Deep dive into current eSpeak implementation failures.
    2.  **Attempt Fix:** Prioritize fixing eSpeak-NG, preferably by modifying C++ bindings for direct buffer retrieval, falling back to improving file handling.
    3.  **Alternative:** If fixing eSpeak is unviable, research and integrate a different free, local TTS engine (e.g., Piper, pyttsx3) via a new wrapper class.
    4.  **Integration:** Detail integration into `VoxDeiSynthesizer` and `SacredMachineryEngine`.
    5.  **Effects:** Ensure existing robotic post-processing (`_apply_robotic_effects`) is applied.
- **Justification:** Addresses the core functionality block (FR2, FR3) while respecting constraints (C1, C2, C3, C4). Prioritizes fixing existing code before introducing new dependencies.
- **Alternatives Considered:** Directly jumping to a new TTS library without attempting a fix.

---

#### [2025-04-08 09:23:53] - Decision: Select `py-espeak-ng` as TTS Engine Replacement
- **Context:** The initial `python-espeak-ng` implementation failed due to unreliable file-based communication. Evaluation of `py-espeak-ng` was requested.
- **Evaluation Summary:**
    - **Functionality:** Meets requirements (buffer synthesis, parameter control).
    - **Robotic Voice:** Plausible via parameter control and existing post-processing.
    - **Cost:** Free (Apache-2.0 license).
    - **Maintainability:** Acceptable (last commit Oct 2024).
    - **Integration:** Feasible, likely simpler than current method.
- **Decision:** Proceed with `py-espeak-ng` as the TTS engine replacement.
- **Justification:** Directly addresses the core issue (file I/O) with a more robust API. Leverages existing eSpeak NG dependency, minimizing disruption compared to entirely new TTS systems (Coqui, Piper). Meets functional and cost requirements.
- **Alternatives Considered:** Coqui TTS, Piper TTS (deferred for now as `py-espeak-ng` is a closer fit to the existing structure).
---


#### [2025-04-08 09:59:00] - Decision: Use Command-Line Wrapper for eSpeak NG
- **Context:** Attempts to use Python libraries (`py-espeak-ng`, `espeakng`) failed to produce audio output reliably within the test environment, despite the command-line tool working.
- **Decision:** Implement `EspeakNGWrapper` by directly calling the `/usr/bin/espeak-ng` command using `subprocess.run`, passing text via a temporary file and capturing WAV audio from stdout.
- **Justification:** Bypasses Python library integration issues and leverages the known working command-line tool. Provides a robust way to get audio data.
- **Alternatives Considered:** Further debugging Python libraries, switching to Piper/Coqui TTS (deferred).



#### [2025-04-08 14:47:14] - Decision: Use `pedalboard` for Initial Reverb Implementation
- **Context:** Requirement REQ-ART-E01 calls for a high-quality reverb effect. Minimal implementation is needed to pass initial tests.
- **Decision:** Use the `pedalboard.Reverb` class for the initial implementation of `apply_high_quality_reverb`.
- **Justification:** `pedalboard` is a capable audio effects library, suggested in the task guidance. It provides a readily available reverb effect suitable for a minimal implementation. Parameter mapping from `ReverbParameters` (defined by tests) to `pedalboard.Reverb` parameters is feasible, although some parameters like `pre_delay` require simulation (padding).
- **Alternatives Considered:** Implementing a reverb algorithm from scratch (too complex for minimal implementation), using `scipy.signal.convolve` with an Impulse Response (requires finding/managing IR files).
## Progress
*Milestones, completed tasks, overall status.*



#### [2025-04-08 09:59:00] - Task: Implement TTS Fix (Command-Line Wrapper)
- **Status:** Completed.
- **Deliverables:** Modified `EspeakNGWrapper` in `src/robotic_psalms/synthesis/tts/engines/espeak.py` to use `subprocess.run`. Updated tests in `tests/synthesis/tts/test_espeak.py` and `tests/synthesis/test_vox_dei.py`. All relevant tests are passing.
---


#### [2025-04-08 10:23:06] - Task: Resolve Pylance Issues in vox_dei.py
- **Status:** Completed.
- **Deliverables:** Modified `src/robotic_psalms/synthesis/vox_dei.py` to remove unused imports, remove deprecated `EspeakWrapper` fallback, and refactor filter implementations to use `signal.butter(..., output='sos')` and `signal.sosfiltfilt` for stability and type safety. Pylance issues resolved.


#### [2025-04-08 10:41:13] - Task: Improve TTS Test Coverage
- **Status:** Completed.
- **Deliverables:** Added unit tests to `tests/synthesis/tts/test_espeak.py` and `tests/synthesis/test_vox_dei.py` covering error handling, parameter variations, and edge cases. Fixed int16 scaling bug in `espeak.py`. Resolved associated Pylance errors.
- **Coverage:** `espeak.py` improved from 71% to 94%. `vox_dei.py` improved from 86% to 95%.


#### [2025-04-08 10:49:49] - Task: Improve Sacred Machinery Test Coverage (Feedback)
- **Status:** Completed.
- **Deliverables:** Added unit tests to `tests/test_sacred_machinery.py` covering `process_psalm` success/error cases, effects application, and helper methods (indirectly). Debugged and fixed test failures related to mocking and validation.
- **Coverage:** `sacred_machinery.py` improved from 13% to 73%.


#### [2025-04-08 14:47:14] - Task: Implement Minimal High-Quality Reverb (REQ-ART-E01 - Green Phase)
- **Status:** Completed.
- **Deliverables:** Created `src/robotic_psalms/synthesis/effects.py` with `ReverbParameters` model and `apply_high_quality_reverb` function using `pedalboard`. Added `pedalboard` dependency to `pyproject.toml`. Updated `tests/synthesis/test_effects.py` to handle Pydantic v2 and reverb length changes. All tests pass.


#### [2025-04-08 14:54:13] - Task: Update Integration Tests for High-Quality Reverb (REQ-ART-E01 - Integration TDD Red Phase)
- **Status:** Completed (Red Phase).
- **Deliverables:** Modified `tests/test_sacred_machinery.py` (`test_process_psalm_applies_haunting`) to assert call to `apply_high_quality_reverb`. Test fails with `AttributeError` as expected.


#### [2025-04-08 15:35:52] - Task: Update Documentation for Reverb Integration (REQ-ART-E01 - Documentation)
- **Status:** Completed.
- **Deliverables:** Updated `README.md` configuration example and parameter guide. Updated docstrings and code in `src/robotic_psalms/config.py` (added `ReverbConfig`, modified `HauntingParameters`) and `src/robotic_psalms/synthesis/sacred_machinery.py` (updated docstrings, replaced old reverb logic with call to `apply_high_quality_reverb`, removed `_generate_reverb_ir`).
