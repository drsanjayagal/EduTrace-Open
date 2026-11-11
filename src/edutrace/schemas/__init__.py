"""Table schemas for EduTrace-Open.

Schemas are declared as lightweight ``TableSchema`` objects rather than
Pydantic models because:
* We generate millions of rows; Pydantic validation per row would dominate
  runtime.
* Pandas/Polars/Arrow dtypes are the real contract; the schema is used by
  validators, exporters, and the data dictionary.

If you need per-row validation for testing, use :func:`validate_row`.
"""

from __future__ import annotations

from edutrace.schemas.tables import (
    ALL_TABLES,
    TABLE_SCHEMAS,
    ColumnSpec,
    TableSchema,
    get_schema,
    validate_row,
)

__all__ = [
    "ALL_TABLES",
    "TABLE_SCHEMAS",
    "ColumnSpec",
    "TableSchema",
    "get_schema",
    "validate_row",
]
