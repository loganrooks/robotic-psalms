"""Base protocols for TTS engines"""
from typing import Protocol, runtime_checkable
from enum import Enum
import numpy as np
import numpy.typing as npt


class ParameterEnum(Enum):
    RATE = 1
    PITCH = 2
    VOLUME = 3

@runtime_checkable
class TTSEngine(Protocol):
    Parameter: ParameterEnum
    
    def synth(self, text: str) -> npt.NDArray[np.float32]: ...
    def set_voice(self, voice: str) -> None: ...
    def set_parameter(self, param: ParameterEnum, value: int) -> None: ...