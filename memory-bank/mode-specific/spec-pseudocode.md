# Specification Writer Specific Memory

*This file stores context, notes, and decisions specific to the Specification Writer mode.*

---

## Functional Requirements
<!-- Append requirements here -->
### Feature: FR1 - Latin Text Input
- Added: 2025-04-08 06:55:44
- Description: The system shall accept Latin psalm text as input.
- Acceptance criteria: 1. System can read text from a specified file path (likely plain text).
- Dependencies: File I/O, Configuration for input path.
- Status: Draft

### Feature: FR2 - TTS Synthesis
- Added: 2025-04-08 06:55:44
- Description: The system shall synthesize the input Latin text into audible speech using a TTS engine.
- Acceptance criteria: 1. Given Latin text, the system produces corresponding audio data.
- Dependencies: Selected TTS Engine, Latin language support in TTS.
- Status: Draft

### Feature: FR3 - Robotic Voice Quality
- Added: 2025-04-08 06:55:44
- Description: The synthesized speech shall possess a robotic/computerized quality.
- Acceptance criteria: 1. Synthesized audio output is clearly non-human and robotic in timbre. 2. Voice parameters (if available) are configured for robotic effect.
- Dependencies: TTS Engine capabilities/parameters.
- Status: Draft

### Feature: FR4 - Configuration Handling
- Added: 2025-04-08 06:55:44
- Description: The system shall allow configuration (e.g., via `config.yml`) to specify input text, output path, and potentially basic synthesis parameters.
- Acceptance criteria: 1. System reads config file (`config.yml`). 2. Input path, output path are configurable. 3. Minimal essential synthesis parameters are configurable.
- Dependencies: `config.py`, YAML parser.
- Status: Draft

### Feature: FR5 - Audio Layer Combination
- Added: 2025-04-08 06:55:44
- Description: The system shall combine the synthesized vocals with existing ambient pads, drones, and percussion layers.
- Acceptance criteria: 1. Output audio contains both synthesized vocals and background ambient layers.
- Dependencies: Existing audio generation modules (`sacred_machinery.py`?), Audio mixing library (e.g., pydub, soundfile).
- Status: Draft

### Feature: FR6 - Audio File Output
- Added: 2025-04-08 06:55:44
- Description: The system shall output the final arrangement as an audio file.
- Acceptance criteria: 1. System writes a playable audio file (e.g., WAV, MP3) to the configured output path.
- Dependencies: Audio mixing library, File I/O, Configuration for output path/format.
- Status: Draft


### Feature: REQ-STAB-01 - Resolve Delay Feedback XFail
- Added: 2025-04-12 06:28:29
- Description: Investigate the failing test for `pedalboard.Delay` feedback (`test_complex_delay_feedback_parameter`). Determine if it's a library issue, test inaccuracy, or implementation error. If unresolvable with `pedalboard`, either find/implement an alternative delay function that supports reliable feedback or document the limitation and adjust the test/parameter.
- Acceptance criteria: 1. The `test_complex_delay_feedback_parameter` test passes OR is documented as unachievable with the current library and potentially removed/modified.
- Dependencies: `tests/synthesis/test_effects.py`, `src/robotic_psalms/synthesis/effects.py`, `pedalboard` library.
- Status: Draft
- TDD Anchors: Test delay feedback produces audible, distinctly different output for feedback=0.1 vs feedback=0.8, with increasing energy/repeats for higher feedback.

### Feature: REQ-STAB-02 - Address Chorus NumVoices XFail
- Added: 2025-04-12 06:28:29
- Description: The `pedalboard.Chorus` ignores `num_voices`. Either implement multi-voice chorus logic manually (e.g., using multiple `pedalboard.Delay` instances with LFO modulation) within `apply_chorus`, or confirm the limitation is acceptable, remove the `num_voices` parameter from `ChorusParameters`, and remove the corresponding `xfail` test (`test_chorus_parameters_affect_output`).
- Acceptance criteria: 1. The `test_chorus_parameters_affect_output` related to `num_voices` passes (if implemented) OR the `num_voices` parameter and test are removed.
- Dependencies: `tests/synthesis/test_effects.py`, `src/robotic_psalms/synthesis/effects.py`, `pedalboard` library.
- Status: Draft
- TDD Anchors: (If implementing) Test `apply_chorus` output with `num_voices=4` is audibly thicker/different compared to `num_voices=2`.

### Feature: REQ-STAB-03 - Fix Glitch Repeat Logic
- Added: 2025-04-12 06:28:29
- Description: Correct the offset calculation or slicing logic within the `_apply_repeat_glitch` helper function in `effects.py` so that the `repeat_count` parameter functions as intended, creating the specified number of repetitions.
- Acceptance criteria: 1. The `test_refined_glitch_repeat_count_affects_output` test passes.
- Dependencies: `tests/synthesis/test_effects.py`, `src/robotic_psalms/synthesis/effects.py`.
- Status: Draft
- TDD Anchors: Test `apply_refined_glitch` with `glitch_type='repeat'` produces output where `repeat_count=3` results in more repetitions / longer modified segment compared to `repeat_count=2`.

### Feature: REQ-STAB-04 - Verify/Refine Melody Contour Accuracy
- Added: 2025-04-12 06:28:29
- Description: Analyze the failing `test_apply_melody_contour_shifts_pitch`. Improve the reliability of pitch detection within the test (e.g., using different algorithms, averaging over segments) or refine the `_apply_melody_contour` implementation in `vox_dei.py` (potentially adjusting `librosa.effects.pitch_shift` parameters) to ensure accurate pitch tracking.
- Acceptance criteria: 1. The `test_apply_melody_contour_shifts_pitch` test passes consistently, demonstrating accurate pitch tracking within a defined tolerance (e.g., +/- 10 Hz).
- Dependencies: `tests/synthesis/test_vox_dei.py`, `src/robotic_psalms/synthesis/vox_dei.py`, `librosa` library.
- Status: Draft
- TDD Anchors: Test `_apply_melody_contour` output segments match target melody pitches within +/- 10 Hz tolerance when analyzed with a reliable pitch detection method.

### Feature: REQ-ART-A01-v2 - Complex Pad Generation
- Added: 2025-04-12 06:28:29
- Description: Enhance `_generate_pads` in `sacred_machinery.py` to produce more complex, evolving textures suitable for the target aesthetic. Explore techniques like wavetable synthesis, additive synthesis, or more sophisticated modulation (multiple LFOs, envelopes) on filters and amplitude. Define *new* tests first to quantify "complexity" and "evolution".
- Acceptance criteria: 1. New tests measuring spectral complexity (e.g., number of significant peaks, spectral centroid variance) and spectral evolution (e.g., spectral flux over time) pass. 2. Subjective listening confirms richer, evolving pad sounds.
- Dependencies: `tests/test_sacred_machinery.py`, `src/robotic_psalms/synthesis/sacred_machinery.py`.
- Status: Draft
- TDD Anchors: Define and implement tests: `test_generate_pads_spectral_centroid_variance`, `test_generate_pads_spectral_flux`. Ensure `_generate_pads` output passes these new metric thresholds.

### Feature: REQ-ART-A02-v2 - Rich Drone Generation
- Added: 2025-04-12 06:28:29
- Description: Enhance `_generate_drones` in `sacred_machinery.py` for richer harmonic content and subtle movement. Explore techniques like FM synthesis, multiple detuned oscillators, slow crossfading between sound sources, or subtle filtering/modulation. Define *new* tests first to quantify "richness" and "movement".
- Acceptance criteria: 1. New tests measuring harmonic richness (e.g., harmonic count, inharmonicity ratio) and spectral movement (e.g., low spectral flux but non-zero variance) pass. 2. Subjective listening confirms richer, subtly moving drone sounds.
- Dependencies: `tests/test_sacred_machinery.py`, `src/robotic_psalms/synthesis/sacred_machinery.py`.
- Status: Draft
- TDD Anchors: Define and implement tests: `test_generate_drones_harmonic_richness`, `test_generate_drones_spectral_movement`. Ensure `_generate_drones` output passes these new metric thresholds.

### Feature: REQ-ART-MEL-03 - Syllable/Note Duration Control
- Added: 2025-04-12 06:28:29
- Updated: 2025-04-12 20:19:00
- Description: Implement a mechanism to control the duration of synthesized syllables or notes, allowing rhythmic phrasing aligned with the input melody (`REQ-ART-MEL-01`/`02`). Uses forced alignment to identify word/phoneme boundaries in the synthesized audio and time-stretching (`librosa`) to adjust segment durations to match target durations derived from the MIDI input.
- Acceptance criteria: 1. Vocal output rhythmically follows durations specified in conjunction with the melody input format (within tolerance). 2. Audio quality remains acceptable after time-stretching.
- Dependencies: `src/robotic_psalms/synthesis/vox_dei.py`, `src/robotic_psalms/utils/midi_parser.py`, `espeak-ng` (TTS), `librosa` (time-stretch), Forced Alignment library (e.g., `aeneas`, `pyfoal`), `numpy`.
- Status: Design Complete
- TDD Anchors: See TDD Anchors section below (related to Forced Aligner, Mapping, Stretching, Integration).


### Feature: REQ-ART-V04 - Granular Vocal Textures
- Added: 2025-04-13 00:22:52
- Description: Integrate granular synthesis capabilities to process vocal segments, enabling the creation of evolving soundscapes, rhythmic effects, or unique textural transformations from the vocal source.
- Acceptance criteria: 1. A new effect module/function (e.g., `apply_granular_synthesis`) is implemented, likely in `effects.py`. 2. Configurable parameters (e.g., `grain_size_ms`, `overlap`, `pitch_variation`, `density`, `window_shape`) are exposed via a Pydantic model (e.g., `GranularParameters`) and integrated into `PsalmConfig`, applied conditionally. 3. Unit tests verify the effect modifies the audio signal in a way consistent with granular synthesis (e.g., spectral changes, temporal changes). 4. Unit tests verify parameter control influences the output characteristics. 5. Subjective listening confirms the effect can transform vocal input into distinct textures.
- Dependencies: `src/robotic_psalms/synthesis/effects.py`, `src/robotic_psalms/config.py`, potentially a granular synthesis library (e.g., `librosa`, `soundgrain`, custom implementation).
- Status: Draft (P4)
- TDD Anchors:
    - `test_granular_effect_exists`: Verify function/model import.
    - `test_granular_effect_modifies_audio`: Check output differs significantly from input.
    - `test_granular_parameter_grain_size`: Verify changing grain size alters output characteristics (e.g., spectral content, perceived texture).
    - `test_granular_parameter_density`: Verify changing density alters output.
    - `test_granular_integration`: Mock and test conditional application within `VoxDeiSynthesizer` or `SacredMachineryEngine`.

### Feature: REQ-ART-M02 - Stereo Panning
- Added: 2025-04-13 00:22:52
- Description: Introduce stereo panning controls for individual synthesized layers (Vocals, Pads, Drones, Percussion) during the final mixing stage.
- Acceptance criteria: 1. Panning parameters (e.g., `vocal_pan`, `pad_pan`, `drone_pan`, `percussion_pan`) are added to `PsalmConfig`, accepting values from -1.0 (full left) to 1.0 (full right), defaulting to 0.0 (center). 2. The mixing logic within `SacredMachineryEngine.process_psalm` is updated to produce stereo output. 3. The mixing logic applies the configured panning to each layer before summation. 4. Unit tests verify that panning parameters correctly influence the left/right channel balance of the final mix.
- Dependencies: `src/robotic_psalms/synthesis/sacred_machinery.py`, `src/robotic_psalms/config.py`, `numpy`.
- Status: Draft (P4)
- TDD Anchors:
    - `test_mix_produces_stereo_output`: Verify output array has 2 channels.
    - `test_pan_left`: Configure `layer_pan = -1.0`, verify energy is predominantly in the left channel (channel 0).
    - `test_pan_right`: Configure `layer_pan = 1.0`, verify energy is predominantly in the right channel (channel 1).
    - `test_pan_center`: Configure `layer_pan = 0.0`, verify energy is roughly equal in both channels.
    - `test_pan_multiple_layers`: Configure different pans for different layers, verify combined output reflects this.

### Feature: REQ-FIX-01 - Investigate/Resolve Delay Feedback XFail
- Added: 2025-04-13 00:22:52
- Description: Re-evaluate the `pedalboard.Delay` feedback limitation identified in P1. Research alternative Python delay implementations (custom DSP, other libraries) that offer reliable feedback control. If a suitable alternative is found and integration is feasible, implement it as a replacement for `pedalboard.Delay`. Otherwise, document the limitation clearly and accept the `xfail`.
- Acceptance criteria: 1. The `test_complex_delay_feedback_parameter` test in `tests/synthesis/test_effects.py` passes consistently. 2. OR: A clear analysis and justification for accepting the limitation is documented, and the test remains `xfail` or is modified appropriately.
- Dependencies: `tests/synthesis/test_effects.py`, `src/robotic_psalms/synthesis/effects.py`, `pedalboard` library, potentially alternative DSP libraries.
- Status: Draft (P4)
- TDD Anchors:
    - (If implementing replacement): Re-use or adapt `test_complex_delay_feedback_parameter` to verify that increasing the feedback parameter results in more audible repeats and energy buildup.

### Feature: REQ-FIX-02 - Investigate/Resolve Chorus Voices XFail
- Added: 2025-04-13 00:22:52
- Description: Re-evaluate the `pedalboard.Chorus` limitation where `num_voices` is ignored. If multi-voice chorus is deemed important for the artistic goals, research and implement a manual multi-voice chorus (e.g., using multiple modulated delays). If the current `pedalboard.Chorus` effect is sufficient, confirm this decision, remove the `num_voices` parameter from `ChorusParameters`/`ChorusConfig`, and remove the corresponding `xfail` test.
- Acceptance criteria: 1. The `test_chorus_parameters_affect_output` test related to `num_voices` in `tests/synthesis/test_effects.py` passes consistently (if manual implementation is chosen). 2. OR: The `num_voices` parameter is removed from configuration and models, and the corresponding test is removed or modified.
- Dependencies: `tests/synthesis/test_effects.py`, `src/robotic_psalms/synthesis/effects.py`, `pedalboard` library.
- Status: Draft (P4)
- TDD Anchors:
    - (If implementing replacement): Create tests verifying that increasing `num_voices` results in an audibly thicker/more complex chorus effect compared to fewer voices.


## Non-Functional Requirements
<!-- Append requirements here -->

## Pseudocode Blocks
<!-- Append pseudocode here -->
### Pseudocode: TTS Fix/Replacement Strategy - Full
- Created: 2025-04-08 07:01:07
- Updated: 2025-04-08 07:01:07
```pseudocode
# Pseudocode: Vocal Synthesis Fix/Replacement

## Overview

This document outlines the pseudocode steps for investigating, fixing, or replacing the Text-to-Speech (TTS) engine within the `robotic-psalms` project, specifically focusing on the `VoxDeiSynthesizer` and its dependencies. The goal is to enable functional, robotic-sounding vocal synthesis using a free, locally runnable engine, integrating its output (as a NumPy float32 array) back into the main audio generation pipeline (`SacredMachineryEngine`).

## Modules & Data Structures

// --- Interfaces ---
INTERFACE TTSEngine
    METHOD initialize(config: Dict) -> Boolean
    METHOD set_parameter(param_name: String, value: Any) -> Void
    METHOD set_voice(voice_properties: Dict) -> Void
    METHOD synthesize(text: String) -> NumpyArray[Float32] // Returns audio data
    METHOD get_supported_parameters() -> List[String]
    METHOD get_available_voices() -> List[Dict]
    METHOD cleanup() -> Void
END INTERFACE

// --- Core Synthesizer ---
CLASS VoxDeiSynthesizer
    // Attributes
    config: PsalmConfig
    sample_rate: Integer
    tts_engine: TTSEngine
    logger: Logger

    // Methods
    METHOD __init__(config: PsalmConfig, sample_rate: Integer)
    METHOD _initialize_tts_engine() -> TTSEngine // Selects and initializes the best available engine
    METHOD synthesize_text(text: String) -> NumpyArray[Float32]
    METHOD _apply_robotic_effects(audio: NumpyArray[Float32]) -> NumpyArray[Float32]
    METHOD _apply_formant_shift(audio: NumpyArray[Float32], factor: Float) -> NumpyArray[Float32] // Existing
    METHOD _apply_timbre_blend(audio: NumpyArray[Float32]) -> NumpyArray[Float32] // Existing (calls choir/android/machinery filters)
    METHOD _choir_filter(audio: NumpyArray[Float32]) -> NumpyArray[Float32] // Existing
    METHOD _android_filter(audio: NumpyArray[Float32]) -> NumpyArray[Float32] // Existing
    METHOD _machinery_filter(audio: NumpyArray[Float32]) -> NumpyArray[Float32] // Existing
END CLASS

// --- Main Engine (Integration Point) ---
CLASS SacredMachineryEngine
    // Attributes
    config: PsalmConfig
    vox_dei: VoxDeiSynthesizer
    // ... other synthesizers (pads, drones, percussion)

    // Methods
    METHOD generate_psalm(text: String) -> NumpyArray[Float32] // Combines all layers
    // ... other methods
END CLASS

## 1. Investigation of Current TTS Implementation

FUNCTION investigate_current_tts()
    // Goal: Analyze EspeakNGWrapper, EspeakWrapper, and espeakmodulecore.cpp
    // to understand the current workflow and identify failure points.

    PRINT "Analyzing src/robotic_psalms/synthesis/tts/engines/espeak.py..."
    // 1.1. Review EspeakNGWrapper.__init__
    //      - Check espeak module import and espeak.core.init call.
    //      - Note initialization mode (AUDIO_OUTPUT_RETRIEVAL).
    //      - Note hardcoded temp file paths: _pcm_path = "/tmp/espeak-wave", _wav_path = "/tmp/espeak-wave.wav". Potential Issue: Permissions, collisions, reliability.
    //      - Note espeak.set_wave_filename call.

    // 1.2. Review EspeakNGWrapper.synth
    //      - Note call to _speaker.say(text).
    //      - Note polling loop waiting for _pcm_path.exists(). Potential Issue: Race condition, file never created.
    //      - Note call to _pcm_to_wav. Potential Issue: Assumes fixed PCM format (16-bit, 22050Hz, mono), conversion errors.
    //      - Note call to sf.read(_wav_path). Potential Issue: WAV file corruption, format mismatch.
    //      - Note cleanup of _wav_path.

    // 1.3. Review EspeakWrapper (Legacy)
    //      - Confirm it's marked "DO NOT USE" and synth returns empty array.

    PRINT "Analyzing lib/espeakmodulecore.cpp..."
    // 1.4. Review PyEspeakCB (Callback Function)
    //      - Understand how events are handled.
    //      - Identify where wave data is potentially available (event->type == espeakEVENT_LIST_TERMINATED).
    //      - Note the DoCallback function writing raw data to `wave_filename` if set. Confirms source of /tmp/espeak-wave. Potential Issue: File I/O within callback is risky.

    // 1.5. Review pyespeak_initialize
    //      - Note setting of PyEspeakCB via espeak_SetSynthCallback.

    // 1.6. Review pyespeak_set_wave_filename
    //      - Confirms how the filename used in the callback is set from Python.

    PRINT "Analyzing src/robotic_psalms/synthesis/vox_dei.py..."
    // 1.7. Review VoxDeiSynthesizer.__init__
    //      - Note the attempt to load EspeakNGWrapper first, then EspeakWrapper.
    //      - Note how parameters (rate, pitch, volume) are set on the engine.

    // 1.8. Review VoxDeiSynthesizer.synthesize_text
    //      - Note the call to self.espeak.synth(text).
    //      - Note the expectation of a NumPy float32 array return value.
    //      - Note subsequent calls to _apply_formant_shift and _apply_timbre_blend.

    PRINT "Potential Failure Points Summary:"
    PRINT "  - Hardcoded /tmp file paths (permissions, collisions)"
    PRINT "  - Fragile file polling mechanism (race conditions, callback failures)"
    PRINT "  - Risky PCM->WAV conversion (format assumptions, errors)"
    PRINT "  - Inefficient file I/O instead of direct buffer handling"
    PRINT "  - Complexity of C++ callback interacting with Python via files"
    PRINT "  - Potential underlying eSpeak-NG library/binding installation issues"

END FUNCTION

## 2. Attempt eSpeak-NG Fix (If Viable)

FUNCTION attempt_espeak_ng_fix(tts_engine_ref: EspeakNGWrapper) -> Boolean
    // Goal: Modify the existing EspeakNGWrapper and potentially espeakmodulecore.cpp
    // to achieve reliable audio output, preferring direct buffer handling.
    // Constraint: Must remain free, produce robotic voice.

    PRINT "Attempting eSpeak-NG Fix..."

    // --- Option A: Direct Buffer Handling (Preferred) ---
    PRINT "  Attempting Direct Buffer Handling..."
    // 2.A.1. Modify espeakmodulecore.cpp:
    //      - Modify PyEspeakCB or DoCallback: Instead of writing to file, capture the `short* wave` buffer when `event->type == espeakEVENT_LIST_TERMINATED`.
    //      - Devise mechanism to pass this buffer back to Python. Possibilities:
    //          - Store buffer pointer/size globally, add C++ function callable from Python to retrieve it.
    //          - Modify callback signature/return value (might require deeper changes to bindings).
    //          - Use a shared memory segment (more complex).
    //      - Ensure proper memory management (copy buffer if needed).
    //      - Recompile the C++ extension.

    // 2.A.2. Modify EspeakNGWrapper (Python):
    //      - Remove file polling logic (`while not self._pcm_path.exists()`).
    //      - Remove _pcm_to_wav call and associated temp file handling.
    //      - After calling `_speaker.say(text)`, call the new C++ function (or use other mechanism) to retrieve the raw audio buffer (likely `bytes` or `memoryview` in Python).
    //      - Convert the raw buffer (short integers) to NumPy float32 array. Need correct sample rate (query eSpeak? Assume 22050Hz initially?). Need correct byte order/format.
    //      - Normalize the float32 array (e.g., divide by 32768.0).
    //      - Apply volume boost if necessary (as done previously).
    //      - Return the NumPy array.

    IF direct_buffer_handling_successful THEN
        PRINT "  Direct Buffer Handling Fix Successful."
        RETURN TRUE
    ELSE
        PRINT "  Direct Buffer Handling Failed. Attempting File-Based Fix..."
    END IF

    // --- Option B: Improve File-Based Handling (Fallback) ---
    PRINT "  Attempting Improved File-Based Handling..."
    // 2.B.1. Modify EspeakNGWrapper.__init__:
    //      - Replace hardcoded `/tmp/espeak-wave` with `tempfile.NamedTemporaryFile(suffix='.pcm', delete=False)` to get unique, managed paths. Store this path.
    //      - Create a corresponding unique WAV path: `pcm_path.with_suffix('.wav')`.
    //      - Pass the unique PCM path to `espeak.set_wave_filename`.

    // 2.B.2. Modify EspeakNGWrapper.synth:
    //      - Improve file polling: Increase timeout, add more robust checks for file size/completion.
    //      - Add error handling around `_pcm_to_wav` and `sf.read`. Log specific errors.
    //      - Ensure temporary files are reliably deleted in a `finally` block.
    //      - Verify assumed PCM format (16-bit, 22050Hz, mono) matches actual eSpeak-NG output. If not, adjust `_pcm_to_wav` or `sf.read` parameters. Query eSpeak for sample rate if possible (`espeak_GetParameter(espeakSAMPLERATE, 1)` in C++?).

    // 2.B.3. Test thoroughly.

    IF file_based_handling_successful THEN
        PRINT "  Improved File-Based Handling Fix Successful."
        RETURN TRUE
    ELSE
        PRINT "  eSpeak-NG Fix Failed."
        RETURN FALSE
    END IF

END FUNCTION

## 3. Alternative TTS Research & Integration (If Necessary)

FUNCTION research_and_integrate_alternative_tts() -> TTSEngine OR None
    // Goal: Find and integrate a different TTS engine if eSpeak fix fails or is unsuitable.
    // Constraints: Free, local, Python-compatible, capable of robotic voice.

    PRINT "Researching alternative TTS engines..."
    // 3.1. Identify Candidates:
    //      - Search for Python libraries wrapping system TTS (like pyttsx3 - often uses eSpeak/Festival/SAPI).
    //      - Search for standalone Python TTS libraries (e.g., Piper TTS, Coqui TTS - check licenses carefully).
    //      - Prioritize engines with adjustable parameters (pitch, rate, formant?) for robotic quality.

    // 3.2. Evaluate Candidates:
    //      - Check license compatibility (GPL, MIT, Apache, etc.).
    //      - Check ease of installation and dependencies.
    //      - Check documentation for Python API and parameter control.
    //      - Perform basic tests to confirm audio output and potential for robotic voice.

    // 3.3. Select Best Candidate:
    selected_engine_name = choose_best_candidate() // e.g., "piper", "pyttsx3"
    IF selected_engine_name IS None THEN
        PRINT "No suitable alternative TTS engine found."
        RETURN None
    END IF

    PRINT "Integrating selected engine: " + selected_engine_name

    // 3.4. Create New TTSEngine Wrapper:
    //      - Create a new file, e.g., `src/robotic_psalms/synthesis/tts/engines/piper_tts.py`.
    //      - Implement a class `PiperWrapper` that conforms to the `TTSEngine` interface.
    CLASS PiperWrapper IMPLEMENTS TTSEngine
        METHOD __init__(config: Dict)
            // Initialize Piper TTS library, load voice model specified in config.
        END METHOD

        METHOD set_parameter(param_name: String, value: Any) -> Void
            // Map standard parameters (RATE, PITCH, VOLUME) to Piper's API, if possible.
        END METHOD

        METHOD set_voice(voice_properties: Dict) -> Void
            // Potentially reload model or use specific voice variants if supported.
        END METHOD

        METHOD synthesize(text: String) -> NumpyArray[Float32]
            // Call Piper's synthesis function.
            // Ensure output is converted to NumPy float32 array at the target sample rate (resample if needed).
            // Normalize audio data.
        END METHOD

        // Implement other TTSEngine methods (get_supported_parameters, etc.)
        METHOD cleanup() -> Void
            // Release any resources held by the Piper library.
        END METHOD
    END CLASS

    // 3.5. Update VoxDeiSynthesizer._initialize_tts_engine:
    //      - Add logic to attempt loading the new wrapper (e.g., `PiperWrapper`) if eSpeak fails or is explicitly configured.
    //      - Pass necessary configuration (e.g., voice model path) to the wrapper's constructor.

    RETURN instance_of_new_wrapper

END FUNCTION

## 4. Integration into Synthesizers

// --- Integration within VoxDeiSynthesizer ---

CLASS VoxDeiSynthesizer
    METHOD __init__(config: PsalmConfig, sample_rate: Integer)
        self.config = config
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        self.tts_engine = self._initialize_tts_engine() // <--- Integration Point 1
    END METHOD

    METHOD _initialize_tts_engine() -> TTSEngine
        PRINT "Initializing TTS Engine..."
        // Try fixed eSpeak-NG first
        TRY
            engine = EspeakNGWrapper() // Assumes fix was applied
            IF engine.initialize(self.config.tts_config) THEN // Pass relevant config
                 PRINT "Using fixed eSpeak-NG Engine."
                 RETURN engine
            END IF
        CATCH Error AS e
            self.logger.warning("Fixed eSpeak-NG failed: " + e)
        END TRY

        // Try alternative engine (if eSpeak fix failed or wasn't attempted)
        TRY
            // Example: Using PiperWrapper if selected in step 3
            engine = research_and_integrate_alternative_tts() // This would return an instance
            IF engine IS NOT None AND engine.initialize(self.config.tts_config) THEN
                PRINT "Using Alternative TTS Engine."
                RETURN engine
            END IF
        CATCH Error as e
             self.logger.warning("Alternative TTS failed: " + e)
        END TRY

        self.logger.error("No functional TTS engine available.")
        RAISE VoxDeiSynthesisError("TTS Initialization Failed")
    END METHOD

    METHOD synthesize_text(text: String) -> NumpyArray[Float32]
        IF self.tts_engine IS None THEN
            RAISE VoxDeiSynthesisError("No TTS engine available")
        END IF

        TRY
            // Configure engine parameters based on current config (e.g., tempo, articulation)
            // Example: self.tts_engine.set_parameter("RATE", calculated_rate)
            // Example: self.tts_engine.set_parameter("PITCH", calculated_pitch)

            // Synthesize using the chosen engine
            raw_audio = self.tts_engine.synthesize(text) // <--- Integration Point 2

            IF length(raw_audio) == 0 THEN
                RAISE VoxDeiSynthesisError("TTS returned empty audio")
            END IF

            // Apply robotic post-processing
            processed_audio = self._apply_robotic_effects(raw_audio) // <--- Integration Point 3

            RETURN processed_audio

        CATCH Error AS e
            RAISE VoxDeiSynthesisError("TTS synthesis or processing failed: " + str(e))
        END TRY
    END METHOD

    METHOD _apply_robotic_effects(audio: NumpyArray[Float32]) -> NumpyArray[Float32]
        // Goal: Apply existing post-processing for robotic timbre.
        // This function leverages existing methods.

        PRINT "Applying robotic effects..."
        // Apply formant shift based on config
        formant_shifted_audio = self._apply_formant_shift(audio, self.config.voice_range.formant_shift)

        // Apply timbre blend (choir, android, machinery filters) based on config
        timbre_blended_audio = self._apply_timbre_blend(formant_shifted_audio)

        // Optional: Apply final gain/clipping if needed (e.g., np.tanh(audio * gain))
        final_audio = np.tanh(timbre_blended_audio * 2.0) // Example gain/clipping

        RETURN final_audio
    END METHOD

END CLASS


// --- Integration within SacredMachineryEngine ---

CLASS SacredMachineryEngine
    METHOD generate_psalm(text: String) -> NumpyArray[Float32]
        // ... load config ...
        // ... initialize self.vox_dei = VoxDeiSynthesizer(config, sample_rate) ...
        // ... initialize other synths (pads, drones, percussion) ...

        PRINT "Generating vocal track..."
        vocal_track = self.vox_dei.synthesize_text(text) // <--- Integration Point 4

        PRINT "Generating other audio layers..."
        pad_track = self.pad_synth.generate(...)
        drone_track = self.drone_synth.generate(...)
        percussion_track = self.percussion_synth.generate(...)

        PRINT "Mixing audio layers..."
        // Ensure all tracks have the same length (pad/truncate as needed)
        // Mix vocal_track, pad_track, drone_track, percussion_track according to config levels.
        final_mix = mix_audio_layers(vocal_track, pad_track, drone_track, percussion_track)

        RETURN final_mix
    END METHOD
END CLASS
```
#### TDD Anchors:
- Test C++ extension modifications independently if possible.
- Test Python buffer retrieval and conversion to NumPy array.
- Test `EspeakNGWrapper.synth` method returns correctly formatted audio data for known input.
- Test `EspeakNGWrapper.synth` method with file handling, ensure temp files are cleaned up.
- Test handling of potential file I/O errors during synthesis.
- Test `AlternativeWrapper.synthesize` returns correct format (float32 NumPy) and sample rate.
- Test parameter setting (`set_parameter`) works as expected.
- Test `_initialize_tts_engine` selects and initializes the correct engine based on availability/config.
- Test `synthesize_text` calls the TTS engine correctly.
- Verify `synthesize_text` output is a float32 NumPy array at the target sample rate.
- Test `_apply_robotic_effects` calls formant shift and timbre blend.
- Test formant shift application produces expected changes.
- Test timbre blend application produces expected changes.
- Test `generate_psalm` successfully calls `vox_dei.synthesize_text`.
- Test that the final mix contains audible vocal elements.


### Pseudocode: REQ-ART-MEL-03 - Syllable/Note Duration Control
- Created: 2025-04-12 20:19:00
- Updated: 2025-04-12 20:19:00
```pseudocode
# In src/robotic_psalms/synthesis/vox_dei.py

# Add necessary imports for forced alignment library and time stretching
IMPORT forced_alignment_tool # e.g., aeneas, pyfoal
IMPORT librosa
IMPORT numpy as np
FROM typing IMPORT List, Tuple, Optional

CLASS VoxDeiSynthesizer

    # ... (existing methods: __init__, _initialize_tts_engine, _apply_robotic_effects, etc.) ...

    METHOD synthesize_text(self, text: String, midi_path: Optional[String] = None) -> NumpyArray[Float32]
        IF self.tts_engine IS None THEN
            RAISE VoxDeiSynthesisError("No TTS engine available")
        END IF

        TRY
            // --- 1. Initial Synthesis ---
            self.logger.info("Synthesizing raw audio...")
            # Configure TTS parameters if needed (pitch, rate etc. - potentially base values before melody contour)
            # self.tts_engine.set_parameter(...)
            raw_audio = self.tts_engine.synthesize(text)
            IF length(raw_audio) == 0 THEN
                RAISE VoxDeiSynthesisError("TTS returned empty audio")
            END IF
            self.logger.info(f"Raw audio synthesized, length: {len(raw_audio)} samples")

            // --- 2. Duration Control (If MIDI provided) ---
            duration_controlled_audio = raw_audio
            IF midi_path IS NOT None THEN
                self.logger.info(f"Applying duration control using MIDI: {midi_path}")
                TRY
                    # Parse MIDI to get target durations
                    # Assuming midi_parser returns List[Tuple[pitch_hz, duration_sec]]
                    target_notes = parse_midi_melody(midi_path) # Existing function
                    target_durations = [note[1] for note in target_notes]

                    IF target_durations THEN
                        duration_controlled_audio = self._apply_duration_control(
                            raw_audio, text, target_durations
                        )
                        self.logger.info(f"Duration control applied, new length: {len(duration_controlled_audio)} samples")
                    ELSE
                        self.logger.warning("MIDI parsed, but no notes found. Skipping duration control.")
                    END IF
                CATCH Error AS e
                    self.logger.error(f"Failed to apply duration control: {e}. Using raw audio.")
                    # Fallback to raw_audio if duration control fails
                    duration_controlled_audio = raw_audio
            END IF

            // --- 3. Apply Robotic Effects (Formant, Timbre) ---
            self.logger.info("Applying robotic effects...")
            processed_audio = self._apply_robotic_effects(duration_controlled_audio)

            // --- 4. Apply Melody Contour (Pitch Shifting - if MIDI provided) ---
            // Note: Pitch shifting AFTER duration control might be better quality
            final_audio = processed_audio
            IF midi_path IS NOT None AND target_notes THEN
                 self.logger.info("Applying melody contour...")
                 # Assuming _apply_melody_contour takes the audio and the list of (pitch, duration) tuples
                 # It might need modification if it expects original audio timing.
                 # For now, assume it works on the duration-controlled audio.
                 final_audio = self._apply_melody_contour(processed_audio, target_notes)
                 self.logger.info("Melody contour applied.")
            END IF


            RETURN final_audio

        CATCH Error AS e
            RAISE VoxDeiSynthesisError(f"Synthesis pipeline failed: {e}")
        END TRY
    END METHOD

    METHOD _apply_duration_control(self,
                                   audio: NumpyArray[Float32],
                                   text: String,
                                   target_durations: List[float]
                                  ) -> NumpyArray[Float32]

        // --- 2a. Forced Alignment ---
        self.logger.info("Performing forced alignment...")
        # Configure aligner (language, mode: word/phoneme) based on self.config
        # Example using a hypothetical aligner API
        alignment_config = self.config.forced_aligner_config # Get from PsalmConfig
        aligner = forced_alignment_tool.Aligner(alignment_config)

        # Aligner needs audio path or data, and text path or data
        # Save temporary audio file if needed by the aligner
        temp_audio_path = save_temp_wav(audio, self.sample_rate)
        try:
            # Returns list like [(segment_text, start_sec, end_sec), ...]
            # Using 'word' level alignment as initial strategy
            aligned_segments = aligner.align(audio_path=temp_audio_path, text=text, mode='word')
        finally:
            remove_temp_file(temp_audio_path) # Clean up

        IF NOT aligned_segments THEN
            self.logger.warning("Forced alignment returned no segments. Skipping duration control.")
            RETURN audio
        END IF
        self.logger.info(f"Alignment found {len(aligned_segments)} segments.")

        // --- 2b. Map Segments to Target Durations ---
        num_segments = len(aligned_segments)
        num_targets = len(target_durations)
        self.logger.info(f"Mapping {num_segments} aligned segments to {num_targets} target durations.")

        # Simple 1:1 mapping - handle mismatch
        mapped_targets = {} # Dict[segment_index, target_duration]
        for i in range(min(num_segments, num_targets)):
            mapped_targets[i] = target_durations[i]

        if num_segments > num_targets:
            self.logger.warning(f"More aligned segments ({num_segments}) than target durations ({num_targets}). Extra segments will keep original duration.")
        elif num_targets > num_segments:
            self.logger.warning(f"More target durations ({num_targets}) than aligned segments ({num_segments}). Extra durations ignored.")

        // --- 2c. Time Stretching ---
        stretched_pieces = []
        sample_rate_float = float(self.sample_rate)

        for i, (segment_text, start_sec, end_sec) in enumerate(aligned_segments):
            start_sample = int(start_sec * sample_rate_float)
            end_sample = int(end_sec * sample_rate_float)
            audio_segment = audio[start_sample:end_sample]

            original_duration = end_sec - start_sec
            target_duration = mapped_targets.get(i, original_duration) # Use original if no target mapped

            IF original_duration <= 0 or target_duration <= 0 THEN
                self.logger.warning(f"Segment '{segment_text}' has invalid duration (orig: {original_duration}, target: {target_duration}). Skipping stretch.")
                stretched_pieces.append(audio_segment)
                CONTINUE
            END IF

            stretch_factor = target_duration / original_duration
            self.logger.debug(f"Stretching segment '{segment_text}' ({original_duration:.3f}s -> {target_duration:.3f}s), factor: {stretch_factor:.3f}")

            # Avoid extreme stretching if possible, maybe clamp factor?
            # stretch_factor = max(0.5, min(2.0, stretch_factor)) # Example clamping

            IF abs(stretch_factor - 1.0) < 0.01 THEN # Avoid tiny stretches
                 stretched_segment = audio_segment
            ELSE
                # librosa.effects.time_stretch expects rate = 1 / stretch_factor
                # Correction: rate IS the stretch factor. rate > 1 speeds up (shorter), rate < 1 slows down (longer).
                # We want the output duration to be target_duration.
                # If target > original, we need to slow down (rate < 1). rate = original / target
                # If target < original, we need to speed up (rate > 1). rate = original / target
                # So, rate = original_duration / target_duration = 1.0 / stretch_factor
                stretch_rate = 1.0 / stretch_factor
                try:
                    stretched_segment = librosa.effects.time_stretch(y=audio_segment, rate=stretch_rate)
                except Exception as stretch_error:
                    self.logger.error(f"Librosa time_stretch failed for segment '{segment_text}': {stretch_error}. Using original segment.")
                    stretched_segment = audio_segment

            END IF
            stretched_pieces.append(stretched_segment)

        // --- 2d. Concatenate ---
        IF stretched_pieces THEN
            return np.concatenate(stretched_pieces).astype(np.float32)
        ELSE
            self.logger.warning("No segments were stretched. Returning original audio.")
            return audio
        END IF

    END METHOD

END CLASS

# Helper functions (to be defined elsewhere, e.g., utils)
FUNCTION save_temp_wav(audio: NumpyArray[Float32], sample_rate: int) -> String
    # Uses tempfile and soundfile to save audio, returns path
END FUNCTION

FUNCTION remove_temp_file(path: String)
    # Deletes the file at path
END FUNCTION

FUNCTION parse_midi_melody(midi_path: str) -> List[Tuple[float, float]]
    # Existing function in src/robotic_psalms/utils/midi_parser.py
END FUNCTION
```

## TDD Anchors
<!-- Append TDD anchors here -->

#### TDD Anchors: REQ-ART-MEL-03 - Syllable/Note Duration Control
- **Forced Aligner Integration:**
    - `test_forced_aligner_returns_boundaries`: Mock or use a real aligner with known audio/text to verify it returns a list of `(segment, start, end)` tuples.
    - `test_forced_aligner_handles_empty_audio`: Verify behavior with zero-length audio.
    - `test_forced_aligner_handles_no_text`: Verify behavior with empty text.
    - `test_forced_aligner_handles_config`: Verify aligner uses configuration parameters.
- **Mapping Logic:**
    - `test_map_segments_to_durations_equal_length`: Test 1:1 mapping when segment count equals target count.
    - `test_map_segments_to_durations_more_segments`: Test mapping when segments > targets (extra segments use original duration).
    - `test_map_segments_to_durations_more_targets`: Test mapping when targets > segments (extra targets ignored).
- **Time Stretching Segment:**
    - `test_stretch_segment_makes_longer`: Verify stretching with factor < 1.0 increases segment length.
    - `test_stretch_segment_makes_shorter`: Verify stretching with factor > 1.0 decreases segment length.
    - `test_stretch_segment_no_stretch`: Verify stretching with factor ~1.0 results in minimal length change.
    - `test_stretch_segment_handles_zero_duration`: Verify behavior with zero original or target duration.
    - `test_stretch_segment_handles_librosa_error`: Mock `librosa.effects.time_stretch` to raise error, verify original segment is used.
- **`_apply_duration_control` Integration:**
    - `test_apply_duration_control_calls_aligner`: Mock aligner, verify it's called.
    - `test_apply_duration_control_calls_stretcher`: Mock `librosa.effects.time_stretch`, verify it's called for segments needing stretching.
    - `test_apply_duration_control_concatenates_results`: Verify output audio length is approximately the sum of target durations (within tolerance).
    - `test_apply_duration_control_handles_alignment_failure`: Mock aligner to return empty list, verify original audio is returned.
- **`synthesize_text` Integration:**
    - `test_synthesize_text_calls_duration_control_with_midi`: Mock `_apply_duration_control`, verify it's called when `midi_path` is provided.
    - `test_synthesize_text_skips_duration_control_without_midi`: Verify `_apply_duration_control` is NOT called when `midi_path` is None.
    - `test_synthesize_text_applies_effects_after_duration_control`: Mock `_apply_robotic_effects`, verify it receives the output of `_apply_duration_control`.
    - `test_synthesize_text_applies_contour_after_duration_control`: Mock `_apply_melody_contour`, verify it receives the output of `_apply_robotic_effects`.
- **End-to-End (Qualitative/Analysis):**
    - `test_output_rhythm_matches_midi`: Synthesize audio with known text/MIDI rhythm. Analyze output audio (e.g., using onset detection or manual inspection) to confirm segment durations match MIDI note durations.

## System Constraints
<!-- Append new constraints using the format below -->

### Constraint: C1 - Minimal Code Changes
- Added: 2025-04-08 06:55:44
- Description: Except for the vocal synthesis modules (`vox_dei.py`, TTS engines), changes to the existing codebase should be avoided unless strictly necessary to make the vocal synthesis work.
- Impact: Limits refactoring scope; requires working within the existing structure for non-TTS parts.
- Mitigation strategy: Focus development effort solely on TTS integration and `vox_dei.py`. Document any unavoidable changes elsewhere.

### Constraint: C2 - Free TTS
- Added: 2025-04-08 06:55:44
- Description: The TTS solution must be free to use and run locally (no cloud services with associated costs). Open-source solutions like eSpeak, Festival, or similar alternatives are preferred.
- Impact: Narrows down the choice of TTS engines; may require more effort for integration or finding suitable quality.
- Mitigation strategy: Prioritize fixing eSpeak/Festival. If unsuccessful, research and evaluate free, offline Python-compatible TTS libraries (e.g., pyttsx3, Coqui TTS - check licensing).

### Constraint: C3 - Robotic Voice
- Added: 2025-04-08 06:55:44
- Description: The target voice quality is explicitly robotic/non-human.
- Impact: Guides TTS engine selection and parameter tuning. Avoids effort in achieving naturalness.
- Mitigation strategy: Select TTS engines known for robotic voices or highly configurable parameters (like eSpeak). Tune parameters for desired effect.

### Constraint: C4 - Existing Architecture
- Added: 2025-04-08 06:55:44
- Description: Leverage the existing Python project structure (`pyproject.toml`, `src/robotic_psalms/`) and configuration system (`config.py`, `examples/config.yml`).
- Impact: Requires new code to fit within the established patterns and use the existing config system.
- Mitigation strategy: Analyze existing structure (`__init__.py`, `cli.py`, `config.py`) before implementation. Place new TTS code within `src/robotic_psalms/synthesis/tts/engines/`.
