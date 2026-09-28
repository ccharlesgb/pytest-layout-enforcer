"""Configuration loading for pytest-layout-enforcer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from typing import Any


DEFAULT_FEATURE_PATTERN = r"[a-z][a-z0-9_]*"


class ConfigError(ValueError):
    """Raised when the tool configuration is invalid."""


@dataclass(frozen=True)
class Layout:
    """One source tree and its corresponding test tree."""

    source: Path
    tests: Path


@dataclass(frozen=True)
class Config:
    """Validated project configuration."""

    root: Path
    layouts: tuple[Layout, ...]
    enabled: bool = True
    feature_pattern: str = DEFAULT_FEATURE_PATTERN
    feature_separator: str = "_"
    require_tests: bool = False
    include_init: bool = False
    exclude_sources: tuple[str, ...] = ()
    exclude_tests: tuple[str, ...] = ()

    @property
    def compiled_feature_pattern(self) -> re.Pattern[str]:
        return re.compile(rf"^(?:{self.feature_pattern})$")

    @classmethod
    def from_pyproject(cls, path: Path) -> Config | None:
        """Load configuration, returning ``None`` when the tool is not configured."""

        pyproject = path.resolve()
        try:
            with pyproject.open("rb") as handle:
                document = tomllib.load(handle)
        except FileNotFoundError as error:
            raise ConfigError(f"pyproject.toml not found: {pyproject}") from error
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"invalid TOML in {pyproject}: {error}") from error

        table = document.get("tool", {}).get("pytest-layout-enforcer")
        if table is None:
            return None
        if not isinstance(table, dict):
            raise ConfigError("[tool.pytest-layout-enforcer] must be a table")

        root = pyproject.parent
        raw_layouts = table.get("layouts")
        if not isinstance(raw_layouts, list) or not raw_layouts:
            raise ConfigError(
                "configure at least one [[tool.pytest-layout-enforcer.layouts]] table"
            )

        layouts: list[Layout] = []
        for index, raw_layout in enumerate(raw_layouts, start=1):
            if not isinstance(raw_layout, dict):
                raise ConfigError(f"layout {index} must be a table")
            source = _relative_path(raw_layout.get("source"), f"layout {index} source")
            tests = _relative_path(raw_layout.get("tests"), f"layout {index} tests")
            layouts.append(Layout(root / source, root / tests))

        feature_pattern = _string(
            table, "feature-pattern", DEFAULT_FEATURE_PATTERN
        )
        try:
            re.compile(rf"^(?:{feature_pattern})$")
        except re.error as error:
            raise ConfigError(f"invalid feature-pattern: {error}") from error

        separator = _string(table, "feature-separator", "_")
        if not separator or any(character in separator for character in "/\\."):
            raise ConfigError(
                "feature-separator must be non-empty and cannot contain '/', '\\', or '.'"
            )

        return cls(
            root=root,
            layouts=tuple(layouts),
            enabled=_boolean(table, "enabled", True),
            feature_pattern=feature_pattern,
            feature_separator=separator,
            require_tests=_boolean(table, "require-tests", False),
            include_init=_boolean(table, "include-init", False),
            exclude_sources=_string_list(table, "exclude-sources"),
            exclude_tests=_string_list(table, "exclude-tests"),
        )


def find_pyproject(start: Path) -> Path:
    """Find the nearest pyproject.toml at or above ``start``."""

    current = start.resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    raise ConfigError(f"could not find pyproject.toml from {start}")


def _relative_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{label} must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ConfigError(f"{label} must stay within the project root")
    return path


def _string(table: dict[str, Any], key: str, default: str) -> str:
    value = table.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(f"{key} must be a string")
    return value


def _boolean(table: dict[str, Any], key: str, default: bool) -> bool:
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{key} must be a boolean")
    return value


def _string_list(table: dict[str, Any], key: str) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be an array of strings")
    return tuple(value)

