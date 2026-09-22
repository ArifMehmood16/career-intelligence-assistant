"""PLAN 13C.3 — structured CV extraction with verified quotes.

The delivered model claim extractor kept only texts the rules extractor had
already found, so a CV whose experience was not a tidy bullet list lost every
role after the regex stopped. The model now returns roles (employer, title,
date range) and claims beneath them. Each claim carries a verbatim quote; the
server locates it in the stored text. Dates are parsed in domain code — the
model never supplies recency or duration.
"""

from __future__ import annotations

import json
from datetime import date

from career_assistant.adapters.extraction.claims_model import ModelClaimExtractor
from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.normalisation import normalise_text

AS_OF = date(2026, 9, 18)

PROSE_CV = normalise_text(
    "Alex Rivera. Analytics Engineer.\n"
    "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
    "Owned dbt models that cover the core order and inventory marts in production.\n"
    "Designed incremental models in Snowflake for daily sales reporting.\n"
    "Blue Harbour Retail — Data Analyst, March 2020 – December 2022.\n"
    "Built Looker dashboards for store performance and inventory turn.\n"
)


class _ScriptedCompletion:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.calls = 0
        self.last_request: CompletionRequest | None = None

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=8192,
            max_output_tokens=1024,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls += 1
        self.last_request = request
        return CompletionResult(
            text=json.dumps(self._payload),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


def _role(
    *,
    employer: str,
    title: str,
    date_range_quote: str,
    claims: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "employer": employer,
        "title": title,
        "date_range_quote": date_range_quote,
        "claims": claims,
    }


def _claim(
    quote: str,
    *,
    competency: str = "",
    scope: str = "",
    technologies: list[str] | None = None,
    outcome: str = "",
) -> dict[str, object]:
    return {
        "quote": quote,
        "competency": competency,
        "scope": scope,
        "technologies": technologies or [],
        "outcome": outcome,
    }


_FULL_PAYLOAD = {
    "roles": [
        _role(
            employer="Northwind Analytics Ltd",
            title="Analytics Engineer",
            date_range_quote="January 2023 – Present",
            claims=[
                _claim(
                    (
                        "Owned dbt models that cover the core order and "
                        "inventory marts in production."
                    ),
                    competency="dbt",
                    scope="production marts",
                    technologies=["dbt"],
                    outcome="core order and inventory marts in production",
                ),
                _claim(
                    (
                        "Designed incremental models in Snowflake for daily "
                        "sales reporting."
                    ),
                    competency="sql",
                    technologies=["Snowflake"],
                ),
            ],
        ),
        _role(
            employer="Blue Harbour Retail",
            title="Data Analyst",
            date_range_quote="March 2020 – December 2022",
            claims=[
                _claim(
                    (
                        "Built Looker dashboards for store performance and "
                        "inventory turn."
                    ),
                    competency="bi",
                    technologies=["Looker"],
                ),
                _claim(
                    "Invented a CUDA kernel for warehouse optimisation.",
                    competency="cuda",
                ),
            ],
        ),
    ]
}


def _extract(payload: dict[str, object], text: str = PROSE_CV):
    completion = _ScriptedCompletion(payload)
    result = ModelClaimExtractor(completion, as_of=AS_OF).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )
    return result, completion


def test_the_regex_finds_nothing_in_this_prose_cv() -> None:
    rules = RulesClaimExtractor(as_of=AS_OF).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=PROSE_CV,
    )

    assert rules.claims == ()


def test_the_model_extracts_claims_from_every_role() -> None:
    result, completion = _extract(_FULL_PAYLOAD)

    contexts = [c.context for c in result.claims]
    assert any("dbt models" in t for t in contexts)
    assert any("Looker dashboards" in t for t in contexts)
    assert {c.employer for c in result.claims} == {
        "Northwind Analytics Ltd",
        "Blue Harbour Retail",
    }
    assert completion.calls == 1
    assert completion.last_request is not None
    assert "UNTRUSTED_CV" in completion.last_request.user


def test_an_unverifiable_quote_is_dropped_and_counted() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    assert all("CUDA kernel" not in c.context for c in result.claims)
    assert result.dropped_unverifiable == 1


def test_every_span_round_trips_to_its_quote() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    by_id = {span.id: span for span in result.spans}
    assert result.claims
    for claim in result.claims:
        assert claim.source_span_ids
        span = by_id[claim.source_span_ids[0]]
        assert PROSE_CV[span.start_offset : span.end_offset] == claim.context
        assert span.text == claim.context


def test_recency_and_duration_come_from_parsed_role_dates_not_the_model() -> None:
    payload = {
        "roles": [
            _role(
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
                date_range_quote="January 2023 – Present",
                claims=[
                    _claim(
                        (
                            "Owned dbt models that cover the core order and "
                            "inventory marts in production."
                        ),
                        competency="dbt",
                    )
                ],
            ),
            _role(
                employer="Blue Harbour Retail",
                title="Data Analyst",
                date_range_quote="March 2020 – December 2022",
                claims=[
                    _claim(
                        (
                            "Built Looker dashboards for store performance and "
                            "inventory turn."
                        ),
                        competency="bi",
                    )
                ],
            ),
        ]
    }
    # If a model tries to assert recency, the field is not even read.
    payload["roles"][1]["recency_signal"] = "recent"  # type: ignore[index]

    result, _ = _extract(payload)

    by_employer = {c.employer: c for c in result.claims}
    assert by_employer["Northwind Analytics Ltd"].recency_signal == "recent"
    assert by_employer["Northwind Analytics Ltd"].duration_signal.endswith("y")
    assert by_employer["Northwind Analytics Ltd"].period_start == date(2023, 1, 1)
    assert by_employer["Northwind Analytics Ltd"].period_end is None
    assert by_employer["Blue Harbour Retail"].recency_signal in {"mid", "old"}
    assert by_employer["Blue Harbour Retail"].recency_signal != "recent"
    assert by_employer["Blue Harbour Retail"].period_start == date(2020, 3, 1)
    assert by_employer["Blue Harbour Retail"].period_end == date(2022, 12, 1)


def test_claim_structure_carries_scope_technologies_and_outcome() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    dbt = next(c for c in result.claims if "dbt models" in c.context)
    assert dbt.competency == "dbt"
    assert dbt.scope == "production marts"
    assert "dbt" in dbt.technologies
    assert "inventory marts" in dbt.outcome


def test_falls_back_to_the_rules_result_when_nothing_verifies() -> None:
    bulleted = normalise_text(
        "Experience\n"
        "Acme — Engineer\n"
        "January 2023 – Present\n"
        "- Owned dbt models in production\n"
    )
    payload = {
        "roles": [
            _role(
                employer="Invented Corp",
                title="CTO",
                date_range_quote="January 1999 – Present",
                claims=[_claim("invented entirely")],
            )
        ]
    }

    result, _ = _extract(payload, text=bulleted)

    assert any("dbt models" in c.context for c in result.claims)
    assert result.dropped_unverifiable == 1
