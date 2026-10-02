"""Each search's candidates are stored as the verdict's trace (PLAN 18.6).

"Why did the judge see this bullet and not that one?" is then a query.
"""

from __future__ import annotations

import pytest
from tests.support.v2_seed import Seeded

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.search import RetrievalTrace
from career_assistant.domain.search import SearchHit

pytestmark = pytest.mark.integration


def _trace(seeded: Seeded, round_: int = 0) -> RetrievalTrace:
    return RetrievalTrace(
        verdict_id=seeded.verdict,
        round=round_,
        query_text="5+ years of Python",
        hits=(
            SearchHit(
                chunk_id=seeded.cv_chunk,
                fused_score=1 / 61 + 1 / 62,
                dense_rank=1,
                lexical_rank=2,
                exact_rank=None,
            ),
        ),
    )


def test_a_search_trace_is_stored_and_read_back(
    seeded: Seeded,
    uow: SqlUnitOfWork,
) -> None:
    with uow:
        uow.traces.save(seeded.workspace, _trace(seeded, 1))
        uow.commit()
    with uow:
        traces = uow.traces.list_for_verdict(seeded.workspace, seeded.verdict)

    # The seeded fixture already holds a round-0 trace for the same chunk.
    assert [t.round for t in traces] == [0, 1]
    assert traces[1] == _trace(seeded, 1)


def test_a_trace_is_not_visible_from_another_workspace(
    seeded: Seeded,
    uow: SqlUnitOfWork,
) -> None:
    with uow:
        found = uow.traces.list_for_verdict(
            "00000000-0000-0000-0000-000000000000", seeded.verdict
        )

    assert found == ()


@pytest.mark.parametrize("round_", [-1, 2])
def test_only_the_first_search_and_one_rewrite_are_rounds(
    seeded: Seeded,
    uow: SqlUnitOfWork,
    round_: int,
) -> None:
    with uow, pytest.raises(ValueError, match="round"):
        uow.traces.save(seeded.workspace, _trace(seeded, round_))
