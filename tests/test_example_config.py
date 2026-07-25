"""Test that the documented example configuration is valid"""
from pathlib import Path

import yaml

from robotic_psalms.config import PsalmConfig

EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "examples" / "config.yml"


def test_example_config_parses_as_psalm_config() -> None:
    """`examples/config.yml`, the file the README tells users to pass via
    `--config`, must parse into a valid `PsalmConfig`."""
    with open(EXAMPLE_CONFIG_PATH) as f:
        config_dict = yaml.safe_load(f)

    config = PsalmConfig(**config_dict)

    assert isinstance(config, PsalmConfig)
