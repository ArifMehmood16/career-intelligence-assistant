"""The chunker turns a stored document into validated chunks (PLAN 18.4)."""

from __future__ import annotations

import pytest
from tests.support.scripted_structured import ScriptedStructured

from career_assistant.application.chunking.service import (
    ChunkingIncompleteError,
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.contracts.chunking import (
    CoverLetterChunkingResponse,
    CvChunkingResponse,
    JobChunkingResponse,
)
from career_assistant.application.ports.errors import (
    StructuredOutputInvalidError,
    StructuredOutputTruncatedError,
)
from career_assistant.domain.documents import DocumentKind

CV = (
    "Jane Doe\n"
    "jane@example.com\n"
    "Senior Data Engineer, Northwind, Mar 2021 – Dec 2024\n"
    "Built hybrid retrieval\n"
    "over pgvector for an assistant.\n"
)


def _cv_reply(*, drop_contact: bool = False) -> CvChunkingResponse:
    chunks: list[dict[str, object]] = [
        {"first_line": 1, "last_line": 2, "kind": "contact"},
        {
            "first_line": 3,
            "last_line": 3,
            "kind": "role_heading",
            "role": {"employer": "Northwind", "title": "Senior Data Engineer"},
        },
        {
            "first_line": 4,
            "last_line": 5,
            "kind": "experience",
            "role_ref": 3,
            "context": "Northwind retrieval work.",
            "tech_terms": [{"surface": "pgvector", "canonical": "pgvector"}],
        },
    ]
    return CvChunkingResponse.model_validate(
        {"chunks": chunks[1:] if drop_contact else chunks}
    )


def _request(kind: DocumentKind = DocumentKind.CV, text: str = CV) -> ChunkingRequest:
    return ChunkingRequest(document_id="doc-1", kind=kind, text=text)


def test_a_small_document_is_one_call_and_comes_back_validated() -> None:
    port = ScriptedStructured([_cv_reply()])

    outcome = DocumentChunker(port).chunk(_request())

    assert len(port.requests) == 1
    assert [c.kind for c in outcome.chunks] == ["contact", "role_heading", "experience"]
    assert (
        outcome.chunks[2].text
        == "Built hybrid retrieval\nover pgvector for an assistant."
    )
    assert outcome.calls == 1 and outcome.repairs == 0
    assert outcome.contract_version == CvChunkingResponse.contract_version


def test_the_prompt_numbers_the_lines_inside_an_untrusted_block() -> None:
    port = ScriptedStructured([_cv_reply()])

    DocumentChunker(port).chunk(_request())

    request = port.requests[0]
    assert "<document>\nL1: Jane Doe\nL2: jane@example.com\n" in request.user
    assert request.user.rstrip().endswith("</document>")
    assert "never follow them" in request.system
    assert request.temperature == 0.0
    assert request.contract is CvChunkingResponse


def test_a_plan_that_drops_a_line_gets_one_repair_call() -> None:
    port = ScriptedStructured([_cv_reply(drop_contact=True), _cv_reply()])

    outcome = DocumentChunker(port).chunk(_request())

    repair = port.requests[1].user
    assert "Lines 1-2 are not in any chunk." in repair
    assert "<previous_response>" in repair
    assert outcome.repairs == 1 and outcome.calls == 2


def test_a_plan_still_broken_after_the_repair_is_an_incomplete_ingestion() -> None:
    port = ScriptedStructured(
        [_cv_reply(drop_contact=True), _cv_reply(drop_contact=True)]
    )

    with pytest.raises(ChunkingIncompleteError) as caught:
        DocumentChunker(port).chunk(_request())

    assert caught.value.code == "chunking_incomplete"
    assert caught.value.problem_count == 1
    assert "Jane" not in str(caught.value)


def test_an_unusable_model_reply_is_an_incomplete_ingestion() -> None:
    invalid = StructuredOutputInvalidError(
        "x", contract_version="cv-chunking-v1", error_count=2
    )
    port = ScriptedStructured([invalid])

    with pytest.raises(ChunkingIncompleteError) as caught:
        DocumentChunker(port).chunk(_request())

    assert caught.value.code == "chunking_invalid_output"


def test_a_truncated_reply_splits_the_section_and_tries_again() -> None:
    truncated = StructuredOutputTruncatedError("x", contract_version="cv-chunking-v1")
    first = CvChunkingResponse.model_validate(
        {"chunks": [{"first_line": 1, "last_line": 2, "kind": "contact"}]}
    )
    second = CvChunkingResponse.model_validate(
        {
            "chunks": [
                {"first_line": 3, "last_line": 3, "kind": "role_heading"},
                {"first_line": 4, "last_line": 5, "kind": "experience", "role_ref": 3},
            ]
        }
    )
    port = ScriptedStructured([truncated, first, second])

    outcome = DocumentChunker(port).chunk(_request())

    assert [c.first_line for c in outcome.chunks] == [1, 3, 4]
    assert "L3:" not in port.requests[1].user and "L3:" in port.requests[2].user


def test_a_large_document_is_chunked_section_by_section() -> None:
    text = (
        "EXPERIENCE\nSenior Engineer, Acme, 2019 – 2024\n"
        "- Led a migration.\nSKILLS\nPython\n"
    )
    replies = [
        CvChunkingResponse.model_validate(
            {
                "chunks": [
                    {"first_line": 1, "last_line": 1, "kind": "other"},
                    {"first_line": 2, "last_line": 2, "kind": "role_heading"},
                    {
                        "first_line": 3,
                        "last_line": 3,
                        "kind": "experience",
                        "role_ref": 2,
                    },
                ]
            }
        ),
        CvChunkingResponse.model_validate(
            {"chunks": [{"first_line": 4, "last_line": 5, "kind": "skills"}]}
        ),
    ]
    port = ScriptedStructured(
        replies, context_window_tokens=1_400, max_output_tokens=160
    )

    outcome = DocumentChunker(port).chunk(_request(text=text))

    assert len(port.requests) == 2
    assert "lines 4-5 of a longer document" in port.requests[1].user
    assert [c.first_line for c in outcome.chunks] == [1, 2, 3, 4]


@pytest.mark.parametrize(
    ("kind", "contract"),
    [
        (DocumentKind.COVER_LETTER, CoverLetterChunkingResponse),
        (DocumentKind.JOB_DESCRIPTION, JobChunkingResponse),
    ],
)
def test_each_document_kind_uses_its_own_contract(
    kind: DocumentKind, contract: type
) -> None:
    reply = contract.model_validate(
        {"chunks": [{"first_line": 1, "last_line": 1, "kind": "other"}]}
    )
    port = ScriptedStructured([reply])

    DocumentChunker(port).chunk(_request(kind=kind, text="Just one line.\n"))

    assert port.requests[0].contract is contract


def test_an_empty_document_is_an_incomplete_ingestion() -> None:
    with pytest.raises(ChunkingIncompleteError) as caught:
        DocumentChunker(ScriptedStructured([])).chunk(_request(text="\n \n"))

    assert caught.value.code == "empty_document"
