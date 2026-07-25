"""Sacred Machinery synthesis components"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .sacred_machinery import SacredMachineryEngine
    from .vox_dei import VoxDeiSynthesizer, VoxDeiSynthesisError

__all__ = ['SacredMachineryEngine', 'VoxDeiSynthesizer', 'VoxDeiSynthesisError']

# Re-exports below are lazy (PEP 562): `..config` imports `.synthesis.effects`,
# which runs this file. Eagerly importing sacred_machinery/vox_dei here used
# to pull `..config` back in before it had finished initializing, raising
# ImportError. Resolving the names on first access instead breaks the cycle
# while keeping `robotic_psalms.synthesis.SacredMachineryEngine` etc. working.
_LAZY_ATTRS = {
    'SacredMachineryEngine': ('.sacred_machinery', 'SacredMachineryEngine'),
    'VoxDeiSynthesizer': ('.vox_dei', 'VoxDeiSynthesizer'),
    'VoxDeiSynthesisError': ('.vox_dei', 'VoxDeiSynthesisError'),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr = _LAZY_ATTRS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    import importlib
    module = importlib.import_module(module_name, __name__)
    value = getattr(module, attr)
    globals()[name] = value
    return value
