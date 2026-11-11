"""Shared type aliases and enums used across schema definitions."""

from __future__ import annotations

from edutrace.constants import (
    AcademicStanding,
    AccessConstraintLevel,
    AssessmentType,
    BandwidthCategory,
    CompletionStatus,
    ConnectivityCategory,
    CourseType,
    DependencyType,
    DeviceCategory,
    EnrolmentStatus,
    EventType,
    FeedbackType,
    InteractionChannel,
    InterventionOutcome,
    InterventionTrigger,
    InterventionType,
    ProgressionOutcome,
    ProgressionType,
    QualificationLevel,
    ResourceFormat,
    ResourceType,
    ResponseStatus,
    StudyMode,
    SubmissionStatus,
    SupportChannel,
    TrajectoryState,
)

# Logical dtypes used in ColumnSpec. Maps to the actual storage dtype in
# exporters and validators.
DTYPE_STR = "string"
DTYPE_INT = "int64"
DTYPE_FLOAT = "float64"
DTYPE_BOOL = "bool"
DTYPE_DATETIME = "datetime64[ns]"

ENUM_REGISTRY: dict[str, tuple[str, ...]] = {
    "event_type": tuple(e.value for e in EventType),
    "interaction_channel": tuple(e.value for e in InteractionChannel),
    "enrolment_status": tuple(e.value for e in EnrolmentStatus),
    "completion_status": tuple(e.value for e in CompletionStatus),
    "resource_type": tuple(e.value for e in ResourceType),
    "resource_format": tuple(e.value for e in ResourceFormat),
    "assessment_type": tuple(e.value for e in AssessmentType),
    "submission_status": tuple(e.value for e in SubmissionStatus),
    "feedback_type": tuple(e.value for e in FeedbackType),
    "trajectory_state": tuple(e.value for e in TrajectoryState),
    "progression_type": tuple(e.value for e in ProgressionType),
    "academic_standing": tuple(e.value for e in AcademicStanding),
    "progression_outcome": tuple(e.value for e in ProgressionOutcome),
    "intervention_type": tuple(e.value for e in InterventionType),
    "intervention_trigger": tuple(e.value for e in InterventionTrigger),
    "support_channel": tuple(e.value for e in SupportChannel),
    "response_status": tuple(e.value for e in ResponseStatus),
    "intervention_outcome": tuple(e.value for e in InterventionOutcome),
    "device_category": tuple(e.value for e in DeviceCategory),
    "connectivity_category": tuple(e.value for e in ConnectivityCategory),
    "bandwidth_category": tuple(e.value for e in BandwidthCategory),
    "access_constraint_level": tuple(e.value for e in AccessConstraintLevel),
    "qualification_level": tuple(e.value for e in QualificationLevel),
    "study_mode": tuple(e.value for e in StudyMode),
    "course_type": tuple(e.value for e in CourseType),
    "dependency_type": tuple(e.value for e in DependencyType),
}


__all__ = [
    "DTYPE_STR",
    "DTYPE_INT",
    "DTYPE_FLOAT",
    "DTYPE_BOOL",
    "DTYPE_DATETIME",
    "ENUM_REGISTRY",
]
