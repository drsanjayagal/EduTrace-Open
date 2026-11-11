"""Central constants shared across the EduTrace-Open codebase.

This module centralises string literals and numeric limits so that schemas,
generators, and validators cannot drift apart. Any categorical value that
appears in a schema *must* be registered here.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Allowed learning-event types."""

    LOGIN = "login"
    LOGOUT = "logout"
    RESOURCE_VIEW = "resource_view"
    RESOURCE_DOWNLOAD = "resource_download"
    VIDEO_START = "video_start"
    VIDEO_PAUSE = "video_pause"
    VIDEO_COMPLETE = "video_complete"
    QUIZ_OPEN = "quiz_open"
    QUIZ_SUBMIT = "quiz_submit"
    ASSIGNMENT_VIEW = "assignment_view"
    ASSIGNMENT_SUBMIT = "assignment_submit"
    DISCUSSION_VIEW = "discussion_view"
    DISCUSSION_POST = "discussion_post"
    FORUM_REPLY = "forum_reply"
    MODULE_OPEN = "module_open"
    MODULE_COMPLETE = "module_complete"
    LEARNING_PATH_ACCESS = "learning_path_access"
    FEEDBACK_VIEW = "feedback_view"


ALL_EVENT_TYPES: Final[tuple[str, ...]] = tuple(e.value for e in EventType)


class InteractionChannel(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP_APP = "desktop_app"
    API = "api"


class EnrolmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"
    FAILED = "failed"


class CompletionStatus(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    NOT_COMPLETED = "not_completed"


class ResourceType(str, Enum):
    LECTURE_VIDEO = "lecture_video"
    READING = "reading"
    QUIZ = "quiz"
    ASSIGNMENT_BRIEF = "assignment_brief"
    SLIDE_DECK = "slide_deck"
    DATASET = "dataset"
    INTERACTIVE_EXERCISE = "interactive_exercise"
    DISCUSSION_THREAD = "discussion_thread"


class ResourceFormat(str, Enum):
    PDF = "pdf"
    VIDEO_MP4 = "video_mp4"
    HTML = "html"
    CSV = "csv"
    NOTEBOOK = "notebook"
    AUDIO = "audio"


class AssessmentType(str, Enum):
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    EXAM = "exam"
    PROJECT = "project"
    FORMATIVE_CHECK = "formative_check"


class SubmissionStatus(str, Enum):
    SUBMITTED = "submitted"
    DRAFT = "draft"
    MISSED = "missed"
    GRADED = "graded"


class FeedbackType(str, Enum):
    AUTO = "auto"
    INSTRUCTOR = "instructor"
    PEER = "peer"
    RUBRIC = "rubric"


class TrajectoryState(str, Enum):
    THRIVING = "thriving"
    STEADY = "steady"
    AT_RISK = "at_risk"
    DISENGAGED = "disengaged"


class ProgressionType(str, Enum):
    SEMESTER_END = "semester_end"
    COURSE_COMPLETION = "course_completion"
    PROBATION_REVIEW = "probation_review"
    PROGRAMME_EXIT = "programme_exit"


class AcademicStanding(str, Enum):
    GOOD = "good"
    WARNING = "warning"
    PROBATION = "probation"
    DISMISSED = "dismissed"


class ProgressionOutcome(str, Enum):
    ADVANCED = "advanced"
    CONDITIONAL = "conditional"
    REPEATED = "repeated"
    WITHDRAWN = "withdrawn"


class InterventionType(str, Enum):
    ADVISOR_MEETING = "advisor_meeting"
    TUTORING = "tutoring"
    WELLBEING_REFERRAL = "wellbeing_referral"
    EXTENSION_GRANTED = "extension_granted"
    ACCESSIBILITY_SUPPORT = "accessibility_support"
    AUTOMATED_NUDGE = "automated_nudge"


class InterventionTrigger(str, Enum):
    LOW_ENGAGEMENT = "low_engagement"
    MISSED_ASSESSMENT = "missed_assessment"
    LOW_SCORE = "low_score"
    SELF_REFERRAL = "self_referral"
    STAFF_REFERRAL = "staff_referral"


class SupportChannel(str, Enum):
    IN_PERSON = "in_person"
    VIDEO_CALL = "video_call"
    EMAIL = "email"
    LMS_MESSAGE = "lms_message"
    PHONE = "phone"


class ResponseStatus(str, Enum):
    ACCEPTED = "accepted"
    DECLINED = "declined"
    PENDING = "pending"
    NO_RESPONSE = "no_response"


class InterventionOutcome(str, Enum):
    IMPROVED = "improved"
    NO_CHANGE = "no_change"
    WORSENED = "worsened"
    ONGOING = "ongoing"


class DeviceCategory(str, Enum):
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    TABLET = "tablet"
    SMARTPHONE = "smartphone"
    SHARED_DEVICE = "shared_device"


class ConnectivityCategory(str, Enum):
    BROADBAND = "broadband"
    MOBILE_DATA = "mobile_data"
    SATELLITE = "satellite"
    INTERMITTENT = "intermittent"


class BandwidthCategory(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AccessConstraintLevel(str, Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class QualificationLevel(str, Enum):
    UNDERGRADUATE = "undergraduate"
    POSTGRADUATE = "postgraduate"
    DOCTORAL = "doctoral"


class StudyMode(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    ONLINE = "online"


class CourseType(str, Enum):
    CORE = "core"
    ELECTIVE = "elective"
    LAB = "lab"
    SEMINAR = "seminar"


class DependencyType(str, Enum):
    PREREQUISITE = "prerequisite"
    CO_REQUISITE = "co_requisite"
    RECOMMENDED = "recommended"


# ---------------------------------------------------------------------------
# Numeric limits and shared constants
# ---------------------------------------------------------------------------

MIN_SCORE: Final[float] = 0.0
MAX_SCORE: Final[float] = 100.0

TABLE_SEED_OFFSET: Final[int] = 0xE4_00_00
DEFAULT_RANDOM_SEED: Final[int] = 20261110

PASS_GRADE: Final[float] = 40.0


# ---------------------------------------------------------------------------
# Phase 2 additions: controlled vocabulary for structural choices
# ---------------------------------------------------------------------------

INSTITUTION_TYPES: Final[tuple[str, ...]] = (
    "university",
    "polytechnic",
    "liberal_arts_college",
    "technical_institute",
)

PROGRAMME_DISCIPLINES: Final[tuple[str, ...]] = (
    "computer_science",
    "data_science",
    "electrical_engineering",
    "mechanical_engineering",
    "civil_engineering",
    "business_administration",
    "economics",
    "psychology",
    "mathematics",
    "physics",
    "life_sciences",
    "education",
)

ENTRY_PATHWAYS: Final[tuple[str, ...]] = (
    "standard_admission",
    "transfer",
    "mature_entry",
    "international",
    "scholarship",
)

LEARNING_PREFERENCES: Final[tuple[str, ...]] = (
    "video_first",
    "reading_first",
    "interactive_first",
    "discussion_first",
)

REGIONS: Final[tuple[str, ...]] = (
    "north",
    "south",
    "east",
    "west",
    "central",
)

COUNTRIES: Final[tuple[str, ...]] = ("IN",)


# ---------------------------------------------------------------------------
# Phase 3 additions: behavioural model parameters
# ---------------------------------------------------------------------------

WEEKLY_ENGAGEMENT_MULTIPLIERS: Final[dict[str, float]] = {
    "very_early": 0.55,
    "early": 0.85,
    "mid": 1.00,
    "late": 0.90,
    "final": 0.40,
}

_EVENT_ORDER: Final[tuple[str, ...]] = ALL_EVENT_TYPES


def _weight_vector(**kw: float) -> tuple[float, ...]:
    """Build an event-weight vector aligned with ``_EVENT_ORDER``."""
    total = sum(kw.values())
    if total <= 0:
        raise ValueError("At least one weight must be positive")
    return tuple(kw.get(e, 0.0) / total for e in _EVENT_ORDER)


EVENT_TYPE_WEIGHTS_BY_PHASE: Final[dict[str, tuple[float, ...]]] = {
    "early": _weight_vector(
        login=0.06, logout=0.04, resource_view=0.16, resource_download=0.05,
        video_start=0.10, video_pause=0.05, video_complete=0.07,
        quiz_open=0.02, quiz_submit=0.01,
        assignment_view=0.08, assignment_submit=0.01,
        discussion_view=0.08, discussion_post=0.02, forum_reply=0.01,
        module_open=0.12, module_complete=0.03,
        learning_path_access=0.06, feedback_view=0.03,
    ),
    "mid": _weight_vector(
        login=0.06, logout=0.04, resource_view=0.15, resource_download=0.06,
        video_start=0.10, video_pause=0.06, video_complete=0.08,
        quiz_open=0.05, quiz_submit=0.04,
        assignment_view=0.06, assignment_submit=0.04,
        discussion_view=0.06, discussion_post=0.03, forum_reply=0.02,
        module_open=0.06, module_complete=0.03,
        learning_path_access=0.03, feedback_view=0.03,
    ),
    "late": _weight_vector(
        login=0.05, logout=0.03, resource_view=0.10, resource_download=0.05,
        video_start=0.08, video_pause=0.04, video_complete=0.06,
        quiz_open=0.08, quiz_submit=0.07,
        assignment_view=0.06, assignment_submit=0.10,
        discussion_view=0.04, discussion_post=0.02, forum_reply=0.01,
        module_open=0.06, module_complete=0.06,
        learning_path_access=0.04, feedback_view=0.05,
    ),
}

VIDEO_DURATION_RANGE: Final[tuple[int, int]] = (180, 1800)
READING_DURATION_RANGE: Final[tuple[int, int]] = (120, 900)
QUIZ_DURATION_RANGE: Final[tuple[int, int]] = (300, 1800)
OTHER_DURATION_RANGE: Final[tuple[int, int]] = (30, 600)

RESOURCE_TYPE_WEIGHTS: Final[dict[str, float]] = {
    "lecture_video": 0.35,
    "reading": 0.25,
    "slide_deck": 0.10,
    "quiz": 0.15,
    "assignment_brief": 0.10,
    "discussion_thread": 0.05,
}

RESOURCE_FORMAT_BY_TYPE: Final[dict[str, tuple[str, ...]]] = {
    "lecture_video": ("video_mp4",),
    "reading": ("pdf", "html"),
    "slide_deck": ("pdf", "html"),
    "quiz": ("html",),
    "assignment_brief": ("pdf", "html"),
    "discussion_thread": ("html",),
}

ASSESSMENT_TYPE_WEIGHTS: Final[dict[str, float]] = {
    "quiz": 0.50,
    "formative_check": 0.25,
    "assignment": 0.20,
    "exam": 0.05,
}

# -- Interaction-channel weights (single source of truth). -----------------
# Weighted categorical for the channel through which an event is recorded.
# Consumed by ``learning_event.py`` (via this module) and by
# ``simulation/temporal_models.py`` (which imports from here).

INTERACTION_CHANNEL_WEIGHTS: Final[dict[str, float]] = {
    "web": 0.40,
    "mobile": 0.35,
    "tablet": 0.10,
    "desktop_app": 0.13,
    "api": 0.02,
}


# ---------------------------------------------------------------------------
# Phase 4 additions: assessment and feedback model parameters
# ---------------------------------------------------------------------------

ATTEMPT_PROBABILITY_BY_TYPE: Final[dict[str, float]] = {
    "quiz": 1.00,
    "formative_check": 1.00,
    "assignment": 0.85,
    "exam": 0.95,
}

SCORE_MODEL: Final[dict[str, float]] = {
    "intercept": 0.55,
    "beta_preparedness": 2.10,
    "beta_engagement": 0.90,
    "beta_difficulty": 2.20,
    "beta_prior_attempts": 0.25,
    "noise_sd": 0.35,
}

LATE_SUBMISSION_BASE: Final[float] = 0.12

FEEDBACK_DELAY_LOG_NORMAL: Final[dict[str, dict[str, float]]] = {
    "auto":       {"mu": 0.30, "sigma": 0.60},
    "instructor": {"mu": 4.00, "sigma": 0.80},
    "peer":       {"mu": 3.20, "sigma": 0.90},
    "rubric":     {"mu": 2.50, "sigma": 0.70},
}

FEEDBACK_TYPE_WEIGHTS: Final[dict[str, float]] = {
    "auto": 0.45,
    "instructor": 0.35,
    "peer": 0.15,
    "rubric": 0.05,
}

SUBMISSION_STATUS_WEIGHTS: Final[dict[str, float]] = {
    "graded":    0.80,
    "submitted": 0.15,
    "draft":     0.03,
    "missed":    0.02,
}

ENROLMENT_COMPLETION_ATTEMPT_FRACTION: Final[float] = 0.50


# ---------------------------------------------------------------------------
# Phase 5 additions: digital access, progression, and intervention parameters
# ---------------------------------------------------------------------------

DEVICE_CATEGORY_WEIGHTS: Final[dict[str, float]] = {
    "laptop": 0.55,
    "desktop": 0.15,
    "tablet": 0.10,
    "smartphone": 0.15,
    "shared_device": 0.05,
}

CONNECTIVITY_CATEGORY_WEIGHTS: Final[dict[str, float]] = {
    "broadband": 0.60,
    "mobile_data": 0.25,
    "satellite": 0.05,
    "intermittent": 0.10,
}

BANDWIDTH_CATEGORY_WEIGHTS: Final[dict[str, float]] = {
    "high": 0.50,
    "medium": 0.35,
    "low": 0.15,
}

ACCESS_RELIABILITY_WEIGHTS: Final[dict[str, float]] = {
    "broadband": 0.90,
    "mobile_data": 0.65,
    "satellite": 0.50,
    "intermittent": 0.30,
    "high_bandwidth": 0.90,
    "medium_bandwidth": 0.65,
    "low_bandwidth": 0.35,
    "laptop": 0.85,
    "desktop": 0.90,
    "tablet": 0.65,
    "smartphone": 0.55,
    "shared_device": 0.35,
}

ACCESS_CONSTRAINT_THRESHOLDS: Final[tuple[tuple[str, float], ...]] = (
    ("severe", 0.30),
    ("moderate", 0.55),
    ("mild", 0.75),
    ("none", 1.01),
)

STANDING_GPA_WARNING: Final[float] = 5.0
STANDING_GPA_PROBATION: Final[float] = 4.0
STANDING_GPA_DISMISSED: Final[float] = 2.0

GRADE_POINT_DIVISOR: Final[float] = 10.0

INTERVENTION_TYPE_BY_TRIGGER: Final[dict[str, dict[str, float]]] = {
    "low_engagement": {
        "advisor_meeting": 0.40,
        "tutoring": 0.25,
        "automated_nudge": 0.25,
        "wellbeing_referral": 0.10,
    },
    "missed_assessment": {
        "advisor_meeting": 0.35,
        "extension_granted": 0.35,
        "tutoring": 0.20,
        "automated_nudge": 0.10,
    },
    "low_score": {
        "tutoring": 0.40,
        "advisor_meeting": 0.35,
        "accessibility_support": 0.15,
        "wellbeing_referral": 0.10,
    },
    "self_referral": {
        "advisor_meeting": 0.40,
        "wellbeing_referral": 0.30,
        "accessibility_support": 0.20,
        "tutoring": 0.10,
    },
    "staff_referral": {
        "advisor_meeting": 0.45,
        "tutoring": 0.30,
        "accessibility_support": 0.15,
        "wellbeing_referral": 0.10,
    },
}

SUPPORT_CHANNEL_WEIGHTS: Final[dict[str, float]] = {
    "in_person": 0.30,
    "video_call": 0.25,
    "email": 0.25,
    "lms_message": 0.15,
    "phone": 0.05,
}

RESPONSE_STATUS_WEIGHTS: Final[dict[str, float]] = {
    "accepted": 0.55,
    "pending": 0.20,
    "declined": 0.10,
    "no_response": 0.15,
}

INTERVENTION_OUTCOME_WEIGHTS: Final[dict[str, float]] = {
    "improved": 0.55,
    "no_change": 0.30,
    "worsened": 0.10,
    "ongoing": 0.05,
}

RISK_ENGAGEMENT_THRESHOLD: Final[float] = 0.30
RISK_GRADE_THRESHOLD: Final[float] = 45.0
MISSED_ITEM_FRACTION_THRESHOLD: Final[float] = 0.40
