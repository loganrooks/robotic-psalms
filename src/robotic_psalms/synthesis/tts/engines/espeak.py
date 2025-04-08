"""eSpeak wrapper implementations"""
import importlib
import logging
from pathlib import Path
import time
from typing import Any, List, Optional
import struct
import wave
import tempfile

import numpy as np
import numpy.typing as npt
import soundfile as sf
from ..base import TTSEngine, ParameterEnum


class EspeakWrapperBase:
    """Base wrapper for eSpeak engines"""
    Parameter = ParameterEnum  # Use the base ParameterEnum

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._engine: Optional[Any] = None
        self._wave_data: List[bytes] = []
        self._pcm_path: Optional[Path] = None
        self._wav_path: Optional[Path] = None
        self._samplerate: int = 22050 # Default sample rate

    def synth(self, text: str) -> npt.NDArray[np.float32]:
        """Synthesize text using NG API - Base implementation (should be overridden)"""
        if not self._engine:
            return np.array([], dtype=np.float32)

        # This base method is not intended for direct use after NG wrapper changes.
        # Returning empty array directly. The functional implementation is in EspeakNGWrapper.
        self.logger.warning("EspeakWrapperBase.synth called directly - returning empty array.")
        return np.array([], dtype=np.float32)

    def set_voice(self, voice: str) -> None:
        """Set voice language - base implementation"""
        pass

    def set_parameter(self, param: ParameterEnum, value: int) -> None:
        """Set synthesis parameters - base implementation"""
        pass

    def cleanup(self):
        """Clean up temporary files if they exist."""
        if hasattr(self, '_pcm_path') and self._pcm_path and self._pcm_path.exists():
            try:
                self.logger.debug(f"Cleaning up PCM file: {self._pcm_path}")
                self._pcm_path.unlink()
            except OSError as e:
                self.logger.error(f"Error deleting PCM file {self._pcm_path}: {e}")
        if hasattr(self, '_wav_path') and self._wav_path and self._wav_path.exists():
             try:
                 self.logger.debug(f"Cleaning up WAV file: {self._wav_path}")
                 self._wav_path.unlink()
             except OSError as e:
                 self.logger.error(f"Error deleting WAV file {self._wav_path}: {e}")
        # Reset paths
        self._pcm_path = None
        self._wav_path = None

    def __del__(self):
        """Ensure temporary files are cleaned up on object deletion."""
        self.cleanup()


class EspeakNGWrapper(EspeakWrapperBase, TTSEngine):
    """espeak-ng wrapper implementation using improved file handling"""
    def __init__(self) -> None:
        super().__init__()
        self._speaker: Optional[Any] = None # Initialize speaker attribute
        try:
            self.logger.debug("Attempting to import espeak-ng module")
            # The actual module name might be 'espeakng' or similar depending on the binding
            try:
                espeak = importlib.import_module('espeakng') # Try 'espeakng' first
                self.logger.info("Imported 'espeakng' module.")
            except ImportError:
                self.logger.warning("Failed to import 'espeakng', trying 'espeak'.")
                espeak = importlib.import_module('espeak') # Fallback to 'espeak'
                self.logger.info("Imported 'espeak' module.")

            # Initialize core with RETRIEVAL mode (no playback)
            self.logger.debug("Initializing espeak core")
            # Check available initialization methods
            samplerate = -1 # Initialize samplerate
            if hasattr(espeak, 'core') and hasattr(espeak.core, 'initialize'):
                 # Newer python-espeak-ng structure
                 # Need to figure out the correct arguments for initialize
                 # Assuming it might take options or path like the older one
                 # Let's try initializing without arguments first if possible,
                 # or check the signature if available.
                 # For now, assume it returns samplerate directly or needs mode.
                 # Trying with AUDIO_OUTPUT_RETRIEVAL if it's defined at the top level
                 audio_output_mode = getattr(espeak, 'AUDIO_OUTPUT_RETRIEVAL', 1) # Default to 1 if not found
                 samplerate = espeak.core.initialize(audio_output_mode)
                 self._engine = espeak.core # Store the core module
                 self.logger.debug(f"Initialized espeak core (new API), samplerate: {samplerate}")
            elif hasattr(espeak, 'initialize'):
                 # Older structure or direct binding
                 audio_output_mode = getattr(espeak, 'AUDIO_OUTPUT_RETRIEVAL', 1)
                 samplerate = espeak.initialize(audio_output_mode)
                 self._engine = espeak # Store the main module
                 self.logger.debug(f"Initialized espeak core (old API), samplerate: {samplerate}")
            else:
                 raise ImportError("Could not find a suitable initialize function in espeak/espeakng module.")

            if not isinstance(samplerate, int) or samplerate <= 0:
                # Attempt to get samplerate via get_parameter if init didn't return it
                if hasattr(self._engine, 'get_parameter') and hasattr(self._engine, 'SAMPLERATE'):
                     try:
                         samplerate = self._engine.get_parameter(self._engine.SAMPLERATE, 1)
                         self.logger.info(f"Retrieved samplerate via get_parameter: {samplerate}")
                     except Exception as e_param:
                          self.logger.warning(f"Could not get samplerate via get_parameter: {e_param}")
                          samplerate = -1 # Indicate failure
                if samplerate <= 0 :
                     self.logger.warning(f"eSpeak initialization returned invalid/unknown samplerate: {samplerate}. Defaulting to 22050.")
                     samplerate = 22050 # Fallback default

            self._samplerate = samplerate # Store the reported or default sample rate

            # Use tempfile for unique paths
            with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as pcm_file:
                self._pcm_path = Path(pcm_file.name)
            self._wav_path = self._pcm_path.with_suffix(".wav")
            self.logger.debug(f"Using temporary PCM path: {self._pcm_path}")
            self.logger.debug(f"Using temporary WAV path: {self._wav_path}")

            # Create speaker instance (if applicable, structure varies)
            if hasattr(espeak, 'Espeak'):
                self._speaker = espeak.Espeak() # Older structure?
                self.logger.debug("Created espeak.Espeak() instance.")
            # Check if synth is directly on the engine object we stored
            elif hasattr(self._engine, 'synth'):
                 self._speaker = None # No separate speaker object needed
                 self.logger.debug("Using direct engine.synth() method.")
            else:
                 raise ImportError("Could not find a way to synthesize (no Espeak class or engine.synth).")

            # Configure speaker parameters if speaker object exists
            if self._speaker and hasattr(self._speaker, 'param'):
                self._speaker.param = {
                    'rate': 150,
                    'pitch': 50,
                    'volume': 200  # Maximum volume
                }
                self.logger.debug("Set parameters on speaker object.")

            # Set wave output path for PCM data using the unique temp path
            self.logger.debug(f"Setting wave output filename to {self._pcm_path}")
            assert self._engine is not None, "Engine should be initialized before setting wave filename"
            if hasattr(self._engine, 'set_wave_filename'):
                 self._engine.set_wave_filename(str(self._pcm_path))
                 self.logger.debug("Set wave filename via engine.set_wave_filename()")
            else:
                 self.logger.error("Unable to set wave output filename via engine.")
                 raise RuntimeError("Cannot set espeak wave output filename.")

        except (ImportError, RuntimeError, AttributeError) as e:
            self.logger.error(f"Failed to initialize espeak-ng wrapper: {e}", exc_info=True)
            self._engine = None
            self._speaker = None
            self.cleanup() # Clean up temp files if init fails
            raise # Re-raise the exception

    def _pcm_to_wav(self, pcm_path: Path, wav_path: Path, samplerate: int) -> None:
        """Convert raw PCM (16-bit mono) to WAV format"""
        self.logger.debug(f"Converting PCM '{pcm_path}' to WAV '{wav_path}' at {samplerate} Hz")
        try:
            with open(pcm_path, 'rb') as pcm_file:
                pcm_data = pcm_file.read()

            if not pcm_data:
                self.logger.warning("PCM file is empty, cannot convert to WAV.")
                # Create an empty WAV file to avoid downstream errors maybe?
                with wave.open(str(wav_path), 'wb') as wav_file:
                     wav_file.setnchannels(1)
                     wav_file.setsampwidth(2)
                     wav_file.setframerate(samplerate)
                     wav_file.writeframes(b'') # Write empty frames
                return

            with wave.open(str(wav_path), 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(samplerate)
                wav_file.writeframes(pcm_data)
            self.logger.debug("PCM to WAV conversion successful.")
        except Exception as e:
            self.logger.error(f"PCM to WAV conversion failed: {e}", exc_info=True)
            # Attempt to clean up potentially corrupted WAV file
            if wav_path.exists():
                try:
                    wav_path.unlink()
                except OSError:
                    pass
            raise # Re-raise the exception

    def set_voice(self, voice: str) -> None:
        """Set voice language"""
        if not self._engine: return
        self.logger.debug(f"Setting voice to: {voice}")
        try:
            if self._speaker and hasattr(self._speaker, 'voice'):
                # Assumes voice setting is via speaker object property
                self._speaker.voice = {"language": voice}
            elif hasattr(self._engine, 'set_voice_by_name'):
                 # Assumes voice setting is via core engine function
                 self._engine.set_voice_by_name(voice)
            else:
                 self.logger.warning("Could not determine how to set voice.")
        except Exception as e:
            self.logger.error(f"Failed to set voice to '{voice}': {e}", exc_info=True)


    def set_parameter(self, param: ParameterEnum, value: int) -> None:
        """Set synthesis parameters"""
        if not self._engine: return

        param_map_speaker = {
            ParameterEnum.RATE: 'rate',
            ParameterEnum.PITCH: 'pitch',
            ParameterEnum.VOLUME: 'volume'
        }
        # Mapping for core engine parameters (constants might differ)
        # Need to access constants via the imported module, not self._engine directly initially
        espeak_module = None
        try:
            espeak_module = importlib.import_module('espeakng')
        except ImportError:
            try:
                espeak_module = importlib.import_module('espeak')
            except ImportError:
                 self.logger.error("Cannot import espeak/espeakng module for parameter constants.")
                 return

        param_map_core = {
            ParameterEnum.RATE: getattr(espeak_module, 'RATE', None),
            ParameterEnum.PITCH: getattr(espeak_module, 'PITCH', None),
            ParameterEnum.VOLUME: getattr(espeak_module, 'VOLUME', None),
        }

        try:
            if self._speaker and param in param_map_speaker:
                param_name = param_map_speaker[param]
                if hasattr(self._speaker, 'param') and isinstance(self._speaker.param, dict):
                    self.logger.debug(f"Setting speaker param '{param_name}' to {value}")
                    self._speaker.param[param_name] = value
                else:
                     self.logger.warning(f"Speaker object lacks 'param' dict attribute.")
            elif param in param_map_core and param_map_core[param] is not None and hasattr(self._engine, 'set_parameter'):
                 core_param_enum = param_map_core[param]
                 self.logger.debug(f"Setting core param '{param.name}' (enum {core_param_enum}) to {value}")
                 self._engine.set_parameter(core_param_enum, value, 0) # 0 for absolute
            else:
                 self.logger.warning(f"Could not set parameter '{param.name}'. No method found or enum missing.")

        except Exception as e:
             self.logger.error(f"Failed to set parameter {param.name} to {value}: {e}", exc_info=True)


    def synth(self, text: str) -> npt.NDArray[np.float32]:
        """Synthesize text using espeak API with improved file handling"""
        if not self._engine:
            self.logger.error("Synth called but engine not initialized.")
            return np.array([], dtype=np.float32)

        # Ensure temp file paths are valid and engine is available
        if not self._pcm_path or not self._wav_path:
             self.logger.error("Temporary file paths are not set.")
             # Attempt to recreate them
             try:
                 assert self._engine is not None, "Engine must be initialized to recreate temp files"
                 with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as pcm_file:
                     self._pcm_path = Path(pcm_file.name)
                 self._wav_path = self._pcm_path.with_suffix(".wav")
                 self.logger.info(f"Recreated temp paths: PCM={self._pcm_path}, WAV={self._wav_path}")
                 # Re-set the filename in espeak
                 if hasattr(self._engine, 'set_wave_filename'):
                     self._engine.set_wave_filename(str(self._pcm_path))
                 else:
                      raise RuntimeError("Cannot set espeak wave output filename.")
             except Exception as e:
                 self.logger.critical(f"Failed to recreate temporary files: {e}", exc_info=True)
                 return np.array([], dtype=np.float32)

        # --- Main Synthesis Logic ---
        pcm_path = self._pcm_path # Local variable for clarity
        wav_path = self._wav_path # Local variable for clarity

        try:
            self.logger.debug(f"Synthesizing text to PCM file: {pcm_path} - Text: {text[:50]}...")
            # Clear any previous temp file content before synthesis
            if pcm_path.exists():
                try:
                    pcm_path.unlink()
                except OSError as e:
                    self.logger.warning(f"Could not delete old PCM file {pcm_path}: {e}")
            if wav_path.exists():
                 try:
                     wav_path.unlink()
                 except OSError as e:
                     self.logger.warning(f"Could not delete old WAV file {wav_path}: {e}")

            # Perform synthesis
            if self._speaker:
                self.logger.debug("Calling speaker.say()")
                self._speaker.say(text)
                # We might need to call sync here depending on the library version
                if hasattr(self._speaker, 'sync'):
                    self.logger.debug("Calling speaker.sync()")
                    self._speaker.sync()
            elif hasattr(self._engine, 'synth'):
                 self.logger.debug("Calling engine.synth()")
                 # Flags might be needed here? Check python-espeak-ng docs
                 # Example: espeakCHARS_AUTO | espeakENDPAUSE
                 # Need to import these constants if used.
                 espeak_module = importlib.import_module(self._engine.__module__.split('.')[0])
                 flags = getattr(espeak_module, 'espeakCHARS_AUTO', 0)
                 self._engine.synth(text, flags=flags)
                 # Sync might be needed here too
                 if hasattr(self._engine, 'sync'):
                     self.logger.debug("Calling engine.sync()")
                     self._engine.sync()
            else:
                 raise RuntimeError("No valid synthesis method found.")

            # Wait for PCM file with improved polling and timeout
            max_wait_time = 15.0 # Increased timeout
            poll_interval = 0.1 # seconds
            start_time = time.time()
            pcm_file_size = -1 # Use -1 to ensure first check logs size
            logged_empty = False

            self.logger.debug(f"Polling for PCM file: {pcm_path}")
            while time.time() - start_time < max_wait_time:
                try:
                    if pcm_path.exists():
                        current_size = pcm_path.stat().st_size
                        if current_size > 0:
                            # Check if size is stable for a short period
                            time.sleep(poll_interval / 2) # Wait a bit more
                            if pcm_path.exists() and pcm_path.stat().st_size == current_size: # Re-check existence
                                self.logger.debug(f"PCM file found and size stable: {current_size} bytes.")
                                break
                            else: # File changed size or disappeared during the short wait
                                pcm_file_size = pcm_path.stat().st_size if pcm_path.exists() else -1 # Update size if changed
                                if pcm_file_size != -1:
                                     self.logger.debug(f"PCM file growing/changing... Size: {pcm_file_size} bytes.")
                                else:
                                     self.logger.debug("PCM file disappeared during stability check.")
                        elif not logged_empty: # File exists but is empty
                            self.logger.debug("PCM file exists but is empty, waiting...")
                            logged_empty = True # Log this only once
                        # else: file is empty, already logged, continue waiting
                    else:
                        self.logger.debug("PCM file not found yet...")

                except FileNotFoundError:
                    self.logger.debug("PCM file disappeared during polling (or not found yet).")
                except Exception as stat_e:
                    self.logger.error(f"Error checking PCM file status: {stat_e}", exc_info=True)
                    break # Stop polling on error

                time.sleep(poll_interval)
            else:
                # Loop finished without break (timeout)
                self.logger.error(f"PCM file '{pcm_path}' not created or finalized within {max_wait_time} seconds.")
                self.cleanup() # Clean up potentially empty/partial files
                return np.array([], dtype=np.float32)

            # --- Process the audio file ---
            try:
                # Use the samplerate reported by espeak during initialization
                samplerate = self._samplerate
                self.logger.debug(f"Attempting to convert PCM to WAV at {samplerate} Hz.")
                assert isinstance(pcm_path, Path), "PCM path should be a Path object here"
                assert isinstance(wav_path, Path), "WAV path should be a Path object here"
                self._pcm_to_wav(pcm_path, wav_path, samplerate=samplerate)

                self.logger.debug(f"Reading WAV file: {wav_path}")
                # Ensure the WAV path is valid before reading
                if not wav_path.exists() or wav_path.stat().st_size == 0:
                     raise ValueError(f"WAV file {wav_path} is missing or empty after conversion.")

                audio, read_samplerate = sf.read(str(wav_path), dtype='float32')

                if read_samplerate != samplerate:
                     self.logger.warning(f"Read sample rate {read_samplerate} differs from expected {samplerate}. Check conversion.")
                     # Consider resampling if critical:
                     # num_samples = int(len(audio) * samplerate / read_samplerate)
                     # audio = signal.resample(audio, num_samples)

                # Ensure even number of samples (less critical now, but keep for safety?)
                if len(audio) % 2 != 0:
                    audio = audio[:-1]

                # Boost volume
                boost_factor = 4.0
                audio = np.clip(audio * boost_factor, -1.0, 1.0)

                if len(audio) == 0:
                    raise ValueError("Audio data is empty after reading WAV.")

                self.logger.debug(f"Successfully read {len(audio)} float samples, max amplitude: {np.max(np.abs(audio))}")
                return audio.astype(np.float32)

            except Exception as e:
                self.logger.error(f"Failed to process audio file: {e}", exc_info=True)
                return np.array([], dtype=np.float32)

        except Exception as e:
            self.logger.error(f"Synthesis failed unexpectedly: {e}", exc_info=True)
            return np.array([], dtype=np.float32)
        finally:
            # Ensure cleanup happens regardless of success or failure
            self.logger.debug("Running cleanup in finally block.")
            self.cleanup()


class EspeakWrapper(EspeakWrapperBase, TTSEngine):
    """Legacy eSpeak wrapper: DO NOT USE"""
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.warning("Using deprecated eSpeak wrapper")
        self._engine = None # Explicitly set engine to None

    def set_voice(self, voice: str) -> None:
        """Set voice using espeak API"""
        self.logger.warning("Attempted to use set_voice on deprecated EspeakWrapper.")
        # if self._engine: # This will always be false
        #     self._engine.set_voice(language=voice)

    def set_parameter(self, param: ParameterEnum, value: int) -> None:
        """Set parameters using espeak API"""
        self.logger.warning("Attempted to use set_parameter on deprecated EspeakWrapper.")
        # if not self._engine: # This will always be true
        #     return
        # ... rest of original code ...

    def synth(self, text: str) -> npt.NDArray[np.float32]:
        """Synthesize text using espeak API"""
        self.logger.error("Attempted to use synth on deprecated EspeakWrapper.")
        return np.array([], dtype=np.float32)