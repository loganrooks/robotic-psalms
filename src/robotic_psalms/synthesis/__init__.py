"""Sacred Machinery synthesis components

Note: Imports are deferred to avoid circular dependencies with config.py.
Use explicit imports when needed:
    from robotic_psalms.synthesis.sacred_machinery import SacredMachineryEngine
    from robotic_psalms.synthesis.vox_dei import VoxDeiSynthesizer
"""

__all__ = ['SacredMachineryEngine', 'VoxDeiSynthesizer', 'VoxDeiSynthesisError']


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == 'SacredMachineryEngine':
        from .sacred_machinery import SacredMachineryEngine
        return SacredMachineryEngine
    elif name == 'VoxDeiSynthesizer':
        from .vox_dei import VoxDeiSynthesizer
        return VoxDeiSynthesizer
    elif name == 'VoxDeiSynthesisError':
        from .vox_dei import VoxDeiSynthesisError
        return VoxDeiSynthesisError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")