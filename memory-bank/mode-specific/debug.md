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

### Issue: [DELAY-FEEDBACK-XFAIL] - `test_complex_delay_feedback_parameter` xfails due to identical output - [Status: Investigated] - [2025-04-11 15:57:30]
- **Reported**: 2025-04-11 15:49:05 (Initial Task) / **Severity**: Medium / **Symptoms**: `tests/synthesis/test_effects.py::test_complex_delay_feedback_parameter` marked `xfail` because changing `feedback` (0.5 vs 0.8) in `apply_complex_delay` produced numerically identical outputs (`np.allclose` with `atol=1e-9`), even with `wet_dry_mix=1.0`.
- **Investigation**:
    1. Reviewed test: Used sine wave input, `wet_dry_mix=1.0`, `feedback=0.5` vs `0.8`, `atol=1e-9`. Logic sound, but sine wave might mask differences. [2025-04-11 15:49:51]
    2. Reviewed implementation (`apply_complex_delay`): Confirmed `feedback` parameter correctly passed to `pedalboard.Delay`. [2025-04-11 15:50:02]
    3. Modified test: Changed input to impulse signal. Ran tests: Still `xfailed`. [2025-04-11 15:50:29]
    4. Modified test: Used impulse, increased `delay_time_ms` to 1000.0, used extreme feedback (0.1 vs 0.9). Ran tests: Still `xfailed`. [2025-04-11 15:50:55]
    5. Checked `pedalboard` version: `0.9.16`. [2025-04-11 15:51:10]
    6. Searched web for known issues with `pedalboard==0.9.16` `Delay` feedback: No relevant issues found. [2025-04-11 15:51:18]
    7. Added temporary direct test (`test_direct_pedalboard_delay_feedback`) using `pedalboard.Delay` directly with impulse, 1000ms delay, 1.0 mix, 0.1 vs 0.9 feedback. [2025-04-11 15:51:36]
    8. Fixed imports for direct test. [2025-04-11 15:53:03]
    9. Ran tests: Direct test failed `AssertionError: Direct pedalboard.Delay test failed: feedback change had no effect`. [2025-04-11 15:53:13]
    10. Removed temporary direct test. [2025-04-11 15:57:05]
- **Root Cause**: The `feedback` parameter in `pedalboard.Delay` (version 0.9.16) does not produce numerically different outputs under the tested conditions (impulse signal, 1s delay, 1.0 mix, feedback 0.1 vs 0.9, `atol=1e-9`), even when used directly. The issue appears to be within the library itself. [2025-04-11 15:57:30]
- **Fix Applied**: None. The issue lies within the external library.
- **Verification**: N/A
- **Related Issues**: None identified.
- **Recommendation**: Keep `test_complex_delay_feedback_parameter` marked as `xfail`. Consider reporting the issue to the `pedalboard` developers or investigating alternative delay implementations if precise feedback control is critical.
