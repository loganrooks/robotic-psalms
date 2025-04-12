# Project Specification: Robotic Psalms - v2.0 (Post-Initial Implementation)

## 1. Introduction & Revised Goal

This document outlines the revised specifications for the Robotic Psalms project following the initial implementation phase guided by `artistic_specification.md`. The core goal remains to generate ethereal, computerized vocal arrangements of traditional Latin psalms, inspired by aesthetics like Jóhann Jóhannsson's "Odi et Amo".

This revision focuses on reassessing the current state, addressing known issues, enhancing core components based on lessons learned, and prioritizing future work to balance **Quality, Flexibility, Ease of Use, Modularity, and Maintainability**.

## 2. Current State Summary (As of 2025-04-12)

### 2.1 Implemented Features

*   **Vocal Synthesis:** Functional TTS (`espeak-ng` wrapper), Robust Formant Shifting (`pyworld`), Melodic Contour (`librosa`), Vocal Layering.
*   **Melody Input:** MIDI file parsing (`pretty_midi`) to guide vocal pitch.
*   **Ambient Layers:** Basic Pad, Drone, and Percussion generation.
*   **Effects Chain:** High-Quality Reverb (`pedalboard`), Complex Delay (`pedalboard` - core), Atmospheric Filters (`scipy`), Chorus (`pedalboard` - core), Spectral Freeze (`librosa`), Refined Glitch (custom), Saturation (`pedalboard`), Master Dynamics (`pedalboard`).
*   **Configuration:** Pydantic models (`config.py`) for detailed parameter control.
*   **Methodology:** Test-Driven Development (`pytest`).

### 2.2 Known Issues & Limitations

*   **Delay Feedback:** `pedalboard.Delay` feedback parameter test fails (`xfail` in `test_effects.py`).
*   **Delay Advanced Params:** `pedalboard.Delay` does not support stereo spread, LFO modulation, or feedback filtering (`xfail` in `test_effects.py`).
*   **Chorus Voices:** `pedalboard.Chorus` ignores the `num_voices` parameter (`xfail` in `test_effects.py`).
*   **Glitch Repeat:** `apply_refined_glitch` logic incorrectly handles `repeat_count > 1` (`xfail` in `test_effects.py`).
*   **Melody Contour Accuracy:** Pitch verification test (`test_apply_melody_contour_shifts_pitch`) failure may indicate minor inaccuracies in pitch shifting or issues with the test's pitch detection method (`xfail` in `test_vox_dei.py`).

### 2.3 Deferred Requirements

*   `REQ-ART-A01`: Complex Pad Generation (Initial tests passed basic implementation).
*   `REQ-ART-A02`: Rich Drone Generation (Initial tests passed basic implementation).
*   `REQ-ART-MEL-03`: Syllable/Note Duration Control (Deferred due to complexity).
*   `REQ-ART-V04`: Granular Vocal Textures (Optional).
*   `REQ-ART-M02`: Stereo Panning (Optional).

## 3. Revised Priorities & Rationale

Based on the goal of balancing Quality, Flexibility, Ease of Use, Modularity, and Maintainability, the following priorities are established:

1.  **[P1] Stability & Quality:** Address known issues (`xfail` tests). Fixing these improves maintainability, reliability, and the quality of existing features.
2.  **[P2] Core Artistic Enhancement:** Improve the fundamental ambient layers (Pads/Drones) which are crucial to the target aesthetic. Requires defining *new*, more stringent tests first.
3.  **[P3] Melodic Refinement:** Revisit Syllable Duration Control (`REQ-ART-MEL-03`), a high-impact feature for flexibility, but requires careful planning.
4.  **[P4] Optional Features:** Consider lower-priority items (`REQ-ART-V04`, `REQ-ART-M02`) if aligned with refined goals and resources allow.

## 4. Functional Requirements (Next Phases)

### 4.1 Phase 1: Stability & Quality (Priority P1)

*   **REQ-STAB-01: Resolve Delay Feedback XFail**
    *   **Description:** Investigate the failing test for `pedalboard.Delay` feedback. Determine if it's a library issue, test inaccuracy, or implementation error. If unresolvable with `pedalboard`, either find/implement an alternative delay function that supports reliable feedback or document the limitation and adjust the test/parameter.
    *   **Acceptance Criteria:** The `test_complex_delay_feedback_parameter` test passes OR is documented as unachievable with the current library and potentially removed/modified.
    *   **TDD Anchor:** Test delay feedback produces audible, distinctly different output for feedback=0.1 vs feedback=0.8, with increasing energy/repeats for higher feedback.

*   **REQ-STAB-02: Address Chorus NumVoices XFail**
    *   **Description:** The `pedalboard.Chorus` ignores `num_voices`. Either implement multi-voice chorus logic manually (e.g., using multiple `pedalboard.Delay` instances with LFO modulation) within `apply_chorus`, or confirm the limitation is acceptable, remove the `num_voices` parameter from `ChorusParameters`, and remove the corresponding `xfail` test.
    *   **Acceptance Criteria:** The `test_chorus_parameters_affect_output` related to `num_voices` passes (if implemented) OR the `num_voices` parameter and test are removed.
    *   **TDD Anchor:** (If implementing) Test `apply_chorus` output with `num_voices=4` is audibly thicker/different compared to `num_voices=2`.

*   **REQ-STAB-03: Fix Glitch Repeat Logic**
    *   **Description:** Correct the offset calculation or slicing logic within the `_apply_repeat_glitch` helper function in `effects.py` so that the `repeat_count` parameter functions as intended, creating the specified number of repetitions.
    *   **Acceptance Criteria:** The `test_refined_glitch_repeat_count_affects_output` test passes.
    *   **TDD Anchor:** Test `apply_refined_glitch` with `glitch_type='repeat'` produces output where `repeat_count=3` results in more repetitions / longer modified segment compared to `repeat_count=2`.

*   **REQ-STAB-04: Verify/Refine Melody Contour Accuracy**
    *   **Description:** Analyze the failing `test_apply_melody_contour_shifts_pitch`. Improve the reliability of pitch detection within the test (e.g., using different algorithms, averaging over segments) or refine the `_apply_melody_contour` implementation in `vox_dei.py` (potentially adjusting `librosa.effects.pitch_shift` parameters) to ensure accurate pitch tracking.
    *   **Acceptance Criteria:** The `test_apply_melody_contour_shifts_pitch` test passes consistently, demonstrating accurate pitch tracking within a defined tolerance (e.g., +/- 10 Hz).
    *   **TDD Anchor:** Test `_apply_melody_contour` output segments match target melody pitches within +/- 10 Hz tolerance when analyzed with a reliable pitch detection method.

### 4.2 Phase 2: Core Artistic Enhancement (Priority P2)

*   **REQ-ART-A01-v2: Complex Pad Generation**
    *   **Description:** Enhance `_generate_pads` in `sacred_machinery.py` to produce more complex, evolving textures suitable for the target aesthetic. Explore techniques like wavetable synthesis, additive synthesis, or more sophisticated modulation (multiple LFOs, envelopes) on filters and amplitude. Define *new* tests first to quantify "complexity" and "evolution".
    *   **Acceptance Criteria:** New tests measuring spectral complexity (e.g., number of significant peaks, spectral centroid variance) and spectral evolution (e.g., spectral flux over time) pass. Subjective listening confirms richer, evolving pad sounds.
    *   **TDD Anchor:** Define and implement tests: `test_generate_pads_spectral_centroid_variance`, `test_generate_pads_spectral_flux`. Ensure `_generate_pads` output passes these new metric thresholds.

*   **REQ-ART-A02-v2: Rich Drone Generation**
    *   **Description:** Enhance `_generate_drones` in `sacred_machinery.py` for richer harmonic content and subtle movement. Explore techniques like FM synthesis, multiple detuned oscillators, slow crossfading between sound sources, or subtle filtering/modulation. Define *new* tests first to quantify "richness" and "movement".
    *   **Acceptance Criteria:** New tests measuring harmonic richness (e.g., harmonic count, inharmonicity ratio) and spectral movement (e.g., low spectral flux but non-zero variance) pass. Subjective listening confirms richer, subtly moving drone sounds.
    *   **TDD Anchor:** Define and implement tests: `test_generate_drones_harmonic_richness`, `test_generate_drones_spectral_movement`. Ensure `_generate_drones` output passes these new metric thresholds.

### 4.3 Phase 3: Melodic Refinement (Priority P3)

*   **REQ-ART-MEL-03: Syllable/Note Duration Control**
    *   **Description:** Implement a mechanism to control the duration of synthesized syllables or notes, allowing rhythmic phrasing aligned with the input melody (`REQ-ART-MEL-01`/`02`). Requires careful design: investigate options like modifying TTS phoneme timing (if possible with `espeak-ng`), or post-processing synthesized audio using time-stretching algorithms (e.g., `librosa.effects.time_stretch`, phase vocoder methods) aligned with syllable boundaries (which may require separate alignment tooling).
    *   **Acceptance Criteria:** Vocal output rhythmically follows durations specified in conjunction with the melody input format.
    *   **TDD Anchor:** Test vocal output aligns specified syllable durations (e.g., 0.25s vs 0.5s) with corresponding melody notes, verifiable via segmentation and timing analysis.

### 4.4 Future Considerations (Priority P4)

*   **REQ-ART-V04:** Granular Vocal Textures.
*   **REQ-ART-M02:** Stereo Panning Controls.
*   **Further Effects:** Explore alternative/additional effects libraries or implementations if `pedalboard` limitations become significant blockers.

## 5. Non-Functional Requirements

*   **Maintainability:** Code should remain well-structured, documented, and covered by tests. Addressing P1 items is key. Aim for >85% test coverage.
*   **Modularity:** Continue separating concerns (e.g., effects, synthesis, orchestration).
*   **Performance:** Monitor synthesis time, especially if complex new algorithms are introduced. Optimize critical paths if necessary. (Currently not a major concern).
*   **Ease of Use:** Configuration via `config.yml` should remain the primary control method. Documentation (`README.md`) should be kept up-to-date.

## 6. Updated Constraints

*   Constraints C1-C4 from `project_specification.md` (Minimal Changes outside focus, Free TTS, Robotic Voice, Existing Architecture) generally still apply, but P2/P3 requirements will necessitate more significant changes within `sacred_machinery.py` and potentially `vox_dei.py`.
*   Dependency licenses must remain compatible (MIT, Apache 2.0 preferred).