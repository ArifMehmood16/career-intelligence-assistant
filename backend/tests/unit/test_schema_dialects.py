"""Each hosted API accepts a different subset of JSON Schema (PLAN 18.1).

OpenAI's strict mode needs every property required and `additionalProperties:
false`; Anthropic's structured outputs need `additionalProperties: false` and do
not accept numeric, string or array-length constraints. Constraints the API cannot
enforce move into the description; the server still validates the full schema.
"""

from __future__ import annotations

from career_assistant.adapters.providers.schema_dialects import (
    anthropic_output_schema,
    openai_strict_schema,
)

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
