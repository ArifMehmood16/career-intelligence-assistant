"""Render a validation error as the text of one repair request (PLAN 18.2).

Each error is a JSON path and Pydantic's message. The invalid values themselves
are never repeated: they may be document text, and the model already has its own
previous reply.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import ValidationError

_OPENING = (
    "Your previous response did not match the required JSON schema. Fix these problems:"
)
_CLOSING = "Return the complete JSON object again, with nothing before or after it."


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
