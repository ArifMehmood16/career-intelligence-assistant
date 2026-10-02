"""Each hosted API accepts a different subset of JSON Schema (PLAN 18.1).

OpenAI's strict mode needs every property required and `additionalProperties:
false`; Anthropic's structured outputs need `additionalProperties: false` and do
not accept numeric, string or array-length constraints. Constraints the API cannot
enforce move into the description; the server still validates the full schema.
"""

from __future__ import annotations

import json

import pytest

from career_assistant.adapters.providers.schema_dialects import (
    anthropic_output_schema,
    drop_strict_mode_nulls,
    openai_strict_schema,
)
from career_assistant.application.contracts.base import VersionedContract
from career_assistant.application.contracts.chunking import (
    CoverLetterChunkResponse,
    CvChunkResponse,
    JobChunkResponse,
)
from career_assistant.application.contracts.judge import JudgeResponse

_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 4},
                    "quote": {"type": "string", "minLength": 1},
                    "note": {"type": "string", "description": "Optional."},
                },
                "required": ["score", "quote"],
            },
        }
    },
    "required": ["verdicts"],
}


def _item(schema: dict[str, object]) -> dict[str, object]:
    verdicts = schema["properties"]["verdicts"]  # type: ignore[index]
    return verdicts["items"]  # type: ignore[no-any-return,index]


def test_openai_strict_requires_every_property_and_forbids_extras() -> None:
    item = _item(openai_strict_schema(_SCHEMA))

    assert item["additionalProperties"] is False
    assert sorted(item["required"]) == ["note", "quote", "score"]  # type: ignore[arg-type]


def test_openai_strict_makes_an_optional_property_nullable() -> None:
    note = _item(openai_strict_schema(_SCHEMA))["properties"]["note"]  # type: ignore[index]

    assert note["type"] == ["string", "null"]


def test_anthropic_keeps_optional_properties_optional() -> None:
    item = _item(anthropic_output_schema(_SCHEMA))

    assert item["additionalProperties"] is False
    assert item["required"] == ["score", "quote"]
    assert item["properties"]["note"]["type"] == "string"  # type: ignore[index]


def test_unsupported_constraints_move_into_the_description() -> None:
    for adapt in (openai_strict_schema, anthropic_output_schema):
        adapted = adapt(_SCHEMA)
        score = _item(adapted)["properties"]["score"]  # type: ignore[index]
        verdicts = adapted["properties"]["verdicts"]  # type: ignore[index]

        assert "minimum" not in score and "maximum" not in score
        assert "minimum: 0" in score["description"]
        assert "maximum: 4" in score["description"]
        assert "minItems" not in verdicts
        assert "minItems: 1" in verdicts["description"]


def test_the_original_schema_is_not_modified() -> None:
    before = repr(_SCHEMA)
    openai_strict_schema(_SCHEMA)
    anthropic_output_schema(_SCHEMA)

    assert repr(_SCHEMA) == before


def test_definitions_and_any_of_members_are_adapted_too() -> None:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {"x": {"anyOf": [{"$ref": "#/$defs/Point"}, {"type": "null"}]}},
        "required": ["x"],
        "$defs": {
            "Point": {
                "type": "object",
                "properties": {"n": {"type": "integer", "maximum": 9}},
                "required": ["n"],
            }
        },
    }

    point = anthropic_output_schema(schema)["$defs"]["Point"]  # type: ignore[index]

    assert point["additionalProperties"] is False
    assert "maximum" not in point["properties"]["n"]


def test_nulls_strict_mode_forced_into_optional_properties_are_removed() -> None:
    reply = '{"verdicts": [{"score": 3, "quote": "led it", "note": null}]}'

    restored = json.loads(drop_strict_mode_nulls(reply, _SCHEMA))

    assert restored == {"verdicts": [{"score": 3, "quote": "led it"}]}


def test_a_null_the_original_schema_requires_is_kept() -> None:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {"level": {"type": ["string", "null"]}},
        "required": ["level"],
    }

    assert json.loads(drop_strict_mode_nulls('{"level": null}', schema)) == {
        "level": None
    }


def test_optional_nulls_inside_definitions_are_removed() -> None:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {"point": {"$ref": "#/$defs/Point"}},
        "required": ["point"],
        "$defs": {
            "Point": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "label": {"type": "string"}},
                "required": ["n"],
            }
        },
    }

    restored = json.loads(
        drop_strict_mode_nulls('{"point": {"n": 1, "label": null}}', schema)
    )

    assert restored == {"point": {"n": 1}}


def test_text_that_is_not_json_is_returned_unchanged() -> None:
    assert drop_strict_mode_nulls("not json", _SCHEMA) == "not json"


def test_defaulted_arrays_stay_arrays_instead_of_becoming_nullable() -> None:
    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
    }

    adapted = openai_strict_schema(schema)

    assert adapted["required"] == ["items"]
    assert adapted["properties"]["items"]["type"] == "array"
    assert "required" not in schema


def test_explicitly_nullable_arrays_keep_one_null_alternative() -> None:
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "anyOf": [
                    {"type": "array", "items": {"type": "string"}},
                    {"type": "null"},
                ]
            }
        },
    }

    adapted = openai_strict_schema(schema)

    assert (
        adapted["properties"]["items"]["anyOf"]
        == schema["properties"]["items"]["anyOf"]
    )


@pytest.mark.parametrize(
    "contract",
    [CvChunkResponse, JobChunkResponse, CoverLetterChunkResponse, JudgeResponse],
)
def test_real_analysis_contract_collections_do_not_acquire_null_types(
    contract: type[VersionedContract],
) -> None:
    original = contract.model_json_schema()
    adapted = openai_strict_schema(original)

    def inspect(before: object, after: object) -> None:
        if isinstance(before, dict) and isinstance(after, dict):
            if before.get("type") == "array":
                assert after["type"] == "array"
            if "properties" in before:
                assert set(after["required"]) == set(before["properties"])
                assert after["additionalProperties"] is False
            for key, value in before.items():
                if key in after:
                    inspect(value, after[key])
        elif isinstance(before, list) and isinstance(after, list):
            for first, second in zip(before, after, strict=False):
                inspect(first, second)

    inspect(original, adapted)
    assert contract.model_json_schema() == original


def test_empty_advert_requirements_remain_valid_after_strict_conversion() -> None:
    reply = json.dumps(
        {
            "chunks": [
                {
                    "first_line": 1,
                    "last_line": 1,
                    "kind": "about",
                    "context": None,
                    "skills": [],
                    "tech_terms": [],
                    "atomic_requirements": [],
                }
            ],
            "taxonomy": [],
        }
    )

    restored = drop_strict_mode_nulls(reply, JobChunkResponse.model_json_schema())
    parsed = JobChunkResponse.model_validate_json(restored)

    assert parsed.chunks[0].atomic_requirements == []
