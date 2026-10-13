"""Method tracing with content-free argument and result summaries (ADR 017).

Summaries describe a value without repeating free text: ids, enums, numbers,
dates, sizes and lengths. A string is shown only when it is a UUID, a hex digest,
or a short token passed under an identifier-like name; anything else is
``str[len=N]``. Domain types can describe themselves with ``log_summary()``.
"""

from __future__ import annotations

import dataclasses
import functools
import inspect
import logging
import re
import time
from collections.abc import Callable, Mapping
from datetime import date
from enum import Enum
from typing import Any

from career_assistant.logconfig import log_debug

_MAX_SUMMARY = 190
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{16,128}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_.:/+-]{1,64}$")
_SAFE_NAMES = frozenset(
    {
        "band",
        "code",
        "id",
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


_RESERVED = frozenset({"fn", "duration_ms", "result", "error"})
_TRACED = "__career_assistant_traced__"


def traced[T](target: T) -> T:
    """Trace a function, or every public method a class defines, at DEBUG.

    ``call.start`` names the function and summarises its arguments; ``call.done``
    adds the duration and a result summary; ``call.error`` names the exception
    type and re-raises. Above DEBUG the wrapper only checks the level.
    """
    if isinstance(target, type):
        for name, member in list(vars(target).items()):
            if not name.startswith("_") and inspect.isfunction(member):
                setattr(target, name, _trace_function(member))
        return target
    if inspect.isfunction(target):
        return _trace_function(target)  # type: ignore[return-value]
    return target


def _trace_function(function: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(function, _TRACED, False) or inspect.isgeneratorfunction(function):
        return function
    logger = logging.getLogger(function.__module__)
    signature = inspect.signature(function)
    name = function.__qualname__

    @functools.wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not logger.isEnabledFor(logging.DEBUG):
            return function(*args, **kwargs)
        log_debug(logger, "call.start", fn=name, **_arguments(signature, args, kwargs))
        started = time.perf_counter()
        try:
            result = function(*args, **kwargs)
        except BaseException as error:
            log_debug(
                logger,
                "call.error",
                fn=name,
                duration_ms=_elapsed_ms(started),
                error=type(error).__name__,
            )
            raise
        log_debug(
            logger,
            "call.done",
            fn=name,
            duration_ms=_elapsed_ms(started),
            result=summarize("result", result),
        )
        return result

    setattr(wrapper, _TRACED, True)
    return wrapper


def _arguments(
    signature: inspect.Signature, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> dict[str, str]:
    try:
        bound = signature.bind_partial(*args, **kwargs)
    except TypeError:
        return {"arguments": f"unbound[{len(args) + len(kwargs)}]"}
    fields: dict[str, str] = {}
    for key, value in bound.arguments.items():
        if key in {"self", "cls"}:
            continue
        label = f"arg_{key}" if key in _RESERVED else key
        fields[label] = summarize(key, value)
    return fields


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


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
