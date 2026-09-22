"""Egress gate, fallback, resilience, key redaction."""

from __future__ import annotations

import json

import pytest
from pydantic import SecretStr
from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.factory import (
    build_completion_port,
    build_egress_policy,
    build_embedding_port,
)
from career_assistant.adapters.providers.hermetic.completion import (
    HermeticCompletionAdapter,
)
from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.adapters.providers.openai.completion import (
    OpenAICompletionAdapter,
)
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
    classify_http_status,
)
from career_assistant.application.ports.errors import (
    EgressNotPermittedError,
    ProviderTransientError,
    ProviderUnavailableError,
)
from career_assistant.application.ports.types import CallRecord, CompletionRequest
from career_assistant.application.providers.accounting import CallAccountant
from career_assistant.application.providers.egress import HostedEgressPolicy
from career_assistant.application.providers.fallback import (
    CompletingWithOptionalFallback,
    FallbackPolicy,
)
from career_assistant.settings import ProviderSettings


def test_hosted_adapter_not_constructible_when_egress_closed() -> None:
    settings = ProviderSettings(
        allow_hosted_providers=False,
        openai_api_key=SecretStr("sk-secret-value"),
        completion_provider="openai",
    )
    with pytest.raises(EgressNotPermittedError):
        build_completion_port(settings, transport=ScriptedTransport({}))


def test_hosted_adapter_not_constructible_without_key() -> None:
    settings = ProviderSettings(
        allow_hosted_providers=True,
        openai_api_key=None,
        completion_provider="openai",
    )
    with pytest.raises(EgressNotPermittedError):
        build_completion_port(settings, transport=ScriptedTransport({}))


def test_no_network_when_egress_closed() -> None:
    transport = ScriptedTransport({})
    settings = ProviderSettings(
        allow_hosted_providers=False,
        openai_api_key=SecretStr("sk-should-never-travel"),
        completion_provider="openai",
    )
    with pytest.raises(EgressNotPermittedError):
        build_completion_port(settings, transport=transport)
    assert transport.calls == []


def test_anthropic_embeddings_rejected() -> None:
    settings = ProviderSettings(
        allow_hosted_providers=True,
        anthropic_api_key=SecretStr("anth-key"),
        embedding_provider="anthropic",
    )
    with pytest.raises(ProviderUnavailableError):
        build_embedding_port(settings, transport=ScriptedTransport({}))


def test_fallback_is_explicit_when_enabled() -> None:
    class Boom:
        provider_id = "openai"

        @property
        def capabilities(self):  # noqa: ANN201
            return HermeticCompletionAdapter().capabilities

        def complete(self, request: CompletionRequest):  # noqa: ANN201
            raise ProviderUnavailableError("upstream down")

    wrapped = CompletingWithOptionalFallback(
        primary=Boom(),  # type: ignore[arg-type]
        local=HermeticCompletionAdapter(),
        policy=FallbackPolicy(allow_local_fallback=True),
    )
    result = wrapped.complete(
        CompletionRequest(system="s", user="- SQL", max_output_tokens=40)
    )
    assert result.fallback_used is True
    assert result.provider_id == "hermetic"


def test_fallback_does_not_happen_silently() -> None:
    class Boom:
        @property
        def capabilities(self):  # noqa: ANN201
            return HermeticCompletionAdapter().capabilities

        def complete(self, request: CompletionRequest):  # noqa: ANN201
            raise ProviderUnavailableError("upstream down")

    wrapped = CompletingWithOptionalFallback(
        primary=Boom(),  # type: ignore[arg-type]
        local=HermeticCompletionAdapter(),
        policy=FallbackPolicy(allow_local_fallback=False),
    )
    with pytest.raises(ProviderUnavailableError):
        wrapped.complete(CompletionRequest(system="s", user="u", max_output_tokens=10))


def test_retry_only_on_transient_status() -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ProviderTransientError("429")
        return "ok"

    policy = ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=2,
        breaker=CircuitBreaker(5),
        sleep=lambda _s: None,
    )
    assert policy.run(flaky) == "ok"
    assert calls["n"] == 2


def test_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=2)
    policy = ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=0,
        breaker=breaker,
        sleep=lambda _s: None,
    )

    def always_fail() -> None:
        raise ProviderTransientError("500")

    with pytest.raises(ProviderTransientError):
        policy.run(always_fail)
    with pytest.raises(ProviderTransientError):
        policy.run(always_fail)
    with pytest.raises(ProviderUnavailableError):
        policy.run(always_fail)


def test_classify_http_status_maps_retryable() -> None:
    with pytest.raises(ProviderTransientError):
        classify_http_status(429)
    with pytest.raises(ProviderTransientError):
        classify_http_status(503)
    with pytest.raises(ProviderUnavailableError):
        classify_http_status(400)


def test_call_accountant_stores_counts_not_content() -> None:
    accountant = CallAccountant()
    accountant.record(
        CallRecord(
            provider_id="hermetic",
            model_tag="rules-v1",
            operation="complete",
            input_tokens=3,
            output_tokens=2,
            latency_ms=1,
            estimated_cost_usd=0.0,
            left_machine=False,
        )
    )
    dumped = str(accountant.records)
    assert "hermetic" in dumped
    assert "CV text" not in dumped


def test_public_snapshot_never_includes_api_keys() -> None:
    settings = ProviderSettings(
        openai_api_key=SecretStr("sk-super-secret-openai"),
        anthropic_api_key=SecretStr("anth-super-secret"),
        allow_hosted_providers=True,
    )
    snapshot = json.dumps(settings.public_snapshot())
    for secret in settings.secret_values():
        assert secret not in snapshot
    assert "sk-" not in snapshot
    assert "masked" not in snapshot.lower()


def test_egress_policy_reports_availability() -> None:
    closed = HostedEgressPolicy(False, "k", "k")
    assert closed.openai_available() is False
    open_gate = HostedEgressPolicy(True, "k", None)
    assert open_gate.openai_available() is True
    assert open_gate.anthropic_available() is False
    assert build_egress_policy(
        ProviderSettings(allow_hosted_providers=True, openai_api_key=SecretStr("k"))
    ).openai_available()


def test_openai_adapter_sends_authorization_only_when_constructed() -> None:
    transport = ScriptedTransport(
        {
            "/chat/completions": HttpResponse(
                200,
                json.dumps(
                    {
                        "choices": [
                            {"message": {"content": "ok"}, "finish_reason": "stop"}
                        ],
                        "usage": {},
                    }
                ).encode(),
                {},
            )
        }
    )
    adapter = OpenAICompletionAdapter(
        api_key="sk-live",
        model_tag="gpt-test",
        transport=transport,
        resilience=ResiliencePolicy(
            timeout_seconds=1.0,
            max_retries=0,
            breaker=CircuitBreaker(5),
            sleep=lambda _s: None,
        ),
    )
    adapter.complete(CompletionRequest(system="s", user="u", max_output_tokens=5))
    assert transport.calls


def test_complete_rechecks_egress_and_makes_no_network_call() -> None:
    transport = ScriptedTransport(
        {
            "/chat/completions": HttpResponse(
                200,
                json.dumps(
                    {
                        "choices": [
                            {"message": {"content": "ok"}, "finish_reason": "stop"}
                        ],
                        "usage": {},
                    }
                ).encode(),
                {},
            )
        }
    )
    settings = ProviderSettings(
        allow_hosted_providers=True,
        openai_api_key=SecretStr("sk-should-never-travel"),
        completion_provider="openai",
        openai_completion_model="gpt-4o-mini",
        provider_allow_local_fallback=True,
    )
    port = build_completion_port(settings, transport=transport)
    settings.allow_hosted_providers = False

    with pytest.raises(EgressNotPermittedError):
        port.complete(CompletionRequest(system="s", user="u", max_output_tokens=5))
    assert transport.calls == []


class _RecordingTransport:
    def __init__(self, response: HttpResponse) -> None:
        self._response = response
        self.json_body: dict[str, object] | None = None

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: object = None,
        json_body: dict[str, object] | None = None,
        timeout_seconds: float,
    ) -> HttpResponse:
        del method, url, headers, timeout_seconds
        self.json_body = json_body
        return self._response


def test_ollama_sends_the_json_schema_as_structured_format() -> None:
    from career_assistant.adapters.providers.ollama.completion import (
        OllamaCompletionAdapter,
    )

    schema = {
        "type": "object",
        "properties": {"requirements": {"type": "array"}},
        "required": ["requirements"],
    }
    transport = _RecordingTransport(
        HttpResponse(200, json.dumps({"response": "{}"}).encode(), {})
    )
    adapter = OllamaCompletionAdapter(
        base_url="http://ollama.test",
        model_tag="llama-test",
        transport=transport,
        resilience=ResiliencePolicy(
            timeout_seconds=1.0,
            max_retries=0,
            breaker=CircuitBreaker(5),
            sleep=lambda _seconds: None,
        ),
    )

    adapter.complete(
        CompletionRequest(
            system="Extract.",
            user="untrusted",
            max_output_tokens=64,
            json_schema=schema,
        )
    )

    assert transport.json_body is not None
    assert transport.json_body["format"] == schema
