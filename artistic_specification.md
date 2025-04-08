# Artistic Specification: Robotic Psalms - "Odi et Amo" Aesthetic

## 1. Goal

This document outlines the refined specifications for the Robotic Psalms project, focusing on achieving a sonic aesthetic inspired by Jóhann Jóhannsson's "Odi et Amo" and similar works. The primary goal is to move beyond basic robotic TTS and create an ethereal, textured, and atmospheric soundscape where the processed vocals are deeply integrated with ambient layers.

## 2. Target Aesthetic Analysis ("Odi et Amo" Style)

Analysis of Jóhann Jóhannsson's relevant work suggests key sonic elements:

*   **Textural Emphasis:** Slow evolution, swells, ambient textures prioritized over distinct melodies.
*   **Integrated Vocals:** Heavy processing (reverb, delay, filtering, layering) often sacrificing intelligibility for atmospheric contribution. Vocals act as another textural layer.
*   **Atmospheric Effects:** Integral use of dense, diffused reverb, complex delays, and potentially subtle analog-style saturation or distortion.
*   **Instrumentation:** Use of drones, sustained tones, simple but evocative harmonic language, and contrast between sonic elements.
*   **Dynamics:** Careful control over dynamics and layering to build atmosphere.

## 3. Current Capabilities Summary

The existing codebase provides:

*   **TTS:** Functional `espeak-ng` integration via command-line wrapper (`EspeakNGWrapper`).
*   **Layers:** Vocals, Pads, Percussion, Drones.
*   **Vocal Effects (`vox_dei.py`):**
    *   FFT-based formant shifting (`_formant_shift`).
    *   Basic timbre blend filters (`_choir_filter`, `_android_filter`, `_machinery_filter`).
*   **Global Effects (`sacred_machinery.py`):**
    *   Basic algorithmic reverb (`_generate_reverb_ir`).
    *   Simple spectral freeze (`_spectral_freeze`).
    *   Randomized digital glitch effect (`_apply_glitch_effect`).
*   **Generation:** Basic pad (`_generate_pads`) and drone (`_generate_drones`) synthesis.
*   **Mixing:** Individual layer normalization followed by simple summation (`_mix_components`).
*   **Configuration:** Pydantic models (`config.py`) for controlling existing parameters, including an optional `midi_input` field.

## 4. Identified Gaps

Comparing the target aesthetic with current capabilities reveals gaps in:

*   **Vocal Processing Sophistication:** Current effects are too basic; lack of layering and advanced techniques. Current TTS likely produces monotone output.
*   **Ambient Texture Quality:** Pad/drone generation is simplistic; reverb and spectral freeze lack depth.
*   **Effects Refinement:** Glitch effect is potentially harsh; lack of saturation options.
*   **Dynamics and Mixing:** Simple summation lacks atmospheric control.
*   **Melodic Control:** No mechanism currently implemented to make vocals follow a specific melody or control note durations.

## 5. Refined Functional Requirements (Artistic Focus)

The following requirements aim to bridge the identified gaps and achieve the target aesthetic. Requirements marked `[P1]` are highest priority. Requirements marked `[P2]` are secondary. Optional/Advanced requirements are marked `[Opt]`.

**5.1 Vocal Processing**

*   **REQ-ART-V01 [P1]: Robust Formant Shifting:** Implement or integrate a more robust formant shifting algorithm (e.g., phase vocoder based) to minimize artifacts and allow smoother control. (Refines existing)
*   **REQ-ART-V02 [P1]: Enhanced Vocal Effects Chain:** Replace/enhance timbre blend filters. Focus on dense reverb, complex delays, and atmospheric filtering suitable for integrating vocals as texture. Remove/replace "choirboy" concept. (Refines existing)
*   **REQ-ART-V03 [P2]: Vocal Layering:** Implement a mechanism to synthesize and layer multiple vocal takes with slight variations (pitch, timing, effects). (New Feature)
*   **REQ-ART-V04 [Opt]: Granular Vocal Textures:** Explore integrating granular synthesis for processing vocal segments. (New Feature)

**5.2 Ambient Layers (Pads/Drones)**

*   **REQ-ART-A01 [P1]: Complex Pad Generation:** Enhance pad generation (`_generate_pads`) for more complex, evolving textures (e.g., wavetable/additive synthesis, slow filter/amp modulation). (Refines existing)
*   **REQ-ART-A02 [P2]: Rich Drone Generation:** Enhance drone generation (`_generate_drones`) for richer harmonic content and movement (e.g., complex FM, crossfading, detuning). (Refines existing)

**5.3 Effects**

*   **REQ-ART-E01 [P1]: High-Quality Reverb:** Replace basic reverb (`_generate_reverb_ir`) with a sophisticated algorithm (e.g., FDN) or allow convolution reverb via IR loading. Expose relevant parameters (pre-delay, diffusion, decay, damping). (Refines existing)
*   **REQ-ART-E02 [P2]: Improved Spectral Freeze:** Replace/enhance spectral freeze (`_spectral_freeze`) for smoother, more controllable sustained textures. (Refines existing)
*   **REQ-ART-E03 [P2]: Refined Glitch Effect:** Refine glitch effect (`_apply_glitch_effect`) for more control and subtlety (e.g., parameterize type/intensity, add tape-style effects). (Refines existing)
*   **REQ-ART-E04 [P2]: Saturation/Distortion:** Introduce configurable analog-style saturation/distortion modules. (New Feature)

**5.4 Mixing and Dynamics**

*   **REQ-ART-M01 [P2]: Master Dynamic Processing:** Implement basic master bus processing (e.g., slow compression, limiting). (New Feature)
*   **REQ-ART-M02 [Opt]: Stereo Panning:** Introduce panning controls for individual layers. (New Feature)

**5.5 Melodic Control**

*   **REQ-ART-MEL-01 [P2]: Melodic Contour Input:** The system shall accept melodic information (pitch sequence) to guide the vocal synthesis, allowing for non-monotone output. (New Feature)
*   **REQ-ART-MEL-02 [P2]: Melodic Input Format:** Define and implement a format for specifying the melody alongside the Latin text (e.g., simplified text-based notation, leverage existing optional `midi_input` field). (New Feature)
*   **REQ-ART-MEL-03 [P2]: Syllable/Note Duration Control:** Allow for specifying variations in the duration of synthesized syllables or notes, enabling rhythmic phrasing and emphasis aligned with the melody. (New Feature)

## 6. Implementation Notes & Constraints

*   Continue leveraging the existing Python structure and configuration system.
*   Prioritize modifications within `vox_dei.py` and `sacred_machinery.py` or introduce new, well-defined modules for specific effects or synthesis techniques.
*   Ensure new parameters are added to the `PsalmConfig` model in `config.py` with appropriate validation and defaults.
*   Melodic control (REQ-ART-MEL-*) will likely require significant changes to `vox_dei.py` and potentially the TTS engine interaction (e.g., synthesizing phonemes/syllables individually and pitch-shifting/time-stretching them). The feasibility with `espeak-ng` needs investigation; alternative TTS or post-processing methods might be required.
*   Maintain focus on free, locally runnable solutions. External libraries should have compatible licenses (MIT, Apache 2.0 preferred).

## 7. TDD Anchors (High-Level)

*   **Vocal Effects:** Test new formant shift preserves pitch, test reverb/delay outputs match expected characteristics, test layering blends correctly.
*   **Ambient Generation:** Test pad/drone outputs have expected harmonic content and modulation.
*   **Global Effects:** Test refined glitch/freeze outputs are qualitatively different and controllable. Test saturation adds expected harmonics.
*   **Mixing:** Test master dynamics affect output levels as expected.
*   **Melodic Control:** Test vocal output follows pitch contour from input (MIDI or other format). Test specified syllable durations are reflected in the output rhythm. Test alignment between lyrics and melody notes.