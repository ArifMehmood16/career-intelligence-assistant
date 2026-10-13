"""Render a validation error as the text of one repair request (PLAN 18.2).

Each error is a JSON path and Pydantic's message. The invalid values themselves
are never repeated: they may be document text, and the model already has its own
previous reply.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from pydantic import ValidationError

_OPENING = (
    "Your previous response did not match the required JSON schema. Fix these problems:"
)
_CLOSING = "Return the complete JSON object again, with nothing before or after it."
# Contract field names are lowercase snake case; anything else came from the model.
_SAFE_KEY = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_MAX_SUMMARY = 170


def render_repair_message(error: ValidationError, *, max_errors: int = 20) -> str:
    problems = [
        f"- {_path(item['loc'])}: {item['msg']}"
        for item in error.errors(include_url=False, include_input=False)
    ]
    shown = problems[:max_errors]
    if len(problems) > max_errors:
        shown.append(f"(and {len(problems) - max_errors} more)")
    return "\n".join([_OPENING, *shown, _CLOSING])


def _path(loc: Sequence[int | str]) -> str:
    path = ""
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
        elif path:
            path += f".{part}"
        else:
            path = part
    return path or "(root)"


def summarize_validation_error(error: ValidationError, *, shown: int = 3) -> str:
    """Where a reply broke its contract, for a log line: paths and error types only.

    A key the contract does not define is shown as ``?``, because the model chose
    its name and it could repeat document text.
    """
    found = [
        f"{_path(_safe_loc(item['loc']))}:{item['type']}"
        for item in error.errors(include_url=False, include_input=False)
    ]
    listed: list[str] = []
    for problem in found[:shown]:
        # Log fields over 200 characters are redacted, so stop well short of that.
        if listed and len(", ".join([*listed, problem])) > _MAX_SUMMARY:
            break
        listed.append(problem)
    if len(found) > len(listed):
        listed.append(f"+{len(found) - len(listed)} more")
    return ", ".join(listed)


def _safe_loc(loc: Sequence[int | str]) -> tuple[int | str, ...]:
    return tuple(
        part if isinstance(part, int) or _SAFE_KEY.match(part) else "?" for part in loc
    )
