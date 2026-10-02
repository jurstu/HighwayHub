from typing import TYPE_CHECKING

__all__ = ["get_logger"]

_LAZY_IMPORTS = {
    # object: file
    "get_logger": ".logging_setup"
}


if TYPE_CHECKING:
    from .logging_setup import get_logger


def __getattr__(name):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module_name = _LAZY_IMPORTS[name]

    try:
        module = import_module(module_name, __name__)
    except ModuleNotFoundError as exc:
        expected = f"{__name__}.{module_name.removeprefix('.')}"

        if exc.name == expected:
            raise AttributeError(
                f"{name!r} is declared by {__name__!r}, "
                f"but its module {expected!r} is not included in this build"
            ) from None

        # Real missing dependency inside the imported module.
        raise

    value = getattr(module, name)
    globals()[name] = value
    return value
