# Debugger Feedback Log

*This file records feedback received regarding the Debugger mode's performance, decisions, or outputs.*

---



### [2025-04-08 11:56:45] - Source: User
- **Issue/Feedback**: After applying resampling fix and reducing haunting intensity:
    1. White noise/static is present after formant shifting (`debug_vocals_02_after_formant_shift.wav`). (Note: User requested *not* to fix this now).
    2. The final vocal output lacks the desired "sing song / hymnal choir quality".
    3. Previous distortion and pitch issues seem resolved.
- **Analysis**:
    1. The `_apply_formant_shift` method likely introduces noise artifacts.
    2. The combination of TTS output and subsequent effects (`_apply_timbre_blend`, specifically `_choir_filter`, and potentially others) is not producing the target aesthetic. The `_choir_filter` needs review.
- **Action Taken/Learnings**: Will focus on improving the hymnal quality by investigating and potentially adjusting the `_choir_filter` and related timbre blending logic in `vox_dei.py`.


### [2025-04-08 11:38:59] - Source: User
- **Issue/Feedback**: Analysis of debug WAV files revealed:
    1. Distortion ("eerie wind") appears after haunting effects (Step 05: `debug_vocals_05_after_haunting.wav`).
    2. Undesirable pitch/speed increase ("chipmunk" effect) appears after resampling (Step 04: `debug_vocals_04_resampled.wav`).
- **Analysis**:
    1. The `_apply_haunting_effects` method (reverb/spectral freeze) in `sacred_machinery.py` is causing severe distortion.
    2. The resampling logic in `sacred_machinery.py` (likely in `_fit_to_length` or the initial check) is incorrectly handling the sample rate change from TTS (22050Hz) to engine (48000Hz), causing pitch shift.
- **Action Taken/Learnings**: Will fix resampling logic in `SacredMachineryEngine.process_psalm` to use the actual TTS sample rate and resample early. Will also reduce the intensity of reverb/spectral freeze in `_apply_haunting_effects`.


### [2025-04-08 11:26:30] - Source: User
- **Issue/Feedback**: After applying the normalization fix for clipping (Issue [CLI-SILENT-VOCALS]), the vocal track in the CLI output (`output.wav` and `output_stems/vocals.wav`) is still heavily distorted and unintelligible, described as sounding like "eerie wind".
- **Analysis**: The normalization prevented silence due to clipping, but revealed an underlying distortion issue in the vocal processing pipeline itself. The distortion might originate from the base TTS output, robotic effects (`VoxDeiSynthesizer`), haunting/glitch effects (`SacredMachineryEngine`), or resampling.
- **Action Taken/Learnings**: Will investigate the source of distortion by systematically checking the audio quality at different stages of the processing pipeline, starting with `VoxDeiSynthesizer`.
<!-- Append feedback entries below -->
<!-- Format:
### [YYYY-MM-DD HH:MM:SS] - Source: [User/Mode/System]
- **Issue/Feedback**: [Description of the feedback]
- **Analysis**: [Brief analysis of the feedback]
- **Action Taken/Learnings**: [How the feedback was addressed or what was learned]
-->