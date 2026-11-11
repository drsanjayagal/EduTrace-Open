# Simulation Assumptions

Every behavioural relationship below is a **modelling assumption**, not an empirical claim. The dataset is synthetic; findings computed from it reflect these assumptions, not real education.

## Structural assumptions

| Assumption | Location | Value |
|---|---|---|
| Institution type distribution | `institution.py` | (0.35, 0.25, 0.15, 0.25) |
| Region distribution | `institution.py` | (0.20, 0.25, 0.20, 0.20, 0.15) |
| Discipline pool | `constants.PROGRAMME_DISCIPLINES` | 12 disciplines |
| Programme duration choice | `programme.py` | 6 or 8 semesters, (0.55, 0.45) |
| Credits per semester | `programme.py` | 20 |
| Course type distribution | `course.py` | (0.55, 0.25, 0.15, 0.05) |
| Course difficulty | `course.py` | Beta(2.5, 2.0) + semester bias |
| Credits per course | `course.py` | 4 (core/elective), 3 (lab/seminar) |
| Module learning hours | `module.py` | Gamma(3, 4) + 2·(seq−1) |

## Learner assumptions

| Assumption | Location | Value |
|---|---|---|
| Preparedness | `learner.py` | Beta(2, 2) |
| Initial engagement | `learner.py` | Beta(2, 2) |
| Learning preference | `learner.py` | (0.45, 0.25, 0.20, 0.10) |
| Entry pathway | `learner.py` | (0.70, 0.10, 0.08, 0.07, 0.05) |
| Study mode | `learner.py` | (0.70, 0.20, 0.10) |

## Enrolment assumptions

| Assumption | Location | Value |
|---|---|---|
| Elective take probability | `enrolment.py` | 0.75 |
| Withdrawal probability | `enrolment.py` | `0.15 · (1 − preparedness)` |
| Enrolment filter by course semester | `enrolment.py` | Only courses whose `semester` = the learner's within-programme semester |

## Learning-resource assumptions

| Assumption | Location | Value |
|---|---|---|
| Resource type weights | `constants.RESOURCE_TYPE_WEIGHTS` | (video 35%, reading 25%, slides 10%, quiz 15%, brief 10%, discussion 5%) |
| Difficulty inheritance | `resource.py` | Parent difficulty ± N(0, 0.05) |
| Accessibility feature rates | `resource.py` | caption 55%, transcript 45%, alt_text 35%, screen_reader 20% (independent) |

## Learning-event assumptions

| Assumption | Location | Value |
|---|---|---|
| Base event rate | `behavioural_models.py` | `mean_events_per_learner_week · (0.6 + 0.8 · engagement)` |
| Weekly event count | `behavioural_models.py` | Poisson(λ · weekly_multiplier) |
| Weekly multiplier | `constants.WEEKLY_ENGAGEMENT_MULTIPLIERS` | early 0.55, mid 1.00, final 0.40 |
| Event type weights | `constants.EVENT_TYPE_WEIGHTS_BY_PHASE` | Phase-dependent (early/mid/late) |
| Channel weights | `temporal_models.INTERACTION_CHANNEL_WEIGHTS` | web 40%, mobile 35%, tablet 10%, desktop 13%, api 2% |
| Hour-of-day profile | `temporal_models._*_HOURS` | Per-channel 24-vector |
| Duration ranges | `constants.*_DURATION_RANGE` | Per type |
| Engagement evolution | `behavioural_models.next_engagement_state` | Mean-reverting random walk |
| Completion flag | `learning_event.py` | True for `video_complete`, `quiz_submit`, `assignment_submit`, `module_complete`, `feedback_view` |

## Assessment assumptions

| Assumption | Location | Value |
|---|---|---|
| Attempt probability | `constants.ATTEMPT_PROBABILITY_BY_TYPE` | quiz/formative 1.0; assignment 0.85; exam 0.95 |
| Score model | `constants.SCORE_MODEL` | See generation_methodology.md |
| Late submission | `constants.LATE_SUBMISSION_BASE` | `0.12 · (1 − preparedness)` for assignments only |
| Submission status weights | `constants.SUBMISSION_STATUS_WEIGHTS` | graded 80%, submitted 15%, draft 3%, missed 2% |
| Duration | `assessment_models.sample_attempt_duration` | Gamma(2, base·multiplier/2) |
| Resubmission | `attempt.py` | Up to 3 attempts for assignments; further attempts allowed when score < 70% |

## Feedback assumptions

| Assumption | Location | Value |
|---|---|---|
| Feedback probability | `feedback.py` | 0.90 per attempt (excluding missed) |
| Feedback type | `constants.FEEDBACK_TYPE_WEIGHTS` | auto 45%, instructor 35%, peer 15%, rubric 5% |
| Delay | `constants.FEEDBACK_DELAY_LOG_NORMAL` | Per-type log-normal |
| Viewed probability | `feedback.py` | `0.65 + 0.25·engagement − 0.15·delay_weeks` |
| Revision flag | `feedback.py` | `0.35 · (1 − score_fraction) · viewed` |

## Weekly engagement assumptions

| Assumption | Location | Value |
|---|---|---|
| Engagement scalar | `behavioural_models.weekly_engagement_scalar` | `min(1, count / (2·λ))` |
| Trajectory thresholds | `behavioural_models.classify_trajectory` | thriving ≥ 0.70; steady ≥ 0.40; at_risk ≥ 0.15; else disengaged |

## Progression assumptions

| Assumption | Location | Value |
|---|---|---|
| GPA scale | `academic_models.grade_to_grade_point` | `final_grade / 10`, clipped [0, 10] |
| Outcome thresholds | `academic_models.classify_progression_outcome` | advanced ≥ 0.80 & GPA ≥ 4.0; conditional ≥ 0.55 & GPA ≥ 3.5; repeated ≥ 0.30 |
| Standing thresholds | `constants.STANDING_GPA_*` | good ≥ 5.0; warning ≥ 4.0; probation ≥ 2.0 |
| Pass threshold | `constants.PASS_GRADE` | 40 |

## Digital access assumptions

| Assumption | Location | Value |
|---|---|---|
| Device | `constants.DEVICE_CATEGORY_WEIGHTS` | laptop 55% |
| Connectivity | `constants.CONNECTIVITY_CATEGORY_WEIGHTS` | broadband 60% |
| Bandwidth | `constants.BANDWIDTH_CATEGORY_WEIGHTS` | high 50% |
| Reliability | `constants.ACCESS_RELIABILITY_WEIGHTS` | Weighted mean of category scores + noise |
| Constraint thresholds | `constants.ACCESS_CONSTRAINT_THRESHOLDS` | severe ≤ 0.30; moderate ≤ 0.55; mild ≤ 0.75; else none |

## Intervention assumptions

| Assumption | Location | Value |
|---|---|---|
| Risk thresholds | `constants.RISK_*` | engagement < 0.30, score < 45, missed fraction > 0.40 |
| Intervention count | `intervention_models.INTERVENTIONS_PER_AT_RISK` | (0, 1, 2) with (0.25, 0.55, 0.20) |
| Type by trigger | `constants.INTERVENTION_TYPE_BY_TRIGGER` | Per-trigger weight vectors |
| Channel | `constants.SUPPORT_CHANNEL_WEIGHTS` | in_person 30%, video_call 25%, email 25%, lms 15%, phone 5% |
| Response | `constants.RESPONSE_STATUS_WEIGHTS` | accepted 55%, pending 20%, declined 10%, no_response 15% |
| Outcome | `constants.INTERVENTION_OUTCOME_WEIGHTS` | improved 55%, no_change 30%, worsened 10%, ongoing 5% |

## What these assumptions do not mean

- **Not empirical.** None of these numbers is calibrated against real student data. Changing them changes the dataset; the dataset does not reveal real populations.
- **Not causal.** The score model is not a causal model; it is a plausible generative story. Downstream causal inferences from this dataset would be invalid.
- **Not intervention effects.** Simulated interventions do not demonstrate real intervention effectiveness.

See [privacy_and_ethics.md](privacy_and_ethics.md).
