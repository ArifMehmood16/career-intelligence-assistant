"""Phase 9.7–9.9 — ask use case: stream/non-stream parity, persist, idempotency."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from career_assistant.application.ask.service import (
    AskEvent,
    AskRequest,
    AskService,
    ConversationStore,
)
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.domain.ask import (
    AnswerKind,
    RoleAnalysisView,
)
from career_assistant.domain.intents import Intent
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreComponent, ScoreExplanation

NOW = datetime(2026, 9, 18, 17, 0, tzinfo=UTC)


@dataclass
class _MemMessage:
    id: str
    author: str
    content: str
    kind: str
    citations: tuple[str, ...]
    provider: str | None
    model: str | None
    left_machine: bool
    client_request_id: str | None
    created_at: datetime


@dataclass
class _MemStore:
    messages: list[_MemMessage] = field(default_factory=list)
    questions_before_answers: list[str] = field(default_factory=list)
    deleted: bool = False

    def ensure_conversation(self, workspace_id: str) -> str:
        return "conv-1"

    def conversation_id_for(self, workspace_id: str) -> str | None:
        return "conv-1" if self.messages else None

    def find_by_client_request_id(
        self, workspace_id: str, client_request_id: str
    ) -> tuple[_MemMessage, _MemMessage] | None:
        q = next(
            (
                m
                for m in self.messages
                if m.author == "user" and m.client_request_id == client_request_id
            ),
            None,
        )
        if q is None:
            return None
        a = next(
            (
                m
                for m in self.messages
                if m.author == "assistant" and m.client_request_id == client_request_id
            ),
            None,
        )
        if a is None:
            return None
        return q, a

    def persist_question(
        self,
        *,
        workspace_id: str,
        conversation_id: str,
        question_id: str,
        client_request_id: str,
        text: str,
    ) -> None:
        self.questions_before_answers.append(question_id)
        self.messages.append(
            _MemMessage(
                id=question_id,
                author="user",
                content=text,
                kind="question",
                citations=(),
                provider=None,
                model=None,
                left_machine=False,
                client_request_id=client_request_id,
                created_at=NOW,
            )
        )

    def persist_answer(
        self,
        *,
        workspace_id: str,
        question_id: str,
        answer_id: str,
        body: str,
        kind: str,
        citations: tuple[str, ...],
        provider: str,
        model_tag: str,
        left_machine: bool,
    ) -> None:
        assert question_id in self.questions_before_answers
        self.messages.append(
            _MemMessage(
                id=answer_id,
                author="assistant",
                content=body,
                kind=kind,
                citations=citations,
                provider=provider,
                model=model_tag,
                left_machine=left_machine,
                client_request_id=next(
                    (
                        m.client_request_id
                        for m in self.messages
                        if m.id == question_id and m.author == "user"
                    ),
                    None,
                ),
                created_at=NOW,
            )
        )

    def list_history(
        self, workspace_id: str, conversation_id: str
    ) -> tuple[_MemMessage, ...]:
        # Insertion order is creation order for this in-memory double.
        return tuple(self.messages)

    def hard_delete(self, workspace_id: str, conversation_id: str) -> None:
        self.messages.clear()
        self.deleted = True


class _TrackingCompletion:
    calls: int = 0
    last_request: CompletionRequest | None = None

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="hermetic",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=False,
            context_window_tokens=2048,
            max_output_tokens=256,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls += 1
        self.last_request = request
        return CompletionResult(
            text="From the CV: Owned dbt models in production.",
            provider_id="hermetic",
            model_tag="rules-v1",
            left_machine=False,
        )


def _role_view() -> RoleAnalysisView:
    req = Requirement(
        id="dbt",
        text="Production dbt experience",
        competency="dbt",
        seniority_signal=None,
        must_have=True,
        source_span_id="jd-dbt",
        extraction_confidence=0.9,
        is_vague=False,
    )
    mapping = RequirementMapping(
        requirement_id="dbt",
        status=MappingStatus.MISSING,
        reason_code=MappingReason.NO_RELATED_CLAIM,
        justifying_span_ids=(),
        justifying_claim_ids=(),
    )
    explanation = ScoreExplanation(
        score=0.0,
        band="limited",
        components=(
            ScoreComponent(
                requirement_id="dbt",
                must_have=True,
                status=MappingStatus.MISSING,
                weight=3.0,
                status_factor=0.0,
                recency_factor=1.0,
                contribution=0.0,
            ),
        ),
        denominator=3.0,
        numerator=0.0,
    )
    return RoleAnalysisView(
        role_id="role-1",
        title="Analytics Engineer",
        explanation=explanation,
        requirements=(req,),
        mappings=(mapping,),
        span_texts={"jd-dbt": "Production dbt experience"},
    )


def _service(
    store: ConversationStore | None = None,
    completion: CompletionPort | None = None,
) -> tuple[AskService, _MemStore, _TrackingCompletion]:
    mem = store if isinstance(store, _MemStore) else _MemStore()
    if isinstance(completion, _TrackingCompletion):
        comp = completion
    else:
        comp = _TrackingCompletion()
    service = AskService(
        store=mem,
        completion=comp,
        known_span_ids=frozenset({"jd-dbt", "cv-dbt"}),
        id_factory=lambda prefix: f"{prefix}-1",
    )
    return service, mem, comp


def test_question_is_persisted_before_answer() -> None:
    service, store, _ = _service()
    result = service.ask(
        AskRequest(
            workspace_id="ws-1",
            conversation_id="conv-1",
            client_request_id="cr-1",
            content="What gaps should I close first?",
            role_id="role-1",
            roles=(_role_view(),),
        )
    )
    assert store.questions_before_answers == ["q-1"]
    assert result.kind is AnswerKind.ANSWER
    assert any(m.kind == "question" for m in store.messages)
    assert any(m.author == "assistant" for m in store.messages)


def test_structured_intent_is_phrased_from_the_stored_analysis() -> None:
    service, _, completion = _service()
    service.ask(
        AskRequest(
            workspace_id="ws-1",
            conversation_id="conv-1",
            client_request_id="cr-1",
            content="What gaps should I close first?",
            role_id="role-1",
            roles=(_role_view(),),
        )
    )
    assert completion.calls == 1
    request = completion.last_request
    assert request is not None
    assert "stored_score=0" in request.user
    assert "do not calculate a new score" in request.system.lower()
    assert "couple of sentences" in request.system.lower()
    assert "several paragraphs" in request.system.lower()
    assert request.max_output_tokens == 256


def test_insufficient_evidence_does_not_call_the_model() -> None:
    service, _, completion = _service()
    result = service.ask(
        AskRequest(
            workspace_id="ws-1",
            conversation_id="conv-1",
            client_request_id="cr-empty",
            content="How well do I fit this role?",
            role_id=None,
            roles=(),
        )
    )
    assert result.kind is AnswerKind.INSUFFICIENT
    assert completion.calls == 0


def test_stream_and_ask_agree_on_final_answer() -> None:
    service, _, _ = _service()
    request = AskRequest(
        workspace_id="ws-1",
        conversation_id="conv-1",
        client_request_id="cr-stream",
        content="How well do I fit this role?",
        role_id="role-1",
        roles=(_role_view(),),
    )
    direct = service.ask(request)
    # Fresh service/store for stream path with same logical request id would
    # hit idempotency — use a twin service with a different id for stream.
    service2, store2, _ = _service()
    events = list(
        service2.stream(
            AskRequest(
                workspace_id="ws-1",
                conversation_id="conv-1",
                client_request_id="cr-stream-2",
                content="How well do I fit this role?",
                role_id="role-1",
                roles=(_role_view(),),
            )
        )
    )
    assert any(e.type == "meta" for e in events)
    assert any(e.type == "token" for e in events)
    assert any(e.type == "citations" for e in events)
    done = next(e for e in events if e.type == "done")
    assert done.kind == direct.kind.value
    # Reassemble tokens and compare to direct content.
    text = "".join(e.text or "" for e in events if e.type == "token")
    assert text == direct.content
    assert store2.messages  # final answer persisted once
    assert sum(1 for m in store2.messages if m.author == "assistant") == 1


def test_repeated_client_request_id_returns_existing_without_duplicate() -> None:
    service, store, completion = _service()
    request = AskRequest(
        workspace_id="ws-1",
        conversation_id="conv-1",
        client_request_id="cr-dup",
        content="What gaps should I close first?",
        role_id="role-1",
        roles=(_role_view(),),
    )
    first = service.ask(request)
    second = service.ask(request)
    assert first.content == second.content
    assert sum(1 for m in store.messages if m.author == "user") == 1
    assert sum(1 for m in store.messages if m.author == "assistant") == 1
    assert completion.calls == 1


def test_partial_tokens_are_never_persisted_as_answers() -> None:
    service, store, _ = _service()
    events: list[AskEvent] = []
    for event in service.stream(
        AskRequest(
            workspace_id="ws-1",
            conversation_id="conv-1",
            client_request_id="cr-partial",
            content="How well do I fit this role?",
            role_id="role-1",
            roles=(_role_view(),),
        )
    ):
        events.append(event)
        if event.type == "token":
            # Mid-stream: only the question may exist, never a partial answer body.
            assert all(
                m.author != "assistant" or m.content == ""
                for m in store.messages
                if False  # answers only appear after done
            )
            assert not any(m.author == "assistant" for m in store.messages)
    assert any(m.author == "assistant" for m in store.messages)


def test_history_order_and_hard_delete() -> None:
    service, store, _ = _service()
    service.ask(
        AskRequest(
            workspace_id="ws-1",
            conversation_id="conv-1",
            client_request_id="cr-a",
            content="What gaps should I close first?",
            role_id="role-1",
            roles=(_role_view(),),
        )
    )
    history = service.history(workspace_id="ws-1", conversation_id="conv-1")
    assert [m.kind for m in history] == ["question", "answer"] or [
        m.author for m in history
    ] == ["user", "assistant"]
    service.delete_history(workspace_id="ws-1", conversation_id="conv-1")
    assert store.deleted is True
    assert service.history(workspace_id="ws-1", conversation_id="conv-1") == ()


def test_stream_meta_includes_intent_and_provider() -> None:
    service, _, _ = _service()
    events = list(
        service.stream(
            AskRequest(
                workspace_id="ws-1",
                conversation_id="conv-1",
                client_request_id="cr-meta",
                content="What gaps should I close first?",
                role_id="role-1",
                roles=(_role_view(),),
            )
        )
    )
    meta = next(e for e in events if e.type == "meta")
    assert meta.intent is Intent.GAPS
    assert meta.provider == "hermetic"
