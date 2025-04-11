# Robotic Psalms

Generate ethereal computerized vocal arrangements of Latin psalms in the style of Jóhann Jóhannsson's "Odi et Amo".

For detailed documentation, please see the [Full Documentation](./docs/index.md).

## Features

- **Input System**
  - Latin lyrics processing with verse/chapter markers
  - Optional MIDI input for melodic structure
  - Configurable psalm settings (tempo, mode, effects)

- **Sacred Machinery Synthesis**
  - Layered glacial synth pads
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

*(Note: Festival is no longer used.)*


#### Installing System Dependencies

Ubuntu/Debian:
```bash
# Install eSpeak NG and PortAudio development libraries
sudo apt-get update
sudo apt-get install espeak-ng portaudio19-dev
```

macOS:
```bash
# Install eSpeak NG and PortAudio
brew install espeak-ng portaudio
```

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

glitch_density: 0.4
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
  spectral_freeze: 0.4

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
- `glitch_density`: Intensity of digital artifacts (0.0-1.0)
- `celestial_harmonicity`: Balance between pure and complex tones
- `phoneme_spacing`: Time between vocal sounds
- `consonant_harshness`: Intensity of consonant sounds
- `reverb`: Configuration for the high-quality reverb effect:
  - `decay_time`: Length of the reverb tail in seconds (e.g., `4.5`).
  - `pre_delay`: Delay in seconds before the reverb effect starts (e.g., `0.02`).
  - `diffusion`: Controls the density and smoothness of the reverb tail (0.0 to 1.0). Higher values are smoother.
  - `damping`: Controls how quickly high frequencies fade in the reverb tail (0.0 to 1.0). Higher values mean less damping (brighter reverb).
  - `wet_dry_mix`: The balance between the original (dry) signal and the reverb (wet) signal (0.0 for full dry, 1.0 for full wet).
- `spectral_freeze`: Amount of spectral time-stretching
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

## Development Status & Roadmap

The core functionality, including text processing and audio synthesis using `espeak-ng`, is currently operational. The system can generate layered audio output based on input text and configuration.

Future development will focus on enhancing the artistic capabilities and achieving a more sophisticated sonic aesthetic, as outlined in the [Artistic Specification](./artistic_specification.md). Key planned features include:

*   **Improved Vocal Processing:** Initial robust formant shifting using `pyworld` (REQ-ART-V01) is integrated. Future work includes enhancing the vocal effects chain focusing on reverb and delay (REQ-ART-V02).
*   **Ambient Texture:** More complex pad and drone generation (REQ-ART-A01, REQ-ART-A02).
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