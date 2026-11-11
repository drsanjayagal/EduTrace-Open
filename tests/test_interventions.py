from __future__ import annotations


def test_support_event_fields_valid(tiny_tables):
    sup = tiny_tables["support_event"]
    if sup.height == 0:
        return
    allowed_types = {
        "advisor_meeting", "tutoring", "wellbeing_referral",
        "extension_granted", "accessibility_support", "automated_nudge",
    }
    assert set(sup["intervention_type"].unique().to_list()).issubset(allowed_types)


def test_support_event_learner_fk(tiny_tables):
    sup = tiny_tables["support_event"]
    if sup.height == 0:
        return
    learners = set(tiny_tables["learner"]["learner_id"].to_list())
    assert set(sup["learner_id"].to_list()).issubset(learners)


def test_intervention_outcomes(tiny_tables):
    sup = tiny_tables["support_event"]
    if sup.height == 0:
        return
    allowed = {"improved", "no_change", "worsened", "ongoing"}
    assert set(sup["intervention_outcome"].unique().to_list()).issubset(allowed)
