"""Table schema definitions for all 16 EduTrace-Open tables.

Each :class:`TableSchema` enumerates:
* column name
* logical dtype
* nullable flag
* whether the column is a primary key or a foreign key
* whether it must be unique
* for enum columns, the valid value set

These are consumed by:
* Validators (structure, relational, temporal).
* Exporters (to coerce dtypes).
* Data dictionary (Phase 11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edutrace.schemas.common import (
    DTYPE_BOOL,
    DTYPE_DATETIME,
    DTYPE_FLOAT,
    DTYPE_INT,
    DTYPE_STR,
    ENUM_REGISTRY,
)


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    dtype: str
    nullable: bool = False
    primary_key: bool = False
    unique: bool = False
    foreign_key: tuple[str, str] | None = None  # (table, column)
    enum_values: tuple[str, ...] | None = None
    min_value: float | None = None
    max_value: float | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.primary_key and self.nullable:
            raise ValueError(f"Primary key {self.name} cannot be nullable")
        if self.enum_values is not None and self.dtype != DTYPE_STR:
            raise ValueError(f"Enum column {self.name} must be a string dtype")


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: tuple[ColumnSpec, ...] = field(default_factory=tuple)
    description: str = ""

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns)

    @property
    def primary_key(self) -> str:
        for c in self.columns:
            if c.primary_key:
                return c.name
        raise ValueError(f"Table {self.name} has no primary key")

    @property
    def foreign_keys(self) -> tuple[ColumnSpec, ...]:
        return tuple(c for c in self.columns if c.foreign_key is not None)


# ---------------------------------------------------------------------------
# Institutional and academic structure
# ---------------------------------------------------------------------------

INSTITUTION = TableSchema(
    name="institution",
    description="Synthetic higher-education institutions.",
    columns=(
        ColumnSpec("institution_id", DTYPE_STR, primary_key=True, unique=True,
                   description="Stable ID, e.g. inst_00000001"),
        ColumnSpec("institution_type", DTYPE_STR, nullable=False,
                   description="Simulated institution type."),
        ColumnSpec("country", DTYPE_STR),
        ColumnSpec("region", DTYPE_STR),
        ColumnSpec("academic_calendar", DTYPE_STR,
                   description="Free-form calendar description."),
        ColumnSpec("timezone", DTYPE_STR),
    ),
)

PROGRAMME = TableSchema(
    name="programme",
    description="Academic programmes delivered by institutions.",
    columns=(
        ColumnSpec("programme_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("institution_id", DTYPE_STR,
                   foreign_key=("institution", "institution_id")),
        ColumnSpec("programme_name", DTYPE_STR),
        ColumnSpec("qualification_level", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["qualification_level"]),
        ColumnSpec("duration_semesters", DTYPE_INT, min_value=1),
        ColumnSpec("discipline", DTYPE_STR),
        ColumnSpec("total_credits", DTYPE_INT, min_value=1),
    ),
)

COURSE = TableSchema(
    name="course",
    description="Courses belonging to programmes.",
    columns=(
        ColumnSpec("course_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("programme_id", DTYPE_STR,
                   foreign_key=("programme", "programme_id")),
        ColumnSpec("course_code", DTYPE_STR, unique=True),
        ColumnSpec("course_name", DTYPE_STR),
        ColumnSpec("credit_value", DTYPE_INT, min_value=1),
        ColumnSpec("semester", DTYPE_INT, min_value=1),
        ColumnSpec("difficulty_level", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("course_type", DTYPE_STR, enum_values=ENUM_REGISTRY["course_type"]),
    ),
)

MODULE = TableSchema(
    name="module",
    description="Modules (weeks/topics) within courses.",
    columns=(
        ColumnSpec("module_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("course_id", DTYPE_STR, foreign_key=("course", "course_id")),
        ColumnSpec("module_name", DTYPE_STR),
        ColumnSpec("module_sequence", DTYPE_INT, min_value=1),
        ColumnSpec("learning_objectives", DTYPE_STR),
        ColumnSpec("estimated_learning_hours", DTYPE_FLOAT, min_value=0.0),
    ),
)

CURRICULUM_DEPENDENCY = TableSchema(
    name="curriculum_dependency",
    description="Directed dependencies between modules.",
    columns=(
        ColumnSpec("dependency_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("predecessor_module_id", DTYPE_STR,
                   foreign_key=("module", "module_id")),
        ColumnSpec("successor_module_id", DTYPE_STR,
                   foreign_key=("module", "module_id")),
        ColumnSpec("dependency_type", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["dependency_type"]),
        ColumnSpec("dependency_strength", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
    ),
)

# ---------------------------------------------------------------------------
# Learner and enrolment
# ---------------------------------------------------------------------------

LEARNER = TableSchema(
    name="learner",
    description="Synthetic learners. Contains no real identifiers.",
    columns=(
        ColumnSpec("learner_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("synthetic_cohort_id", DTYPE_STR),
        ColumnSpec("admission_year", DTYPE_INT, min_value=1990, max_value=2100),
        ColumnSpec("entry_pathway", DTYPE_STR),
        ColumnSpec("study_mode", DTYPE_STR, enum_values=ENUM_REGISTRY["study_mode"]),
        ColumnSpec("programme_id", DTYPE_STR,
                   foreign_key=("programme", "programme_id")),
        ColumnSpec("baseline_preparedness", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("initial_engagement_profile", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("synthetic_learning_preference", DTYPE_STR),
    ),
)

ENROLMENT = TableSchema(
    name="enrolment",
    description="Learner-course enrolments per semester.",
    columns=(
        ColumnSpec("enrolment_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("learner_id", DTYPE_STR, foreign_key=("learner", "learner_id")),
        ColumnSpec("course_id", DTYPE_STR, foreign_key=("course", "course_id")),
        ColumnSpec("academic_year", DTYPE_INT, min_value=1),
        ColumnSpec("semester", DTYPE_INT, min_value=1),
        ColumnSpec("enrolment_date", DTYPE_DATETIME),
        ColumnSpec("completion_date", DTYPE_DATETIME, nullable=True),
        ColumnSpec("enrolment_status", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["enrolment_status"]),
        ColumnSpec("final_grade", DTYPE_FLOAT, nullable=True, min_value=0.0, max_value=100.0),
        ColumnSpec("completion_status", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["completion_status"]),
    ),
)

# ---------------------------------------------------------------------------
# Learning resources and events
# ---------------------------------------------------------------------------

LEARNING_RESOURCE = TableSchema(
    name="learning_resource",
    description="Learning materials attached to modules.",
    columns=(
        ColumnSpec("resource_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("course_id", DTYPE_STR, foreign_key=("course", "course_id")),
        ColumnSpec("module_id", DTYPE_STR, foreign_key=("module", "module_id")),
        ColumnSpec("resource_type", DTYPE_STR, enum_values=ENUM_REGISTRY["resource_type"]),
        ColumnSpec("resource_format", DTYPE_STR, enum_values=ENUM_REGISTRY["resource_format"]),
        ColumnSpec("difficulty_level", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("estimated_duration", DTYPE_FLOAT, min_value=0.0),
        ColumnSpec("accessibility_features", DTYPE_STR),
        ColumnSpec("publication_sequence", DTYPE_INT, min_value=1),
    ),
)

LEARNING_EVENT = TableSchema(
    name="learning_event",
    description="Timestamped LMS interaction events.",
    columns=(
        ColumnSpec("event_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("learner_id", DTYPE_STR, foreign_key=("learner", "learner_id")),
        ColumnSpec("enrolment_id", DTYPE_STR, foreign_key=("enrolment", "enrolment_id")),
        ColumnSpec("course_id", DTYPE_STR, foreign_key=("course", "course_id")),
        ColumnSpec("module_id", DTYPE_STR, foreign_key=("module", "module_id")),
        ColumnSpec("resource_id", DTYPE_STR, nullable=True,
                   foreign_key=("learning_resource", "resource_id")),
        ColumnSpec("event_timestamp", DTYPE_DATETIME),
        ColumnSpec("event_type", DTYPE_STR, enum_values=ENUM_REGISTRY["event_type"]),
        ColumnSpec("event_duration_seconds", DTYPE_INT, min_value=0),
        ColumnSpec("interaction_channel", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["interaction_channel"]),
        ColumnSpec("completion_flag", DTYPE_BOOL),
        ColumnSpec("event_sequence", DTYPE_INT, min_value=1),
    ),
)

# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------

ASSESSMENT_ITEM = TableSchema(
    name="assessment_item",
    description="Assessable items within modules.",
    columns=(
        ColumnSpec("assessment_item_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("course_id", DTYPE_STR, foreign_key=("course", "course_id")),
        ColumnSpec("module_id", DTYPE_STR, foreign_key=("module", "module_id")),
        ColumnSpec("assessment_type", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["assessment_type"]),
        ColumnSpec("difficulty", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("maximum_score", DTYPE_FLOAT, min_value=1.0),
        ColumnSpec("weight", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("learning_objective_id", DTYPE_STR),
    ),
)

ASSESSMENT_ATTEMPT = TableSchema(
    name="assessment_attempt",
    description="Learner attempts at assessment items.",
    columns=(
        ColumnSpec("attempt_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("learner_id", DTYPE_STR, foreign_key=("learner", "learner_id")),
        ColumnSpec("enrolment_id", DTYPE_STR, foreign_key=("enrolment", "enrolment_id")),
        ColumnSpec("assessment_item_id", DTYPE_STR,
                   foreign_key=("assessment_item", "assessment_item_id")),
        ColumnSpec("attempt_number", DTYPE_INT, min_value=1),
        ColumnSpec("attempt_timestamp", DTYPE_DATETIME),
        ColumnSpec("score", DTYPE_FLOAT, min_value=0.0),
        ColumnSpec("maximum_score", DTYPE_FLOAT, min_value=1.0),
        ColumnSpec("duration_seconds", DTYPE_INT, min_value=0),
        ColumnSpec("submission_status", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["submission_status"]),
        ColumnSpec("late_submission_flag", DTYPE_BOOL),
    ),
)

FEEDBACK_EVENT = TableSchema(
    name="feedback_event",
    description="Feedback issued on attempts.",
    columns=(
        ColumnSpec("feedback_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("attempt_id", DTYPE_STR,
                   foreign_key=("assessment_attempt", "attempt_id")),
        ColumnSpec("learner_id", DTYPE_STR, foreign_key=("learner", "learner_id")),
        ColumnSpec("feedback_timestamp", DTYPE_DATETIME),
        ColumnSpec("feedback_type", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["feedback_type"]),
        ColumnSpec("feedback_delay_hours", DTYPE_FLOAT, min_value=0.0),
        ColumnSpec("feedback_viewed", DTYPE_BOOL),
        ColumnSpec("revision_flag", DTYPE_BOOL),
    ),
)

# ---------------------------------------------------------------------------
# Weekly engagement
# ---------------------------------------------------------------------------

WEEKLY_ENGAGEMENT = TableSchema(
    name="weekly_engagement",
    description="Per-learner, per-course, per-week aggregates.",
    columns=(
        ColumnSpec("weekly_record_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("learner_id", DTYPE_STR, foreign_key=("learner", "learner_id")),
        ColumnSpec("course_id", DTYPE_STR, foreign_key=("course", "course_id")),
        ColumnSpec("academic_week", DTYPE_INT, min_value=1),
        ColumnSpec("week_start_date", DTYPE_DATETIME),
        ColumnSpec("login_count", DTYPE_INT, min_value=0),
        ColumnSpec("active_days", DTYPE_INT, min_value=0, max_value=7),
        ColumnSpec("resource_access_count", DTYPE_INT, min_value=0),
        ColumnSpec("total_learning_minutes", DTYPE_FLOAT, min_value=0.0),
        ColumnSpec("assessment_attempt_count", DTYPE_INT, min_value=0),
        ColumnSpec("discussion_activity_count", DTYPE_INT, min_value=0),
        ColumnSpec("engagement_score", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("trajectory_state", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["trajectory_state"]),
    ),
)

# ---------------------------------------------------------------------------
# Progression and support
# ---------------------------------------------------------------------------

PROGRESSION_EVENT = TableSchema(
    name="progression_event",
    description="Semester-end and course-completion progression records.",
    columns=(
        ColumnSpec("progression_event_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("learner_id", DTYPE_STR, foreign_key=("learner", "learner_id")),
        ColumnSpec("programme_id", DTYPE_STR, foreign_key=("programme", "programme_id")),
        ColumnSpec("event_timestamp", DTYPE_DATETIME),
        ColumnSpec("progression_type", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["progression_type"]),
        ColumnSpec("semester_number", DTYPE_INT, min_value=1),
        ColumnSpec("academic_standing", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["academic_standing"]),
        ColumnSpec("credits_attempted", DTYPE_INT, min_value=0),
        ColumnSpec("credits_earned", DTYPE_INT, min_value=0),
        ColumnSpec("progression_outcome", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["progression_outcome"]),
    ),
)

DIGITAL_ACCESS = TableSchema(
    name="digital_access",
    description="Simulated digital-access conditions per learner.",
    columns=(
        ColumnSpec("access_record_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("learner_id", DTYPE_STR, foreign_key=("learner", "learner_id")),
        ColumnSpec("observation_period", DTYPE_STR),
        ColumnSpec("device_category", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["device_category"]),
        ColumnSpec("connectivity_category", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["connectivity_category"]),
        ColumnSpec("bandwidth_category", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["bandwidth_category"]),
        ColumnSpec("access_reliability", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("offline_access_usage", DTYPE_FLOAT, min_value=0.0, max_value=1.0),
        ColumnSpec("accessibility_support_usage", DTYPE_BOOL),
        ColumnSpec("access_constraint_level", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["access_constraint_level"]),
    ),
)

SUPPORT_EVENT = TableSchema(
    name="support_event",
    description="Synthetic academic-support interventions.",
    columns=(
        ColumnSpec("support_event_id", DTYPE_STR, primary_key=True, unique=True),
        ColumnSpec("learner_id", DTYPE_STR, foreign_key=("learner", "learner_id")),
        ColumnSpec("course_id", DTYPE_STR, nullable=True,
                   foreign_key=("course", "course_id")),
        ColumnSpec("intervention_timestamp", DTYPE_DATETIME),
        ColumnSpec("intervention_type", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["intervention_type"]),
        ColumnSpec("intervention_trigger", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["intervention_trigger"]),
        ColumnSpec("support_channel", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["support_channel"]),
        ColumnSpec("response_status", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["response_status"]),
        ColumnSpec("followup_required", DTYPE_BOOL),
        ColumnSpec("intervention_outcome", DTYPE_STR,
                   enum_values=ENUM_REGISTRY["intervention_outcome"]),
    ),
)


# ---------------------------------------------------------------------------
# Registry and helpers
# ---------------------------------------------------------------------------

ALL_TABLES: tuple[TableSchema, ...] = (
    INSTITUTION,
    PROGRAMME,
    COURSE,
    MODULE,
    CURRICULUM_DEPENDENCY,
    LEARNER,
    ENROLMENT,
    LEARNING_RESOURCE,
    LEARNING_EVENT,
    ASSESSMENT_ITEM,
    ASSESSMENT_ATTEMPT,
    FEEDBACK_EVENT,
    WEEKLY_ENGAGEMENT,
    PROGRESSION_EVENT,
    DIGITAL_ACCESS,
    SUPPORT_EVENT,
)

TABLE_SCHEMAS: dict[str, TableSchema] = {t.name: t for t in ALL_TABLES}


def get_schema(name: str) -> TableSchema:
    """Return the :class:`TableSchema` for ``name``."""
    try:
        return TABLE_SCHEMAS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown table: {name!r}") from exc


def validate_row(table: str, row: dict[str, Any]) -> None:
    """Validate a single row dict against a table schema.

    Intended for tests and small-data checks; do not call per-row for large
    generations. Raises :class:`ValueError` on the first violation found.
    """
    schema = get_schema(table)
    expected = set(schema.column_names)
    actual = set(row.keys())
    missing = expected - actual
    extra = actual - expected
    if missing:
        raise ValueError(f"{table}: missing columns {sorted(missing)}")
    if extra:
        raise ValueError(f"{table}: unexpected columns {sorted(extra)}")

    for col in schema.columns:
        value = row[col.name]
        if value is None or (isinstance(value, float) and value != value):  # NaN
            if not col.nullable:
                raise ValueError(f"{table}.{col.name}: null not allowed")
            continue
        if col.enum_values is not None and value not in col.enum_values:
            raise ValueError(
                f"{table}.{col.name}: value {value!r} not in allowed set"
            )
        if col.min_value is not None and value < col.min_value:
            raise ValueError(
                f"{table}.{col.name}: {value} < min {col.min_value}"
            )
        if col.max_value is not None and value > col.max_value:
            raise ValueError(
                f"{table}.{col.name}: {value} > max {col.max_value}"
            )
