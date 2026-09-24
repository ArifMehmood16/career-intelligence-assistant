"""PLAN 13D.6d — the server owns CV spans; the model classifies their ids.

Dates are parsed from the heading span in domain code. A skills list is not a
claim. Completeness covers scoreable evidence: rejected experience or project
assignments, unclassified employment or claim-like spans, and role headings
with no claims. Unclassified narrative, skills or education do not fail alone.
An unparsed date becomes undated without failing the job.
"""

from __future__ import annotations

import json
import re
from datetime import date

from career_assistant.adapters.extraction.claims_model import ModelClaimExtractor
from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.domain.candidate_spans import candidate_units, span_id
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
        self.requests: list[CompletionRequest] = []
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
        self.requests.append(request)
        self.last_request = request
        return CompletionResult(
            text=json.dumps(self._payload),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


def _span_ids_in_request(request: CompletionRequest) -> list[str]:
    return re.findall(r"SPAN ([0-9a-f-]{36})", request.user, flags=re.IGNORECASE)


class _BatchAwareCompletion:
    """Returns assignments only for span ids present in the request.

    Omits one configured id on its first appearance so the extractor must retry.
    """

    def __init__(
        self,
        by_span: dict[str, dict[str, object]],
        *,
        omit_once: str | None = None,
    ) -> None:
        self._by_span = by_span
        self._omit_once = omit_once
        self._omitted = False
        self.calls = 0
        self.requests: list[CompletionRequest] = []

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
        self.requests.append(request)
        assignments: list[dict[str, object]] = []
        for issued in _span_ids_in_request(request):
            if (
                self._omit_once is not None
                and issued == self._omit_once
                and not self._omitted
            ):
                self._omitted = True
                continue
            item = self._by_span.get(issued)
            if item is not None:
                assignments.append(item)
        return CompletionResult(
            text=json.dumps({"assignments": assignments}),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


def _ids(text: str, document_id: str = "doc-cv") -> dict[str, str]:
    found: dict[str, str] = {}
    for start, end, unit in candidate_units(text):
        found[unit] = span_id(document_id, start, end)
    return found


def _assign(
    issued: str,
    kind: str,
    *,
    role: str = "",
    employer: str = "",
    title: str = "",
    competency: str = "",
    scope: str = "",
    technologies: list[str] | None = None,
    outcome: str = "",
) -> dict[str, object]:
    item: dict[str, object] = {"spanId": issued, "kind": kind}
    if role:
        item["roleSpanId"] = role
    if employer:
        item["employer"] = employer
    if title:
        item["title"] = title
    if competency:
        item["competency"] = competency
    if scope:
        item["scope"] = scope
    if technologies:
        item["technologies"] = technologies
    if outcome:
        item["outcome"] = outcome
    return item


def _full_payload(text: str = PROSE_CV) -> dict[str, object]:
    ids = _ids(text)
    northwind = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    blue = ids["Blue Harbour Retail — Data Analyst, March 2020 – December 2022."]
    dbt = (
        "Owned dbt models that cover the core order and inventory marts in production."
    )
    snowflake = "Designed incremental models in Snowflake for daily sales reporting."
    looker = "Built Looker dashboards for store performance and inventory turn."
    return {
        "assignments": [
            _assign(ids["Alex Rivera."], "narrative"),
            _assign(ids["Analytics Engineer."], "narrative"),
            _assign(
                northwind,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(
                ids[dbt],
                "experience",
                role=northwind,
                competency="dbt",
                scope="production marts",
                technologies=["dbt"],
                outcome="core order and inventory marts in production",
            ),
            _assign(
                ids[snowflake],
                "experience",
                role=northwind,
                competency="sql",
                technologies=["Snowflake"],
            ),
            _assign(
                blue,
                "role_heading",
                employer="Blue Harbour Retail",
                title="Data Analyst",
            ),
            _assign(
                ids[looker],
                "experience",
                role=blue,
                competency="bi",
                technologies=["Looker"],
            ),
            _assign("other-doc:0:12", "experience", competency="cuda"),
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


def _six_role_cv() -> str:
    lines = ["Alex Rivera"]
    for index in range(6):
        year = 2014 + index
        end = "Present" if index == 5 else f"December {year}"
        lines.append(f"Employer {index} — Title {index}, January {year} – {end}")
        bullets = 3 if index < 5 else 2
        for bullet in range(bullets):
            lines.append(
                f"Delivered labelled outcome {index}-{bullet} for production systems."
            )
    lines.append("Skills: Python, SQL, Kubernetes")
    return normalise_text("\n".join(lines))


def test_the_regex_finds_nothing_in_this_prose_cv() -> None:
    rules = RulesClaimExtractor(as_of=AS_OF).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=PROSE_CV,
    )

    assert rules.claims == ()


def test_the_model_extracts_claims_from_every_role() -> None:
    result, completion = _extract(_full_payload())

    contexts = [c.context for c in result.claims]
    assert any("dbt models" in t for t in contexts)
    assert any("Looker dashboards" in t for t in contexts)
    assert {c.employer for c in result.claims} == {
        "Northwind Analytics Ltd",
        "Blue Harbour Retail",
    }
    assert result.complete is True
    assert result.roles_detected == 2
    assert result.roles_without_claims == 0
    assert result.spans_supplied == 7
    assert result.claims_accepted == 3
    assert completion.calls == 1
    assert completion.last_request is not None
    assert "UNTRUSTED_CV" in completion.last_request.user
    assert "SPAN " in completion.last_request.user
    assert re.search(
        r"SPAN [0-9a-f-]{36}",
        completion.last_request.user,
        re.IGNORECASE,
    )


def test_an_unknown_span_id_is_rejected() -> None:
    result, _ = _extract(_full_payload())

    assert all("CUDA" not in c.context for c in result.claims)
    assert all(
        all(not span_id.startswith("other-doc:") for span_id in c.source_span_ids)
        for c in result.claims
    )
    assert result.dropped_unverifiable == 1
    assert result.complete is True


def test_every_span_round_trips_to_stored_text() -> None:
    result, _ = _extract(_full_payload())

    by_id = {span.id: span for span in result.spans}
    assert result.claims
    for claim in result.claims:
        assert claim.source_span_ids
        span = by_id[claim.source_span_ids[0]]
        assert PROSE_CV[span.start_offset : span.end_offset] == claim.context
        assert span.text == claim.context


def test_recency_and_duration_come_from_parsed_role_dates_not_the_model() -> None:
    payload = _full_payload()
    assignments = payload["assignments"]
    assert isinstance(assignments, list)
    assignments[4]["recency_signal"] = "recent"

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
    result, _ = _extract(_full_payload())

    dbt = next(c for c in result.claims if "dbt models" in c.context)
    assert dbt.competency == "dbt"
    assert dbt.scope == "production marts"
    assert "dbt" in dbt.technologies
    assert "inventory marts" in dbt.outcome
    assert dbt.title == "Analytics Engineer"


def test_a_response_that_classifies_nothing_is_incomplete() -> None:
    bulleted = normalise_text(
        "Acme — Engineer, January 2023 – Present\n- Owned dbt models in production\n"
    )
    payload = {"assignments": [_assign("other-doc:0:8", "experience")]}

    result, _ = _extract(payload, text=bulleted)

    assert result.claims == ()
    assert result.complete is False
    assert result.dropped_unverifiable >= 1


def test_six_roles_and_seventeen_bullets_keep_their_associations() -> None:
    text = _six_role_cv()
    ids = _ids(text)
    assignments: list[dict[str, object]] = [
        _assign(ids["Alex Rivera"], "narrative"),
        _assign(ids["Skills: Python, SQL, Kubernetes"], "skills"),
    ]
    for index in range(6):
        year = 2014 + index
        end = "Present" if index == 5 else f"December {year}"
        heading = f"Employer {index} — Title {index}, January {year} – {end}"
        heading_id = ids[heading]
        assignments.append(
            _assign(
                heading_id,
                "role_heading",
                employer=f"Employer {index}",
                title=f"Title {index}",
            )
        )
        bullets = 3 if index < 5 else 2
        for bullet in range(bullets):
            line = (
                f"Delivered labelled outcome {index}-{bullet} for production systems."
            )
            assignments.append(_assign(ids[line], "experience", role=heading_id))

    result, _ = _extract({"assignments": assignments}, text=text)

    assert result.complete is True
    assert result.roles_detected == 6
    assert result.claims_accepted == 17
    assert result.roles_without_claims == 0
    assert all("Kubernetes" not in claim.context for claim in result.claims)
    for claim in result.claims:
        marker = claim.context.split("outcome ", 1)[1].split("-", 1)[0]
        assert claim.employer == f"Employer {marker}"
        assert claim.title == f"Title {marker}"
        assert claim.period_start == date(2014 + int(marker), 1, 1)


def test_a_project_claim_stays_on_the_project_not_the_nearest_job() -> None:
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Owned dbt models in production.\n"
        "Portfolio — Side Project, January 2019 – June 2019.\n"
        "Shipped a portfolio orchestration tool used by the team.\n"
    )
    ids = _ids(text)
    job = ids["Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."]
    project = ids["Portfolio — Side Project, January 2019 – June 2019."]
    payload = {
        "assignments": [
            _assign(
                job,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(
                ids["Owned dbt models in production."],
                "experience",
                role=job,
            ),
            _assign(
                project,
                "project_heading",
                employer="Portfolio",
                title="Side Project",
            ),
            _assign(
                ids["Shipped a portfolio orchestration tool used by the team."],
                "project",
                role=project,
            ),
        ]
    }

    result, _ = _extract(payload, text=text)

    shipped = next(c for c in result.claims if "orchestration" in c.context)
    assert shipped.employer == "Portfolio"
    assert shipped.title == "Side Project"
    assert shipped.employer != "Northwind Analytics Ltd"
    assert result.complete is True


def test_formatting_does_not_drop_a_server_owned_span() -> None:
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "* **Owned dbt models in production.**\n"
    )
    ids = _ids(text)
    heading = "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    bullet = next(unit for unit in ids if "Owned dbt" in unit)
    payload = {
        "assignments": [
            _assign(
                ids[heading],
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(ids[bullet], "experience", role=ids[heading], competency="dbt"),
        ]
    }

    result, completion = _extract(payload, text=text)

    assert result.complete is True
    assert result.claims
    assert "Owned dbt" in result.claims[0].context
    assert completion.last_request is not None
    assert "*" not in json.dumps(payload)
    assert "SPAN " in completion.last_request.user


def test_only_the_first_role_fails_completeness() -> None:
    text = _six_role_cv()
    ids = _ids(text)
    heading = ids["Employer 0 — Title 0, January 2014 – December 2014"]
    assignments = [
        _assign(
            heading,
            "role_heading",
            employer="Employer 0",
            title="Title 0",
        )
    ]
    for bullet in range(3):
        line = f"Delivered labelled outcome 0-{bullet} for production systems."
        assignments.append(_assign(ids[line], "experience", role=heading))

    result, _ = _extract({"assignments": assignments}, text=text)

    assert result.complete is False
    assert result.claims_accepted == 3
    assert result.spans_supplied > result.claims_accepted + 1


def test_empty_role_headings_alone_do_not_fail_when_scoreable_claims_attach() -> None:
    """Extra role_heading labels are tracked; they do not fail a complete claim set."""
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Owned dbt models in production.\n"
        "Contoso Ltd — Intern, January 2019 – June 2019.\n"
    )
    ids = _ids(text)
    northwind = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    contoso = ids["Contoso Ltd — Intern, January 2019 – June 2019."]
    payload = {
        "assignments": [
            _assign(
                northwind,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(
                ids["Owned dbt models in production."],
                "experience",
                role=northwind,
            ),
            _assign(
                contoso,
                "role_heading",
                employer="Contoso Ltd",
                title="Intern",
            ),
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.complete is True
    assert result.roles_detected == 2
    assert result.roles_without_claims == 1
    assert result.claims_accepted == 1


def test_a_reference_line_is_not_a_claim_and_does_not_attach() -> None:
    """A model experience label does not turn boilerplate into role evidence."""
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Built Looker dashboards for store performance.\n"
        "References available on request.\n"
    )
    ids = _ids(text)
    heading = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    payload = {
        "assignments": [
            _assign(
                heading,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(
                ids["Built Looker dashboards for store performance."],
                "experience",
            ),
            _assign(ids["References available on request."], "experience"),
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.complete is True
    assert result.claims_accepted == 1
    assert result.claims[0].context.startswith("Built Looker")
    assert result.claims[0].employer == "Northwind Analytics Ltd"
    assert all("References" not in claim.context for claim in result.claims)


def test_a_duplicated_span_is_rejected_and_the_retry_is_kept() -> None:
    """Contradictory labels are not resolved by response order."""
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Built Looker dashboards for store performance.\n"
    )
    ids = _ids(text)
    heading = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    bullet = ids["Built Looker dashboards for store performance."]
    first = {
        "assignments": [
            _assign(
                heading,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(bullet, "experience"),
            _assign(bullet, "narrative"),
        ]
    }
    second = {"assignments": [_assign(bullet, "experience", role=heading)]}
    completion = _SequencedCompletion((first, second))
    result = ModelClaimExtractor(completion, as_of=AS_OF).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )
    assert completion.calls == 2
    assert result.complete is True
    assert result.claims_accepted == 1
    assert result.claims[0].context.startswith("Built Looker")
    assert result.claims[0].employer == "Northwind Analytics Ltd"


class _SequencedCompletion:
    def __init__(self, payloads: tuple[dict[str, object], ...]) -> None:
        self._payloads = payloads
        self.calls = 0

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
        payload = self._payloads[min(self.calls - 1, len(self._payloads) - 1)]
        return CompletionResult(
            text=json.dumps(payload),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


def test_claim_with_missing_role_span_attaches_to_nearest_heading() -> None:
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Owned dbt models in production.\n"
    )
    ids = _ids(text)
    heading = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    payload = {
        "assignments": [
            _assign(
                heading,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            # No roleSpanId — server recovers the preceding employment heading.
            _assign(ids["Owned dbt models in production."], "experience"),
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.complete is True
    assert result.claims_accepted == 1
    assert result.claims[0].employer == "Northwind Analytics Ltd"


def test_orphan_project_claims_fall_back_to_role_without_failing() -> None:
    """A few unattachable claims must not fail a CV that otherwise extracted."""
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Owned dbt models in production.\n"
        "Side work delivered without a project heading line.\n"
    )
    ids = _ids(text)
    heading = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    payload = {
        "assignments": [
            _assign(
                heading,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(
                ids["Owned dbt models in production."],
                "experience",
                role=heading,
            ),
            # Project kind with no project_heading — recover onto the role.
            _assign(
                ids["Side work delivered without a project heading line."],
                "project",
            ),
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.complete is True
    assert result.claims_accepted == 2
    assert {c.employer for c in result.claims} == {"Northwind Analytics Ltd"}


def test_an_unparsed_role_date_stays_undated_without_failing_completeness() -> None:
    """PLAN 13D.6d — lost dates become undated; they do not fail the job alone."""
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, 2023 to now.\n"
        "Owned dbt models in production.\n"
    )
    ids = _ids(text)
    heading = ids["Northwind Analytics Ltd — Analytics Engineer, 2023 to now."]
    payload = {
        "assignments": [
            _assign(
                heading,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(
                ids["Owned dbt models in production."],
                "experience",
                role=heading,
            ),
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.complete is True
    assert result.claims
    assert result.claims[0].period_start is None
    assert result.claims[0].recency_signal == "undated"


def test_unclassified_skills_and_education_do_not_fail_completeness() -> None:
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Owned dbt models in production.\n"
        "Skills: Python, SQL, Kubernetes\n"
        "BSc Mathematics — Synthetic University, 2019\n"
    )
    ids = _ids(text)
    heading = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    payload = {
        "assignments": [
            _assign(
                heading,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(
                ids["Owned dbt models in production."],
                "experience",
                role=heading,
            ),
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.complete is True
    assert result.claims_accepted == 1
    assert result.spans_supplied > 2


def test_iso_role_dates_are_parsed() -> None:
    from career_assistant.domain.recency import parse_date_range

    parsed = parse_date_range("Senior Analytics Engineer — Acme — 2022-01 — Present")
    assert parsed is not None
    assert parsed.start == date(2022, 1, 1)
    assert parsed.end is None


def _assignments_covering(text: str) -> dict[str, dict[str, object]]:
    """Label every unit so a batched extractor can finish the six-role CV."""
    ids = _ids(text)
    by_span: dict[str, dict[str, object]] = {}
    current_role = ""
    for unit, issued in ids.items():
        if " — Title " in unit and "January" in unit:
            employer = unit.split(" — ", 1)[0]
            title = unit.split(" — ", 1)[1].split(",", 1)[0]
            by_span[issued] = _assign(
                issued, "role_heading", employer=employer, title=title
            )
            current_role = issued
        elif unit.startswith("Delivered labelled"):
            by_span[issued] = _assign(issued, "experience", role=current_role)
        elif unit.startswith("Skills:"):
            by_span[issued] = _assign(issued, "skills")
        else:
            by_span[issued] = _assign(issued, "narrative")
    return by_span


def test_claim_extraction_classifies_in_bounded_batches() -> None:
    """One response cannot cover a real CV; the adapter must split the work."""
    text = _six_role_cv()
    by_span = _assignments_covering(text)
    completion = _BatchAwareCompletion(by_span)
    result = ModelClaimExtractor(completion, as_of=AS_OF, batch_size=5).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )

    assert result.complete is True
    assert result.claims_accepted == 17
    assert completion.calls >= 4
    for request in completion.requests:
        assert len(_span_ids_in_request(request)) <= 5


def test_missing_scoreable_span_is_retried_once() -> None:
    text = _six_role_cv()
    by_span = _assignments_covering(text)
    omit = next(
        issued for issued, item in by_span.items() if item.get("kind") == "experience"
    )
    completion = _BatchAwareCompletion(by_span, omit_once=omit)
    result = ModelClaimExtractor(completion, as_of=AS_OF, batch_size=8).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )

    assert completion._omitted is True
    assert completion.calls > len(by_span) // 8
    assert result.complete is True
    assert result.claims_accepted == 17


class _TruncatingThenOkCompletion:
    """First response for a large batch is truncated JSON; splits must recover."""

    def __init__(self, by_span: dict[str, dict[str, object]]) -> None:
        self._by_span = by_span
        self.calls = 0
        self.finish_reasons: list[str | None] = []

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=8192,
            max_output_tokens=4096,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls += 1
        ids = _span_ids_in_request(request)
        # First call for 4+ spans returns truncated garbage at the token cap.
        if self.calls == 1 and len(ids) >= 4:
            self.finish_reasons.append("length")
            return CompletionResult(
                text="{not-json",
                provider_id="scripted",
                model_tag="scripted-v1",
                left_machine=False,
                output_tokens=request.max_output_tokens,
                finish_reason="length",
            )
        self.finish_reasons.append("stop")
        assignments = [self._by_span[i] for i in ids if i in self._by_span]
        return CompletionResult(
            text=json.dumps({"assignments": assignments}),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
            output_tokens=80,
            finish_reason="stop",
        )


def test_truncated_claim_batch_is_split_and_retried() -> None:
    text = normalise_text(
        "Employer 0 — Title 0, January 2020 – December 2020\n"
        "Delivered labelled outcome 0-0 for production systems.\n"
        "Delivered labelled outcome 0-1 for production systems.\n"
        "Delivered labelled outcome 0-2 for production systems.\n"
        "Skills: Python\n"
    )
    by_span = _assignments_covering(text)
    completion = _TruncatingThenOkCompletion(by_span)
    result = ModelClaimExtractor(completion, as_of=AS_OF, batch_size=5).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )

    assert "length" in completion.finish_reasons
    assert completion.calls >= 3
    assert result.complete is True
    assert result.claims_accepted == 3


def test_accounting_completion_records_extract_claims_purpose() -> None:
    from career_assistant.application.providers.accounting import (
        AccountingCompletion,
        CallAccountant,
    )

    text = normalise_text(
        "Employer 0 — Title 0, January 2020 – Present\n"
        "Delivered labelled outcome 0-0 for production systems.\n"
    )
    by_span = _assignments_covering(text)
    accountant = CallAccountant()
    wrapped = AccountingCompletion(
        _BatchAwareCompletion(by_span),
        accountant,
        workspace_id="ws-1",
        purpose="extract_claims",
    )
    result = ModelClaimExtractor(wrapped, as_of=AS_OF, batch_size=10).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )

    assert result.complete is True
    assert accountant.records
    assert all(
        r.metadata.get("purpose") == "extract_claims" for r in accountant.records
    )
    assert all(r.metadata.get("workspace_id") == "ws-1" for r in accountant.records)


def test_an_unclassified_dated_qualification_does_not_fail_completeness() -> None:
    """2026-09-24: a CV lists degrees with month ranges, the model has no education
    kind, and one skipped degree line failed the whole job as if it were a role."""
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Owned dbt models in production.\n"
        "MSc Data Science, Distinction — Synthetic University Sep 2021 – Sep 2022\n"
        "BEng Computer Engineering — Synthetic Institute Sep 2014 – Jun 2018\n"
    )
    ids = _ids(text)
    heading = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    payload = {
        "assignments": [
            _assign(
                heading,
                "role_heading",
                employer="Northwind Analytics Ltd",
                title="Analytics Engineer",
            ),
            _assign(
                ids["Owned dbt models in production."],
                "experience",
                role=heading,
            ),
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.complete is True
    assert result.claims_accepted == 1


def test_an_unclassified_dated_role_heading_still_fails_completeness() -> None:
    text = normalise_text(
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present.\n"
        "Owned dbt models in production.\n"
        "Southwind Data Ltd — Data Engineer, March 2019 – December 2022\n"
    )
    ids = _ids(text)
    heading = ids[
        "Northwind Analytics Ltd — Analytics Engineer, January 2023 – Present."
    ]
    payload = {
        "assignments": [
            _assign(heading, "role_heading", employer="Northwind Analytics Ltd"),
            _assign(ids["Owned dbt models in production."], "experience", role=heading),
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.complete is False
