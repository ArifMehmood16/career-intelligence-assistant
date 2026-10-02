"""Rules that stand in for a model's chunking in hermetic tests (PLAN 18.4).

A test fixture only. It reads the numbered lines from the prompt, follows the
section a heading opens, joins a line that starts in lower case to the chunk
before it (a wrapped PDF line), and copies every quote and term from the lines
themselves, so its output always passes the server's verbatim checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from career_assistant.application.chunking.sections import is_heading
from career_assistant.domain.lines import NumberedLine
from career_assistant.domain.recency import parse_date_range

_DOCUMENT = re.compile(r"<document>\n(.*?)\n</document>", re.DOTALL)
_LINE = re.compile(r"^L(\d+): (.*)$")
_BULLET = re.compile(r"^[-*•–]\s*")
_CONTACT = re.compile(
    r"@|\+?\d[\d ()-]{7,}\d|linkedin|github\.com|https?://|^(name|email|phone|"
    r"mobile|location|website):",
    re.IGNORECASE,
)
_YEARS = re.compile(r"(\d+)\+?\s*years", re.IGNORECASE)
_CV_BODY_KINDS = frozenset({"summary", "qualification", "project"})
_OPTIONAL = ("desirable", "nice to have", "bonus", "a plus")

_CV_MODES = {
    "summary": ("summary", "profile", "about me"),
    "experience": ("experience", "employment", "work history"),
    "skills": ("skills", "technologies"),
    "qualification": ("education", "qualification", "certification", "training"),
    "project": ("project",),
}
_JD_MODES = {
    "optional": ("desirable", "nice to have", "bonus"),
    "requirement": ("requirement", "you'll need", "you will need", "what you need"),
    "responsibility": ("responsibilit", "what you'll do", "you will do"),
    "benefit": ("benefit", "we offer", "perks", "package"),
    "logistics": ("location", "how to apply", "process"),
    "about": ("about",),
}
_LETTER_KINDS = (
    ("aspiration", ("i want", "i hope", "i would like", "i aim", "looking to")),
    ("motivation", ("excited", "passionate", "because", "drawn to")),
    (
        "experience",
        ("i built", "i led", "i delivered", "i designed", "i have ", "i ran"),
    ),
)


def document_lines(user: str) -> list[NumberedLine]:
    match = _DOCUMENT.search(user)
    lines: list[NumberedLine] = []
    for raw in (match.group(1) if match else "").split("\n"):
        found = _LINE.match(raw)
        if found:
            number = int(found.group(1))
            lines.append(NumberedLine(number, 0, 0, found.group(2)))
    return lines


@dataclass
class _Grouper:
    chunks: list[dict[str, Any]] = field(default_factory=list)
    headings: set[int] = field(default_factory=set)

    def add(self, line: NumberedLine, kind: str, **extra: Any) -> None:
        self.chunks.append(
            {"first_line": line.number, "last_line": line.number, "kind": kind, **extra}
        )

    def add_heading(self, line: NumberedLine) -> None:
        self.headings.add(line.number)
        self.add(line, "other")

    def extend(self, line: NumberedLine) -> None:
        self.chunks[-1]["last_line"] = line.number

    @property
    def last_kind(self) -> str | None:
        return self.chunks[-1]["kind"] if self.chunks else None


def _mode(text: str, modes: dict[str, tuple[str, ...]]) -> str | None:
    lowered = text.lower()
    return next(
        (mode for mode, words in modes.items() if any(w in lowered for w in words)),
        None,
    )


def _continues(line: NumberedLine, grouper: _Grouper) -> bool:
    joinable = grouper.last_kind not in (None, "other", "contact", "role_heading")
    return joinable and line.text[:1].islower()


def _terms(text: str) -> list[dict[str, str]]:
    body = text.split(":", 1)[1] if ":" in text else text
    items = [re.sub(r"\s*\(.*?\)", "", item).strip() for item in body.split(",")]
    return [{"surface": i, "canonical": i.lower()} for i in items if i and len(i) <= 40]


def cv_chunks(user: str) -> dict[str, Any]:
    grouper = _Grouper()
    mode: str | None = None
    role: int | None = None
    for line in document_lines(user):
        if is_heading(line):
            mode = _mode(line.text, _CV_MODES)
            grouper.add_heading(line)
        elif _continues(line, grouper):
            grouper.extend(line)
        elif _is_contact(line):
            grouper.add(line, "contact")
        elif parse_date_range(line.text) is not None:
            role = _role_heading(grouper, line)
        elif mode == "skills" or line.text.lower().startswith(
            ("skills", "technologies")
        ):
            grouper.add(line, "skills", tech_terms=_terms(line.text))
        elif mode == "experience" and role is not None:
            grouper.add(line, "experience", role_ref=role)
        else:
            grouper.add(line, mode if mode in _CV_BODY_KINDS else "other")
    return {"chunks": grouper.chunks}


def _is_contact(line: NumberedLine) -> bool:
    short_first_line = line.number == 1 and len(line.text.split()) <= 4
    return short_first_line or _CONTACT.search(line.text) is not None


def _role_heading(grouper: _Grouper, line: NumberedLine) -> int:
    """A date line is a role heading; an employer line just above it joins it."""
    previous = grouper.chunks[-1] if grouper.chunks else None
    joins = (
        previous is not None
        and previous["first_line"] == previous["last_line"] == line.number - 1
        and previous["kind"] in {"other", "experience"}
        and previous["first_line"] not in grouper.headings
    )
    if joins and previous is not None:
        previous["kind"] = "role_heading"
        previous.pop("role_ref", None)
        grouper.extend(line)
        return int(previous["first_line"])
    grouper.add(line, "role_heading")
    return line.number


def letter_chunks(user: str) -> dict[str, Any]:
    grouper = _Grouper()
    for line in document_lines(user):
        if _continues(line, grouper):
            grouper.extend(line)
            continue
        lowered = line.text.lower()
        kind = next(
            (k for k, words in _LETTER_KINDS if any(w in lowered for w in words)),
            "other",
        )
        grouper.add(line, kind)
    return {"chunks": grouper.chunks}


def job_chunks(user: str) -> dict[str, Any]:
    grouper = _Grouper()
    mode: str | None = None
    for line in document_lines(user):
        if is_heading(line) or (_mode(line.text, _JD_MODES) and len(line.text) <= 30):
            mode = _mode(line.text, _JD_MODES)
            grouper.add_heading(line)
        elif _continues(line, grouper):
            grouper.extend(line)
        elif _BULLET.match(line.text) and mode in {
            "requirement",
            "optional",
            "responsibility",
        }:
            kind = "responsibility" if mode == "responsibility" else "requirement"
            grouper.add(line, kind, atomic_requirements=[_requirement(line.text, mode)])
        else:
            grouper.add(
                line, mode if mode in {"benefit", "logistics", "about"} else "other"
            )
    return {"chunks": grouper.chunks}


def _requirement(text: str, mode: str | None) -> dict[str, Any]:
    statement = _BULLET.sub("", text).strip()
    optional = mode == "optional" or any(w in text.lower() for w in _OPTIONAL)
    years = _YEARS.search(text)
    return {
        "quote": text,
        "statement": statement,
        "must_have": not optional,
        "years_expected": float(years.group(1)) if years else None,
        "seniority_expected": None,
        "tech_terms": [],
    }
