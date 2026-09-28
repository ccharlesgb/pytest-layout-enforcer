from pathlib import Path
from types import SimpleNamespace

import pytest

from pytest_layout_enforcer.plugin import pytest_configure


def test_plugin_is_noop_without_configuration(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n")
    pytest_configure(SimpleNamespace(rootpath=tmp_path))


def test_plugin_fails_before_collection_on_violation(tmp_path: Path) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_unknown.py").touch()
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.pytest-layout-enforcer]
[[tool.pytest-layout-enforcer.layouts]]
source = "src/example"
tests = "tests"
"""
    )

    with pytest.raises(pytest.UsageError, match="1 layout violation"):
        pytest_configure(SimpleNamespace(rootpath=tmp_path))

