# Validation Methodology

The validation subsystem runs seven check families against the generated dataset. All checks run against the tables as produced — none of them alters the data.

## 1. Structural (`validation/structural.py`)

- Required columns present.
- Column dtypes match the schema's logical types.
- Non-nullable columns have no nulls.
- Primary keys are unique and non-null.
- Enum columns contain only allowed values.
- Numeric bounds respected.

**Failure indicates** a generator or schema bug.

## 2. Relational (`validation/relational.py`)

Every declared FK is checked by anti-joining the child table against the parent table. Any anti-join rows are orphaned FK values.

**Failure indicates** the generator produced an FK value not present in the parent. This is never acceptable in a valid run.

## 3. Temporal (`validation/temporal.py`)

- `learning_event` timestamps not before the enrolment's start date (1-day tolerance).
- `feedback_event.feedback_timestamp >= assessment_attempt.attempt_timestamp`.
- `assessment_attempt.attempt_timestamp >= enrolment.enrolment_date`.
- `progression_event.semester_number` monotonic per learner.
- Durations non-negative.
- `weekly_engagement.week_start_date` is Monday-aligned.

**Failure indicates** the simulation has a temporal-order bug.

## 4. Statistical (`validation/statistical.py`)

- Flag all-null numeric columns.
- Flag zero-variance in columns where variation is expected by design.

Statistical checks **do not** enforce external benchmarks. A failure here means a column that should vary is constant, which is almost always a generator bug.

## 5. Consistency (`validation/consistency.py`)

- `progression_event.credits_earned` matches the sum of course credits over the learner's completed enrolments in that semester.
- `progression_event.credits_attempted` similarly.
- `weekly_engagement.total_learning_minutes` matches the sum of event durations / 60 for that (learner, course, week).
- Module-dependency violations are reported at `info` severity (they are expected behaviour, not errors).

**Failure indicates** post-hoc enrichment and events disagree.

## 6. Reproducibility (`validation/reproducibility.py`)

Re-runs structural generators with the same seed and asserts byte-identical output. Extended in Phase 11 to cover `institution`, `programme`, `course`, `module`, `learner`, `enrolment`, and one sampled chunk of `learning_event`.

**Failure indicates** non-deterministic RNG usage or hidden global state.

## 7. Leakage (`validation/leakage.py`)

- `feedback_event` timestamps are never in the future relative to their attempt.
- `progression_event` timestamps are never in the future relative to the corresponding enrolments.
- `weekly_engagement` start dates are never after the corresponding enrolments' completion dates.

**Failure indicates** the simulation has used a "future" value to construct an "earlier" record. Any downstream temporal model trained on this data would be leaked.

## Strict mode

`python -m edutrace validate --strict` sets the process exit code to 1 on any `error`-severity failure. `warnings` and `info` entries never fail the run.

## Report

`validation/validation_report.json` contains every check result with `name`, `status`, `message`, `severity`, and structured `details`. Machine-readable; suitable for CI gating.
