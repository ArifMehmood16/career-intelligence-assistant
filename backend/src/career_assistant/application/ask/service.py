"""Ask use case — route, answer, validate, persist; stream and non-stream share it."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Protocol

from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.types import CompletionRequest
from career_assistant.domain.ask import (
    AnswerCitation,
    AnswerKind,
    AnswerResult,
    RoleAnalysisView,
    answer_structured,
    validate_citations,
)
from career_assistant.domain.intents import Intent, route_intent
from career_assistant.domain.prompts import (
    PromptBudget,
    RetrievedSpan,
    build_open_question_prompt,
    select_spans_for_open_question,
)


@dataclass(frozen=True, slots=True)
class AskRequest:
    workspace_id: str
    conversation_id: str
    client_request_id: str
    content: str
    role_id: str | None
    roles: tuple[RoleAnalysisView, ...]
    retrieved_pool: tuple[RetrievedSpan, ...] = ()


@dataclass(frozen=True, slots=True)
class AskEvent:
    type: str  # meta | token | citations | done | error
    text: str | None = None
    kind: str | None = None
    intent: Intent | None = None
    provider: str | None = None
    model: str | None = None
    left_machine: bool | None = None
    question_id: str | None = None
    message_id: str | None = None
    citations: tuple[AnswerCitation, ...] | None = None


class ConversationStore(Protocol):
    def ensure_conversation(self, workspace_id: str) -> str: ...

    def conversation_id_for(self, workspace_id: str) -> str | None: ...

    def find_by_client_request_id(
        self, workspace_id: str, client_request_id: str
    ) -> tuple[object, object] | None: ...

    def persist_question(
        self,
        *,
        workspace_id: str,
        conversation_id: str,
        question_id: str,
        client_request_id: str,
        text: str,
    ) -> None: ...

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
    ) -> None: ...

    def list_history(
        self, workspace_id: str, conversation_id: str
    ) -> tuple[object, ...]: ...

    def hard_delete(self, workspace_id: str, conversation_id: str) -> None: ...


class AskService:
    """Single use case for JSON and SSE ask transports."""

    def __init__(
        self,
        *,
        store: ConversationStore,
        completion: CompletionPort,
        known_span_ids: frozenset[str],
        id_factory: Callable[[str], str],
        prompt_budget: PromptBudget | None = None,
    ) -> None:
        self._store = store
        self._completion = completion
        self._known_span_ids = known_span_ids
        self._id_factory = id_factory
        self._budget = prompt_budget or PromptBudget(
            max_question_chars=2000,
            max_context_chars=8000,
            max_output_tokens=512,
        )

    def ask(self, request: AskRequest) -> AnswerResult:
        existing = self._existing(request)
        if existing is not None:
            return existing
        question_id = self._id_factory("q")
        answer_id = self._id_factory("a")
        self._store.persist_question(
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
            question_id=question_id,
            client_request_id=request.client_request_id,
            text=request.content,
        )
        result, provider, model, left = self._produce(request)
        self._store.persist_answer(
            workspace_id=request.workspace_id,
            question_id=question_id,
            answer_id=answer_id,
            body=result.content,
            kind=result.kind.value,
            citations=tuple(c.span_id for c in result.citations),
            provider=provider,
            model_tag=model,
            left_machine=left,
        )
        return result

    def stream(self, request: AskRequest) -> Iterator[AskEvent]:
        existing = self._existing(request)
        if existing is not None:
            yield from self._replay(existing, request)
            return

        question_id = self._id_factory("q")
        answer_id = self._id_factory("a")
        self._store.persist_question(
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
            question_id=question_id,
            client_request_id=request.client_request_id,
            text=request.content,
        )
        intent = route_intent(request.content, role_id=request.role_id)
        result, provider, model, left = self._produce(request)
        yield AskEvent(
            type="meta",
            question_id=question_id,
            message_id=answer_id,
            intent=intent,
            provider=provider,
            model=model,
            left_machine=left,
        )
        # Stream tokens only; persist the final validated answer after completion.
        for chunk in _chunk_text(result.content):
            yield AskEvent(type="token", text=chunk)
        yield AskEvent(type="citations", citations=result.citations)
        self._store.persist_answer(
            workspace_id=request.workspace_id,
            question_id=question_id,
            answer_id=answer_id,
            body=result.content,
            kind=result.kind.value,
            citations=tuple(c.span_id for c in result.citations),
            provider=provider,
            model_tag=model,
            left_machine=left,
        )
        yield AskEvent(type="done", kind=result.kind.value)

    def history(self, *, workspace_id: str, conversation_id: str) -> tuple[object, ...]:
        return self._store.list_history(workspace_id, conversation_id)

    def delete_history(self, *, workspace_id: str, conversation_id: str) -> None:
        self._store.hard_delete(workspace_id, conversation_id)

    def _existing(self, request: AskRequest) -> AnswerResult | None:
        found = self._store.find_by_client_request_id(
            request.workspace_id, request.client_request_id
        )
        if found is None:
            return None
        question, answer = found
        body = getattr(answer, "content", None) or getattr(answer, "body", "")
        kind_raw = getattr(answer, "kind", AnswerKind.ANSWER.value)
        citations_raw = getattr(answer, "citations", ())
        intent = route_intent(
            getattr(question, "content", request.content),
            role_id=request.role_id,
        )
        return AnswerResult(
            kind=AnswerKind(kind_raw),
            content=str(body),
            citations=tuple(
                AnswerCitation(span_id=str(span_id), label=str(span_id))
                for span_id in citations_raw
            ),
            intent=intent,
        )

    def _replay(self, result: AnswerResult, request: AskRequest) -> Iterator[AskEvent]:
        intent = result.intent
        provider = "mapping" if intent is not Intent.OPEN_QUESTION else "hermetic"
        model = "stored"
        left_machine = False
        question_id: str | None = None
        message_id: str | None = None
        found = self._store.find_by_client_request_id(
            request.workspace_id, request.client_request_id
        )
        if found is not None:
            question, answer = found
            question_id = str(getattr(question, "id", "") or "") or None
            message_id = str(getattr(answer, "id", "") or "") or None
            provider = str(getattr(answer, "provider", None) or provider)
            model = str(
                getattr(answer, "model", None)
                or getattr(answer, "model_tag", None)
                or model
            )
            left_machine = bool(getattr(answer, "left_machine", False))
        yield AskEvent(
            type="meta",
            question_id=question_id,
            message_id=message_id,
            intent=intent,
            provider=provider,
            model=model,
            left_machine=left_machine,
        )
        for chunk in _chunk_text(result.content):
            yield AskEvent(type="token", text=chunk)
        yield AskEvent(type="citations", citations=result.citations)
        yield AskEvent(type="done", kind=result.kind.value)

    def _produce(self, request: AskRequest) -> tuple[AnswerResult, str, str, bool]:
        intent = route_intent(request.content, role_id=request.role_id)
        if intent is not Intent.OPEN_QUESTION:
            result = answer_structured(
                intent,
                request.content,
                roles=request.roles,
                known_span_ids=self._known_span_ids,
            )
            return result, "mapping", "deterministic", False

        selected = select_spans_for_open_question(
            request.content,
            request.retrieved_pool,
            role_id=request.role_id,
        )
        prompt = build_open_question_prompt(
            question=request.content,
            spans=selected,
            budget=self._budget,
        )
        completion = self._completion.complete(
            CompletionRequest(
                system=prompt.system,
                user=prompt.user,
                max_output_tokens=prompt.max_output_tokens,
            )
        )
        citations = tuple(
            AnswerCitation(span_id=item.span.id, label=item.span.text[:80])
            for item in selected
        )
        raw = AnswerResult(
            kind=AnswerKind.ANSWER,
            content=completion.text,
            citations=citations,
            intent=Intent.OPEN_QUESTION,
        )
        result = validate_citations(raw, known_span_ids=self._known_span_ids)
        return (
            result,
            completion.provider_id,
            completion.model_tag,
            completion.left_machine,
        )


def _chunk_text(text: str, size: int = 24) -> tuple[str, ...]:
    if not text:
        return ()
    return tuple(text[i : i + size] for i in range(0, len(text), size))
