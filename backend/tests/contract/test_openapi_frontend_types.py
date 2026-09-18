"""Phase 11.11 — OpenAPI schemas and frontend types agree on shared models."""

from __future__ import annotations

import re
from pathlib import Path

from career_assistant.main import create_app

_REPO = Path(__file__).resolve().parents[3]
_TS_TYPES = _REPO / "frontend" / "src" / "types" / "index.ts"

# Shared product models: TypeScript name → OpenAPI component name.
_SHARED: dict[str, str] = {
    "CvDocument": "CvDocumentResponse",
    "Evidence": "EvidenceResponse",
    "Role": "RoleResponse",
    "Requirement": "RequirementWire",
    "BreakdownRow": "BreakdownRowWire",
    "Citation": "CitationWire",
    "ChatMessage": "ChatMessageWire",
    "Provider": "ProviderResponse",
    "ProviderChoice": "ProviderChoiceResponse",
}

# Fields that both sides must expose (camelCase). API may add more.
_REQUIRED: dict[str, frozenset[str]] = {
    "CvDocument": frozenset({"id", "filename", "pageCount", "parsedAt"}),
    "Evidence": frozenset({"spanId", "documentId", "page", "paragraph", "highlight"}),
    "Role": frozenset({"id", "title", "company", "fitScore", "bandLabel", "counts"}),
    "Requirement": frozenset({"id", "roleId", "text", "type", "status", "evidence"}),
    "BreakdownRow": frozenset({"id", "label", "value", "requirementIds"}),
    "Citation": frozenset({"id", "label", "evidence"}),
    "ChatMessage": frozenset(
        {
            "id",
            "author",
            "content",
            "kind",
            "citations",
            "model",
            "provider",
            "leftMachine",
        }
    ),
    "Provider": frozenset(
        {"id", "name", "kind", "models", "available", "unavailableReason"}
    ),
    "ProviderChoice": frozenset(
        {
            "answerProviderId",
            "answerModel",
            "indexProviderId",
            "indexModel",
        }
    ),
}


def _openapi_properties(schema_name: str) -> set[str]:
    components = create_app().openapi()["components"]["schemas"]
    schema = components[schema_name]
    return set(schema.get("properties", {}))


def _parse_ts_interfaces(source: str) -> dict[str, set[str]]:
    """Extract interface property names (ignores nested object shapes)."""
    interfaces: dict[str, set[str]] = {}
    pattern = re.compile(
        r"export interface (\w+)\s*\{([^}]*)\}",
        re.MULTILINE | re.DOTALL,
    )
    prop_pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*[?]?\s*:", re.MULTILINE)
    for match in pattern.finditer(source):
        name = match.group(1)
        body = match.group(2)
        interfaces[name] = set(prop_pattern.findall(body))
    return interfaces


def test_evidence_requires_span_id_on_both_sides() -> None:
    ts = _parse_ts_interfaces(_TS_TYPES.read_text(encoding="utf-8"))
    assert "spanId" in ts["Evidence"]
    assert "spanId" in _openapi_properties("EvidenceResponse")


def test_shared_models_agree_on_required_fields() -> None:
    ts = _parse_ts_interfaces(_TS_TYPES.read_text(encoding="utf-8"))
    missing: list[str] = []
    for ts_name, oa_name in _SHARED.items():
        required = _REQUIRED[ts_name]
        ts_fields = ts[ts_name]
        oa_fields = _openapi_properties(oa_name)
        for field in required:
            if field not in ts_fields:
                missing.append(f"TypeScript {ts_name} missing {field}")
            if field not in oa_fields:
                missing.append(f"OpenAPI {oa_name} missing {field}")
    assert missing == [], "; ".join(missing)
