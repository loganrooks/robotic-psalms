# Pseudocode: Vocal Synthesis Fix/Replacement

## Overview

This document outlines the pseudocode steps for investigating, fixing, or replacing the Text-to-Speech (TTS) engine within the `robotic-psalms` project, specifically focusing on the `VoxDeiSynthesizer` and its dependencies. The goal is to enable functional, robotic-sounding vocal synthesis using a free, locally runnable engine, integrating its output (as a NumPy float32 array) back into the main audio generation pipeline (`SacredMachineryEngine`).

## Modules & Data Structures

```pseudocode
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
```

## 1. Investigation of Current TTS Implementation

```pseudocode
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
```

## 2. Attempt eSpeak-NG Fix (If Viable)

```pseudocode
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
    // # TDD: Test C++ extension modifications independently if possible.

    // 2.A.2. Modify EspeakNGWrapper (Python):
    //      - Remove file polling logic (`while not self._pcm_path.exists()`).
    //      - Remove _pcm_to_wav call and associated temp file handling.
    //      - After calling `_speaker.say(text)`, call the new C++ function (or use other mechanism) to retrieve the raw audio buffer (likely `bytes` or `memoryview` in Python).
    //      - Convert the raw buffer (short integers) to NumPy float32 array. Need correct sample rate (query eSpeak? Assume 22050Hz initially?). Need correct byte order/format.
    //      - Normalize the float32 array (e.g., divide by 32768.0).
    //      - Apply volume boost if necessary (as done previously).
    //      - Return the NumPy array.
    // # TDD: Test buffer retrieval and conversion to NumPy array.
    // # TDD: Test synth method returns correctly formatted audio data for known input.

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
    // # TDD: Test synth method with file handling, ensure temp files are cleaned up.
    // # TDD: Test handling of potential file I/O errors.

    IF file_based_handling_successful THEN
        PRINT "  Improved File-Based Handling Fix Successful."
        RETURN TRUE
    ELSE
        PRINT "  eSpeak-NG Fix Failed."
        RETURN FALSE
    END IF

END FUNCTION
```

## 3. Alternative TTS Research & Integration (If Necessary)

```pseudocode
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
            // # TDD: Test synthesize returns correct format and sample rate.
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
```

## 4. Integration into Synthesizers

```pseudocode
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
            // # TDD: Verify raw_audio is float32 NumPy array at correct sample rate.

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
        // # TDD: Test formant shift application.

        // Apply timbre blend (choir, android, machinery filters) based on config
        timbre_blended_audio = self._apply_timbre_blend(formant_shifted_audio)
        // # TDD: Test timbre blend application.

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
        // # TDD: Test integration, ensure vocal_track is generated.

        PRINT "Generating other audio layers..."
        pad_track = self.pad_synth.generate(...)
        drone_track = self.drone_synth.generate(...)
        percussion_track = self.percussion_synth.generate(...)

        PRINT "Mixing audio layers..."
        // Ensure all tracks have the same length (pad/truncate as needed)
        // Mix vocal_track, pad_track, drone_track, percussion_track according to config levels.
        final_mix = mix_audio_layers(vocal_track, pad_track, drone_track, percussion_track)
        // # TDD: Test mixing logic (though outside scope of TTS fix).

        RETURN final_mix
    END METHOD
END CLASS
```

## 5. TDD Anchors Summary

*   **eSpeak Fix (Direct Buffer):**
    *   Test C++ extension modifications independently if possible.
    *   Test Python buffer retrieval and conversion to NumPy array.
    *   Test `EspeakNGWrapper.synth` method returns correctly formatted audio data for known input.
*   **eSpeak Fix (File-Based):**
    *   Test `EspeakNGWrapper.synth` method with file handling, ensure temp files are cleaned up.
    *   Test handling of potential file I/O errors during synthesis.
*   **Alternative TTS Wrapper:**
    *   Test `AlternativeWrapper.synthesize` returns correct format (float32 NumPy) and sample rate.
    *   Test parameter setting (`set_parameter`) works as expected.
*   **VoxDeiSynthesizer Integration:**
    *   Test `_initialize_tts_engine` selects and initializes the correct engine based on availability/config.
    *   Test `synthesize_text` calls the TTS engine correctly.
    *   Verify `synthesize_text` output is a float32 NumPy array at the target sample rate.
    *   Test `_apply_robotic_effects` calls formant shift and timbre blend.
    *   Test formant shift application produces expected changes.
    *   Test timbre blend application produces expected changes.
*   **SacredMachineryEngine Integration:**
    *   Test `generate_psalm` successfully calls `vox_dei.synthesize_text`.
    *   Test that the final mix contains audible vocal elements.

## 6. Minimal Changes Constraint

This pseudocode focuses modifications primarily within:
*   `src/robotic_psalms/synthesis/tts/engines/espeak.py` (for the fix)
*   Potentially `lib/espeakmodulecore.cpp` (for the preferred fix)
*   A new file like `src/robotic_psalms/synthesis/tts/engines/alternative_tts.py` (if needed)
*   `src/robotic_psalms/synthesis/vox_dei.py` (for engine initialization and calling the correct `synthesize` method)

Changes to `SacredMachineryEngine` are limited to ensuring `VoxDeiSynthesizer` is called correctly. Other components (pads, drones, percussion, config loading, CLI) remain untouched as per the specification.