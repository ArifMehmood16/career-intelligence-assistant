"""One batched taxonomy call turns new terms into inferred edges (PLAN 18.5).

Inferred edges cite nothing and may only widen a search, so a failed call leaves
the graph without them instead of failing ingestion. A provider that is missing or
not permitted is a configuration fault and still surfaces.
"""

from __future__ import annotations

import pytest
from tests.support.scripted_structured import ScriptedStructured

from career_assistant.application.contracts.taxonomy import TaxonomyResponse
from career_assistant.application.graph.taxonomy import TermTaxonomist
from career_assistant.application.ports.errors import (
    EgressNotPermittedError,
    ProviderTransientError,
    StructuredOutputInvalidError,
)
from career_assistant.domain.knowledge_graph import NodeKind, Relation


def _reply(*terms: dict[str, object]) -> TaxonomyResponse:
    return TaxonomyResponse.model_validate({"terms": list(terms)})


def test_new_terms_are_related_in_one_call_as_inferred_edges() -> None:
    port = ScriptedStructured(
        [
            _reply(
                {
                    "term": "pgvector",
                    "is_a": ["Vector Database"],
                    "extends": ["postgresql"],
                    "aliases": ["pg_vector"],
                }
            )
        ]
    )

    outcome = TermTaxonomist(port).relate(["pgvector", "PGVECTOR", "python"])

    assert len(port.requests) == 1
    assert "<terms>\npgvector\npython\n</terms>" in port.requests[0].user
    assert "untrusted" in port.requests[0].system
    edges = {
        (e.source.name, e.relation, e.target.kind, e.target.name) for e in outcome.edges
    }
    assert edges == {
        ("pgvector", Relation.IS_A, NodeKind.CATEGORY, "vector database"),
        ("pgvector", Relation.EXTENDS, NodeKind.TECHNOLOGY, "postgresql"),
        ("pg_vector", Relation.ALIAS_OF, NodeKind.TECHNOLOGY, "pgvector"),
    }
    assert all(e.inferred and e.cites_line is None for e in outcome.edges)
    assert outcome.failure is None and outcome.provider_id == "scripted"


def test_no_new_terms_means_no_call() -> None:
    port = ScriptedStructured([])

    outcome = TermTaxonomist(port).relate([])

    assert port.requests == [] and outcome.edges == ()


def test_relations_for_terms_not_asked_about_and_self_relations_are_ignored() -> None:
    port = ScriptedStructured(
        [
            _reply(
                {"term": "kubernetes", "is_a": ["orchestrator"]},
                {"term": "python", "aliases": ["Python"], "is_a": ["language"]},
            )
        ]
    )

    outcome = TermTaxonomist(port).relate(["python"])

    assert [(e.source.name, e.target.name) for e in outcome.edges] == [
        ("python", "language")
    ]


@pytest.mark.parametrize(
    "error",
    [
        StructuredOutputInvalidError(
            "x", contract_version="taxonomy-v1", error_count=1
        ),
        ProviderTransientError("x"),
    ],
    ids=["invalid-reply", "transient"],
)
def test_a_failed_call_leaves_the_graph_without_inferred_edges(
    error: Exception,
) -> None:
    outcome = TermTaxonomist(ScriptedStructured([error])).relate(["python"])

    assert outcome.edges == ()
    assert outcome.failure == type(error).__name__


def test_a_provider_that_is_not_permitted_still_surfaces() -> None:
    port = ScriptedStructured([EgressNotPermittedError("x")])

    with pytest.raises(EgressNotPermittedError):
        TermTaxonomist(port).relate(["python"])
