"""Provider catalogue and workspace choice — capability-driven, no vendor branching."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.application.providers.egress import HostedEgressPolicy
from career_assistant.settings import ProviderSettings

_HOSTED = frozenset({"openai", "anthropic"})
_LOCAL = frozenset({"hermetic", "ollama"})


@dataclass(frozen=True, slots=True)
class ProviderSupports:
    completion: bool
    embedding: bool


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    structured_output: bool
    context_window: int | None
    max_output_tokens: int | None
    embedding_dimensions: int | None


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    id: str
    name: str
    kind: str
    models: tuple[str, ...]
    available: bool
    unavailable_reason: str | None
    supports: ProviderSupports
    capabilities: ProviderCapabilities


@dataclass(frozen=True, slots=True)
class ProviderChoice:
    answer_provider_id: str
    answer_model: str
    index_provider_id: str
    index_model: str


class ProviderSelectionRejected(Exception):
    def __init__(self, code: str, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def default_provider_choice(settings: ProviderSettings) -> ProviderChoice:
    return ProviderChoice(
        answer_provider_id=settings.completion_provider,
        answer_model=_default_completion_model(settings, settings.completion_provider),
        index_provider_id=settings.embedding_provider,
        index_model=_default_embedding_model(settings, settings.embedding_provider),
    )


def list_provider_catalogue(
    settings: ProviderSettings, egress: HostedEgressPolicy
) -> tuple[ProviderInfo, ...]:
    return (
        _hermetic(),
        _ollama(settings),
        _openai(settings, egress.openai_available()),
        _anthropic(settings, egress.anthropic_available()),
    )


def apply_provider_choice(
    settings: ProviderSettings,
    egress: HostedEgressPolicy,
    *,
    choice: ProviderChoice,
    acknowledged_egress: bool,
) -> ProviderChoice:
    hosted_selected = (
        choice.answer_provider_id in _HOSTED or choice.index_provider_id in _HOSTED
    )
    if hosted_selected and not acknowledged_egress:
        raise ProviderSelectionRejected(
            code="egress_not_acknowledged",
            message="Hosted providers require acknowledgedEgress confirmation.",
            status_code=409,
        )

    for provider_id in (choice.answer_provider_id, choice.index_provider_id):
        _assert_provider_permitted(provider_id, egress=egress)

    if choice.index_provider_id == "anthropic":
        raise ProviderSelectionRejected(
            code="provider_unavailable",
            message="Anthropic does not provide embeddings.",
            status_code=409,
        )
    return choice


def _assert_provider_permitted(provider_id: str, *, egress: HostedEgressPolicy) -> None:
    if provider_id in _LOCAL:
        return
    if provider_id == "openai":
        if not egress.openai_available():
            raise ProviderSelectionRejected(
                code="egress_not_permitted",
                message=(
                    "OpenAI is not permitted: hosted egress is closed or no key is set."
                ),
                status_code=403,
            )
        return
    if provider_id == "anthropic":
        if not egress.anthropic_available():
            raise ProviderSelectionRejected(
                code="egress_not_permitted",
                message=(
                    "Anthropic is not permitted: hosted egress is closed "
                    "or no key is set."
                ),
                status_code=403,
            )
        return
    raise ProviderSelectionRejected(
        code="provider_unavailable",
        message=f"Unknown provider {provider_id!r}.",
        status_code=409,
    )


def _default_completion_model(settings: ProviderSettings, provider_id: str) -> str:
    if provider_id == "hermetic":
        return "rules-v1"
    if provider_id == "ollama":
        return settings.ollama_completion_model
    if provider_id == "openai":
        return settings.openai_completion_model
    if provider_id == "anthropic":
        return settings.anthropic_completion_model
    return provider_id


def _default_embedding_model(settings: ProviderSettings, provider_id: str) -> str:
    if provider_id == "hermetic":
        return "lexical-hash-v1"
    if provider_id == "ollama":
        return settings.ollama_embedding_model
    if provider_id == "openai":
        return settings.openai_embedding_model
    return provider_id


def _hermetic() -> ProviderInfo:
    return ProviderInfo(
        id="hermetic",
        name="Hermetic",
        kind="local",
        models=("rules-v1", "lexical-hash-v1"),
        available=True,
        unavailable_reason=None,
        supports=ProviderSupports(completion=True, embedding=True),
        capabilities=ProviderCapabilities(
            structured_output=True,
            context_window=8192,
            max_output_tokens=1024,
            embedding_dimensions=64,
        ),
    )


def _ollama(settings: ProviderSettings) -> ProviderInfo:
    return ProviderInfo(
        id="ollama",
        name="Ollama",
        kind="local",
        models=(settings.ollama_completion_model, settings.ollama_embedding_model),
        available=True,
        unavailable_reason=None,
        supports=ProviderSupports(completion=True, embedding=True),
        capabilities=ProviderCapabilities(
            structured_output=True,
            context_window=8192,
            max_output_tokens=2048,
            embedding_dimensions=768,
        ),
    )


def _openai(settings: ProviderSettings, available: bool) -> ProviderInfo:
    reason = None if available else "Hosted egress is closed or no OpenAI key is set."
    return ProviderInfo(
        id="openai",
        name="OpenAI",
        kind="hosted",
        models=(settings.openai_completion_model, settings.openai_embedding_model),
        available=available,
        unavailable_reason=reason,
        supports=ProviderSupports(completion=True, embedding=True),
        capabilities=ProviderCapabilities(
            structured_output=True,
            context_window=128000,
            max_output_tokens=16384,
            embedding_dimensions=1536,
        ),
    )


def _anthropic(settings: ProviderSettings, available: bool) -> ProviderInfo:
    reason = (
        None if available else "Hosted egress is closed or no Anthropic key is set."
    )
    return ProviderInfo(
        id="anthropic",
        name="Anthropic",
        kind="hosted",
        models=(settings.anthropic_completion_model,),
        available=available,
        unavailable_reason=reason,
        supports=ProviderSupports(completion=True, embedding=False),
        capabilities=ProviderCapabilities(
            structured_output=True,
            context_window=200000,
            max_output_tokens=8192,
            embedding_dimensions=None,
        ),
    )
