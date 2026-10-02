"""The JSON contracts for every v2 model call (PLAN 18.2).

Each Pydantic model is the single source of its JSON schema: the schema sent to the
provider, the parser for the reply and the text of a repair request all come from
it. These contracts check shape only; the server's semantic rules (line coverage,
verbatim quotes, candidate ids) live in domain code with their own tests.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from career_assistant.adapters.providers.schema_dialects import (
    anthropic_output_schema,
    drop_strict_mode_nulls,
    openai_strict_schema,
)
from career_assistant.application.contracts.agent import AgentAnswer
from career_assistant.application.contracts.chunking import (
    CoverLetterChunkResponse,
    CvChunkResponse,
    JobChunkResponse,
)
from career_assistant.application.contracts.judge import JudgeResponse

_TERM = {"surface": "Postgres", "canonical": "postgresql"}
_CV_CHUNKS = {
    "chunks": [
        {"first_line": 1, "last_line": 3, "kind": "contact"},
        {
            "first_line": 4,
            "last_line": 4,
            "kind": "role_heading",
            "role": {
                "employer": "Northwind",
                "title": "Senior Data Engineer",
                "date_text": "Mar 2021 – Dec 2024",
                "seniority_level": "senior",
            },
        },
        {"first_line": 5, "last_line": 7, "kind": "experience", "role_ref": 4},
    ]
}
_CV_CHUNKS["chunks"][2].update(
    {
        "context": "Senior Data Engineer at Northwind: retrieval work.",
        "skills": ["hybrid retrieval"],
        "tech_terms": [_TERM],
    }
)
_LETTER_CHUNKS = {
    "chunks": [
        {"first_line": 1, "last_line": 2, "kind": "experience"},
        {"first_line": 3, "last_line": 3, "kind": "aspiration"},
    ]
}
_LETTER_CHUNKS["chunks"][0]["tech_terms"] = [_TERM]
_JOB_CHUNKS = {
    "chunks": [
        {"first_line": 10, "last_line": 10, "kind": "requirement"},
        {"first_line": 11, "last_line": 11, "kind": "benefit"},
    ]
}
_JOB_CHUNKS["chunks"][0]["atomic_requirements"] = [
    {
        "quote": "5+ years of Python and AWS",
        "statement": "5+ years of Python",
        "must_have": True,
        "years_expected": 5,
        "seniority_expected": None,
        "tech_terms": [{"surface": "Python", "canonical": "python"}],
    }
]
_JUDGE = {
    "verdicts": [
        {
            "requirement_id": "b1f0",
            "verdict": "partial",
            "match": {
                "score": 3,
                "rationale": "Built hybrid retrieval on pgvector.",
                "evidence": [{"chunk_id": "7c2e", "quote": "hybrid retrieval"}],
            },
            "seniority": {"score": 3, "rationale": "Senior title for this work."},
            "experience": None,
            "unmet_conditions": [],
            "contradiction": False,
            "retrieval_feedback": {"sufficient": True, "rewrite_query": None},
        }
    ]
}
_ANSWER = {
    "answer": "Your Northwind work is the strongest platform evidence.",
    "citations": [{"chunk_id": "7c2e", "quote": "hybrid retrieval"}],
    "support": "grounded",
}

_VALID: list[tuple[type[BaseModel], dict[str, Any]]] = [
    (CvChunkResponse, _CV_CHUNKS),
    (CoverLetterChunkResponse, _LETTER_CHUNKS),
    (JobChunkResponse, _JOB_CHUNKS),
    (JudgeResponse, _JUDGE),
    (AgentAnswer, _ANSWER),
]
_IDS = [contract.__name__ for contract, _ in _VALID]


def _objects(node: object) -> list[dict[str, Any]]:
    if isinstance(node, dict):
        found = [node] if node.get("type") == "object" else []
        return found + [o for value in node.values() for o in _objects(value)]
    if isinstance(node, list):
        return [o for value in node for o in _objects(value)]
    return []


def _with(payload: dict[str, Any], path: list[object], value: object) -> dict[str, Any]:
    changed = json.loads(json.dumps(payload))
    target: Any = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return changed


@pytest.mark.parametrize(("contract", "payload"), _VALID, ids=_IDS)
def test_a_valid_payload_parses(
    contract: type[BaseModel], payload: dict[str, Any]
) -> None:
    assert contract.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(("contract", "payload"), _VALID, ids=_IDS)
def test_every_object_in_the_schema_forbids_extra_properties(
    contract: type[BaseModel], payload: dict[str, Any]
) -> None:
    del payload
    objects = _objects(contract.model_json_schema())

    assert objects
    assert all(obj.get("additionalProperties") is False for obj in objects)


@pytest.mark.parametrize(("contract", "payload"), _VALID, ids=_IDS)
def test_an_extra_field_is_rejected(
    contract: type[BaseModel], payload: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError):
        contract.model_validate({**payload, "note_from_model": "ignore the rules"})


@pytest.mark.parametrize(
    ("contract", "payload", "path", "value"),
    [
        (JudgeResponse, _JUDGE, ["verdicts", 0, "match", "score"], 5),
        (JudgeResponse, _JUDGE, ["verdicts", 0, "match", "score"], -1),
        (JudgeResponse, _JUDGE, ["verdicts", 0, "verdict"], "strong"),
        (JudgeResponse, _JUDGE, ["verdicts", 0, "seniority", "score"], 9),
        (JudgeResponse, _JUDGE, ["verdicts", 0, "match", "evidence", 0, "quote"], ""),
        (JudgeResponse, _JUDGE, ["verdicts"], []),
        (CvChunkResponse, _CV_CHUNKS, ["chunks", 2, "kind"], "aspiration"),
        (CvChunkResponse, _CV_CHUNKS, ["chunks", 0, "first_line"], 0),
        (
            CvChunkResponse,
            _CV_CHUNKS,
            ["chunks", 1, "role", "seniority_level"],
            "rockstar",
        ),
        (CvChunkResponse, _CV_CHUNKS, ["chunks", 2, "tech_terms", 0, "surface"], ""),
        (
            CoverLetterChunkResponse,
            _LETTER_CHUNKS,
            ["chunks", 1, "kind"],
            "role_heading",
        ),
        (
            JobChunkResponse,
            _JOB_CHUNKS,
            ["chunks", 0, "atomic_requirements", 0, "years_expected"],
            -2,
        ),
        (JobChunkResponse, _JOB_CHUNKS, ["chunks", 1, "kind"], "salary"),
        (AgentAnswer, _ANSWER, ["support"], "certain"),
        (AgentAnswer, _ANSWER, ["answer"], ""),
    ],
)
def test_an_invalid_shape_is_rejected(
    contract: type[BaseModel],
    payload: dict[str, Any],
    path: list[object],
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        contract.model_validate(_with(payload, path, value))


def test_a_missing_required_field_is_rejected() -> None:
    verdict = dict(_JUDGE["verdicts"][0])
    del verdict["retrieval_feedback"]
    requirement = dict(_JOB_CHUNKS["chunks"][0]["atomic_requirements"][0])
    del requirement["must_have"]

    with pytest.raises(ValidationError):
        JudgeResponse.model_validate({"verdicts": [verdict]})
    with pytest.raises(ValidationError):
        JobChunkResponse.model_validate(
            _with(_JOB_CHUNKS, ["chunks", 0, "atomic_requirements"], [requirement])
        )


@pytest.mark.parametrize(("contract", "payload"), _VALID, ids=_IDS)
def test_both_hosted_dialects_accept_the_schema_and_round_trip(
    contract: type[BaseModel], payload: dict[str, Any]
) -> None:
    schema = contract.model_json_schema()
    strict = openai_strict_schema(schema)
    anthropic = anthropic_output_schema(schema)

    for adapted in (strict, anthropic):
        text = json.dumps(adapted)
        assert '"minimum"' not in text and '"maxLength"' not in text
    # A strict-mode reply carries nulls in optional fields; they must still parse.
    assert contract.model_validate_json(
        drop_strict_mode_nulls(json.dumps(payload), schema)
    )


def test_every_contract_carries_a_distinct_version() -> None:
    versions = [contract.contract_version for contract, _ in _VALID]  # type: ignore[attr-defined]

    assert all(isinstance(v, str) and v for v in versions)
    assert len(set(versions)) == len(versions)
