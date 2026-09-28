import json
from pathlib import Path

from pytest_layout_enforcer.cli import main


def configured_project(tmp_path: Path) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.pytest-layout-enforcer]
[[tool.pytest-layout-enforcer.layouts]]
source = "src/example"
tests = "tests"
"""
    )


def test_cli_success(tmp_path: Path, capsys) -> None:
    configured_project(tmp_path)
    (tmp_path / "src/example/core.py").touch()
    (tmp_path / "tests/test_core.py").touch()

    assert main(["check", "--root", str(tmp_path)]) == 0
    assert "layout check passed" in capsys.readouterr().out


def test_cli_json_violation(tmp_path: Path, capsys) -> None:
    configured_project(tmp_path)
    (tmp_path / "tests/test_unknown.py").touch()

    assert main(["check", "--root", str(tmp_path), "--format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["violations"][0]["code"] == "orphan-test"


def test_cli_configuration_error(tmp_path: Path, capsys) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n")

    assert main(["check", "--root", str(tmp_path)]) == 2
    assert "configuration error" in capsys.readouterr().err

