# Auto-Coder Specific Memory

*This file stores context, notes, and decisions specific to the Auto-Coder mode.*

---

## Current Implementation Focus
<!-- Describe the code being worked on -->

## Code Snippets & Logic
<!-- Store relevant code blocks or logic notes -->

## Refactoring Notes
<!-- Track potential refactoring opportunities -->


### Implementation: eSpeak TTS Fix (Buffer Retrieval) - [2025-04-08 07:33:41]
- **Approach**: Modified C++ bindings (`lib/espeakmodulecore.cpp`) to capture audio buffer in callback and expose via `get_last_audio_buffer`. Updated Python wrapper (`src/robotic_psalms/synthesis/tts/engines/espeak.py`) to use this function, removing file I/O. Rebuilt package. (Ref: `pseudocode.md#2-attempt-espeak-ng-fix`)
- **Key Files Modified/Created**:
  - `lib/espeakmodulecore.cpp`: Added buffer capture logic, `pyespeak_get_last_audio_buffer` function, and updated module definition.
  - `src/robotic_psalms/synthesis/tts/engines/espeak.py`: Removed file I/O, polling, and temp file logic; added call to `get_last_audio_buffer` and buffer processing.
- **Notes**: This approach aims for a more robust and efficient audio retrieval from eSpeak-NG compared to the previous file-based method. Requires successful compilation of the C++ extension (needs `python3-dev` headers). Next step is testing.