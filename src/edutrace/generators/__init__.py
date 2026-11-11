"""Generator functions for every EduTrace-Open table."""

from __future__ import annotations

from edutrace.generators.assessment import generate_assessment_items
from edutrace.generators.attempt import generate_attempts_for_chunk
from edutrace.generators.course import generate_courses
from edutrace.generators.curriculum import generate_curriculum_dependencies
from edutrace.generators.digital_access import generate_digital_access
from edutrace.generators.enrolment import (
    generate_enrolments,
    populate_enrolment_outcomes,
)
from edutrace.generators.feedback import generate_feedback_for_chunk
from edutrace.generators.institution import generate_institutions
from edutrace.generators.learner import generate_learners
from edutrace.generators.learning_event import generate_learning_events_for_chunk
from edutrace.generators.module import generate_modules
from edutrace.generators.programme import generate_programmes
from edutrace.generators.progression import generate_progression_events
from edutrace.generators.resource import generate_resources
from edutrace.generators.support_intervention import generate_support_events
from edutrace.generators.weekly_engagement import generate_weekly_engagement

__all__ = [
    "generate_institutions",
    "generate_programmes",
    "generate_courses",
    "generate_modules",
    "generate_curriculum_dependencies",
    "generate_learners",
    "generate_enrolments",
    "populate_enrolment_outcomes",
    "generate_resources",
    "generate_assessment_items",
    "generate_learning_events_for_chunk",
    "generate_attempts_for_chunk",
    "generate_feedback_for_chunk",
    "generate_weekly_engagement",
    "generate_progression_events",
    "generate_digital_access",
    "generate_support_events",
]
