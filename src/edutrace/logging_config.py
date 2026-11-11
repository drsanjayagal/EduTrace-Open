"""Structured logging configuration for EduTrace-Open.

We use stdlib logging with a Rich handler when Rich is available, and fall
back to a plain ``StreamHandler`` otherwise. Loggers are namespaced under
``edutrace`` to avoid clobbering user loggers.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

_LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%S"

_CONFIGURED: bool = False


def configure_logging(level: str | int = "INFO", use_rich: bool = True) -> None:
    """Configure the ``edutrace`` logger tree exactly once.

    Idempotent: repeated calls are no-ops except for updating the level.
    """
    global _CONFIGURED

    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), logging.INFO)
    else:
        numeric_level = level

    root = logging.getLogger("edutrace")

    if _CONFIGURED:
        root.setLevel(numeric_level)
        for handler in root.handlers:
            handler.setLevel(numeric_level)
        return

    handler: logging.Handler
    if use_rich:
        try:
            from rich.logging import RichHandler

            handler = RichHandler(rich_tracebacks=True, show_path=False)
        except ImportError:  # pragma: no cover - rich is a hard dependency
            handler = logging.StreamHandler(sys.stderr)
    else:
        handler = logging.StreamHandler(sys.stderr)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    if not isinstance(handler, logging.StreamHandler) or use_rich is False:
        handler.setFormatter(formatter)

    root.setLevel(numeric_level)
    root.addHandler(handler)
    root.propagate = False

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under ``edutrace``.

    ``get_logger(__name__)`` from within the package produces the right name
    automatically; callers outside the package should pass an explicit suffix
    like ``"edutrace.cli"``.
    """
    if not name.startswith("edutrace"):
        name = f"edutrace.{name}"
    return logging.getLogger(name)
