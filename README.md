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
  reverb_decay: 8.0
  spectral_freeze: 0.4

vocal_timbre:
  choirboy: 0.4
  android: 0.4
  machinery: 0.2
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
- `reverb_decay`: Length of reverb tail (seconds)
- `spectral_freeze`: Amount of spectral time-stretching

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

*   **Improved Vocal Processing:** More robust formant shifting (REQ-ART-V01), enhanced vocal effects chain focusing on reverb and delay (REQ-ART-V02).
*   **Ambient Texture:** More complex pad and drone generation (REQ-ART-A01, REQ-ART-A02).
*   **Effects Refinement:** High-quality reverb (e.g., FDN or convolution) (REQ-ART-E01), improved spectral freeze (REQ-ART-E02), refined glitch effects (REQ-ART-E03), and saturation (REQ-ART-E04).
*   **Melodic Control:** Guiding vocal synthesis with melodic input (REQ-ART-MEL-01, REQ-ART-MEL-02, REQ-ART-MEL-03).

**Known Issues:**
*   Formant shifting can sometimes introduce audible noise artifacts.

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