"""Pytest adapter for the layout checker."""

from __future__ import annotations

import pytest

from .checker import check_layout
from .cli import _print_text
from .config import Config, ConfigError


def pytest_configure(config: pytest.Config) -> None:
    """Check the project once, before pytest begins collection."""

    if hasattr(config, "workerinput"):
        return

    pyproject = config.rootpath / "pyproject.toml"
    if not pyproject.is_file():
        return

    try:
        settings = Config.from_pyproject(pyproject)
    except ConfigError as error:
        raise pytest.UsageError(f"pytest-layout-enforcer: {error}") from error

    if settings is None or not settings.enabled:
        return

    result = check_layout(settings)
    if not result.ok:
        _print_text(result)
        raise pytest.UsageError(
            f"pytest-layout-enforcer found {len(result.violations)} layout violation(s)"
        )

