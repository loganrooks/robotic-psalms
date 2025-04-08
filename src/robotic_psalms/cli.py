import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np
import numpy.typing as npt
import soundfile as sf
import yaml
from matplotlib import pyplot as plt

from .config import PsalmConfig
from .synthesis.sacred_machinery import SacredMachineryEngine

AudioData = Dict[str, Union[npt.NDArray[np.float32], int]]

def setup_logging(verbose: bool = False) -> None:
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def load_config(config_path: Optional[Path]) -> PsalmConfig:
    """Load configuration from YAML file"""
    if config_path is None:
        return PsalmConfig()
        
    try:
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
        return PsalmConfig(**config_dict)
    except Exception as e:
        logging.error(f"Failed to load config from {config_path}: {str(e)}")
        sys.exit(1)

def load_lyrics(lyrics_path: Path) -> str:
    """Load Latin text from file"""
    try:
        return lyrics_path.read_text()
    except Exception as e:
        logging.error(f"Failed to load lyrics from {lyrics_path}: {str(e)}")
        sys.exit(1)

def save_audio(audio_path: Path, audio_data: AudioData) -> None:
    """Save audio files"""
    try:
        # Save stems
        stems_dir = audio_path.parent / f"{audio_path.stem}_stems"
        stems_dir.mkdir(exist_ok=True)
        
        for name, data in audio_data.items():
            if name == 'sample_rate':
                continue
                
            if isinstance(data, np.ndarray):
                stem_path = stems_dir / f"{name}.wav"
                sf.write(stem_path, data, audio_data['sample_rate'])
                logging.info(f"Saved {name} stem to {stem_path}")
            
        # Save combined mix
        sf.write(
            audio_path, 
            audio_data['combined'],
            audio_data['sample_rate']
        )
        logging.info(f"Saved combined mix to {audio_path}")
        
    except Exception as e:
        logging.error(f"Failed to save audio: {str(e)}")
        sys.exit(1)

def generate_waveform(audio_path: Path) -> None:
    """Generate waveform visualization"""
    try:
        # Load audio safely
        audio, sr = sf.read(str(audio_path))
        
        # Create new figure
        plt.figure(figsize=(12, 4))
        plt.clf()
        
        # Plot safely
        plt.plot(np.arange(len(audio)) / sr, audio)
        plt.title("Sacred Machinery Waveform")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        
        # Save and close
        plot_path = audio_path.with_suffix('.png')
        plt.savefig(str(plot_path))
        plt.close()
        
        logging.info(f"Saved waveform visualization to {plot_path}")
        
    except Exception as e:
        logging.error(f"Failed to generate waveform: {str(e)}")
        

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ethereal computerized vocal arrangements of Latin psalms"
    )
    
    parser.add_argument(
        "lyrics",
        type=Path,
        help="Path to Latin lyrics text file"
    )
    
    parser.add_argument(
        "output",
        type=Path,
        help="Output path for generated audio"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to YAML configuration file"
    )
    
    parser.add_argument(
        "--duration",
        type=float,
        default=180.0,
        help="Duration in seconds (default: 180.0)"
    )
    
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate waveform visualization"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Load configuration
    config = load_config(args.config)
    
    # Load lyrics
    lyrics = load_lyrics(args.lyrics)
    
    try:
        # Initialize engine
        engine = SacredMachineryEngine(config)
        
        # Process psalm
        logging.info("Processing psalm...")
        result = engine.process_psalm(lyrics, args.duration)
        
        # Prepare audio data for saving
        audio_data: AudioData = {
            'combined': result.combined,
            'vocals': result.vocals,
            'pads': result.pads,
            'percussion': result.percussion,
            'drones': result.drones,
            'sample_rate': result.sample_rate
        }
        
        # Save audio files
        save_audio(args.output, audio_data)
        
        # Generate visualization if requested
        if args.visualize:
            generate_waveform(args.output)
            
        logging.info("Processing complete!")
        
    except Exception as e:
        logging.error(f"Processing failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()