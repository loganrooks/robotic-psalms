# Project Specification: Robotic Psalms v3.0

**Version:** 3.0
**Date:** 2025-04-13
**Status:** Active

**Document Purpose:** This document supersedes `project_specification_v2.md`. It reflects the project state after the completion of development phases P1 (Stability & Quality), P2 (Core Artistic Enhancement), and P3 (Melodic Refinement - Duration Control), and outlines the priorities and requirements for the next phase (P4).

---

## 1. Introduction

The Robotic Psalms project aims to generate ethereal, computerized vocal arrangements of traditional Latin psalms, integrated with ambient textures, inspired by the "Odi et Amo" aesthetic. This version (v3.0) updates the project specification following significant development work addressing stability, core artistic features, and melodic control.

## 2. Current State Summary (Post P1, P2, P3)

### 2.1 Implemented Features & Capabilities

*   **Core Synthesis Engine (`SacredMachineryEngine`):** Mixes vocal, pad, drone, and percussion layers.
*   **Vocal Synthesis (`VoxDeiSynthesizer`):**
    *   **TTS:** Uses `espeak-ng` via command-line wrapper (`subprocess.run`) for robotic voice synthesis.
    *   **Formant Shifting:** Robust implementation using `pyworld` (`apply_robust_formant_shift`).
    *   **Melodic Contour:** Applies pitch contour based on MIDI input (`midi_path`) using `librosa.pyin` and `librosa.effects.pitch_shift`.
    *   **Duration Control:** Aligns synthesized vocal rhythm to MIDI note durations using `pyfoal` (forced alignment) and `librosa.effects.time_stretch`.
    *   **Layering:** Synthesizes and mixes multiple vocal layers with configurable pitch and timing variations.
*   **Ambient Layers:**
    *   **Pads:** Enhanced generation (`_generate_pads`) with LFO modulation on filters/amplitude for evolving textures.
    *   **Drones:** Enhanced generation (`_generate_drones`) using detuned oscillators and LFO modulation for richer harmonics and movement.
*   **Effects Processing (`effects.py`, integrated into `SacredMachineryEngine`):**
    *   **Reverb:** High-quality reverb using `pedalboard.Reverb`.
    *   **Delay:** Complex delay using `pedalboard.Delay` (basic parameters functional).
    *   **Chorus:** Chorus effect using `pedalboard.Chorus` (basic parameters functional).
    *   **Glitch:** Refined glitch effect with multiple types ('repeat', 'stutter', 'tape_stop', 'bitcrush') and configurable parameters.
    *   **Saturation:** Analog-style saturation using `pedalboard.Distortion`.
    *   **Spectral Freeze:** Improved spectral freeze using `librosa` STFT.
*   **Mixing & Mastering:**
    *   **Master Dynamics:** Compressor and Limiter applied to the final mix using `pedalboard`.
*   **Configuration:** Comprehensive configuration via `config.py` (Pydantic) and `config.yml`.
*   **Input:** Accepts Latin text file path and optional MIDI file path (`midi_path`) for melody and duration control. (Future: Custom DSL planned).
*   **Testing:** Extensive unit and integration tests cover most implemented features.

### 2.2 Known Issues & Limitations

*   **Delay Feedback (`pedalboard`):** The feedback parameter in `pedalboard.Delay` does not function as expected in tests (`test_complex_delay_feedback_parameter` marked `xfail`). This appears to be a library limitation. (REQ-STAB-01 partially addressed - investigated).
*   **Chorus Voices (`pedalboard`):** The `num_voices` parameter in `pedalboard.Chorus` is ignored by the underlying implementation. The corresponding test (`test_chorus_parameters_affect_output`) is marked `xfail`. (REQ-STAB-02 partially addressed - investigated).
*   **Other `pedalboard` Limitations:** Tests related to advanced delay parameters (stereo spread, LFO, filtering) are marked `xfail` as these are not directly supported by `pedalboard.Delay`.
*   **TTS Quality:** `espeak-ng` provides a robotic quality but lacks naturalness and expressiveness options found in more advanced TTS systems.

### 2.3 Deferred Requirements

The following requirements from the original artistic specification or v2 remain unimplemented:

*   **REQ-ART-V04:** Granular Vocal Textures
*   **REQ-ART-M02:** Stereo Panning
*   **(Deferred)** MusicXML Input Parsing (See P5)

## 3. Revised Priorities (P4 and Beyond)

With P1-P3 complete, the focus shifts towards optional features, refinement, and addressing known limitations.

*   **Phase 4 (P4): Input Enhancement & Optional Features**
    1.  **REQ-INPUT-DSL-01:** Design and Implement Custom DSL for Input.
    2.  **REQ-ART-V04:** Implement Granular Vocal Textures.
    3.  **REQ-ART-M02:** Implement Stereo Panning for layers.
    4.  **REQ-FIX-01:** Investigate/Resolve Delay Feedback `xfail`.
    5.  **REQ-FIX-02:** Investigate/Resolve Chorus Voices `xfail`.
*   **Phase 5 (P5): Exploration & Enhancement** (Lower Priority / Future Work)
    *   Further refinement/optimization of existing effects and synthesis modules.
    *   Exploration of alternative user input methods (e.g., MusicXML parsing).
    *   Investigation of alternative TTS engines for different vocal qualities.
    *   Addressing any remaining minor `xfail` tests or quality improvements.

## 4. Functional Requirements (Next Phase - P4)

### 4.1 REQ-INPUT-DSL-01: Custom Domain-Specific Language (DSL) for Input

*   **Description:** Design and implement a text-based Domain-Specific Language (DSL) that allows users to specify the core elements for a psalm generation, including Latin text, melodic contour, rhythm/duration, and potentially basic articulation or dynamics, within a single input file. This aims to provide a more integrated and flexible input method compared to separate text and MIDI files.
*   **Acceptance Criteria:**
    1.  A clear syntax for the DSL is defined and documented.
    2.  A parser (e.g., using Lark, Ply, or TextX) is implemented to read and interpret the DSL file.
    3.  The parser successfully extracts Latin text, note information (pitch, duration), and any other defined parameters.
    4.  The parser provides informative error messages for syntax errors.
    5.  The extracted data is correctly mapped and passed to the relevant synthesis components (`VoxDeiSynthesizer`, potentially `SacredMachineryEngine`).
    6.  The system can generate audio based on input from a valid DSL file.
*   **TDD Anchors:**
    *   `test_dsl_parser_valid_syntax`: Test parsing of various valid DSL constructs.
    *   `test_dsl_parser_invalid_syntax`: Test error handling for common syntax mistakes.
    *   `test_dsl_data_extraction_text`: Verify correct extraction of Latin text segments.
    *   `test_dsl_data_extraction_notes`: Verify correct extraction of notes with pitch and duration.
    *   `test_dsl_integration_synthesizer`: Test that data extracted from DSL is correctly passed to `VoxDeiSynthesizer`.
    *   `test_dsl_end_to_end`: Test generating audio from a simple DSL file.

### 4.2 REQ-ART-V04: Granular Vocal Textures

*   **Description:** Integrate granular synthesis capabilities to process vocal segments, enabling the creation of evolving soundscapes, rhythmic effects, or unique textural transformations from the vocal source.
*   **Acceptance Criteria:**
    1.  A new effect module/function (e.g., `apply_granular_synthesis`) is implemented, likely in `effects.py`.
    2.  Configurable parameters (e.g., `grain_size_ms`, `overlap`, `pitch_variation`, `density`, `window_shape`) are exposed via a Pydantic model (e.g., `GranularParameters`) and integrated into `PsalmConfig`, applied conditionally.
    3.  Unit tests verify the effect modifies the audio signal in a way consistent with granular synthesis (e.g., spectral changes, temporal changes).
    4.  Unit tests verify parameter control influences the output characteristics.
    5.  Subjective listening confirms the effect can transform vocal input into distinct textures.
*   **TDD Anchors:**
    *   `test_granular_effect_exists`: Verify function/model import.
    *   `test_granular_effect_modifies_audio`: Check output differs significantly from input.
    *   `test_granular_parameter_grain_size`: Verify changing grain size alters output characteristics (e.g., spectral content, perceived texture).
    *   `test_granular_parameter_density`: Verify changing density alters output.
    *   `test_granular_integration`: Mock and test conditional application within `VoxDeiSynthesizer` or `SacredMachineryEngine`.

### 4.3 REQ-ART-M02: Stereo Panning

*   **Description:** Introduce stereo panning controls for individual synthesized layers (Vocals, Pads, Drones, Percussion) during the final mixing stage.
*   **Acceptance Criteria:**
    1.  Panning parameters (e.g., `vocal_pan`, `pad_pan`, `drone_pan`, `percussion_pan`) are added to `PsalmConfig`, accepting values from -1.0 (full left) to 1.0 (full right), defaulting to 0.0 (center).
    2.  The mixing logic within `SacredMachineryEngine.process_psalm` is updated to produce stereo output.
    3.  The mixing logic applies the configured panning to each layer before summation.
    4.  Unit tests verify that panning parameters correctly influence the left/right channel balance of the final mix.
*   **TDD Anchors:**
    *   `test_mix_produces_stereo_output`: Verify output array has 2 channels.
    *   `test_pan_left`: Configure `layer_pan = -1.0`, verify energy is predominantly in the left channel (channel 0).
    *   `test_pan_right`: Configure `layer_pan = 1.0`, verify energy is predominantly in the right channel (channel 1).
    *   `test_pan_center`: Configure `layer_pan = 0.0`, verify energy is roughly equal in both channels.
    *   `test_pan_multiple_layers`: Configure different pans for different layers, verify combined output reflects this.

### 4.4 REQ-FIX-01: Investigate/Resolve Delay Feedback XFail

*   **Description:** Re-evaluate the `pedalboard.Delay` feedback limitation identified in P1. Research alternative Python delay implementations (custom DSP, other libraries like `pedalboard`'s underlying `JUCE`, `scipy.signal`, etc.) that offer reliable feedback control. If a suitable alternative is found and integration is feasible, implement it as a replacement for `pedalboard.Delay`. Otherwise, document the limitation clearly and accept the `xfail`.
*   **Acceptance Criteria:**
    1.  The `test_complex_delay_feedback_parameter` test in `tests/synthesis/test_effects.py` passes consistently.
    2.  OR: A clear analysis and justification for accepting the limitation is documented, and the test remains `xfail` or is modified appropriately.
*   **TDD Anchors:**
    *   (If implementing replacement): Re-use or adapt `test_complex_delay_feedback_parameter` to verify that increasing the feedback parameter results in more audible repeats and energy buildup.

### 4.5 REQ-FIX-02: Investigate/Resolve Chorus Voices XFail

*   **Description:** Re-evaluate the `pedalboard.Chorus` limitation where `num_voices` is ignored. If multi-voice chorus is deemed important for the artistic goals, research and implement a manual multi-voice chorus (e.g., using multiple modulated delays). If the current `pedalboard.Chorus` effect is sufficient, confirm this decision, remove the `num_voices` parameter from `ChorusParameters`/`ChorusConfig`, and remove the corresponding `xfail` test.
*   **Acceptance Criteria:**
    1.  The `test_chorus_parameters_affect_output` test related to `num_voices` in `tests/synthesis/test_effects.py` passes consistently (if manual implementation is chosen).
    2.  OR: The `num_voices` parameter is removed from configuration and models, and the corresponding test is removed or modified.
*   **TDD Anchors:**
    *   (If implementing replacement): Create tests verifying that increasing `num_voices` results in an audibly thicker/more complex chorus effect compared to fewer voices.

## 5. Non-Functional Requirements

*   **Maintainability:** Code should remain modular, well-documented, and adhere to Python best practices.
*   **Testability:** New features must include comprehensive unit and integration tests. Overall test coverage should be maintained or increased.
*   **Performance:** The system must run locally on typical developer hardware within a reasonable time frame (e.g., synthesis time should not be excessively long for moderate input).
*   **Extensibility:** The architecture should allow for future addition or modification of effects and synthesis modules.

## 6. Constraints

*   **TTS Engine:** Must remain free and locally runnable. `espeak-ng` is the current baseline.
*   **Core Language:** Python 3.
*   **Project Structure:** Adhere to the existing `src/robotic_psalms` structure and `pyproject.toml` based dependency management (Poetry).
*   **Configuration:** Utilize the existing Pydantic-based configuration system (`config.py`, `config.yml`).
*   **Licensing:** All dependencies must have permissive licenses (MIT, Apache 2.0, BSD, etc.) compatible with potential future distribution.

---