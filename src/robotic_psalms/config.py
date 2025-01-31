from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

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

class HauntingParameters(BaseModel):
    """Parameters controlling ethereal qualities"""
    reverb_decay: float = Field(
        default=5.0,
        ge=0.5,
        le=30.0,
        description="Reverb decay time (seconds)"
    )
    spectral_freeze: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Amount of spectral freezing effect"
    )

class VocalTimbre(BaseModel):
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
    vocal_timbre: VocalTimbre = Field(
        default_factory=VocalTimbre,
        description="Voice timbre blend settings"
    )
    midi_mapping: MIDIMapping = Field(
        default_factory=MIDIMapping,
        description="MIDI CC control mappings"
    )
    midi_input: Optional[str] = Field(
        default=None,
        description="Path to input MIDI file"
    )

    class Config:
        use_enum_values = True