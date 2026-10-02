"""The verdict cache key: same inputs, same prompt, same model (ADR 014)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from career_assistant.application.judge.cache import ModelIdentity, verdict_key
from career_assistant.domain.candidate_facts import (
    CandidateFacts,
    Coverage,
    RoleFact,
    TermFact,
)
from career_assistant.domain.experience import ExperienceFact
from career_assistant.domain.judging import Candidate, RequirementPacket

AS_OF = date(2026, 9, 1)
MODEL = ModelIdentity("ollama", "qwen2.5:7b", model_digest="sha256:aaa")
NONE = ExperienceFact(0, 0, 0, None, ongoing=False)
FACTS = CandidateFacts(
    terms=(
        TermFact("pgvector", Coverage.EXACT, replace(NONE, months=12, dated_roles=1)),
        TermFact("kafka", Coverage.MISSING, NONE),
    ),
    roles=(RoleFact("Data Engineer", "Northwind", "mid", None),),
)
C1 = Candidate("c1", "experience", "cv", "Built retrieval over pgvector.")
C2 = Candidate("c2", "skills", "cv", "pgvector, Python")
PACKET = RequirementPacket(
    requirement_id="r1",
    quote="Vector databases",
    statement="Has used a vector database.",
    must_have=True,
    terms=("pgvector",),
    candidates=(C1, C2),
)


def _key(**changes: object) -> str:
    inputs: dict[str, object] = {
        "packet": PACKET,
        "facts": FACTS,
        "model": MODEL,
        "as_of": AS_OF,
    }
    inputs.update(changes)
    return verdict_key(
        inputs["packet"],  # type: ignore[arg-type]
        inputs["facts"],  # type: ignore[arg-type]
        inputs["model"],  # type: ignore[arg-type]
        as_of=inputs["as_of"],  # type: ignore[arg-type]
    )


def test_the_same_inputs_give_the_same_key() -> None:
    assert _key() == _key()
    assert len(_key()) == 64


def test_every_input_the_verdict_depends_on_changes_the_key() -> None:
    changed = [
        _key(model=replace(MODEL, model_digest="sha256:bbb")),
        _key(model=replace(MODEL, model_tag="qwen2.5:14b")),
        _key(model=replace(MODEL, provider_id="openai")),
        _key(as_of=date(2026, 10, 1)),
        _key(packet=replace(PACKET, candidates=(C2, C1))),
        _key(packet=replace(PACKET, candidates=(replace(C1, text="Other."), C2))),
        _key(packet=replace(PACKET, years_expected=3.0)),
        _key(packet=replace(PACKET, must_have=False)),
        _key(facts=replace(FACTS, roles=())),
        _key(
            facts=replace(
                FACTS,
                terms=(TermFact("pgvector", Coverage.ALIAS, NONE), FACTS.terms[1]),
            )
        ),
    ]

    assert _key() not in changed
    assert len(set(changed)) == len(changed)


def test_a_fact_about_a_term_the_requirement_never_names_does_not() -> None:
    other = replace(FACTS, terms=(FACTS.terms[0],))

    assert _key(facts=other) == _key()


def test_a_model_with_no_digest_still_has_a_key() -> None:
    assert _key(model=replace(MODEL, model_digest=None)) != _key()
