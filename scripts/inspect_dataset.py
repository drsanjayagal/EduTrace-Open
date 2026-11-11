"""Standalone wrapper around ``edutrace inspect``.

Usage:
    python scripts/inspect_dataset.py --input data/generated --json out.json
"""

from __future__ import annotations

import sys

from edutrace.cli import app


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    try:
        app(args=["inspect", *argv])
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
