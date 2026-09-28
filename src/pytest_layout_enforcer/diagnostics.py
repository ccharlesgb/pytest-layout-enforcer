"""Diagnostics emitted by the layout checker."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Violation:
    """A single actionable layout violation."""

    code: str
    path: Path
    message: str
    expected: tuple[Path, ...] = ()

    def as_dict(self, root: Path) -> dict[str, object]:
        return {
            "code": self.code,
            "path": _display(self.path, root),
            "message": self.message,
            "expected": [_display(path, root) for path in self.expected],
        }


def _display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()

