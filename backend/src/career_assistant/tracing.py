"""Method tracing with content-free argument and result summaries (ADR 017).

Summaries describe a value without repeating free text: ids, enums, numbers,
dates, sizes and lengths. A string is shown only when it is a UUID, a hex digest,
or a short token passed under an identifier-like name; anything else is
``str[len=N]``. Domain types can describe themselves with ``log_summary()``.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Mapping
from datetime import date
from enum import Enum

_MAX_SUMMARY = 190
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{16,128}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_.:/+-]{1,64}$")
_SAFE_NAMES = frozenset(
    {
        "band",
        "code",
        "kind",
        "method",
        "mode",
        "operation",
        "phase",
        "pipeline",
        "purpose",
        "stage",
        "state",
        "status",
        "task",
        "verdict",
    }
)
_SAFE_SUFFIXES = ("_id", "_tag", "_version", "_code", "_kind")


def summarize(name: str, value: object) -> str:
    """Describe ``value`` for a log line without any of its free text."""
    return _clip(_summary(name, value, nested=False))


def _summary(name: str, value: object, *, nested: bool) -> str:
    scalar = _scalar(name, value)
    if scalar is not None:
        return scalar
    own = getattr(value, "log_summary", None)
    if callable(own):
        return str(own())
    if isinstance(value, bytes | bytearray):
        return f"bytes[len={len(value)}]"
    if isinstance(value, Mapping):
        return f"dict[len={len(value)}]"
    if isinstance(value, list | tuple | set | frozenset):
        return _collection(value)
    fields = _fields(value)
    if fields is None:
        return type(value).__name__
    if nested:
        return type(value).__name__
    inner = ",".join(
        f"{field}={_summary(field, item, nested=True)}" for field, item in fields
    )
    return f"{type(value).__name__}({inner})"


def _scalar(name: str, value: object) -> str | None:
    if value is None or isinstance(value, bool | int | float):
        return str(value)
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value if _shown(name, value) else f"str[len={len(value)}]"
    return None


def _shown(name: str, value: str) -> bool:
    if _UUID.match(value) or _HEX_DIGEST.match(value):
        return True
    named = name in _SAFE_NAMES or name.endswith(_SAFE_SUFFIXES)
    return named and _TOKEN.match(value) is not None


def _collection(
    value: list[object] | tuple[object, ...] | set[object] | frozenset[object],
) -> str:
    kind = type(value).__name__
    if not value:
        return f"{kind}[0]"
    names = {type(item).__name__ for item in value}
    item = f" {names.pop()}" if len(names) == 1 else ""
    return f"{kind}[{len(value)}{item}]"


def _fields(value: object) -> list[tuple[str, object]] | None:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return [(f.name, getattr(value, f.name)) for f in dataclasses.fields(value)]
    model_fields = getattr(type(value), "model_fields", None)
    if isinstance(model_fields, Mapping):
        return [(field, getattr(value, field)) for field in model_fields]
    return None


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_SUMMARY else f"{text[: _MAX_SUMMARY - 1]}…"
