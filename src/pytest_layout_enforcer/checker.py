"""Core test-layout validation, independent of pytest and the CLI."""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
from pathlib import Path

from .config import Config, Layout
from .diagnostics import Violation


@dataclass(frozen=True)
class _Source:
    path: Path
    relative: Path

    @property
    def stem(self) -> str:
        return self.relative.stem


@dataclass(frozen=True)
class CheckResult:
    """Summary and violations from a complete project scan."""

    root: Path
    violations: tuple[Violation, ...]
    source_count: int
    test_count: int

    @property
    def ok(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "source_count": self.source_count,
            "test_count": self.test_count,
            "violations": [
                violation.as_dict(self.root) for violation in self.violations
            ],
        }


def check_layout(config: Config) -> CheckResult:
    """Validate every configured layout and return all violations."""

    violations: list[Violation] = []
    source_count = 0
    test_count = 0

    for layout in config.layouts:
        layout_violations, layout_source_count, layout_test_count = _check_one(
            config, layout
        )
        violations.extend(layout_violations)
        source_count += layout_source_count
        test_count += layout_test_count

    violations.sort(key=lambda item: (item.path.as_posix(), item.code, item.message))
    return CheckResult(
        root=config.root,
        violations=tuple(violations),
        source_count=source_count,
        test_count=test_count,
    )


def _check_one(
    config: Config, layout: Layout
) -> tuple[list[Violation], int, int]:
    if not layout.source.is_dir():
        return (
            [
                Violation(
                    code="missing-source-root",
                    path=layout.source,
                    message="configured source directory does not exist",
                )
            ],
            0,
            0,
        )

    sources = _discover_sources(config, layout)
    tests = _discover_tests(config, layout)
    violations: list[Violation] = []
    tested_sources: set[Path] = set()

    for test_path, test_relative in tests:
        violation, source = _match_test(config, layout, sources, test_path, test_relative)
        if violation is not None:
            violations.append(violation)
        elif source is not None:
            tested_sources.add(source.path)

    if config.require_tests:
        for source in sources:
            if source.path not in tested_sources:
                expected = _expected_path(layout, source)
                violations.append(
                    Violation(
                        code="missing-test",
                        path=source.path,
                        message="source module has no matching test file",
                        expected=(expected,),
                    )
                )

    return violations, len(sources), len(tests)


def _discover_sources(config: Config, layout: Layout) -> list[_Source]:
    sources: list[_Source] = []
    test_root = layout.tests.resolve()
    for path in sorted(layout.source.rglob("*.py")):
        resolved = path.resolve()
        if resolved == test_root or test_root in resolved.parents:
            continue
        relative = path.relative_to(layout.source)
        if not config.include_init and path.name == "__init__.py":
            continue
        if _excluded(relative, config.exclude_sources):
            continue
        sources.append(_Source(path=path, relative=relative))
    return sources


def _discover_tests(config: Config, layout: Layout) -> list[tuple[Path, Path]]:
    if not layout.tests.is_dir():
        return []
    tests: list[tuple[Path, Path]] = []
    for path in sorted(layout.tests.rglob("test_*.py")):
        relative = path.relative_to(layout.tests)
        if _excluded(relative, config.exclude_tests):
            continue
        tests.append((path, relative))
    return tests


def _match_test(
    config: Config,
    layout: Layout,
    sources: list[_Source],
    test_path: Path,
    test_relative: Path,
) -> tuple[Violation | None, _Source | None]:
    payload = test_path.stem.removeprefix("test_")
    exact = [source for source in sources if payload == source.stem]
    valid_feature: list[_Source] = []
    invalid_feature: list[_Source] = []

    for source in sources:
        prefix = f"{source.stem}{config.feature_separator}"
        if not payload.startswith(prefix):
            continue
        feature = payload[len(prefix) :]
        if config.compiled_feature_pattern.fullmatch(feature):
            valid_feature.append(source)
        else:
            invalid_feature.append(source)

    candidates = exact or valid_feature
    in_directory = [
        source for source in candidates if source.relative.parent == test_relative.parent
    ]

    if len(in_directory) == 1:
        return None, in_directory[0]

    if len(in_directory) > 1:
        return _ambiguous(layout, test_path, in_directory), None

    if len(candidates) == 1:
        source = candidates[0]
        expected = _expected_path(layout, source, test_path.name)
        return (
            Violation(
                code="misplaced-test",
                path=test_path,
                message=f"test for {source.relative.as_posix()} is in the wrong directory",
                expected=(expected,),
            ),
            None,
        )

    if len(candidates) > 1:
        return _ambiguous(layout, test_path, candidates), None

    invalid_in_directory = [
        source
        for source in invalid_feature
        if source.relative.parent == test_relative.parent
    ]
    if len(invalid_in_directory) == 1:
        source = invalid_in_directory[0]
        return (
            Violation(
                code="invalid-feature",
                path=test_path,
                message=(
                    f"feature name does not match /{config.feature_pattern}/ "
                    f"for module {source.relative.as_posix()}"
                ),
            ),
            None,
        )

    return (
        Violation(
            code="orphan-test",
            path=test_path,
            message="test filename does not map to a source module",
        ),
        None,
    )


def _ambiguous(layout: Layout, test_path: Path, sources: list[_Source]) -> Violation:
    expected = tuple(_expected_path(layout, source) for source in sources)
    modules = ", ".join(source.relative.as_posix() for source in sources)
    return Violation(
        code="ambiguous-test",
        path=test_path,
        message=f"test filename could refer to multiple source modules: {modules}",
        expected=expected,
    )


def _expected_path(layout: Layout, source: _Source, name: str | None = None) -> Path:
    filename = name or f"test_{source.stem}.py"
    return layout.tests / source.relative.parent / filename


def _excluded(relative: Path, patterns: tuple[str, ...]) -> bool:
    candidate = relative.as_posix()
    return any(
        fnmatch.fnmatchcase(candidate, pattern)
        or fnmatch.fnmatchcase(relative.name, pattern)
        for pattern in patterns
    )

