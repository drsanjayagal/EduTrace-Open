"""Standalone wrapper around ``edutrace validate``.

Usage:
    python scripts/validate_dataset.py --input data/generated --strict
"""

from __future__ import annotations

import sys

from edutrace.cli import app


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    try:
        app(args=["validate", *argv])
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
