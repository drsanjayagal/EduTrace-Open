"""Filesystem helpers.

All paths are handled via :class:`pathlib.Path`. No absolute paths are
hard-coded; callers supply the output root from configuration.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    """Create ``path`` (and parents) if missing and return it as a Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_rmdir(path: str | Path) -> None:
    """Recursively remove ``path`` if it exists. No error if absent."""
    p = Path(path)
    if p.exists():
        shutil.rmtree(p)


def list_files(root: str | Path, pattern: str = "*") -> list[Path]:
    """Return sorted files under ``root`` matching ``pattern``."""
    p = Path(root)
    if not p.exists():
        return []
    return sorted(p.rglob(pattern))


def relative_to_root(path: str | Path, root: str | Path) -> str:
    """Return a POSIX-style path for ``path`` relative to ``root``."""
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def file_size_bytes(path: str | Path) -> int:
    """Return the size of ``path`` in bytes."""
    return Path(path).stat().st_size
