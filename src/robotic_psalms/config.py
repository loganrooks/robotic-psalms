from enum import Enum
from typing import Optional
from .synthesis.effects import ResonantFilterParameters, BandpassFilterParameters
from pydantic import BaseModel, Field, model_validator # Corrected import
from dataclasses import dataclass


class LiturgicalMode(str, Enum):
    """Church modes for psalm settings"""
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    AEOLIAN = "aeolian"

class RoboticArticulation(BaseModel):
    """Parameters controlling robotic voice articulation"""
    phoneme_spacing: float = Field(
        default=1.0,
        ge=0.1,
        le=2.0,
        description="Time between phonemes (seconds)"
    )
    consonant_harshness: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Intensity of consonant sounds"
    )

class ReverbConfig(BaseModel):
    """Configuration for the high-quality reverb effect."""
    decay_time: float = Field(
        default=4.5,
        gt=0.0,
        description="Reverb tail length (decay time) in seconds."
    )
    pre_delay: float = Field(
        default=0.02,
        ge=0.0,
        description="Delay before the reverb effect starts, in seconds."
    )
    diffusion: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Controls the density/smoothness of the reverb tail (0.0 to 1.0). Higher values are smoother."
    )
    damping: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="High-frequency damping factor (0.0 to 1.0). Controls how quickly high frequencies fade in the reverb. Lower values mean more damping (darker reverb)."
    )
    wet_dry_mix: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Mix between the original (dry) and reverb (wet) signal (0.0 = dry, 1.0 = wet)."
    )

# Moved DelayConfig here
class DelayConfig(BaseModel):
    """Configuration for the complex delay effect.

    Mirrors the parameters in `synthesis.effects.DelayParameters`.
    Note: Some parameters (stereo_spread, LFO, filters) are included for future
    compatibility but are not currently utilized by the underlying `pedalboard.Delay` effect.
    """
    delay_time_ms: float = Field(
        default=500.0,
        gt=0.0,
        description="Delay time in milliseconds."
    )
    feedback: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Feedback amount (0.0 to 1.0). Controls the number of repetitions."
    )
    wet_dry_mix: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Mix between the original (dry) and delayed (wet) signal (0.0 = dry, 1.0 = wet). Default 0.0 disables the effect."
    )
    stereo_spread: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Stereo spread of the delay taps (0.0 to 1.0). Currently unused."
    )
    lfo_rate_hz: float = Field(
        default=1.0,
        gt=0.0,
        description="Rate of the Low-Frequency Oscillator (LFO) modulating the delay time, in Hz. Currently unused."
    )
    lfo_depth: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Depth of the LFO modulation (0.0 to 1.0). Currently unused."
    )
    filter_low_hz: float = Field(
        default=20.0,
        ge=20.0,
        description="Low-cut filter frequency for the feedback path, in Hz. Currently unused."
    )
    filter_high_hz: float = Field(
        default=20000.0,
        le=22000.0, # Nyquist for 44.1kHz
        description="High-cut filter frequency for the feedback path, in Hz. Currently unused."
    )

    @model_validator(mode='after')
    def check_filter_order(self):
        if self.filter_low_hz > self.filter_high_hz:
            raise ValueError("filter_low_hz cannot be greater than filter_high_hz")
        return self

class HauntingParameters(BaseModel):
    """Parameters controlling ethereal qualities, including reverb and spectral freeze."""
    reverb: ReverbConfig = Field(
        default_factory=ReverbConfig,
        description="Configuration for the high-quality reverb effect."
    )
    spectral_freeze: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Amount of spectral freezing effect"
    )

class VocalTimbre(BaseModel): # Removed empty lines below
    """Three-way blend between voice types"""
    choirboy: float = Field(
        default=0.33,
        ge=0.0,
        le=1.0,
        description="Choirboy voice component"
    )
    android: float = Field(
        default=0.33,
        ge=0.0,
        le=1.0,
        description="Android voice component"
    )
    machinery: float = Field(
        default=0.33,
        ge=0.0,
        le=1.0,
        description="Machinery voice component"
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Normalize weights to sum to 1.0
        total = self.choirboy + self.android + self.machinery
        if total > 0:
            self.choirboy /= total
            self.android /= total
            self.machinery /= total

class MIDIMapping(BaseModel):
    """MIDI CC mappings for real-time control"""
    glitch_density: int = Field(
        default=1,
        ge=0,
        le=127,
        description="CC number for glitch density"
    )
    harmonicity: int = Field(
        default=2,
        ge=0,
        le=127,
        description="CC number for harmonicity"
    )
    articulation: int = Field(
        default=3,
        ge=0,
        le=127,
        description="CC number for articulation"
    )
    haunting: int = Field(
        default=4,
        ge=0,
        le=127,
        description="CC number for haunting intensity"
    )

class MixLevels(BaseModel):
    """Audio mix level settings"""
    vocals: float = Field(default=1.0, ge=0.0, le=2.0)
    pads: float = Field(default=0.8, ge=0.0, le=2.0)
    percussion: float = Field(default=0.6, ge=0.0, le=2.0)
    drones: float = Field(default=0.7, ge=0.0, le=2.0)

class VoiceRange(BaseModel):
    """Voice range and pitch settings"""
    base_pitch: str = Field(
        default="C3",
        pattern="^[A-G][#b]?[0-8]$",
        description="Base pitch in scientific notation"
    )
    formant_shift: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Formant shift factor for voice character. Uses pyworld for robust shifting, preserving pitch better than simpler methods. Values > 1.0 raise formants (brighter/smaller perceived source), < 1.0 lowers them (darker/larger)."
    )

class PsalmConfig(BaseModel):
    """Main configuration for psalm processing"""
    mode: LiturgicalMode = Field(
        default=LiturgicalMode.DORIAN,
        description="Liturgical mode for composition"
    )
    tempo_scale: float = Field(
        default=1.0,
        ge=0.25,
        le=2.0,
        description="Tempo scaling factor"
    )
    glitch_density: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Density of glitch effects"
    )
    celestial_harmonicity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Balance between sine and sawtooth waves"
    )
    robotic_articulation: RoboticArticulation = Field(
        default_factory=RoboticArticulation,
        description="Voice articulation settings"
    )
    haunting_intensity: HauntingParameters = Field(
        default_factory=HauntingParameters,
        description="Ethereal effect parameters"
    )
    delay_effect: Optional[DelayConfig] = Field( # This was inserted correctly before
        default=None,
        description="Optional configuration for the complex delay effect. If None, the effect is disabled."
    )
    resonant_filter_params: Optional[ResonantFilterParameters] = Field(
        default=None,
        description="Optional configuration for the resonant low-pass filter effect. If None, the effect is disabled."
    )
    bandpass_filter_params: Optional[BandpassFilterParameters] = Field(
        default=None,
        description="Optional configuration for the band-pass filter effect. If None, the effect is disabled. Takes precedence over resonant filter if both are defined."
    )
    voice_range: VoiceRange = Field(
        default_factory=VoiceRange,
        description="Voice range settings"
    )
    vocal_timbre: VocalTimbre = Field(
        default_factory=VocalTimbre,
        description="Voice timbre blend settings"
    )
    midi_mapping: MIDIMapping = Field(
        default_factory=MIDIMapping,
        description="MIDI CC control mappings"
    )
    mix_levels: MixLevels = Field(
        default_factory=MixLevels,
        description="Audio mix level settings"
    )
    midi_input: Optional[str] = Field(
        default=None,
        description="Path to input MIDI file"
    )


    class Config:
        use_enum_values = True
