from __future__ import annotations

import polars as pl


def test_event_timestamp_not_before_enrolment(tiny_tables):
    ev = tiny_tables["learning_event"]
    enr = tiny_tables["enrolment"].select("enrolment_id", "enrolment_date")
    joined = ev.join(enr, on="enrolment_id", how="inner")
    bad = joined.filter(
        pl.col("event_timestamp").dt.date()
        < (pl.col("enrolment_date").dt.date() - pl.duration(days=1))
    )
    assert bad.height == 0


def test_feedback_after_attempt(tiny_tables):
    fb = tiny_tables["feedback_event"]
    att = tiny_tables["assessment_attempt"]
    joined = fb.join(att, on="attempt_id", how="inner")
    bad = joined.filter(pl.col("feedback_timestamp") < pl.col("attempt_timestamp"))
    assert bad.height == 0


def test_durations_non_negative(tiny_tables):
    ev = tiny_tables["learning_event"]
    assert (ev["event_duration_seconds"] >= 0).all()
    att = tiny_tables["assessment_attempt"]
    assert (att["duration_seconds"] >= 0).all()


def test_weekly_week_start_is_monday(tiny_tables):
    weekly = tiny_tables["weekly_engagement"]
    if weekly.height == 0:
        return
    bad = weekly.filter(pl.col("week_start_date").dt.weekday() != 1)
    assert bad.height == 0
