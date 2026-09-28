from pathlib import Path

import pytest

from pytest_layout_enforcer.config import Config, ConfigError, find_pyproject


def write_config(root: Path, body: str) -> Path:
    path = root / "pyproject.toml"
    path.write_text(body)
    return path


def test_loads_multiple_layouts_and_options(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
[tool.pytest-layout-enforcer]
feature-separator = "__"
require-tests = true
include-init = true
exclude-sources = ["generated/**"]
exclude-tests = ["legacy/**"]

[[tool.pytest-layout-enforcer.layouts]]
source = "src/one"
tests = "tests/one"

[[tool.pytest-layout-enforcer.layouts]]
source = "src/two"
tests = "tests/two"
""",
    )

    config = Config.from_pyproject(path)

    assert config is not None
    assert len(config.layouts) == 2
    assert config.feature_separator == "__"
    assert config.require_tests
    assert config.include_init
    assert config.exclude_sources == ("generated/**",)


def test_returns_none_when_not_configured(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[project]\nname = 'example'\n")
    assert Config.from_pyproject(path) is None


@pytest.mark.parametrize(
    "body, message",
    [
        ("[tool.pytest-layout-enforcer]", "at least one"),
        (
            """
[tool.pytest-layout-enforcer]
feature-pattern = "["
[[tool.pytest-layout-enforcer.layouts]]
source = "src/pkg"
tests = "tests"
""",
            "invalid feature-pattern",
        ),
        (
            """
[tool.pytest-layout-enforcer]
[[tool.pytest-layout-enforcer.layouts]]
source = "../elsewhere"
tests = "tests"
""",
            "project root",
        ),
    ],
)
def test_rejects_invalid_configuration(
    tmp_path: Path, body: str, message: str
) -> None:
    path = write_config(tmp_path, body)
    with pytest.raises(ConfigError, match=message):
        Config.from_pyproject(path)


def test_finds_nearest_pyproject(tmp_path: Path) -> None:
    expected = write_config(tmp_path, "")
    nested = tmp_path / "one" / "two"
    nested.mkdir(parents=True)
    assert find_pyproject(nested) == expected

