"""eSpeak wrapper implementations"""
import logging
from typing import Optional
import subprocess
import io
import os
import tempfile
import shlex # For safe command construction

import numpy as np
import numpy.typing as npt
import soundfile as sf

from ..base import TTSEngine, ParameterEnum

# EspeakNGWrapper using command-line execution
class EspeakNGWrapper(TTSEngine):
    """espeak-ng wrapper implementation using direct command-line execution."""
    Parameter = ParameterEnum.RATE # Satisfy protocol

    def __init__(self, voice: str = "en", rate: int = 175, pitch: int = 50, volume: int = 100) -> None:
        """
        Initializes the EspeakNGWrapper for command-line execution.

        Args:
            voice (str): Voice/language code (default: 'en').
            rate (int): Speaking rate in words per minute (default: 175, espeak-ng default).
            pitch (int): Pitch adjustment (0-99, default: 50).
            volume (int): Amplitude adjustment (0-200, default: 100).
        """
        self.logger = logging.getLogger(__name__)
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume # Corresponds to espeak-ng -a flag (amplitude)
        self.espeak_cmd = "/usr/bin/espeak-ng" # Path confirmed earlier
        self.input_file_path: Optional[str] = None # Initialize temporary file path tracker

        # Verify command exists
        if not os.path.exists(self.espeak_cmd):
             self.logger.error(f"espeak-ng command not found at {self.espeak_cmd}")
             # Optionally try finding in PATH if absolute path fails? For now, rely on the known path.
             raise FileNotFoundError(f"espeak-ng command not found at {self.espeak_cmd}")
        self.logger.info(f"EspeakNGWrapper initialized using command: {self.espeak_cmd}")

    def set_voice(self, voice: str) -> None:
        """Set voice language."""
        self.logger.debug(f"Setting voice to: {voice}")
        self.voice = voice

    def set_parameter(self, param: ParameterEnum, value: int) -> None:
        """Set synthesis parameters."""
        if param == ParameterEnum.RATE:
            # espeak-ng speed: words per minute (80-?)
            value = max(80, value) # Clamp lower bound
            self.logger.debug(f"Setting rate (speed) to {value}")
            self.rate = value
        elif param == ParameterEnum.PITCH:
            # espeak-ng pitch: 0-99
            value = max(0, min(value, 99)) # Clamp value
            self.logger.debug(f"Setting pitch to {value}")
            self.pitch = value
        elif param == ParameterEnum.VOLUME:
            # espeak-ng amplitude: 0-200
            value = max(0, min(value, 200)) # Clamp value
            self.logger.debug(f"Setting volume (amplitude) to {value}")
            self.volume = value
        else:
            self.logger.warning(f"Unsupported parameter: {param}")

    def synth(self, text: str) -> tuple[npt.NDArray[np.float32], int]:
        """Synthesize text using espeak-ng command and return audio data and sample rate."""
        self.input_file_path = None # Reset path for each call

        # Use a temporary file for the input text to handle potential command length limits and special characters
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as temp_input_file:
                temp_input_file.write(text)
                self.input_file_path = temp_input_file.name # Assign path here
            self.logger.debug(f"Using temporary file for input: {self.input_file_path}")

            command_list = [
                self.espeak_cmd,
                "-v", self.voice,
                "-s", str(self.rate),    # Speed flag
                "-p", str(self.pitch),   # Pitch flag
                "-a", str(self.volume),  # Amplitude flag
                "-f", self.input_file_path,   # Read text from file
                "--stdout"               # Output WAV to stdout
            ]

            self.logger.debug(f"Executing command: {' '.join(shlex.quote(arg) for arg in command_list)}")

            # Execute the command
            result = subprocess.run(command_list, capture_output=True, check=False) # check=False to inspect errors manually

            # Check for errors
            if result.returncode != 0:
                error_message = result.stderr.decode('utf-8', errors='ignore').strip()
                self.logger.error(f"espeak-ng command failed (code {result.returncode}): {error_message}")
                return np.array([], dtype=np.float32), 0 # Return empty array and 0 sample rate on error

            wav_bytes = result.stdout
            if not wav_bytes:
                self.logger.error("espeak-ng command succeeded but produced empty stdout.")
                return np.array([], dtype=np.float32), 0 # Return empty array and 0 sample rate on error

            # Process the WAV bytes
            try:
                audio_data, sample_rate = sf.read(io.BytesIO(wav_bytes))
                self.logger.debug(f"Read {len(audio_data)} samples at {sample_rate}Hz from espeak-ng stdout.")

                if audio_data.ndim > 1:
                    audio_data = np.mean(audio_data, axis=1)

                # Check if data needs conversion and scaling
                if audio_data.dtype.kind == 'i': # Check if it's an integer type
                    # Scale integer types to [-1.0, 1.0] float range
                    int_dtype = np.dtype(audio_data.dtype.type) # Explicitly create dtype object
                    dtype_info = np.iinfo(int_dtype) # type: ignore
                    max_val = float(dtype_info.max) # Use float for division
                    audio_data = audio_data.astype(np.float32) / max_val
                elif audio_data.dtype != np.float32:
                    # Handle other non-float types if necessary
                    audio_data = audio_data.astype(np.float32)
                # Ensure it's float32 at the end
                # Return both audio data and sample rate
                return audio_data.astype(np.float32), sample_rate

            except Exception as e:
                self.logger.error(f"Failed to read/process WAV bytes from espeak-ng: {e}")
                return np.array([], dtype=np.float32), 0 # Return empty array and 0 sample rate on error

        except FileNotFoundError:
             # This shouldn't happen if __init__ check passes, but handle defensively
            self.logger.error(f"espeak-ng command not found at {self.espeak_cmd} during synth.")
            return np.array([], dtype=np.float32), 0 # Return empty array and 0 sample rate on error
        except Exception as e:
            self.logger.error(f"Unexpected error during espeak-ng synthesis: {e}")
            return np.array([], dtype=np.float32), 0 # Return empty array and 0 sample rate on error
        finally:
            # Ensure temporary file is deleted
            if self.input_file_path and os.path.exists(self.input_file_path):
                try:
                    os.remove(self.input_file_path)
                    self.logger.debug(f"Removed temporary input file: {self.input_file_path}")
                except OSError as e:
                    self.logger.error(f"Error removing temporary file {self.input_file_path}: {e}")


# Keep the legacy wrapper for completeness, but mark as unused/deprecated clearly
class EspeakWrapper(TTSEngine):
    """Legacy eSpeak wrapper: DO NOT USE - Placeholder"""
    Parameter = ParameterEnum.RATE # Satisfy protocol

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.critical("Attempted to initialize DEPRECATED EspeakWrapper. This should not happen.")
        # Raise an error to prevent accidental usage
        raise NotImplementedError("EspeakWrapper is deprecated and non-functional.")

    def set_voice(self, voice: str) -> None:
        raise NotImplementedError("EspeakWrapper is deprecated.")

    def set_parameter(self, param: ParameterEnum, value: int) -> None:
        raise NotImplementedError("EspeakWrapper is deprecated.")

    def synth(self, text: str) -> tuple[npt.NDArray[np.float32], int]:
        raise NotImplementedError("EspeakWrapper is deprecated.")