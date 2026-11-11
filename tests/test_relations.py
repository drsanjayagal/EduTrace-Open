from __future__ import annotations


def _fk_ok(child, child_col, parent, parent_col) -> bool:
    import polars as pl
    cv = child.filter(pl.col(child_col).is_not_null()).select(
        pl.col(child_col).alias("_k")
    )
    pv = parent.select(pl.col(parent_col).alias("_k")).unique()
    orphans = cv.join(pv, on="_k", how="anti")
    return orphans.height == 0


def test_learner_programme_fk(tiny_tables):
    assert _fk_ok(
        tiny_tables["learner"], "programme_id",
        tiny_tables["programme"], "programme_id",
    )


def test_enrolment_fks(tiny_tables):
    assert _fk_ok(
        tiny_tables["enrolment"], "learner_id",
        tiny_tables["learner"], "learner_id",
    )
    assert _fk_ok(
        tiny_tables["enrolment"], "course_id",
        tiny_tables["course"], "course_id",
    )


def test_event_fks(tiny_tables):
    assert _fk_ok(
        tiny_tables["learning_event"], "learner_id",
        tiny_tables["learner"], "learner_id",
    )
    assert _fk_ok(
        tiny_tables["learning_event"], "course_id",
        tiny_tables["course"], "course_id",
    )
    assert _fk_ok(
        tiny_tables["learning_event"], "module_id",
        tiny_tables["module"], "module_id",
    )


def test_attempt_and_feedback_fks(tiny_tables):
    assert _fk_ok(
        tiny_tables["assessment_attempt"], "assessment_item_id",
        tiny_tables["assessment_item"], "assessment_item_id",
    )
    assert _fk_ok(
        tiny_tables["feedback_event"], "attempt_id",
        tiny_tables["assessment_attempt"], "attempt_id",
    )


def test_progression_fks(tiny_tables):
    assert _fk_ok(
        tiny_tables["progression_event"], "learner_id",
        tiny_tables["learner"], "learner_id",
    )


def test_support_fks(tiny_tables):
    assert _fk_ok(
        tiny_tables["support_event"], "learner_id",
        tiny_tables["learner"], "learner_id",
    )
