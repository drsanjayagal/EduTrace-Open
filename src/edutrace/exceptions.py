"""Exception hierarchy for EduTrace-Open.

All raised exceptions inherit from :class:`EduTraceError` so callers can
catch the whole family without importing every subclass.
"""

from __future__ import annotations


class EduTraceError(Exception):
    """Base class for all EduTrace-Open errors."""


class ConfigError(EduTraceError):
    """Raised when a configuration file is missing, malformed, or invalid."""


class SchemaError(EduTraceError):
    """Raised when a generated record violates a registered schema."""


class ValidationError(EduTraceError):
    """Raised when a validation stage fails in strict mode."""


class RelationalIntegrityError(EduTraceError):
    """Raised when a foreign key or uniqueness constraint is violated."""


class TemporalIntegrityError(EduTraceError):
    """Raised when timestamps violate the documented temporal rules."""


class PipelineError(EduTraceError):
    """Raised when the generation pipeline cannot proceed."""


class CheckpointError(EduTraceError):
    """Raised when a checkpoint cannot be written or resumed."""


class ExportError(EduTraceError):
    """Raised when an export format fails to write."""
