# Robotic Psalms

Generate ethereal computerized vocal arrangements of Latin psalms in the style of Jóhann Jóhannsson's "Odi et Amo".

For detailed documentation, please see the [Full Documentation](./docs/index.md).

## Features

- **Input System**
  - Latin lyrics processing with verse/chapter markers
  - Optional MIDI input for melodic structure
  - Syllable/Note Duration Control (via MIDI)
  - Configurable psalm settings (tempo, mode, effects)

- **Sacred Machinery Synthesis**
  - Evolving glacial synth pads
  - Advanced vocal synthesis combining eSpeak/Festival
  - Stochastic metallic percussion
  - Dynamic drone modulation

- **Customizable Parameters**
  - Glitch density control
  - Celestial harmonicity blending
  - Robotic articulation settings
  - Haunting intensity adjustments
  - Voice timbre morphing

- **Output Options**
  - 24-bit WAV stems and master
  - Waveform visualization
  - Automatic mode documentation

## System Requirements

This project relies on specific system and Python libraries.

### Required System Packages

1.  **eSpeak NG (System Library):**
    *   This project requires the `espeak-ng` text-to-speech engine (version 1.50 or later recommended) to be installed on your system. It provides the core speech synthesis capabilities.
    *   Installation instructions vary by operating system (see below).

2.  **Audio Libraries:**
    *   **PortAudio:** Required for real-time audio I/O (used by `sounddevice`).
    *   Installation instructions vary by operating system (see below).

3.  **FFmpeg:**
    *   Required by `pyfoal` (and potentially other audio libraries) for audio file reading and manipulation.
    *   Installation instructions vary by operating system (see below).

*(Note: Festival is no longer used.)*


#### Installing System Dependencies

Ubuntu/Debian:
```bash
# Install eSpeak NG, PortAudio development libraries, and FFmpeg
sudo apt-get update
sudo apt-get install espeak-ng portaudio19-dev ffmpeg
```

macOS:
```bash
# Install eSpeak NG, PortAudio, and FFmpeg
brew install espeak-ng portaudio ffmpeg
```
 - **`pyfoal` and `pypar`:** Used for forced alignment to enable syllable/note duration control. `pyfoal` is installed via PyPI, while `pypar` is installed directly from its Git repository as it's a dependency of `pyfoal` not available on PyPI. These are installed automatically as core dependencies.

### Python Requirements
- Python 3.9 or higher
- Virtual environment recommended
- **`espeakng` Python Wrapper:** This package uses the `espeakng` Python library by `sayak-brm` ([PyPI](https://pypi.org/project/espeakng/), [GitHub](https://github.com/sayak-brm/espeakng-python)) to interact with the system's `espeak-ng` engine. It's installed as an optional dependency. **Note:** This is distinct from other similarly named wrappers.
## Installation

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install the package with the `espeak-ng` optional dependency. For development, use the `-e` flag for an editable install:
```bash
# Install for usage
pip install ".[espeak-ng]"

# Install for development
pip install -e ".[espeak-ng, dev]"
```
*Note: The `dev` extra includes tools like `pytest`, `black`, `mypy`, etc.*

## Usage

After installation, the `robotic-psalms` command will be available in your terminal:

```bash
# Basic usage with default settings
robotic-psalms examples/psalm.txt output.wav

# Using custom configuration and visualization
robotic-psalms examples/psalm.txt output.wav --config examples/config.yml --duration 180 --visualize
```

### Configuration

Create a YAML configuration file to customize the synthesis:

```yaml
mode: "dorian"  # Liturgical mode
tempo_scale: 0.8  # Slower tempo

  glitch_effect: # Optional refined glitch effect configuration
    glitch_type: "stutter" # Type: "repeat", "stutter", "tape_stop", "bitcrush"
    intensity: 0.6         # Probability of applying glitch per chunk (0.0-1.0)
    chunk_size_ms: 50      # Size of audio chunks to process in ms (int, > 0)
    repeat_count: 3        # For 'repeat'/'stutter': Number of repetitions (int, >= 2)
    tape_stop_speed: 0.8   # For 'tape_stop': Speed factor (0.0 < speed < 1.0)
    bitcrush_depth: 8      # For 'bitcrush': Target bit depth (int, 1-16)
    bitcrush_rate_factor: 4 # For 'bitcrush': Sample rate reduction factor (int, >= 1)
celestial_harmonicity: 0.7

robotic_articulation:
  phoneme_spacing: 1.2
  consonant_harshness: 0.3

haunting_intensity:
  reverb: # New high-quality reverb settings
    decay_time: 4.5       # Reverb tail length in seconds (float, > 0.0)
    pre_delay: 0.02       # Delay before reverb starts in seconds (float, >= 0.0)
    diffusion: 0.7        # Controls the density/smoothness of the reverb tail (float, 0.0 to 1.0)
    damping: 0.8          # High-frequency damping, makes reverb darker (float, 0.0 to 1.0)
    wet_dry_mix: 0.3      # Mix between original (dry) and reverb (wet) signal (float, 0.0 to 1.0)
  spectral_freeze: # Optional configuration for the improved spectral freeze effect
    freeze_point: 0.5    # Normalized time point (0.0-1.0) to capture spectrum
    blend_amount: 0.8    # Blend between original and frozen (0.0=original, 1.0=frozen)
    fade_duration: 1.5   # Duration (seconds) to fade the blend amount

vocal_timbre:
  choirboy: 0.4
  android: 0.4
  machinery: 0.2
  formant_shift_factor: 1.2 # Shift formants up slightly (range 0.5-2.0)
  delay_effect: # Optional complex delay effect
    delay_time_ms: 500.0  # Delay time in milliseconds (float, > 0.0)
    feedback: 0.3         # Feedback amount (float, 0.0 to 1.0) - NOTE: Test currently fails for this param
    wet_dry_mix: 0.2      # Mix between original (dry) and delayed (wet) signal (float, 0.0 to 1.0)
    # stereo_spread: 0.0    # Stereo spread (float, 0.0 to 1.0) - Currently unimplemented
    # lfo_frequency: 0.0    # LFO frequency for delay time modulation (float, >= 0.0) - Currently unimplemented
    # lfo_depth: 0.0        # LFO depth for delay time modulation (float, 0.0 to 1.0) - Currently unimplemented
    # filter_cutoff: 20000.0 # Low-pass filter cutoff frequency in Hz (float, > 0.0) - Currently unimplemented
    # filter_resonance: 0.0 # Filter resonance (float, >= 0.0) - Currently unimplemented
    resonant_filter: # Optional resonant low-pass filter (RBJ Biquad)
      cutoff_hz: 5000.0   # Cutoff frequency in Hz (float, > 0.0)
      q: 1.0            # Resonance factor (Q) (float, > 0.0)
    bandpass_filter: # Optional bandpass filter (Butterworth)
      center_hz: 1000.0   # Center frequency in Hz (float, > 0.0)
      q: 2.0            # Quality factor (Q) (float, > 0.0)
      order: 2          # Filter order (integer, > 0, default: 2)
    chorus_params: # Optional chorus effect applied to the vocal timbre
      rate_hz: 1.5          # Chorus modulation rate in Hz (float, > 0.0)
      depth: 0.25           # Chorus modulation depth (float, 0.0 to 1.0)
      delay_ms: 7.0         # Base delay time for chorus voices in milliseconds (float, > 0.0)
      feedback: 0.0         # Feedback amount for chorus voices (float, 0.0 to 1.0)
      wet_dry_mix: 0.5      # Mix between original (dry) and chorus (wet) signal (float, 0.0 to 1.0)
      # num_voices: 3       # Number of chorus voices (integer, >= 2) - Currently ignored by implementation
    saturation_effect: # Optional saturation/distortion effect
      drive: 0.5          # Amount of distortion (float, 0.0 to 1.0)
      tone: 0.5           # Tone control (0.0=dark, 1.0=bright)
      mix: 0.3            # Wet/dry mix (0.0=dry, 1.0=wet)
    num_vocal_layers: 1           # Number of vocal layers to generate (int, >= 1)
    layer_pitch_variation: 0.0    # Max random pitch shift per layer in semitones (float, >= 0.0)
    layer_timing_variation_ms: 0.0 # Max random timing shift per layer in milliseconds (float, >= 0.0)
  master_dynamics: # Optional master dynamics processing
    enable_compressor: true
    compressor_threshold_db: -18.0
    compressor_ratio: 3.0
    compressor_attack_ms: 5.0
    compressor_release_ms: 150.0
    enable_limiter: true
    limiter_threshold_db: -0.5
```

### Input Format

Psalm text files should use Latin text with verse markers:

```
[VERSE 1]
Deus misereatur nostri, et benedicat nobis
illuminet vultum suum super nos, et misereatur nostri.

[VERSE 2]
Ut cognoscamus in terra viam tuam,
in omnibus gentibus salutare tuum.
```

### Output

The system generates:
- Master WAV file (24-bit/48kHz)
- Individual stems (vocals, pads, percussion, drones)
- Waveform visualization with glitch art overlay
- Processing documentation

## Examples

Example files are provided in the `examples/` directory:
- `config.yml`: Sample configuration
- `psalm.txt`: Example Latin psalm

Try them out:

```bash
robotic-psalms examples/psalm.txt output.wav --config examples/config.yml --visualize
```

## Parameter Guide

### Liturgical Modes
- `dorian`: Mystical, contemplative
- `phrygian`: Tense, mysterious
- `lydian`: Bright, transcendent
- `mixolydian`: Noble, euphoric
- `aeolian`: Dark, melancholic

### Effect Parameters
- `glitch_effect`: (Optional) Configuration for the refined glitch effect. If omitted or set to `null`, the effect is disabled.
  - `glitch_type`: The type of glitch to apply. Options: `"repeat"` (repeats the chunk), `"stutter"` (repeats the chunk multiple times quickly), `"tape_stop"` (simulates a tape machine slowing down), `"bitcrush"` (reduces bit depth and sample rate).
  - `intensity`: The probability (0.0 to 1.0) that a glitch will be applied to any given audio chunk. Higher values mean more frequent glitches.
  - `chunk_size_ms`: The duration in milliseconds of the audio chunks processed for potential glitching (e.g., `50`). Must be greater than 0.
  - `repeat_count`: For `"repeat"` and `"stutter"` types, the number of times the chunk is repeated (e.g., `3`). Must be 2 or greater.
  - `tape_stop_speed`: For `"tape_stop"` type, the factor by which playback speed decreases (e.g., `0.8`). Must be between 0.0 and 1.0 (exclusive of 0.0).
  - `bitcrush_depth`: For `"bitcrush"` type, the target bit depth for quantization (e.g., `8`). Must be between 1 and 16.
  - `bitcrush_rate_factor`: For `"bitcrush"` type, the factor by which the sample rate is reduced (e.g., `4`). Must be 1 or greater.
- `celestial_harmonicity`: Balance between pure and complex tones
- `phoneme_spacing`: Time between vocal sounds
- `consonant_harshness`: Intensity of consonant sounds
- `reverb`: Configuration for the high-quality reverb effect:
  - `decay_time`: Length of the reverb tail in seconds (e.g., `4.5`).
  - `pre_delay`: Delay in seconds before the reverb effect starts (e.g., `0.02`).
  - `diffusion`: Controls the density and smoothness of the reverb tail (0.0 to 1.0). Higher values are smoother.
  - `damping`: Controls how quickly high frequencies fade in the reverb tail (0.0 to 1.0). Higher values mean less damping (brighter reverb).
  - `wet_dry_mix`: The balance between the original (dry) signal and the reverb (wet) signal (0.0 for full dry, 1.0 for full wet).
- `spectral_freeze`: (Optional) Configuration for the smooth spectral freeze effect. If omitted or set to `null`, the effect is disabled.
  - `freeze_point`: Normalized time point (0.0 to 1.0) in the audio to capture the spectrum from (e.g., `0.5` for the middle).
  - `blend_amount`: Blend between the original and frozen spectrum (0.0 = original, 1.0 = fully frozen) (e.g., `0.8`).
  - `fade_duration`: Duration in seconds over which to fade the `blend_amount` from 0 to its target value (e.g., `1.5`).
- `formant_shift_factor`: Adjusts vocal formants (0.5-2.0). Values > 1.0 raise formants (brighter/smaller perceived source), < 1.0 lowers them (darker/larger). Uses `pyworld` for robust shifting, preserving pitch better than simpler methods.
- `delay_effect`: (Optional) Configuration for a complex delay effect applied to the final output. If this section is omitted or `wet_dry_mix` is set to 0, the effect is disabled.
  - `delay_time_ms`: The primary delay time in milliseconds (e.g., `500.0`). Must be greater than 0.
  - `feedback`: The amount of the delayed signal fed back into the delay line (0.0 to 1.0). Higher values create more repetitions. *Note: The unit test for this parameter currently fails due to limitations in the underlying `pedalboard.Delay` implementation.*
  - `wet_dry_mix`: The balance between the original (dry) signal and the delayed (wet) signal (0.0 for full dry, 1.0 for full wet).
  - `stereo_spread`: *Currently unimplemented.* Intended to control stereo width.
  - `lfo_frequency`: *Currently unimplemented.* Intended for LFO modulation of delay time.
  - `lfo_depth`: *Currently unimplemented.* Intended for LFO modulation depth.
  - `filter_cutoff`: *Currently unimplemented.* Intended for filtering the delayed signal.
  - `filter_resonance`: *Currently unimplemented.* Intended for filter resonance.
- `resonant_filter`: (Optional) Configuration for a resonant low-pass filter applied to the vocal timbre. Uses an RBJ Biquad implementation.
  - `cutoff_hz`: The filter's cutoff frequency in Hz (e.g., `5000.0`). Must be greater than 0.
  - `q`: The resonance factor (Q) (e.g., `1.0`). Higher values create a sharper peak at the cutoff. Must be greater than 0.
- `bandpass_filter`: (Optional) Configuration for a bandpass filter applied to the vocal timbre. Uses a Butterworth implementation.
  - `center_hz`: The center frequency of the bandpass filter in Hz (e.g., `1000.0`). Must be greater than 0.
  - `q`: The quality factor (Q) of the filter (e.g., `2.0`). Higher values result in a narrower bandwidth. Must be greater than 0.
  - `order`: The order of the Butterworth filter (e.g., `2`). Higher orders create a steeper rolloff. Must be greater than 0, defaults to 2.
- `chorus_params`: (Optional) Configuration for a chorus effect applied to the vocal timbre. If this section is omitted or `wet_dry_mix` is set to 0, the effect is disabled.
  - `rate_hz`: The modulation frequency of the chorus effect in Hertz (e.g., `1.5`). Must be greater than 0.
  - `depth`: The depth of the chorus modulation (0.0 to 1.0). Controls the intensity of the pitch variation.
  - `delay_ms`: The base delay time for the chorus voices in milliseconds (e.g., `7.0`). Must be greater than 0.
  - `feedback`: The amount of the chorus signal fed back into the effect (0.0 to 1.0). Can create a more resonant or flanging sound at higher values.
  - `wet_dry_mix`: The balance between the original (dry) signal and the chorus (wet) signal (0.0 for full dry, 1.0 for full wet).
  - `num_voices`: *Currently ignored by the implementation.* Intended to control the number of chorus voices.
- `saturation_effect`: (Optional) Configuration for a saturation/distortion effect applied to the final output. If this section is omitted or `mix` is set to 0, the effect is disabled.
  - `drive`: The amount of distortion applied (0.0 to 1.0). Higher values increase saturation.
  - `tone`: Controls the brightness of the distortion (0.0 for dark, 1.0 for bright).
  - `mix`: The balance between the original (dry) signal and the saturated (wet) signal (0.0 for full dry, 1.0 for full wet).
- `num_vocal_layers`: (Integer, >= 1, Default: 1) The number of individual vocal layers to synthesize and mix. Setting to 1 disables layering.
- `layer_pitch_variation`: (Float, >= 0.0, Default: 0.0) The maximum random pitch variation applied to each vocal layer, measured in semitones. A value of 0.5 means each layer's pitch can be shifted randomly between -0.5 and +0.5 semitones relative to the base pitch.
- `layer_timing_variation_ms`: (Float, >= 0.0, Default: 0.0) The maximum random timing variation applied to each vocal layer, measured in milliseconds. A value of 50 means each layer can start randomly between -50ms and +50ms relative to the original timing.
- `master_dynamics`: (Optional) Configuration for master bus dynamics processing (compressor and limiter). Applied to the final mix. If omitted, or if individual `enable_` flags are false, the respective effect is disabled.
  - `enable_compressor`: (Boolean, Default: false) Enables the compressor.
  - `compressor_threshold_db`: (Float, Default: -20.0) The level (dB) above which compression starts.
  - `compressor_ratio`: (Float, >= 1.0, Default: 4.0) The amount of gain reduction (e.g., 4.0 means 4:1 ratio).
  - `compressor_attack_ms`: (Float, > 0.0, Default: 5.0) How quickly the compressor reacts to signals above the threshold (milliseconds).
  - `compressor_release_ms`: (Float, > 0.0, Default: 100.0) How quickly the compressor stops reducing gain after the signal falls below the threshold (milliseconds).
  - `enable_limiter`: (Boolean, Default: true) Enables the limiter.
  - `limiter_threshold_db`: (Float, <= 0.0, Default: -1.0) The maximum level (dB) the output signal is allowed to reach. Prevents clipping.

- `midi_path`: (Optional, String) Path to a MIDI file containing the desired melody and rhythm.
  - **Functionality**: If provided, this enables two features:
    1.  **Melodic Contour (REQ-ART-MEL-01):** The pitch of the synthesized vocals will follow the pitches of the notes in the MIDI file.
    2.  **Duration Control (REQ-ART-MEL-03):** The duration of synthesized speech segments (currently aligned at the word level) will be adjusted to match the duration of corresponding notes in the MIDI file. This uses forced alignment (`pyfoal`) and time-stretching (`librosa`).
  - **Format**: A valid file path string (e.g., `"./melodies/my_melody.mid"`).
  - **Parsing**: The `src.robotic_psalms.utils.midi_parser.parse_midi_melody` utility is used internally to convert the MIDI notes into a list of `(pitch_hz, duration_sec)` tuples.
  - **Example (Configuration)**:
    ```yaml
    # In your config.yml
    midi_path: "path/to/your/melody.mid"
    ```
  - **Example (Python API)**:
    ```python
    # When calling the synthesizer directly
    synthesizer.synthesize_text(text="...", midi_path="path/to/your/melody.mid")
    ```
  - **Notes**:
    - Ensure the MIDI file is accessible. Parsing errors might occur for invalid MIDI files.
    - Melodic contour quality depends on MIDI accuracy and pitch shifting.
    - **Duration Control Limitations**:
      - Alignment is currently performed at the **word level**. If the number of words in the text doesn't match the number of notes in the MIDI, duration control may behave unpredictably or be partially applied.
      - Forced alignment accuracy (`pyfoal`) directly impacts the quality of duration matching. Inaccurate alignments lead to incorrect stretching.
      - Time-stretching (`librosa.effects.time_stretch`) can introduce audio artifacts, especially with large stretch factors (significant differences between spoken duration and MIDI note duration).
### Voice Timbre
Blend between three voice characteristics:
- `choirboy`: Pure, angelic qualities
- `android`: Synthetic, processed sound
- `machinery`: Mechanical, industrial tones

## Development

To install development dependencies:

```bash
pip install -e ".[dev]"
```

This will install additional tools:
- pytest: For running tests
- black: Code formatting
- isort: Import sorting
- mypy: Type checking
*   **Duration Control (REQ-ART-MEL-03):**
    *   Alignment is word-level; mismatches between word count and MIDI note count can lead to unpredictable results.
    *   Time-stretching (`librosa`) can introduce audio artifacts, especially with large stretch factors.
    *   Accuracy depends heavily on the forced alignment quality from `pyfoal`.

## Development Status & Roadmap

The core functionality, including text processing and audio synthesis using `espeak-ng`, is currently operational. The system can generate layered audio output based on input text and configuration.

Future development will focus on enhancing the artistic capabilities and achieving a more sophisticated sonic aesthetic, as outlined in the [Artistic Specification](./artistic_specification.md). Key planned features include:

*   **Improved Vocal Processing:** Initial robust formant shifting using `pyworld` (REQ-ART-V01) is integrated. Future work includes enhancing the vocal effects chain focusing on reverb and delay (REQ-ART-V02).
*   **Ambient Texture:** Enhanced, evolving pad generation (REQ-ART-A01-v2) and richer, evolving drone generation (REQ-ART-A02-v2) implemented.
*   **Effects Refinement:** High-quality reverb (e.g., FDN or convolution) (REQ-ART-E01), improved spectral freeze (REQ-ART-E02), refined glitch effects (REQ-ART-E03), and saturation (REQ-ART-E04).
*   **Melodic Control:** Guiding vocal synthesis with melodic input (REQ-ART-MEL-01, REQ-ART-MEL-02, REQ-ART-MEL-03).

**Known Issues:**
*   The `pyworld`-based formant shifting, while robust, may still introduce subtle artifacts depending on the audio and shift factor.

## Troubleshooting

### Common Issues

1.  **`espeak-ng` System Library Not Found/Working:**
    *   **Error:** May manifest as `FileNotFoundError` when the code tries to call `/usr/bin/espeak-ng`, errors from the `espeakng` Python wrapper failing to connect (e.g., `EspeakNGError`), or silent/incorrect audio output.
    *   **Solution:** Ensure the `espeak-ng` system package (version 1.50+) is correctly installed (see System Requirements). Verify the `espeak-ng` command works directly in your terminal (e.g., `espeak-ng "hello"`). Check system PATH if installed in a non-standard location.

2.  **`espeakng` Python Wrapper (`sayak-brm`) Issues:**
    *   **Error:** `ModuleNotFoundError: No module named 'espeakng'`
    *   **Solution:** Make sure you installed the package with the correct `espeak-ng` extra: `pip install ".[espeak-ng]"`. Verify the `espeakng` package is listed in `pip list`.
    *   **Error:** Errors related to shared library loading (`.so`, `.dylib`, `.dll`).
    *   **Solution:** The `sayak-brm/espeakng-python` wrapper relies on finding the `espeak-ng` shared library. Ensure the system installation is complete and potentially check `LD_LIBRARY_PATH` (Linux) or system equivalents if the library isn't found automatically. Refer to the [wrapper's documentation](https://sayak-brm.github.io/espeakng-python/) for specific troubleshooting.

3.  **PortAudio Not Found:**
    *   **Error:** `OSError: PortAudio library not found` (or similar errors from `sounddevice`).
    *   **Solution:** Ensure the PortAudio development library (`portaudio19-dev` on Debian/Ubuntu, `portaudio` via Homebrew on macOS) is installed.

4.  **Audio Output Issues (Clipping, Silence):**
    *   **Symptom:** Output audio is silent or heavily distorted/clipped.
    *   **Possible Causes:** Check mix levels in your configuration (`config.yml`). Ensure input audio files (if used) are within a reasonable range. Internal normalization aims to prevent clipping, but extreme settings might still cause issues.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/enhancement`)
3. Commit changes (`git commit -am 'Add enhancement'`)
4. Push to branch (`git push origin feature/enhancement`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Inspired by Jóhann Jóhannsson's "Odi et Amo"
- Uses the `espeak-ng` system library via the `espeakng` Python wrapper ([sayak-brm/espeakng-python](https://github.com/sayak-brm/espeakng-python)) for text-to-speech.
- Built with Python's scientific computing stack