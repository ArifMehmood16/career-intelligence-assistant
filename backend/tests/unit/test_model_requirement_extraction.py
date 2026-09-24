"""PLAN 13C.2b — the model extracts; the server verifies the quote.

The delivered model extractor ran the rules extractor first and then discarded
every model requirement whose text was not already in the rules output. It could
only remove what the regex had found, never find what the regex missed, so a
prose advert produced nothing at all.

The model now returns a verbatim quote and the kind of item it is. The server
locates the quote in the stored text and builds the span from those offsets.
Anything that does not verify is dropped and counted — never repaired, never
fuzzy-matched. That verification is also the prompt-injection defence.
"""

from __future__ import annotations

import json
from pathlib import Path

from career_assistant.adapters.extraction.model_backed import ModelRequirementExtractor
from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.domain.candidate_spans import candidate_units, span_id
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.mapping import map_requirements
from career_assistant.domain.normalisation import normalise_text
from career_assistant.domain.requirements import ItemType

ROOT = Path(__file__).resolve().parents[3]
JD_DIR = ROOT / "sample-data" / "fixtures" / "job-descriptions"

PROSE_ADVERT = normalise_text(
    "About the job\n"
    "We are hiring a forward deployed engineer to run agents in production.\n"
    "You will need strong experience with APIs, JSON and webhooks.\n"
    "You should be comfortable reading a failing run trace.\n"
    "The salary is 70,000 to 80,000 pounds depending on experience.\n"
    "This is not a platform support role.\n"
)

PACKAGE_ADVERT = normalise_text(
    "You will need strong experience with APIs, JSON and webhooks.\n"
    "Package and practicalities\n"
    "£70,000 - £80,000 depending on experience\n"
    "Share options, awarded on performance\n"
    "Delivery commission once you lead client accounts\n"
    "Remote (UK) with quarterly team days in Newcastle, travel and hotels "
    "covered; London co-working available\n"
    "Full-time employee role: applicants must have the right to work in the UK\n"
)


class _SequencedCompletion:
    """Returns each payload in order; the last one repeats if called again."""

    def __init__(self, payloads: tuple[dict[str, object], ...]) -> None:
        self._payloads = payloads
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
        payload = self._payloads[min(self.calls - 1, len(self._payloads) - 1)]
        return CompletionResult(
            text=json.dumps(payload),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


class _ScriptedCompletion:
    """Returns a fixed structured payload; records what it was asked."""

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


def _item(issued: str, item_type: str, *, must_have: bool = True, competency: str = ""):
    return {
        "spanId": issued,
        "item_type": item_type,
        "must_have": must_have,
        "competency": competency,
    }


def _id_for(text: str, needle: str, document_id: str = "doc-jd") -> str:
    for start, end, unit in candidate_units(text):
        if needle in unit:
            return span_id(document_id, start, end)
    raise AssertionError(needle)


def _classify(
    text: str,
    kinds: dict[str, str],
    *,
    document_id: str = "doc-jd",
    extra: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for start, end, unit in candidate_units(text):
        kind = "non_requirement"
        for needle, named in kinds.items():
            if needle in unit:
                kind = named
                break
        items.append(
            _item(
                span_id(document_id, start, end),
                kind,
                must_have=kind in {"requirement", "responsibility"},
            )
        )
    items.extend(extra)
    return {"classifications": items}


_PROSE_KINDS = {
    "APIs, JSON": "requirement",
    "failing run trace": "responsibility",
    "salary": "benefit",
    "platform support": "non_requirement",
}

_FULL_PAYLOAD = _classify(
    PROSE_ADVERT,
    _PROSE_KINDS,
    extra=(_item("other-doc:0:12", "requirement"),),
)


def _extract(payload: dict[str, object], text: str = PROSE_ADVERT):
    completion = _ScriptedCompletion(payload)
    result = ModelRequirementExtractor(completion).extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=text,
    )
    return result, completion


def test_one_line_with_two_sentences_is_two_spans() -> None:
    """PLAN 13D.6c — the server splits a line; the model does not merge it."""
    text = normalise_text("Know Python. Know SQL.\n")
    units = [unit for _, _, unit in candidate_units(text)]
    assert units == ["Know Python.", "Know SQL."]


def test_the_regex_finds_nothing_in_this_advert() -> None:
    """The baseline the model has to beat — no bullets, so no rule output."""
    rules = RulesRequirementExtractor().extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=PROSE_ADVERT,
    )

    assert rules.requirements == ()


def test_the_model_finds_prose_requirements_the_regex_cannot() -> None:
    result, completion = _extract(_FULL_PAYLOAD)

    texts = [r.text for r in result.requirements]
    assert any("APIs, JSON and webhooks" in t for t in texts)
    assert any("failing run trace" in t for t in texts)
    assert completion.calls == 1
    assert completion.last_request is not None
    assert "UNTRUSTED_JOB_DESCRIPTION" in completion.last_request.user
    assert completion.last_request.max_output_tokens == 4096


def test_requirement_extraction_classifies_spans_in_bounded_batches() -> None:
    """A long advert is split. Each batch still uses the output cap."""
    text = normalise_text(
        "\n".join(
            f"You will need skill number {index} in production." for index in range(4)
        )
    )
    completion = _ScriptedCompletion(_label_every_span(text, "requirement"))
    result = ModelRequirementExtractor(completion, batch_size=2).extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=text,
    )
    assert completion.calls == 2
    assert result.complete is True
    assert len(result.requirements) == 4
    assert completion.last_request is not None
    assert completion.last_request.max_output_tokens == 4096


def test_an_unknown_span_id_is_dropped_and_counted() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    assert all("other-doc" not in r.source_span_id for r in result.requirements)
    assert result.dropped_unverifiable == 1
    assert result.complete is True


def test_every_span_round_trips_to_its_quote() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    by_id = {span.id: span for span in result.spans}
    assert result.requirements
    for requirement in result.requirements:
        span = by_id[requirement.source_span_id]
        assert PROSE_ADVERT[span.start_offset : span.end_offset] == requirement.text
        assert span.text == requirement.text


def test_item_types_from_the_model_are_preserved_and_only_some_are_scored() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    kinds = {r.item_type for r in result.requirements}
    assert ItemType.BENEFIT in kinds
    assert ItemType.NON_REQUIREMENT in kinds

    mappings = map_requirements(result.requirements, [])
    assert len(mappings) == 2
    assert all(
        r.is_scoreable
        for r in result.requirements
        if r.id in {m.requirement_id for m in mappings}
    )


def test_competency_is_the_models_open_vocabulary_not_the_keyword_list() -> None:
    text = normalise_text(
        "You will need strong experience with APIs, JSON and webhooks.\n"
    )
    payload = {
        "classifications": [
            _item(
                _id_for(text, "APIs, JSON"),
                "requirement",
                competency="forward-deployed-engineering",
            )
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.requirements[0].competency == "forward-deployed-engineering"


def test_seniority_and_vagueness_are_read_from_the_verified_quote() -> None:
    text = normalise_text(
        "We need a senior engineer with ownership of outcomes end to end.\n"
    )
    payload = {
        "classifications": [
            _item(
                _id_for(text, "senior engineer"),
                "requirement",
            )
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.requirements[0].seniority_signal == "senior"
    assert result.requirements[0].is_vague is True


def test_an_injected_instruction_cannot_invent_a_requirement() -> None:
    """The model obeys the injection; verification is what stops it."""
    text = normalise_text((JD_DIR / "jd-injection-attempt.txt").read_text())
    kinds = {
        "dbt": "requirement",
        "SQL": "requirement",
        "Looker": "requirement",
        "Retail": "requirement",
    }
    payload = _classify(
        text,
        kinds,
        extra=(
            _item("other-doc:0:8", "requirement"),
            _item("fit-score-is-100", "requirement"),
            _item("cuda-span", "requirement"),
        ),
    )

    result, _ = _extract(payload, text=text)

    joined = " ".join(requirement.text.lower() for requirement in result.requirements)
    assert "fit score is 100" not in joined
    scored = [
        requirement.text.lower()
        for requirement in result.requirements
        if requirement.is_scoreable
    ]
    assert any("dbt" in item for item in scored)
    assert not any("cuda" in item or "ros2" in item for item in scored)
    assert not any("perfect match" in item for item in scored)
    assert result.dropped_unverifiable == 3
    assert result.complete is True


def test_a_quote_the_document_does_not_contain_is_never_repaired() -> None:
    payload = {
        "classifications": [
            _item("not-a-server-span", "requirement"),
        ]
    }

    result, _ = _extract(payload)

    assert result.requirements == ()
    assert result.complete is False
    assert result.dropped_unverifiable >= 1


def test_markdown_survives_without_the_model_copying_markers() -> None:
    """PLAN 13D.6c — the model returns a span id, not the asterisks."""
    text = normalise_text(
        "* **Python Proficiency:** build services in Python\n"
        "You will be responsible for:\n"
        "Operate the production platform\n"
        "Pension, holiday and shares\n"
        "Hybrid working in London and the right to work in the UK\n"
    )
    payload = _classify(
        text,
        {
            "Python Proficiency": "requirement",
            "responsible for": "responsibility",
            "Operate the production": "responsibility",
            "Pension": "benefit",
            "Hybrid working": "logistics",
        },
    )
    assert "*" not in json.dumps(payload)
    result, _ = _extract(payload, text=text)
    assert result.complete is True
    texts = [requirement.text for requirement in result.requirements]
    assert any("Python Proficiency" in item for item in texts)
    heading = next(
        item for item in result.requirements if "responsible for" in item.text
    )
    assert heading.item_type is ItemType.NON_REQUIREMENT
    assert heading.is_scoreable is False
    mappings = map_requirements(result.requirements, [])
    mapped = {
        requirement.text
        for requirement in result.requirements
        if requirement.id in {row.requirement_id for row in mappings}
    }
    assert any("Python Proficiency" in item for item in mapped)
    assert any("Operate the production" in item for item in mapped)
    assert not any(
        "Pension" in item or "Hybrid" in item or "responsible" in item
        for item in mapped
    )


def test_a_partial_classification_is_not_a_complete_extraction() -> None:
    """PLAN 13D.6c — one accepted span does not stand in for the document."""
    payload = {
        "classifications": [
            _item(_id_for(PROSE_ADVERT, "APIs, JSON"), "requirement", competency="api")
        ]
    }
    result, _ = _extract(payload)
    assert any("APIs" in requirement.text for requirement in result.requirements)
    assert result.complete is False


def test_a_duplicated_span_id_is_rejected() -> None:
    issued = _id_for(PROSE_ADVERT, "APIs, JSON")
    payload = {
        "classifications": [
            _item(issued, "requirement"),
            _item(issued, "benefit"),
        ]
    }
    result, _ = _extract(payload)
    assert all(
        requirement.source_span_id != issued for requirement in result.requirements
    )
    assert result.complete is False


def test_falls_back_to_the_rules_result_when_nothing_verifies() -> None:
    bulleted = normalise_text("Requirements\n- Own production for live agents\n")
    payload = {"classifications": [_item("invented-span", "requirement")]}

    result, _ = _extract(payload, text=bulleted)

    assert result.requirements == ()
    assert result.complete is False


def test_the_system_prompt_teaches_the_model_to_structure_package_lines() -> None:
    """Pay, equity and location are language, not a regex. The prompt must say so."""
    result, completion = _extract(_FULL_PAYLOAD)

    assert result.requirements
    assert completion.last_request is not None
    system = completion.last_request.system.lower()
    schema = completion.last_request.json_schema
    assert schema is not None
    item_type = schema["properties"]["classifications"]["items"]["properties"][
        "item_type"
    ]
    assert "spanId" in schema["properties"]["classifications"]["items"]["properties"]
    description = str(item_type.get("description", "")).lower()

    assert "share options" in system
    assert "right to work" in system
    assert "must_have is priority" in system
    assert "benefit" in description
    assert "logistics" in description
    assert "salary" in description


def test_classification_instructions_follow_the_untrusted_job_text() -> None:
    """A long advert buries a system prompt; restating kind after the JD is the ask."""
    _, completion = _extract(_FULL_PAYLOAD)

    assert completion.last_request is not None
    user = completion.last_request.user
    marker = "UNTRUSTED_JOB_DESCRIPTION_END"
    assert marker in user
    after = user.split(marker, 1)[1].lower()
    assert "benefit" in after
    assert "logistics" in after
    assert "requirement" in after


def test_a_package_block_is_extracted_structured_and_not_scored() -> None:
    payload = _classify(
        PACKAGE_ADVERT,
        {
            "APIs, JSON": "requirement",
            "£70,000": "benefit",
            "Share options": "benefit",
            "Delivery commission": "benefit",
            "Remote (UK)": "logistics",
            "right to work": "logistics",
            "Package and practicalities": "non_requirement",
        },
    )

    result, _ = _extract(payload, text=PACKAGE_ADVERT)

    by_text = {r.text: r.item_type for r in result.requirements}
    assert by_text["£70,000 - £80,000 depending on experience"] is ItemType.BENEFIT
    assert by_text["Share options, awarded on performance"] is ItemType.BENEFIT
    assert (
        by_text["Delivery commission once you lead client accounts"] is ItemType.BENEFIT
    )
    assert any(kind is ItemType.LOGISTICS for kind in by_text.values())
    assert ItemType.REQUIREMENT in by_text.values()

    mappings = map_requirements(result.requirements, [])
    mapped_text = {
        req.text
        for req in result.requirements
        if req.id in {row.requirement_id for row in mappings}
    }
    assert mapped_text == {
        "You will need strong experience with APIs, JSON and webhooks."
    }


AVIVA_LIKE_ADVERT = normalise_text(
    "A bit about the job:\n"
    "You will contribute directly to the delivery velocity of our Applied AI "
    "Engineering team, building well-tested, high-quality code for multi-agent "
    "systems, context engineering and AI evaluation under the close guidance of "
    "lead engineers.\n"
    "You will be responsible for:\n"
    "Own production releases for agent workflows.\n"
    "Skills and experience we're looking for:\n"
    "You'll bring experience in many of these areas:\n"
    "GenAI Frameworks: Exposure to frameworks like AWS Strands, OpenAI Agents "
    "SDK, Google ADK, DSPy or similar libraries (LangChain/LangGraph, LlamaIndex).\n"
    "Why Aviva:\n"
    "This is an opportunity to help build AI in a highly trusted environment, "
    "where customer outcomes, governance and responsible innovation matter.\n"
    "You'll join a business with proven AI capability, significant digital reach, "
    "modern technology foundations and the ambition to scale AI across the "
    "organisation.\n"
)


def test_about_why_headings_and_pitch_are_not_scoreable_when_model_mislabels() -> None:
    """Headings and About/Why body copy are not gaps — even if the model says so."""
    # Model wrongly calls every line a responsibility/requirement.
    payload = _classify(
        AVIVA_LIKE_ADVERT,
        {
            "A bit about the job:": "responsibility",
            "contribute directly": "responsibility",
            "You will be responsible for:": "responsibility",
            "Own production releases": "responsibility",
            "Skills and experience": "responsibility",
            "You'll bring experience": "responsibility",
            "GenAI Frameworks": "requirement",
            "Why Aviva:": "responsibility",
            "This is an opportunity": "responsibility",
            "You'll join a business": "responsibility",
        },
    )

    result, _ = _extract(payload, text=AVIVA_LIKE_ADVERT)

    scoreable = [req for req in result.requirements if req.is_scoreable]
    scoreable_text = " ".join(req.text for req in scoreable)
    assert "Own production releases" in scoreable_text
    assert "GenAI Frameworks" in scoreable_text
    for marker in (
        "A bit about the job:",
        "You will be responsible for:",
        "Skills and experience we're looking for:",
        "You'll bring experience in many of these areas:",
        "Why Aviva:",
        "contribute directly to the delivery velocity",
        "This is an opportunity",
        "You'll join a business",
    ):
        assert all(marker not in req.text for req in scoreable), marker


SECTIONED_PACKAGE = normalise_text(
    "Benefits:\n"
    "£70,000 - £80,000 depending on experience\n"
    "Logistics:\n"
    "Remote (UK) with quarterly team days in Newcastle\n"
    "## Benefits\n"
    "Share options, awarded on performance\n"
    "## Logistics\n"
    "Full-time employee role with the right to work in the UK\n"
    "## Requirements\n"
    "You will need strong experience with APIs, JSON and webhooks.\n"
)


def _label_every_span(text: str, kind: str) -> dict[str, object]:
    return {
        "classifications": [
            _item(span_id("doc-jd", start, end), kind, must_have=True)
            for start, end, _unit in candidate_units(text)
        ]
    }


def test_benefit_and_logistics_sections_stay_unscoreable_when_model_mislabels() -> None:
    """Colon and Markdown headings keep package lines out of the score."""
    result, _ = _extract(
        _label_every_span(SECTIONED_PACKAGE, "requirement"), text=SECTIONED_PACKAGE
    )

    by_text = {requirement.text: requirement for requirement in result.requirements}
    salary = by_text["£70,000 - £80,000 depending on experience"]
    remote = by_text["Remote (UK) with quarterly team days in Newcastle"]
    shares = by_text["Share options, awarded on performance"]
    right_to_work = by_text["Full-time employee role with the right to work in the UK"]
    skill = by_text["You will need strong experience with APIs, JSON and webhooks."]
    assert salary.item_type is ItemType.BENEFIT
    assert remote.item_type is ItemType.LOGISTICS
    assert shares.item_type is ItemType.BENEFIT
    assert right_to_work.item_type is ItemType.LOGISTICS
    assert skill.item_type is ItemType.REQUIREMENT
    for line in (salary, remote, shares, right_to_work):
        assert line.must_have is False
        assert line.is_scoreable is False
    for heading in (
        "Benefits:",
        "Logistics:",
        "## Benefits",
        "## Logistics",
        "## Requirements",
    ):
        assert by_text[heading].is_scoreable is False
    mapped = {
        requirement.text
        for requirement in result.requirements
        if requirement.id
        in {row.requirement_id for row in map_requirements(result.requirements, [])}
    }
    assert mapped == {skill.text}


_PACKAGE_KINDS = {
    "APIs, JSON": "requirement",
    "£70,000": "benefit",
    "Share options": "benefit",
    "Delivery commission": "benefit",
    "Remote (UK)": "logistics",
    "right to work": "logistics",
    "Package and practicalities": "non_requirement",
}


def _package_items() -> list[dict[str, object]]:
    payload = _classify(PACKAGE_ADVERT, _PACKAGE_KINDS)
    items = payload["classifications"]
    assert isinstance(items, list)
    return items


def _with_field(items: list[dict[str, object]], issued: str, **fields: object):
    rewritten: list[dict[str, object]] = []
    for item in items:
        if item["spanId"] != issued:
            rewritten.append(item)
            continue
        clone = dict(item)
        for key, value in fields.items():
            if value is _DROP:
                clone.pop(key, None)
            else:
                clone[key] = value
        rewritten.append(clone)
    return rewritten


class _Drop:
    pass


_DROP = _Drop()


def test_an_invalid_item_type_is_not_a_scoreable_requirement() -> None:
    """A missing or unknown kind must not turn pay or remote work into a requirement."""
    salary = _id_for(PACKAGE_ADVERT, "£70,000")
    remote = _id_for(PACKAGE_ADVERT, "Remote (UK)")
    spoils: tuple[tuple[object, object], ...] = (
        (_DROP, "logistics"),
        (None, "logistics"),
        (1, "logistics"),
        ("perk", _DROP),
    )
    for salary_type, remote_type in spoils:
        items = _with_field(_package_items(), salary, item_type=salary_type)
        items = _with_field(items, remote, item_type=remote_type)
        result, completion = _extract({"classifications": items}, text=PACKAGE_ADVERT)
        mapped = {
            requirement.text
            for requirement in result.requirements
            if requirement.id
            in {row.requirement_id for row in map_requirements(result.requirements, [])}
        }
        assert result.complete is False
        assert completion.calls == 2
        assert not any("£70,000" in text or "Remote (UK)" in text for text in mapped)
        assert all(
            "£70,000" not in requirement.text
            and "Remote (UK)" not in requirement.text
            or not requirement.is_scoreable
            for requirement in result.requirements
        )


def test_a_missing_or_non_boolean_must_have_is_not_accepted() -> None:
    text = normalise_text(
        "You will need strong experience with APIs, JSON and webhooks.\n"
    )
    issued = _id_for(text, "APIs, JSON")
    for must_have in (_DROP, None, "true", 1):
        item: dict[str, object] = {
            "spanId": issued,
            "item_type": "requirement",
            "competency": "api",
        }
        if must_have is not _DROP:
            item["must_have"] = must_have
        result, _ = _extract({"classifications": [item]}, text=text)
        assert result.complete is False
        assert result.requirements == ()
        assert not any(requirement.must_have for requirement in result.requirements)


def test_one_retry_accepts_a_later_valid_classification() -> None:
    salary = _id_for(PACKAGE_ADVERT, "£70,000")
    remote = _id_for(PACKAGE_ADVERT, "Remote (UK)")
    skill = _id_for(PACKAGE_ADVERT, "APIs, JSON")
    first = _with_field(_package_items(), salary, item_type="perk")
    first = _with_field(first, remote, item_type=_DROP)
    second = {
        "classifications": [
            _item(salary, "benefit", must_have=False),
            _item(remote, "logistics", must_have=False),
        ]
    }
    completion = _SequencedCompletion(
        ({"classifications": first}, second),
    )
    result = ModelRequirementExtractor(completion).extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=PACKAGE_ADVERT,
    )
    assert completion.calls == 2
    retry = completion.requests[1].user
    assert f"SPAN {salary}" in retry
    assert f"SPAN {remote}" in retry
    assert f"SPAN {skill}" not in retry
    assert result.complete is True
    by_text = {requirement.text: requirement for requirement in result.requirements}
    assert by_text["£70,000 - £80,000 depending on experience"].item_type is (
        ItemType.BENEFIT
    )
    remote_req = next(
        requirement
        for requirement in result.requirements
        if "Remote (UK)" in requirement.text
    )
    assert remote_req.item_type is ItemType.LOGISTICS
    mapped = {
        requirement.text
        for requirement in result.requirements
        if requirement.is_scoreable
    }
    assert mapped == {"You will need strong experience with APIs, JSON and webhooks."}
