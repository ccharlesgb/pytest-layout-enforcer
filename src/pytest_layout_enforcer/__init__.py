"""Enforce a mirrored relationship between Python modules and their tests."""

from .checker import CheckResult, check_layout
from .config import Config, ConfigError, Layout
from .diagnostics import Violation

__all__ = [
    "CheckResult",
    "Config",
    "ConfigError",
    "Layout",
    "Violation",
    "check_layout",
]

__version__ = "0.1.0"

