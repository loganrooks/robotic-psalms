# Debugger Specific Memory

*This file stores context, notes, and decisions specific to the Debugger mode.*

---



### Issue: [CLI-SILENT-VOCALS] - Silent vocals in CLI output despite passing tests - [Status: Resolved] - [2025-04-08 11:22:22]
- **Reported**: 2025-04-08 11:17:07 / **Severity**: High / **Symptoms**: `output.wav` generated via CLI (`robotic-psalms ...`) contains no audible vocals, only other stems. Unit tests for TTS (`test_espeak.py`, `test_vox_dei.py`) pass.
- **Investigation**:
    1. Reviewed `cli.py`: Confirmed correct argument parsing and config loading/passing. [2025-04-08 11:17:48]
    2. Reviewed `examples/config.yml`: Confirmed `mix_levels.vocals` is 1.0. [2025-04-08 11:18:02]
    3. Reviewed `sacred_machinery.py`: Identified potential failure point in `try/except` block around `vox_dei.synthesize_text`. [2025-04-08 11:18:09]
    4. Added logging to `process_psalm` around synthesis call. [2025-04-08 11:18:23]
    5. Ran CLI with `--verbose`: Logs showed synthesis succeeded and returned audio data. [2025-04-08 11:20:23]
    6. Added logging to `_mix_components` before mix level application. [2025-04-08 11:20:39]
    7. Ran CLI with `--verbose`: Logs showed `vocals` max amplitude was ~7.6, indicating severe clipping after effects/resampling. [2025-04-08 11:21:08]
- **Root Cause**: Audio processing steps (resampling, effects like reverb convolution) within `SacredMachineryEngine.process_psalm` amplified the vocal signal significantly beyond the [-1.0, 1.0] range. While the final *combined* mix was normalized in `_mix_components`, the individual stems (including `vocals`) were returned and saved without normalization, resulting in clipped/silent audio in `output_stems/vocals.wav`. [2025-04-08 11:21:27]

- **Final Status**: Fixes for resampling pitch shift and haunting effect distortion applied. Debug save points retained in code for future analysis (activated by `--verbose` flag). Remaining issues noted below.
- **Remaining Issues**:
    - White noise/static introduced during formant shifting (`_apply_formant_shift` in `vox_dei.py`).
    - Vocal output lacks desired "sing song / hymnal choir quality" (requires further investigation/tuning of effects, particularly `_choir_filter`).

- **Fix Applied (Attempt 2)**: 
    1. Corrected resampling logic in `SacredMachineryEngine.process_psalm` to use actual TTS sample rate and resample immediately after synthesis. [2025-04-08 11:39:26]
    2. Modified `examples/config.yml` to reduce `haunting_intensity`: `reverb_decay` set to 2.0, `spectral_freeze` set to 0.1. [2025-04-08 11:41:04]
- **Verification**: Pending user confirmation after running the fixed code.
- **Fix Applied**: Added a `_normalize_audio` helper method to `SacredMachineryEngine` and called it on `vocals`, `pads`, `percussion`, and `drones` within `process_psalm` immediately before the call to `_mix_components` and the creation of `SynthesisResult`. This ensures all stems are within the correct amplitude range before being returned or mixed. [2025-04-08 11:22:10]
- **Verification**: Pending user confirmation after running the fixed code.
- **Related Issues**: None identified.
## Current Bug/Issue
<!-- Describe the bug being investigated -->

## Debugging Steps & Observations
<!-- Log debugging actions and findings -->

## Potential Root Causes
<!-- List hypotheses about the cause -->

## Fixes Applied/Attempted
<!-- Document code changes made -->