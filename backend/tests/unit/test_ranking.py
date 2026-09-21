"""Phase 13A.7 — equal scores share a competition rank."""

from __future__ import annotations

from career_assistant.domain.ranking import RankableRole, rank_roles


def test_equal_scores_share_competition_rank() -> None:
    ranked = rank_roles(
        (
            RankableRole(id="b", title="Beta", fit_score=80, because=("sql",)),
            RankableRole(id="a", title="Alpha", fit_score=80, because=("dbt",)),
            RankableRole(id="c", title="Gamma", fit_score=40, because=()),
        )
    )

    assert [(item.id, item.rank, item.tied) for item in ranked] == [
        ("a", 1, True),
        ("b", 1, True),
        ("c", 3, False),
    ]
    assert ranked[0].because == ("dbt",)
    assert ranked[1].because == ("sql",)
