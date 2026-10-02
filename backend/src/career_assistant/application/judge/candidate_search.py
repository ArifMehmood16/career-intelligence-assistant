"""CandidateSearch over hybrid search and the analysed CV's chunks (PLAN 18.10).

The query is embedded as a query and matched against vectors stored as
documents by the same model. A hit outside the analysed CV is dropped, so the
judge only ever sees chunks whose role and dates this search can state.
"""

from __future__ import annotations

from collections.abc import Sequence

from career_assistant.application.judge.matching import CandidateSearchResult
from career_assistant.application.ports.chunks import EmbeddingModel, StoredChunk
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.progress import plan_calls
from career_assistant.application.ports.search import HybridQuery, HybridSearchPort
from career_assistant.application.ports.types import EmbeddingRequest
from career_assistant.domain.chunking import RoleProposal
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.judging import Candidate, RequirementPacket
from career_assistant.domain.search import query_terms


class HybridCandidateSearch:
    def __init__(
        self,
        *,
        workspace_id: str,
        cv_chunks: Sequence[StoredChunk],
        embedding: EmbeddingPort,
        search: HybridSearchPort,
        max_chars_per_text: int,
    ) -> None:
        self._workspace_id = workspace_id
        self._chunks = {s.chunk_id: s for s in cv_chunks}
        self._roles = {
            s.chunk.first_line: s.chunk.role
            for s in cv_chunks
            if s.chunk.role is not None
        }
        self._embedding = embedding
        self._search = search
        self._max_chars = max_chars_per_text

    def find(
        self, requirement: RequirementPacket, query_text: str
    ) -> CandidateSearchResult:
        return self.find_all([(requirement, query_text)])[0]

    def find_all(
        self, items: Sequence[tuple[RequirementPacket, str]]
    ) -> tuple[CandidateSearchResult, ...]:
        """One embedding request for every query, then one search each."""
        plan_calls()
        if not items:
            return ()
        plan_calls(embedding=1)
        embedded = self._embedding.embed(
            EmbeddingRequest(
                texts=tuple(text for _, text in items),
                max_chars_per_text=self._max_chars,
                input_type="query",
            )
        )
        stored_under = EmbeddingModel(
            embedded.provider_id, embedded.model_tag, embedded.dimensions, "document"
        )
        return tuple(
            self._from_vector(requirement, text, vector, stored_under.key)
            for (requirement, text), vector in zip(items, embedded.vectors, strict=True)
        )

    def _from_vector(
        self,
        requirement: RequirementPacket,
        query_text: str,
        vector: tuple[float, ...],
        model_key: str,
    ) -> CandidateSearchResult:
        found = self._search.search(
            HybridQuery(
                workspace_id=self._workspace_id,
                text=query_text,
                embedding=vector,
                terms=query_terms(requirement.terms),
                embedding_model_key=model_key,
                sources=(DocumentKind.CV,),
            )
        )
        hits = tuple(hit for hit in found if hit.chunk_id in self._chunks)
        return CandidateSearchResult(
            hits=hits,
            candidates=tuple(self._candidate(self._chunks[h.chunk_id]) for h in hits),
        )

    def _candidate(self, stored: StoredChunk) -> Candidate:
        chunk = stored.chunk
        role = self._roles.get(chunk.role_ref) if chunk.role_ref else None
        return Candidate(
            chunk_id=stored.chunk_id,
            kind=chunk.kind,
            source=DocumentKind.CV.value,
            text=chunk.text,
            role=_label(role),
            dates=role.dates if role is not None else None,
        )


def _label(role: RoleProposal | None) -> str | None:
    if role is None:
        return None
    parts = [part for part in (role.title, role.employer) if part]
    return " at ".join(parts) or None
