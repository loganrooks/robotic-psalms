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



#### [2025-04-08 07:33:41] - Decision: Modify eSpeak C++ Bindings for Buffer Retrieval
- **Context:** Analysis of `espeak.py` and `espeakmodulecore.cpp` confirmed the unreliable file-based I/O mechanism for retrieving synthesized audio.
- **Decision:** Modified `lib/espeakmodulecore.cpp` to capture the audio buffer directly within the C callback (`PyEspeakCB`) and expose it via a new Python function (`get_last_audio_buffer`). This avoids file I/O.
- **Justification:** Provides a more robust and efficient method for audio retrieval compared to file polling, directly addressing the primary failure point identified in the investigation.
- **Alternatives Considered:** Improving file-based handling (less reliable), switching to a different TTS engine (deferred).
---
---

## Progress
*Milestones, completed tasks, overall status.*

---

#### [2025-04-08 07:33:41] - Progress: eSpeak TTS Fix Implemented
- **Status:** Modified C++ bindings (`lib/espeakmodulecore.cpp`) and Python wrapper (`src/robotic_psalms/synthesis/tts/engines/espeak.py`) to use direct audio buffer retrieval.
- **Deliverables:** Updated C++ and Python source files.
- **Next Step:** Run `pytest` to verify the fix against existing tests.