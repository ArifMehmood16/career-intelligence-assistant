"""Agent answer contract (ADR 015).

Citations are checked by the server: each chunk must have been returned by a tool
call in the same turn, and each quote must appear in it verbatim.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from career_assistant.application.contracts.base import (
    Contract,
    NonEmpty,
    VersionedContract,
)


class Citation(Contract):
    chunk_id: NonEmpty
    quote: NonEmpty = Field(description="Words copied exactly from that chunk.")


class AgentAnswer(VersionedContract):
    contract_version = "agent-answer-v1"
    answer: NonEmpty = Field(max_length=4_000)
    citations: list[Citation] = Field(default_factory=list)
    support: Literal["grounded", "partial", "insufficient"]
