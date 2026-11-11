"""Entry point for ``python -m edutrace``."""

from __future__ import annotations

from edutrace.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
