-- Example analytical queries over an EduTrace-Open output directory.
-- Run with:
--   duckdb -c ".read examples/duckdb_queries.sql"
-- Or in Python:
--   import duckdb; duckdb.sql(open('examples/duckdb_queries.sql').read())

-- Adjust the path prefix as needed.
CREATE VIEW events   AS SELECT * FROM 'data/generated/learning/learning_event.parquet';
CREATE VIEW weekly   AS SELECT * FROM 'data/generated/learning/weekly_engagement.parquet';
CREATE VIEW attempts AS SELECT * FROM 'data/generated/assessment/assessment_attempt.parquet';
CREATE VIEW learners AS SELECT * FROM 'data/generated/learners/learner.parquet';
CREATE VIEW enrols   AS SELECT * FROM 'data/generated/learners/enrolment.parquet';
CREATE VIEW support  AS SELECT * FROM 'data/generated/interventions/support_event.parquet';

-- 1. Top-20 event types by count.
SELECT event_type, COUNT(*) AS n
FROM events
GROUP BY event_type
ORDER BY n DESC
LIMIT 20;

-- 2. Weekly active-day distribution.
SELECT academic_week, AVG(active_days) AS mean_active_days, AVG(engagement_score) AS mean_engagement
FROM weekly
GROUP BY academic_week
ORDER BY academic_week;

-- 3. Mean attempt score by assessment type.
SELECT i.assessment_type,
       AVG(a.score / a.maximum_score) AS mean_score_fraction,
       COUNT(*) AS n
FROM attempts a
JOIN (SELECT * FROM 'data/generated/assessment/assessment_item.parquet') i
  ON a.assessment_item_id = i.assessment_item_id
GROUP BY i.assessment_type
ORDER BY mean_score_fraction DESC;

-- 4. Engagement vs final grade (Pearson r over learners).
WITH per_learner AS (
    SELECT w.learner_id,
           AVG(w.engagement_score) AS mean_engagement
    FROM weekly w
    GROUP BY w.learner_id
),
grades AS (
    SELECT learner_id, AVG(final_grade) AS mean_grade
    FROM enrols
    WHERE final_grade IS NOT NULL
    GROUP BY learner_id
)
SELECT CORR(mean_engagement, mean_grade) AS pearson_r
FROM per_learner p
JOIN grades g USING (learner_id);

-- 5. Support interventions by type and outcome.
SELECT intervention_type, intervention_outcome, COUNT(*) AS n
FROM support
GROUP BY intervention_type, intervention_outcome
ORDER BY intervention_type, n DESC;

-- 6. Learners with severe digital-access constraints (count per academic year).
SELECT observation_period, COUNT(*) AS n_learners
FROM 'data/generated/accessibility/digital_access.parquet'
WHERE access_constraint_level = 'severe'
GROUP BY observation_period
ORDER BY observation_period;
