"""Adapt one JSON Schema to what each hosted structured-output API accepts.

The Pydantic contract is the single source of every schema. OpenAI's strict mode
and Anthropic's structured outputs each accept a subset of JSON Schema, so the
adapters send an adapted copy. Constraints an API cannot enforce move into the
field's description, where the model still reads them, and the server validates
every response against the original schema, so no constraint is lost.
"""

from __future__ import annotations

import copy
import json
from typing import Any

# Numeric, string and array-length constraints neither API enforces in the schema.
_MOVED_TO_DESCRIPTION = (
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
)
_CHILD_SCHEMA_LISTS = ("anyOf", "oneOf", "allOf", "prefixItems")
_CHILD_SCHEMA_MAPS = ("properties", "$defs", "definitions")


def openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Require every field, preserve arrays, make optional scalars nullable."""
    adapted = copy.deepcopy(schema)
    _walk(adapted, require_all=True)
    return adapted


def drop_strict_mode_nulls(text: str, schema: dict[str, Any]) -> str:
    """Undo the nulls strict mode forces into properties the caller left optional.

    Callers wrote their schema with those properties optional and read them with
    `.get()`, so a forced null must look like an absent property again.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    _drop_nulls(payload, schema, root=schema)
    return json.dumps(payload, ensure_ascii=False)


def anthropic_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """No extra properties; optional properties stay optional."""
    adapted = copy.deepcopy(schema)
    _walk(adapted, require_all=False)
    return adapted


def _drop_nulls(value: object, node: dict[str, Any], *, root: dict[str, Any]) -> None:
    node = _resolve(node, root)
    if isinstance(value, list) and isinstance(node.get("items"), dict):
        for item in value:
            _drop_nulls(item, node["items"], root=root)
        return
    if not isinstance(value, dict):
        return
    for member in node.get("anyOf", []):
        if isinstance(member, dict) and "properties" in _resolve(member, root):
            _drop_nulls(value, member, root=root)
    properties: dict[str, Any] = node.get("properties", {})
    required = set(node.get("required", []))
    for name in [key for key in value if key in properties]:
        if value[name] is None and name not in required:
            del value[name]
        else:
            _drop_nulls(value[name], properties[name], root=root)


def _resolve(node: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return node
    target: Any = root
    for part in ref[2:].split("/"):
        target = target.get(part, {}) if isinstance(target, dict) else {}
    return target if isinstance(target, dict) else {}


def _walk(node: dict[str, Any], *, require_all: bool) -> None:
    _move_constraints(node)
    if node.get("type") == "object" or "properties" in node:
        _close_object(node, require_all=require_all)
    for key in _CHILD_SCHEMA_MAPS:
        for child in node.get(key, {}).values():
            _walk_if_schema(child, require_all=require_all)
    for key in _CHILD_SCHEMA_LISTS:
        for child in node.get(key, []):
            _walk_if_schema(child, require_all=require_all)
    _walk_if_schema(node.get("items"), require_all=require_all)


def _walk_if_schema(child: object, *, require_all: bool) -> None:
    if isinstance(child, dict):
        _walk(child, require_all=require_all)


def _close_object(node: dict[str, Any], *, require_all: bool) -> None:
    node["additionalProperties"] = False
    if not require_all:
        return
    properties: dict[str, Any] = node.get("properties", {})
    required = set(node.get("required", []))
    for name, child in properties.items():
        if name not in required and isinstance(child, dict):
            _make_nullable(child)
    node["required"] = list(properties)


def _make_nullable(node: dict[str, Any]) -> None:
    kind = node.get("type")
    # Defaulted collections can be present as []; wrapping nested collections in
    # nullable types can make the advert schema unacceptable to OpenAI.
    if kind in ("array", "null"):
        return
    if isinstance(kind, str):
        node["type"] = [kind, "null"]
    elif isinstance(kind, list):
        node["type"] = [*kind, "null"] if "null" not in kind else kind
    elif "anyOf" in node:
        if {"type": "null"} not in node["anyOf"]:
            node["anyOf"] = [*node["anyOf"], {"type": "null"}]
    else:
        inner = dict(node)
        node.clear()
        node["anyOf"] = [inner, {"type": "null"}]


def _move_constraints(node: dict[str, Any]) -> None:
    notes = [f"{key}: {node.pop(key)}" for key in _MOVED_TO_DESCRIPTION if key in node]
    if not notes:
        return
    existing = str(node.get("description", "")).strip()
    node["description"] = " ".join([existing, f"({'; '.join(notes)})"]).strip()
