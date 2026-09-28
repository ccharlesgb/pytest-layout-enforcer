from pathlib import Path

from pytest_layout_enforcer.checker import check_layout
from pytest_layout_enforcer.config import Config, Layout


def make_config(
    root: Path,
    *,
    test_root: str = "tests",
    require_tests: bool = False,
    feature_separator: str = "_",
    feature_pattern: str = r"[a-z][a-z0-9_]*",
) -> Config:
    source = root / "src" / "example"
    tests = root / test_root
    source.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)
    return Config(
        root=root,
        layouts=(Layout(source, tests),),
        require_tests=require_tests,
        feature_separator=feature_separator,
        feature_pattern=feature_pattern,
    )


def touch(root: Path, relative: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def codes(config: Config) -> list[str]:
    return [violation.code for violation in check_layout(config).violations]


def test_accepts_exact_feature_and_mirrored_nested_tests(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    touch(tmp_path, "src/example/core.py")
    touch(tmp_path, "src/example/services/billing.py")
    touch(tmp_path, "tests/test_core.py")
    touch(tmp_path, "tests/test_core_parsing.py")
    touch(tmp_path, "tests/services/test_billing_refunds.py")

    result = check_layout(config)

    assert result.ok
    assert result.source_count == 2
    assert result.test_count == 3


def test_reports_misplaced_test_with_destination(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    touch(tmp_path, "src/example/services/billing.py")
    test = touch(tmp_path, "tests/test_billing.py")

    violation = check_layout(config).violations[0]

    assert violation.code == "misplaced-test"
    assert violation.path == test
    assert violation.expected == (tmp_path / "tests/services/test_billing.py",)


def test_reports_orphan_test(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    touch(tmp_path, "src/example/core.py")
    touch(tmp_path, "tests/test_unknown.py")
    assert codes(config) == ["orphan-test"]


def test_reports_invalid_feature_name(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    touch(tmp_path, "src/example/core.py")
    touch(tmp_path, "tests/test_core_Bad.py")
    assert codes(config) == ["invalid-feature"]


def test_reports_ambiguous_single_underscore_feature(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    touch(tmp_path, "src/example/data.py")
    touch(tmp_path, "src/example/data_loader.py")
    touch(tmp_path, "tests/test_data_loader_cache.py")
    assert codes(config) == ["ambiguous-test"]


def test_exact_module_name_wins_over_feature_interpretation(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    touch(tmp_path, "src/example/data.py")
    touch(tmp_path, "src/example/data_loader.py")
    touch(tmp_path, "tests/test_data_loader.py")
    assert check_layout(config).ok


def test_double_underscore_separator_avoids_module_name_ambiguity(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path, feature_separator="__")
    touch(tmp_path, "src/example/data.py")
    touch(tmp_path, "src/example/data_loader.py")
    touch(tmp_path, "tests/test_data_loader__cache.py")
    assert check_layout(config).ok


def test_require_tests_reports_each_untested_source(tmp_path: Path) -> None:
    config = make_config(tmp_path, require_tests=True)
    touch(tmp_path, "src/example/core.py")

    violation = check_layout(config).violations[0]

    assert violation.code == "missing-test"
    assert violation.expected == (tmp_path / "tests/test_core.py",)


def test_inline_test_tree_is_not_treated_as_source(tmp_path: Path) -> None:
    config = make_config(tmp_path, test_root="src/example/tests")
    touch(tmp_path, "src/example/core.py")
    touch(tmp_path, "src/example/tests/test_core.py")
    result = check_layout(config)
    assert result.ok
    assert result.source_count == 1


def test_init_and_non_test_helpers_are_ignored(tmp_path: Path) -> None:
    config = make_config(tmp_path, require_tests=True)
    touch(tmp_path, "src/example/__init__.py")
    touch(tmp_path, "tests/conftest.py")
    touch(tmp_path, "tests/helpers.py")
    assert check_layout(config).ok


def test_exclusions_apply_relative_to_each_root(tmp_path: Path) -> None:
    base = make_config(tmp_path)
    config = Config(
        root=base.root,
        layouts=base.layouts,
        exclude_sources=("generated/**",),
        exclude_tests=("legacy/**",),
    )
    touch(tmp_path, "src/example/generated/schema.py")
    touch(tmp_path, "tests/legacy/test_unknown.py")
    assert check_layout(config).ok


def test_missing_source_root_is_a_violation(tmp_path: Path) -> None:
    config = Config(
        root=tmp_path,
        layouts=(Layout(tmp_path / "missing", tmp_path / "tests"),),
    )
    assert codes(config) == ["missing-source-root"]

