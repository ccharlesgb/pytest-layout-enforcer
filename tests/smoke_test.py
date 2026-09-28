"""Verify that an installed distribution exposes its public integrations."""

from importlib.metadata import entry_points, version

import pytest_layout_enforcer


assert version("pytest-layout-enforcer") == pytest_layout_enforcer.__version__

scripts = entry_points(group="console_scripts")
assert any(
    entry.name == "pytest-layout-enforcer"
    and entry.value == "pytest_layout_enforcer.cli:main"
    for entry in scripts
)

plugins = entry_points(group="pytest11")
assert any(
    entry.name == "layout-enforcer"
    and entry.value == "pytest_layout_enforcer.plugin"
    for entry in plugins
)

