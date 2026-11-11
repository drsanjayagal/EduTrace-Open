"""Programme generator.

Each programme belongs to exactly one institution, has a discipline drawn
from ``PROGRAMME_DISCIPLINES``, a qualification level, a duration in
semesters, and a total credit count.

Programmes are assigned round-robin across institutions (1st institution
gets the first programme, 2nd gets the second, etc.), cycling if there are
more programmes than institutions. That is a modelling assumption, not an
empirical claim.

Durations and credits are drawn from small, documented distributions so
counts remain plausible but not identical.
"""

from __future__ import annotations

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import PROGRAMME_DISCIPLINES, QualificationLevel
from edutrace.utils.ids import PREFIX_PROGRAMME, format_ids
from edutrace.utils.random_state import RandomStateManager

_QUALIFICATION_LEVELS = tuple(q.value for q in QualificationLevel)

# Duration (semesters) distribution for a 3-year vs 4-year programme.
# Modelling assumption: 6-semester (3-year) programmes are 55% of the mix.
_DURATION_CHOICES = (6, 8)
_DURATION_WEIGHTS = (0.55, 0.45)


def generate_programmes(
    config: EduTraceConfig,
    rng: RandomStateManager,
    institutions: pl.DataFrame,
) -> pl.DataFrame:
    n = config.generation.num_programmes
    if n <= 0:
        return _empty()

    inst_ids = institutions["institution_id"].to_list()
    if not inst_ids:
        raise ValueError("Cannot generate programmes without institutions")

    g = rng.table_rng("programme")

    # Round-robin assignment.
    programme_to_inst = [
        inst_ids[i % len(inst_ids)] for i in range(n)
    ]

    disciplines = g.choice(PROGRAMME_DISCIPLINES, size=n).tolist()
    durations = g.choice(_DURATION_CHOICES, size=n, p=_DURATION_WEIGHTS).tolist()

    # Qualification level given duration: 6 semesters -> UG, 8 -> UG or PG.
    qualifications: list[str] = []
    for dur in durations:
        if dur == 6:
            qualifications.append(QualificationLevel.UNDERGRADUATE.value)
        else:
            if g.random() < 0.35:
                qualifications.append(QualificationLevel.POSTGRADUATE.value)
            else:
                qualifications.append(QualificationLevel.UNDERGRADUATE.value)

    credits = [d * 20 for d in durations]  # 20 credits per semester, assumption

    # Human-readable programme name from discipline + qualification.
    names = [
        f"{disc.replace('_', ' ').title()} "
        f"({qual.replace('_', ' ').title()})"
        for disc, qual in zip(disciplines, qualifications, strict=True)
    ]

    ids = format_ids(PREFIX_PROGRAMME, list(range(1, n + 1)))

    return pl.DataFrame(
        {
            "programme_id": ids,
            "institution_id": programme_to_inst,
            "programme_name": names,
            "qualification_level": qualifications,
            "duration_semesters": durations,
            "discipline": disciplines,
            "total_credits": credits,
        }
    ).with_columns(
        [
            pl.col("programme_id").cast(pl.Utf8),
            pl.col("institution_id").cast(pl.Utf8),
            pl.col("programme_name").cast(pl.Utf8),
            pl.col("qualification_level").cast(pl.Utf8),
            pl.col("duration_semesters").cast(pl.Int64),
            pl.col("discipline").cast(pl.Utf8),
            pl.col("total_credits").cast(pl.Int64),
        ]
    )


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "programme_id": pl.Utf8,
            "institution_id": pl.Utf8,
            "programme_name": pl.Utf8,
            "qualification_level": pl.Utf8,
            "duration_semesters": pl.Int64,
            "discipline": pl.Utf8,
            "total_credits": pl.Int64,
        }
    )
