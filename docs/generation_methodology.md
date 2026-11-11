# Generation Methodology

## Overview

EduTrace-Open generates data in four stages, in dependency order:

1. **Structural** — institutions, programmes, courses, modules, curriculum dependencies, learners, enrolments, learning resources, assessment items, digital access.
2. **Stochastic (chunked by learner)** — learning events, assessment attempts, feedback events.
3. **Post-hoc** — enrolment outcome enrichment, weekly engagement aggregation, progression events, support events.
4. **Persistence** — Parquet/CSV/JSONL output plus manifest and validation.

Each stage is pure-functional in its behaviour (given the same configuration, seed, and upstream tables, it produces the same output).

## Random-state design

A single `RandomStateManager(seed)` is created from `project.random_seed`. Each generator draws from:

- `rng.table_rng(table_name)` for global structural choices (e.g. which institution gets which programme).
- `rng.row_rng(table_name, row_key)` for per-row choices, where `row_key` is a stable integer hash of the row's identifying tuple (`row_key_from_ints`).

Row-level RNGs mean a row's values never depend on how many other rows were generated before it, so chunked generation is byte-identical regardless of chunk size (for values). See [reproducibility.md](reproducibility.md).

## Structural generators

Deterministic given the seed. Counts come from `generation.*` in the config. Names, categories, difficulties, and durations come from documented distributions in `constants.py`.

## Stochastic generators

`learning_event` is driven by `simulation/behavioural_models.py`:

- Each learner has a `LearnerBehaviour` (base event rate, initial engagement, per-resource-type bias).
- For each learner-week, a Poisson event count is drawn with rate `λ = base_rate · weekly_multiplier`.
- For each event, an event type is drawn from `EVENT_TYPE_WEIGHTS_BY_PHASE[phase]`, a channel from `INTERACTION_CHANNEL_WEIGHTS`, and a resource from the module's resources weighted by the learner's preference.
- Engagement state evolves by a mean-reverting random walk, independent of chunk boundaries.

`assessment_attempt` is driven by `simulation/assessment_models.py`:

- Attempt probability per item = `ATTEMPT_PROBABILITY_BY_TYPE[type]`.
- Score = `maximum_score · sigmoid(z)` where `z = intercept + β_p·preparedness + β_e·engagement − β_d·difficulty − β_a·prior_attempts + N(0, σ)`.
- Coefficients live in `constants.SCORE_MODEL`.

`feedback_event` is driven by `FEEDBACK_TYPE_WEIGHTS` and log-normal delays. `revision_flag` correlates with viewed × low score.

## Post-hoc enrichment

- `populate_enrolment_outcomes` computes `final_grade` (weighted mean of best per-item scores) and `completion_date` (max attempt timestamp) for enrolments with sufficient attempts.
- `generate_weekly_engagement` aggregates learning events per (learner, course, week).
- `generate_progression_events` computes credits, GPA, standing, and outcome per (learner, semester).
- `generate_support_events` classifies risk per (learner, semester) and samples interventions.

## Assumptions

Every modelling choice is documented in [simulation_assumptions.md](simulation_assumptions.md) with its location in code. None is claimed to reflect empirical higher-education populations.
