"""Structural validation: columns, dtypes, nullability, enums, bounds, PKs.

These checks run against the schema declared in ``schemas/tables.py``.
They are the strongest guarantee that generated data conforms to the
documented format. They do *not* check realism.
"""

from __future__ import annotations

import polars as pl

from edutrace.schemas.tables import ALL_TABLES, TableSchema
from edutrace.validation._report import CheckResult

# Mapping from the logical dtype names in schemas.tables to Polars dtypes
# or Polars dtype predicates. Kept here so the validator is self-contained.
DTYPE_STR_DTYPES_MAP = {
    "string": pl.Utf8,
    "int64": pl.Int64,
    "float64": pl.Float64,
    "bool": pl.Boolean,
    "datetime64[ns]": pl.Datetime,  # us is accepted under the Datetime family
}


def run_structural_checks(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for schema in ALL_TABLES:
        if schema.name not in tables:
            results.append(
                CheckResult(
                    name=f"structural.missing_table.{schema.name}",
                    status="fail",
                    message=f"Table {schema.name!r} not present",
                )
            )
            continue
        df = tables[schema.name]
        results.extend(_check_table(df, schema))
    return results


def _check_table(df: pl.DataFrame, schema: TableSchema) -> list[CheckResult]:
    out: list[CheckResult] = []

    # Column presence.
    actual_cols = set(df.columns)
    expected_cols = set(schema.column_names)
    missing = expected_cols - actual_cols
    extra = actual_cols - expected_cols
    if missing:
        out.append(
            CheckResult(
                name=f"structural.columns.{schema.name}.missing",
                status="fail",
                message=f"{schema.name}: missing columns {sorted(missing)}",
            )
        )
    if extra:
        out.append(
            CheckResult(
                name=f"structural.columns.{schema.name}.extra",
                status="fail",
                message=f"{schema.name}: unexpected columns {sorted(extra)}",
            )
        )
    if missing:
        return out  # Cannot check further safely.

    # Dtype check.
    for col in schema.columns:
        expected_dtype = DTYPE_STR_DTYPES_MAP.get(col.dtype)
        actual_dtype = df.schema[col.name]
        if expected_dtype is None:
            continue
        if expected_dtype is pl.Datetime:
            if not isinstance(actual_dtype, pl.Datetime):
                out.append(
                    CheckResult(
                        name=f"structural.dtype.{schema.name}.{col.name}",
                        status="fail",
                        message=(
                            f"{schema.name}.{col.name}: expected Datetime, "
                            f"got {actual_dtype}"
                        ),
                    )
                )
        else:
            if actual_dtype != expected_dtype:
                out.append(
                    CheckResult(
                        name=f"structural.dtype.{schema.name}.{col.name}",
                        status="fail",
                        message=(
                            f"{schema.name}.{col.name}: expected {expected_dtype}, "
                            f"got {actual_dtype}"
                        ),
                    )
                )

    # Nullability.
    for col in schema.columns:
        if not col.nullable:
            null_count = int(df[col.name].null_count())
            if null_count > 0:
                out.append(
                    CheckResult(
                        name=f"structural.nullable.{schema.name}.{col.name}",
                        status="fail",
                        message=(
                            f"{schema.name}.{col.name}: {null_count} null(s) "
                            "found in non-nullable column"
                        ),
                        details={"null_count": null_count},
                    )
                )

    # Primary key uniqueness.
    if schema.primary_key:
        pk = schema.primary_key
        dupes = df[pk].is_duplicated().sum()
        if dupes > 0:
            out.append(
                CheckResult(
                    name=f"structural.pk.{schema.name}",
                    status="fail",
                    message=(
                        f"{schema.name}.{pk}: {int(dupes)} duplicate(s) found"
                    ),
                    details={"duplicate_count": int(dupes)},
                )
            )
        if df[pk].null_count() > 0:
            out.append(
                CheckResult(
                    name=f"structural.pk_null.{schema.name}",
                    status="fail",
                    message=f"{schema.name}.{pk}: nulls present in primary key",
                )
            )

    # Uniqueness for any unique column.
    for col in schema.columns:
        if col.unique and not col.primary_key:
            dupes = df[col.name].is_duplicated().sum()
            if dupes > 0:
                out.append(
                    CheckResult(
                        name=f"structural.unique.{schema.name}.{col.name}",
                        status="fail",
                        message=(
                            f"{schema.name}.{col.name}: {int(dupes)} duplicate(s)"
                        ),
                        details={"duplicate_count": int(dupes)},
                    )
                )

    # Enum membership.
    for col in schema.columns:
        if col.enum_values is None:
            continue
        distinct = df[col.name].drop_nulls().unique().to_list()
        bad = [v for v in distinct if v not in col.enum_values]
        if bad:
            out.append(
                CheckResult(
                    name=f"structural.enum.{schema.name}.{col.name}",
                    status="fail",
                    message=(
                        f"{schema.name}.{col.name}: values outside enum "
                        f"{bad[:5]}"
                    ),
                    details={"bad_values": bad[:20]},
                )
            )

    # Numeric bounds.
    for col in schema.columns:
        if col.min_value is None and col.max_value is None:
            continue
        series = df[col.name].drop_nulls()
        if series.is_empty():
            continue
        if col.min_value is not None:
            bad_min = int((series < col.min_value).sum())
            if bad_min > 0:
                out.append(
                    CheckResult(
                        name=f"structural.min.{schema.name}.{col.name}",
                        status="fail",
                        message=(
                            f"{schema.name}.{col.name}: {bad_min} value(s) < "
                            f"{col.min_value}"
                        ),
                    )
                )
        if col.max_value is not None:
            bad_max = int((series > col.max_value).sum())
            if bad_max > 0:
                out.append(
                    CheckResult(
                        name=f"structural.max.{schema.name}.{col.name}",
                        status="fail",
                        message=(
                            f"{schema.name}.{col.name}: {bad_max} value(s) > "
                            f"{col.max_value}"
                        ),
                    )
                )

    return out
