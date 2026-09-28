"""Command-line interface for pytest-layout-enforcer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from collections.abc import Sequence

from .checker import CheckResult, check_layout
from .config import Config, ConfigError, find_pyproject


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pytest-layout-enforcer",
        description="Enforce mirrored source and test layouts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="check the configured layouts")
    check.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="project directory or pyproject.toml (default: current directory)",
    )
    check.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pyproject = (
            args.root.resolve()
            if args.root.name == "pyproject.toml"
            else find_pyproject(args.root)
        )
        config = Config.from_pyproject(pyproject)
        if config is None:
            raise ConfigError(
                f"{pyproject} has no [tool.pytest-layout-enforcer] configuration"
            )
    except ConfigError as error:
        if args.format == "json":
            print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        else:
            print(f"configuration error: {error}", file=sys.stderr)
        return 2

    if not config.enabled:
        if args.format == "json":
            print(json.dumps({"ok": True, "enabled": False, "violations": []}, indent=2))
        else:
            print("pytest-layout-enforcer is disabled")
        return 0

    result = check_layout(config)
    if args.format == "json":
        print(json.dumps(result.as_dict(), indent=2))
    else:
        _print_text(result)
    return 0 if result.ok else 1


def _print_text(result: CheckResult) -> None:
    if result.ok:
        print(
            f"layout check passed ({result.source_count} source modules, "
            f"{result.test_count} test files)"
        )
        return

    for violation in result.violations:
        data = violation.as_dict(result.root)
        print(f"{data['path']}: {violation.code}: {violation.message}")
        for expected in data["expected"]:
            print(f"  expected: {expected}")
    count = len(result.violations)
    print(f"layout check failed with {count} violation{'s' if count != 1 else ''}")


if __name__ == "__main__":
    raise SystemExit(main())

