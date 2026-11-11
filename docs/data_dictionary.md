# Data Dictionary

Every EduTrace-Open table has:
* **primary key** — a stable `prefix_<8-digit-int>` identifier,
* **foreign keys** — declared in `schemas/tables.py` and enforced by the relational validator,
* **column types** — logical types listed below; the physical dtypes are Polars (`Utf8`, `Int64`, `Float64`, `Boolean`, `Datetime("us")`).

All datetimes are timezone-naive and expressed in the configured `project.timezone` (default `Asia/Kolkata`).

## institutional/institution

Synthetic higher-education institutions.

| Column | Type | Notes |
|---|---|---|
| institution_id | string | PK. `inst_<N>`. |
| institution_type | string | One of `university`, `polytechnic`, `liberal_arts_college`, `technical_institute`. |
| country | string | Simulated country code. |
| region | string | Simulated region label. |
| academic_calendar | string | Free-form description of the calendar. |
| timezone | string | IANA timezone. |

## institutional/programme

| Column | Type | Notes |
|---|---|---|
| programme_id | string | PK. `prog_<N>`. |
| institution_id | string | FK → institution. |
| programme_name | string | Synthesised name from discipline + level. |
| qualification_level | string | One of `undergraduate`, `postgraduate`, `doctoral`. |
| duration_semesters | int | 6 or 8 (assumption). |
| discipline | string | One of 12 predefined disciplines. |
| total_credits | int | `duration_semesters * 20`. |

## academic/course

| Column | Type | Notes |
|---|---|---|
| course_id | string | PK. `crs_<N>`. |
| programme_id | string | FK → programme. |
| course_code | string | Unique. `C<semester*100 + n>`. |
| course_name | string | |
| credit_value | int | 3 or 4. |
| semester | int | Within-programme sequence index (1..N). |
| difficulty_level | float | 0..1. |
| course_type | string | `core`, `elective`, `lab`, `seminar`. |

## academic/module

| Column | Type | Notes |
|---|---|---|
| module_id | string | PK. `mod_<N>`. |
| course_id | string | FK → course. |
| module_name | string | |
| module_sequence | int | 1..num_modules_per_course. |
| learning_objectives | string | Free text. |
| estimated_learning_hours | float | Gamma-shaped; later sequences higher. |

## academic/curriculum_dependency

| Column | Type | Notes |
|---|---|---|
| dependency_id | string | PK. `dep_<N>`. |
| predecessor_module_id | string | FK → module. |
| successor_module_id | string | FK → module. |
| dependency_type | string | `prerequisite`, `co_requisite`, `recommended`. |
| dependency_strength | float | 0..1. |

## learners/learner

| Column | Type | Notes |
|---|---|---|
| learner_id | string | PK. `lrn_<N>`. |
| synthetic_cohort_id | string | `coh_<year>_<programme_id>`. |
| admission_year | int | Simulated. |
| entry_pathway | string | `standard_admission`, `transfer`, `mature_entry`, `international`, `scholarship`. |
| study_mode | string | `full_time`, `part_time`, `online`. |
| programme_id | string | FK → programme. |
| baseline_preparedness | float | 0..1. Beta(2,2). |
| initial_engagement_profile | float | 0..1. Beta(2,2). |
| synthetic_learning_preference | string | `video_first`, `reading_first`, `interactive_first`, `discussion_first`. |

## learners/enrolment

| Column | Type | Notes |
|---|---|---|
| enrolment_id | string | PK. `enr_<N>`. |
| learner_id | string | FK → learner. |
| course_id | string | FK → course. |
| academic_year | int | Admission year + offset. |
| semester | int | Within-year (1 or 2). |
| enrolment_date | datetime | Semester start. |
| completion_date | datetime | Null for withdrawn / incomplete. Populated from best attempt timestamps. |
| enrolment_status | string | `active`, `completed`, `withdrawn`, `failed`. |
| final_grade | float | Weighted mean of best per-item scores (0..100). Null when not attempted. |
| completion_status | string | `in_progress`, `completed`, `not_completed`. |

## learning/learning_resource

| Column | Type | Notes |
|---|---|---|
| resource_id | string | PK. `res_<N>`. |
| course_id | string | FK → course. |
| module_id | string | FK → module. |
| resource_type | string | One of 8 resource types. |
| resource_format | string | Format constrained by type. |
| difficulty_level | float | Inherits from module difficulty ± noise. |
| estimated_duration | float | Minutes (approx.). |
| accessibility_features | string | Semicolon-separated flags. |
| publication_sequence | int | 1..N within module. |

## learning/learning_event

The largest table by row count.

| Column | Type | Notes |
|---|---|---|
| event_id | string | PK. `evt_<N>`. |
| learner_id | string | FK → learner. |
| enrolment_id | string | FK → enrolment. |
| course_id | string | FK → course. |
| module_id | string | FK → module. |
| resource_id | string | FK → learning_resource. Nullable. |
| event_timestamp | datetime | Within the enrolment's semester. |
| event_type | string | One of 18 event types. |
| event_duration_seconds | int | 0 for instantaneous events. |
| interaction_channel | string | `web`, `mobile`, `tablet`, `desktop_app`, `api`. |
| completion_flag | bool | True for completion-representing events. |
| event_sequence | int | Within learner-week. |

## assessment/assessment_item

| Column | Type | Notes |
|---|---|---|
| assessment_item_id | string | PK. `asit_<N>`. |
| course_id | string | FK → course. |
| module_id | string | FK → module. |
| assessment_type | string | `quiz`, `formative_check`, `assignment`, `exam`. |
| difficulty | float | 0..1. |
| maximum_score | float | 10 or 100. |
| weight | float | Normalised per module, sums to 1. |
| learning_objective_id | string | Free text `LO_<module_id>_<k>`. |

## assessment/assessment_attempt

| Column | Type | Notes |
|---|---|---|
| attempt_id | string | PK. `att_<N>`. |
| learner_id | string | FK → learner. |
| enrolment_id | string | FK → enrolment. |
| assessment_item_id | string | FK → assessment_item. |
| attempt_number | int | 1..3 for assignments; 1 otherwise. |
| attempt_timestamp | datetime | Within module's week. |
| score | float | 0..maximum_score. |
| maximum_score | float | Same as the item's maximum_score. |
| duration_seconds | int | Sample from type-dependent gamma. |
| submission_status | string | `graded`, `submitted`, `draft`, `missed`. |
| late_submission_flag | bool | True for late assignments. |

## assessment/feedback_event

| Column | Type | Notes |
|---|---|---|
| feedback_id | string | PK. `fbk_<N>`. |
| attempt_id | string | FK → assessment_attempt. |
| learner_id | string | FK → learner. |
| feedback_timestamp | datetime | Attempt timestamp + delay. |
| feedback_type | string | `auto`, `instructor`, `peer`, `rubric`. |
| feedback_delay_hours | float | Log-normal per type. |
| feedback_viewed | bool | Bernoulli of learner engagement + delay. |
| revision_flag | bool | Bernoulli of (1 - score_fraction) * viewed. |

## learning/weekly_engagement

Aggregated from `learning_event` per (learner, course, academic_week).

| Column | Type | Notes |
|---|---|---|
| weekly_record_id | string | PK. `wk_<N>`. |
| learner_id | string | FK → learner. |
| course_id | string | FK → course. |
| academic_week | int | 1..N. |
| week_start_date | datetime | Monday-aligned. |
| login_count | int | Events of type `login`. |
| active_days | int | Distinct event days. |
| resource_access_count | int | Resource-view events. |
| total_learning_minutes | float | Sum of event durations / 60. |
| assessment_attempt_count | int | Quiz/assignment submits. |
| discussion_activity_count | int | Discussion events. |
| engagement_score | float | `min(1, count / (2·λ))`. |
| trajectory_state | string | `thriving`, `steady`, `at_risk`, `disengaged`. |

## learners/progression_event

One row per (learner, semester).

| Column | Type | Notes |
|---|---|---|
| progression_event_id | string | PK. `prg_<N>`. |
| learner_id | string | FK → learner. |
| programme_id | string | FK → programme. |
| event_timestamp | datetime | Semester end date at 18:00. |
| progression_type | string | `semester_end`, `course_completion`, `probation_review`, `programme_exit`. |
| semester_number | int | Within-programme. |
| academic_standing | string | `good`, `warning`, `probation`, `dismissed`. |
| credits_attempted | int | Sum of credits in that semester. |
| credits_earned | int | Sum of credits for completed enrolments. |
| progression_outcome | string | `advanced`, `conditional`, `repeated`, `withdrawn`. |

## accessibility/digital_access

One row per (learner, academic year).

| Column | Type | Notes |
|---|---|---|
| access_record_id | string | PK. `acc_<N>`. |
| learner_id | string | FK → learner. |
| observation_period | string | `AY<year>`. |
| device_category | string | `laptop`, `desktop`, `tablet`, `smartphone`, `shared_device`. |
| connectivity_category | string | `broadband`, `mobile_data`, `satellite`, `intermittent`. |
| bandwidth_category | string | `high`, `medium`, `low`. |
| access_reliability | float | 0..1. Derived from categories + noise. |
| offline_access_usage | float | 0..1. |
| accessibility_support_usage | bool | |
| access_constraint_level | string | `none`, `mild`, `moderate`, `severe`. |

## interventions/support_event

| Column | Type | Notes |
|---|---|---|
| support_event_id | string | PK. `sup_<N>`. |
| learner_id | string | FK → learner. |
| course_id | string | FK → course. Nullable. |
| intervention_timestamp | datetime | ~week 10 of the semester ± jitter. |
| intervention_type | string | One of 6 types. |
| intervention_trigger | string | `low_engagement`, `missed_assessment`, `low_score`, `self_referral`, `staff_referral`. |
| support_channel | string | `in_person`, `video_call`, `email`, `lms_message`, `phone`. |
| response_status | string | `accepted`, `pending`, `declined`, `no_response`. |
| followup_required | bool | |
| intervention_outcome | string | `improved`, `no_change`, `worsened`, `ongoing`. |
