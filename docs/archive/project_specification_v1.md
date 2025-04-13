# Project Specification: Robotic Psalms

## 1. Overview

Robotic Psalms aims to generate ethereal, computerized vocal arrangements of traditional Latin psalms. It combines synthesized robotic voices with ambient pads, drones, and subtle percussion to create a unique sonic experience.

## 2. Current State

The project codebase exists but is currently **non-functional**, specifically concerning the core vocal synthesis component (`src/robotic_psalms/synthesis/vox_dei.py` and associated TTS modules). While other features like pad generation, drone synthesis, percussion, configuration handling, and output formatting are present, the inability to synthesize vocals prevents the application from fulfilling its primary purpose.

## 3. Objectives (Phase 1: Minimal Viable Functionality)

The immediate priority is to achieve basic functionality by fixing the vocal synthesis pipeline.

*   **Fix Vocal Synthesis:** Repair or replace the components responsible for text-to-speech (TTS) generation within `src/robotic_psalms/synthesis/vox_dei.py` and its dependencies (e.g., `src/robotic_psalms/synthesis/tts/engines/espeak.py`, potentially `lib/espeakmodulecore.cpp` if eSpeak is pursued). The goal is to produce audible vocal output from input Latin text.
*   **Robotic Voice Quality:** The synthesized voice *must* have a distinctly robotic or computerized timbre, aligning with the project's aesthetic. Natural-sounding voices are explicitly *not* desired for this phase.
*   **Free TTS Solution:** The chosen TTS engine or method *must* be free to run locally without requiring paid services or licenses. Investigate fixing the existing eSpeak/Festival integration first. If unfeasible, identify and integrate a suitable free alternative (e.g., other open-source TTS engines compatible with Python).
*   **Minimal Other Changes:** Modifications to other existing features (pads, percussion, drones, configuration options via `config.yml`, output formats) should be strictly minimized. The focus is solely on enabling the core vocal synthesis.

## 4. Functional Requirements

*   **FR1:** The system shall accept Latin psalm text as input (source format TBD, likely plain text file as per `examples/psalm.txt`).
*   **FR2:** The system shall synthesize the input Latin text into audible speech using a TTS engine.
*   **FR3:** The synthesized speech shall possess a robotic/computerized quality.
*   **FR4:** The system shall allow configuration (e.g., via `config.yml`) to specify input text, output path, and potentially basic synthesis parameters (though additions should be minimal).
*   **FR5:** The system shall combine the synthesized vocals with existing (presumably functional) ambient pads, drones, and percussion layers.
*   **FR6:** The system shall output the final arrangement as an audio file (format TBD, likely WAV or MP3 based on existing code/config).

## 5. Constraints

*   **C1: Minimal Code Changes:** Except for the vocal synthesis modules (`vox_dei.py`, TTS engines), changes to the existing codebase should be avoided unless strictly necessary to make the vocal synthesis work.
*   **C2: Free TTS:** The TTS solution must be free to use and run locally (no cloud services with associated costs). Open-source solutions like eSpeak, Festival, or similar alternatives are preferred.
*   **C3: Robotic Voice:** The target voice quality is explicitly robotic/non-human.
*   **C4: Existing Architecture:** Leverage the existing Python project structure (`pyproject.toml`, `src/robotic_psalms/`) and configuration system (`config.py`, `examples/config.yml`).

## 6. Next Steps (Post-Phase 1)

*   Testing and validation of the vocal synthesis output.
*   Refinement of the robotic voice parameters.
*   Potential refactoring or improvements to other modules once core functionality is restored.