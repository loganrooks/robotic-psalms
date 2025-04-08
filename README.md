# Robotic Psalms

Generate ethereal computerized vocal arrangements of Latin psalms in the style of Jóhann Jóhannsson's "Odi et Amo".

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

Before installing the Python package, you need to install the following system dependencies:

### Required System Packages

1. **Text-to-Speech Engines**
  - **eSpeak-NG** (recommended):
    - Actively maintained fork
    - Better voice quality
    - Improved language support
    - Install: `sudo apt-get install espeak-ng libespeak-ng-dev`

  - **eSpeak** (fallback):
    - Original implementation 
    - Legacy compatibility
    - Install: `sudo apt-get install espeak libespeak-dev`

   - Festival: Required for secondary vocal synthesis

The system will try eSpeak-NG first, falling back to eSpeak if needed.


2. **Audio Libraries**
   - PortAudio: Required for real-time audio processing

#### Installing System Dependencies

Ubuntu/Debian:
```bash
# Install TTS engines and audio libraries
sudo apt-get update
sudo apt-get install espeak-ng festival portaudio19-dev
```

macOS:
```bash
# Install TTS engines and audio libraries
brew install espeak-ng festival portaudio
```

### Python Requirements
- Python 3.9 or higher
- Virtual environment recommended

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install the package in development mode:
```bash
pip install -e .
```

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

## Troubleshooting

### Common Issues

1. **TTS Engine Not Found**
   ```
   VoxDeiSynthesisError: eSpeak initialization failed
   ```
   Solution: Ensure eSpeak is installed: `sudo apt-get install espeak`

2. **PortAudio Not Found**
   ```
   OSError: PortAudio library not found
   ```
   Solution: Install PortAudio: `sudo apt-get install portaudio19-dev`

3. **Festival Not Running**
   ```
   VoxDeiSynthesisError: Festival initialization failed
   ```
   Solution: Ensure Festival is installed and running: `sudo apt-get install festival`

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
- Uses eSpeak and Festival for text-to-speech
- Built with Python's scientific computing stack