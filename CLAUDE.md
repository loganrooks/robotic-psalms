# Claude Code Project Guide: Robotic Psalms

## Project Overview

**Robotic Psalms** generates ethereal, computerized vocal arrangements of Latin psalms, inspired by Jóhann Jóhannsson's "Odi et Amo" aesthetic. The project combines synthesized robotic vocals with ambient textures (pads, drones, percussion) and advanced audio effects to create atmospheric, textured soundscapes.

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (requires espeak-ng, portaudio, ffmpeg system packages)
pip install -e ".[dev]"

# Run tests
pytest

# Run the CLI
robotic-psalms examples/psalm.txt output.wav --config examples/config.yml
```

## Architecture

### Core Components

```
src/robotic_psalms/
├── cli.py                    # Command-line interface
├── config.py                 # Pydantic configuration models
├── __main__.py               # Entry point
└── synthesis/
    ├── sacred_machinery.py   # Master synthesis engine (mixing, layer generation)
    ├── vox_dei.py            # Vocal synthesis (TTS, formant shifting, melody)
    ├── effects.py            # Audio effects library
    └── tts/
        └── engines/espeak.py # espeak-ng command-line wrapper
```

### Key Classes

- **`SacredMachineryEngine`** (`sacred_machinery.py`): Orchestrates audio generation, mixing all layers
- **`VoxDeiSynthesizer`** (`vox_dei.py`): Handles vocal synthesis with TTS, formant shifting, and melody control
- **`PsalmConfig`** (`config.py`): Pydantic model for all configuration parameters

### Data Flow

```
Input (text + optional MIDI) → VoxDeiSynthesizer → Vocal Audio
                             → SacredMachineryEngine → Pads/Drones/Percussion
                             → Effects Processing → Master Mix → WAV Output
```

## Technology Stack

- **Audio Processing**: librosa, scipy, numpy, soundfile, pedalboard
- **Vocoder/Formant**: pyworld
- **TTS**: espeak-ng (via subprocess)
- **MIDI**: pretty_midi, mido
- **Forced Alignment**: pyfoal
- **Configuration**: Pydantic, PyYAML
- **Testing**: pytest

## Development Guidelines

### Code Style

- **Formatter**: black (line length: 88)
- **Import Sorting**: isort (black profile)
- **Type Checking**: mypy
- **Linting**: flake8

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/robotic_psalms

# Run specific test file
pytest tests/synthesis/test_effects.py

# Run tests matching pattern
pytest -k "test_reverb"
```

### Test Status

- **172 tests passing**
- **6 tests xfail** (expected failures due to library limitations):
  - `test_complex_delay_feedback_parameter` - pedalboard.Delay feedback issue
  - `test_chorus_parameters_affect_output` - pedalboard.Chorus num_voices ignored
  - Other advanced delay parameter tests (stereo spread, LFO, filtering)

### File Size Guidelines

- Keep files under 500 lines when possible
- Current larger files are acceptable given their cohesive functionality:
  - `effects.py` (~1142 lines) - comprehensive effects library
  - `sacred_machinery.py` (~853 lines) - master synthesis engine
  - `vox_dei.py` (~694 lines) - vocal synthesis pipeline

## Current Project Status

### Completed Phases (P1-P3)

- **P1 - Stability**: Fixed TTS with espeak-ng subprocess wrapper
- **P2 - Artistic Enhancement**: Enhanced pads/drones, implemented effects suite
- **P3 - Melodic Refinement**: MIDI input, melody contour, duration control

### Current Phase (P4)

Priority features to implement:

1. **REQ-INPUT-DSL-01**: Custom DSL for input (highest priority)
2. **REQ-ART-V04**: Granular vocal textures
3. **REQ-ART-M02**: Stereo panning for layers
4. **REQ-FIX-01/02**: Investigate delay/chorus library limitations

## Key Configuration

Configuration is via YAML files or Pydantic models. See `examples/config.yml` for a complete example.

Key parameters:
- `mode`: Liturgical mode (dorian, phrygian, lydian, mixolydian, aeolian)
- `midi_path`: Optional MIDI file for melody/duration control
- `formant_shift_factor`: Vocal formant adjustment (0.5-2.0)
- `haunting_intensity.reverb`: High-quality reverb settings
- `glitch_effect`: Refined glitch with types (repeat, stutter, tape_stop, bitcrush)

## Important Files

| File | Purpose |
|------|---------|
| `project_specification_v3.md` | Active development roadmap |
| `artistic_specification.md` | Artistic goals and requirements |
| `docs/research-reports/` | Technical research and analysis |
| `memory-bank/` | Historical context from prior development |
| `examples/` | Sample input files and configuration |

## Common Tasks

### Adding a New Effect

1. Define parameters in `src/robotic_psalms/config.py` (Pydantic model)
2. Implement effect function in `src/robotic_psalms/synthesis/effects.py`
3. Integrate into `SacredMachineryEngine` or `VoxDeiSynthesizer`
4. Write tests in `tests/synthesis/test_effects.py`
5. Update `README.md` parameter guide

### Modifying Vocal Synthesis

Key methods in `vox_dei.py`:
- `synthesize_text()`: Main entry point
- `_apply_melody_contour()`: Pitch following from MIDI
- `_apply_duration_control()`: Time-stretching to match MIDI
- `_apply_robotic_effects()`: Post-processing effects

### Running End-to-End

```bash
# Basic generation
robotic-psalms examples/psalm.txt output.wav

# With full configuration
robotic-psalms examples/psalm.txt output.wav \
    --config examples/config.yml \
    --duration 180 \
    --visualize
```

## System Dependencies

Required system packages (must be installed before pip install):

- **espeak-ng** (1.50+): TTS engine
- **portaudio19-dev**: Audio I/O
- **ffmpeg**: Audio file manipulation (for pyfoal)

```bash
# Ubuntu/Debian
sudo apt-get install espeak-ng portaudio19-dev ffmpeg

# macOS
brew install espeak-ng portaudio ffmpeg
```

## Notes for Development

- The project uses **Test-Driven Development (TDD)** - write failing tests first
- **Effects** are built on `pedalboard` library - some advanced features have limitations
- **Forced alignment** via `pyfoal` is word-level only (not phoneme-level)
- **Time-stretching** can introduce artifacts with extreme stretch factors
- The `memory-bank/` directory contains historical context from RooCode development
