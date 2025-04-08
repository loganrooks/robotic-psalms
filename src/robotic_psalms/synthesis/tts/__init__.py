"""Text-to-speech engine implementations"""

from .base import TTSEngine
from .engines.espeak import EspeakWrapper, EspeakNGWrapper


__all__ = [
    'TTSEngine',
    'EspeakWrapper',
    'EspeakNGWrapper',
]