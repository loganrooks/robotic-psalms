"""Test basic installation and dependency setup"""
import importlib
import subprocess
import sys
from typing import List, Tuple

try:
    import pytest
except ImportError:
    print("pytest not installed. Run: pip install -e '.[dev]'")
    sys.exit(1)

def test_python_version() -> None:
    """Ensure Python version is 3.9+"""
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 9), "Python 3.9+ is required"

def check_dependency(name: str) -> Tuple[bool, str]:
    """Check if a dependency can be imported"""
    try:
        importlib.import_module(name)
        return True, f"{name} is installed"
    except ImportError as e:
        return False, f"Failed to import {name}: {str(e)}"

def test_core_dependencies() -> None:
    """Test that all core dependencies are available"""
    dependencies = [
        "numpy",
        "scipy",
        "librosa",
        "mido",
        "sounddevice",
        "pydantic",
        "yaml",
        "matplotlib",
        "soundfile"
    ]
    
    results = [check_dependency(dep) for dep in dependencies]
    errors = [msg for success, msg in results if not success]
    
    if errors:
        pytest.fail("\n".join(errors))

def test_tts_dependencies() -> None:
    """Test text-to-speech engine availability"""
    # Check eSpeak-NG
    try:
        subprocess.run(["espeak-ng", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Check regular eSpeak
        try:
            subprocess.run(["espeak", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.fail("Neither eSpeak-NG nor eSpeak is installed")
    
    # Check Festival
    try:
        subprocess.run(
            ["festival", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.fail("Festival is not installed or not in PATH")

def test_robotic_psalms_import() -> None:
    """Test that the package can be imported"""
    import robotic_psalms
    from robotic_psalms import config, cli
    from robotic_psalms.synthesis import vox_dei, sacred_machinery
    
    assert hasattr(cli, 'main'), "CLI main function not found"
    assert hasattr(config, 'PsalmConfig'), "PsalmConfig not found"
    assert hasattr(sacred_machinery, 'SacredMachineryEngine'), "SacredMachineryEngine not found"
    assert hasattr(vox_dei, 'VoxDeiSynthesizer'), "VoxDeiSynthesizer not found"


def test_pyfoal_import() -> None:
    """Test that the pyfoal package can be imported"""
    try:
        # Just try importing the main package
        import pyfoal
        assert pyfoal is not None, "pyfoal module could not be imported"
    except ImportError as e:
        pytest.fail(f"Failed to import pyfoal: {str(e)}")
