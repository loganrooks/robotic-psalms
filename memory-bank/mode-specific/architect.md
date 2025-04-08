# Architect Specific Memory

*This file stores context, notes, diagrams, and decisions specific to the Architect mode.*

---

## System Diagrams
<!-- Append new diagrams using the format below -->

## Component Specifications
<!-- Append new component specs using the format below -->

### Component Specification: TTS Engine (py-espeak-ng Evaluation) - [2025-04-08 09:24:04]
- **Responsibility**: Synthesize text into audible speech waveforms.
- **Dependencies**: Python 3, `espeak-ng` system binary.
- **Interfaces Exposed**: Python API (`ESpeakNG` class with methods like `synth_wav`, `say`, `g2p`, and attributes like `pitch`, `speed`, `voice`).
- **Evaluation Summary (py-espeak-ng):**
    - **Functionality:** Meets requirements (buffer synthesis via `synth_wav()`, parameter control for pitch/speed/voice).
    - **Robotic Voice:** Plausible. Core eSpeak NG parameters controllable; requires integration with existing post-processing (`_apply_robotic_effects`).
    - **Cost:** Free (Apache-2.0 license).
    - **Maintainability:** Acceptable (API clear, last commit Oct 2024).
    - **Integration:** Feasible and likely improvement over current file I/O method. Involves replacing `subprocess` calls with direct API usage in `EspeakNGWrapper`.
- **Recommendation:** Proceed with `py-espeak-ng` integration.


## Interface Definitions
<!-- Append new interface definitions using the format below -->

## Data Models
<!-- Append new data models using the format below -->