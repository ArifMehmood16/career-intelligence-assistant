"""Validate the chunk plan a model proposes (ADR 013, PLAN 18.4).

The model groups server-numbered lines. Structural problems reject the whole plan
and go back to the model once: a line in no chunk or in two, chunks out of order or
outside the lines, an oversized chunk, a role reference to nothing, a requirement
quote the text does not contain. A field that is not in the chunk's own text — an
invented technology, skill or employer, years or a level the advert never states —
is dropped and counted instead. Nothing here is fuzzy: whitespace and case are
normalised, and every word must still be there.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, replace

from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.lines import NumberedLine
from career_assistant.domain.recency import DateRange, parse_date_range


@dataclass(frozen=True, slots=True)
class TechTermProposal:
    surface: str
    canonical: str


@dataclass(frozen=True, slots=True)
class RoleProposal:
    employer: str | None = None
    title: str | None = None
    date_text: str | None = None
    seniority_level: str | None = None
    dates: DateRange | None = None


@dataclass(frozen=True, slots=True)
class AtomicRequirementProposal:
    quote: str
    statement: str
    must_have: bool
    years_expected: float | None
    seniority_expected: str | None
    tech_terms: tuple[TechTermProposal, ...]


@dataclass(frozen=True, slots=True)
class ProposedChunk:
    first_line: int
    last_line: int
    kind: str
    context: str | None = None
    skills: tuple[str, ...] = ()
    tech_terms: tuple[TechTermProposal, ...] = ()
    role: RoleProposal | None = None
    role_ref: int | None = None
    atomic_requirements: tuple[AtomicRequirementProposal, ...] = ()


@dataclass(frozen=True, slots=True)
class ChunkLimits:
    max_lines: int = 40
    max_chars: int = 4_000


@dataclass(frozen=True, slots=True)
class Chunk:
    first_line: int
    last_line: int
    start_offset: int
    end_offset: int
    kind: str
    text: str
    evidence_eligible: bool
    context: str | None
    skills: tuple[str, ...]
    tech_terms: tuple[TechTermProposal, ...]
    role: RoleProposal | None
    role_ref: int | None
    atomic_requirements: tuple[AtomicRequirementProposal, ...]


@dataclass(frozen=True, slots=True)
class ChunkPlan:
    """Accepted chunks, or the problems that reject the plan. Never both."""

    chunks: tuple[Chunk, ...]
    problems: tuple[str, ...]
    dropped_fields: int


DEFAULT_CHUNK_LIMITS = ChunkLimits()
_EVIDENCE_KINDS: dict[DocumentKind, frozenset[str]] = {
    DocumentKind.CV: frozenset({"experience", "project", "skills", "qualification"}),
    DocumentKind.COVER_LETTER: frozenset({"experience"}),
    DocumentKind.JOB_DESCRIPTION: frozenset(),
}
# Words that state a level. A level the advert does not state is not kept.
_LEVEL_WORDS: dict[str, tuple[str, ...]] = {
    "intern": ("intern", "internship"),
    "junior": ("junior", "graduate", "entry level", "entry-level"),
    "mid": ("mid", "mid-level", "intermediate"),
    "senior": ("senior", "sr"),
    "lead": ("lead",),
    "principal": ("principal", "staff"),
    "director": ("director", "head of"),
}
_NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


def validate_chunk_plan(
    kind: DocumentKind,
    lines: Sequence[NumberedLine],
    text: str,
    proposals: Sequence[ProposedChunk],
    *,
    limits: ChunkLimits = DEFAULT_CHUNK_LIMITS,
    advert_title: str = "",
    known_role_headings: frozenset[int] = frozenset(),
) -> ChunkPlan:
    """Check a proposed grouping of `lines` (a whole document or one section)."""
    by_number = {line.number: line for line in lines}
    problems = [
        *_order_problems(proposals),
        *_bounds_problems(proposals, by_number),
        *_coverage_problems(proposals, by_number),
    ]
    if problems:
        return ChunkPlan(chunks=(), problems=tuple(problems), dropped_fields=0)
    headings = known_role_headings | {
        p.first_line for p in proposals if p.kind == "role_heading"
    }
    chunks: list[Chunk] = []
    dropped = 0
    for proposal in proposals:
        chunk_text = _text_of(proposal, by_number, text)
        problems.extend(_chunk_problems(proposal, chunk_text, limits, headings))
        accepted, lost = _accept(kind, proposal, chunk_text, by_number, advert_title)
        chunks.append(accepted)
        dropped += lost
    if problems:
        return ChunkPlan(chunks=(), problems=tuple(problems), dropped_fields=0)
    return ChunkPlan(chunks=tuple(chunks), problems=(), dropped_fields=dropped)


def _order_problems(proposals: Sequence[ProposedChunk]) -> list[str]:
    starts = [p.first_line for p in proposals]
    if starts != sorted(starts):
        return ["Chunks must be listed in line order."]
    return []


def _bounds_problems(
    proposals: Sequence[ProposedChunk], by_number: Mapping[int, NumberedLine]
) -> list[str]:
    first, last = min(by_number, default=1), max(by_number, default=0)
    problems: list[str] = []
    for p in proposals:
        where = f"The chunk at lines {p.first_line}-{p.last_line}"
        if p.last_line < p.first_line:
            problems.append(f"{where} ends before it starts.")
        elif p.first_line < first:
            problems.append(f"{where} starts before the first line, {first}.")
        elif p.last_line > last:
            problems.append(f"{where} goes past the last line, {last}.")
    return problems


def _coverage_problems(
    proposals: Sequence[ProposedChunk], by_number: Mapping[int, NumberedLine]
) -> list[str]:
    counts = dict.fromkeys(by_number, 0)
    for p in proposals:
        for number in range(p.first_line, p.last_line + 1):
            if number in counts:
                counts[number] += 1
    missing = [n for n, seen in counts.items() if seen == 0]
    problems = [_missing_message(run) for run in _runs(missing)]
    problems.extend(
        f"Line {n} is in more than one chunk." for n, seen in counts.items() if seen > 1
    )
    return problems


def _chunk_problems(
    proposal: ProposedChunk,
    chunk_text: str,
    limits: ChunkLimits,
    headings: AbstractSet[int],
) -> list[str]:
    where = f"The chunk at lines {proposal.first_line}-{proposal.last_line}"
    problems: list[str] = []
    if proposal.last_line - proposal.first_line + 1 > limits.max_lines:
        problems.append(f"{where} is longer than {limits.max_lines} lines.")
    elif len(chunk_text) > limits.max_chars:
        problems.append(f"{where} is longer than {limits.max_chars} characters.")
    ref = proposal.role_ref
    if ref is not None and (ref not in headings or ref >= proposal.first_line):
        problems.append(
            f"{where} has role_ref {ref}, which is not the first line of an earlier "
            "role_heading chunk."
        )
    haystack = _norm(chunk_text)
    for requirement in proposal.atomic_requirements:
        if _norm(requirement.quote) not in haystack:
            problems.append(
                f"{where} quotes {requirement.quote!r}, which is not in those lines."
            )
    return problems


def _accept(
    kind: DocumentKind,
    proposal: ProposedChunk,
    chunk_text: str,
    by_number: Mapping[int, NumberedLine],
    advert_title: str,
) -> tuple[Chunk, int]:
    haystack = _norm(chunk_text)
    terms, lost_terms = _verbatim_terms(proposal.tech_terms, haystack)
    skills = tuple(s for s in proposal.skills if _norm(s) in haystack)
    role, lost_role = _verbatim_role(proposal.role, haystack)
    requirements, lost_requirements = _checked_requirements(
        proposal.atomic_requirements, haystack, advert_title
    )
    lost = lost_terms + len(proposal.skills) - len(skills) + lost_role
    chunk = Chunk(
        first_line=proposal.first_line,
        last_line=proposal.last_line,
        start_offset=by_number[proposal.first_line].start_offset,
        end_offset=by_number[proposal.last_line].end_offset,
        kind=proposal.kind,
        text=chunk_text,
        evidence_eligible=proposal.kind in _EVIDENCE_KINDS[kind],
        context=proposal.context,
        skills=skills,
        tech_terms=terms,
        role=role,
        role_ref=proposal.role_ref,
        atomic_requirements=requirements,
    )
    return chunk, lost + lost_requirements


def _verbatim_terms(
    terms: Sequence[TechTermProposal], haystack: str
) -> tuple[tuple[TechTermProposal, ...], int]:
    kept = tuple(t for t in terms if _norm(t.surface) in haystack)
    return kept, len(terms) - len(kept)


def _verbatim_role(
    role: RoleProposal | None, haystack: str
) -> tuple[RoleProposal | None, int]:
    if role is None:
        return None, 0
    fields = {
        "employer": role.employer,
        "title": role.title,
        "date_text": role.date_text,
    }
    kept = {k: v for k, v in fields.items() if v is not None and _norm(v) in haystack}
    lost = sum(1 for v in fields.values() if v is not None) - len(kept)
    date_text = kept.get("date_text")
    dates = parse_date_range(date_text) if isinstance(date_text, str) else None
    return (
        replace(role, **{**dict.fromkeys(fields), **kept}, dates=dates),
        lost,
    )


def _checked_requirements(
    requirements: Sequence[AtomicRequirementProposal], haystack: str, advert_title: str
) -> tuple[tuple[AtomicRequirementProposal, ...], int]:
    checked: list[AtomicRequirementProposal] = []
    lost = 0
    for requirement in requirements:
        quote = _norm(requirement.quote)
        terms, lost_terms = _verbatim_terms(requirement.tech_terms, haystack)
        years = requirement.years_expected
        if years is not None and not _states_years(quote, years):
            years = None
        level = requirement.seniority_expected
        if level is not None and not _states_level(
            f"{quote} {_norm(advert_title)}", level
        ):
            level = None
        lost += lost_terms
        lost += (years is None) != (requirement.years_expected is None)
        lost += (level is None) != (requirement.seniority_expected is None)
        checked.append(
            replace(
                requirement,
                tech_terms=terms,
                years_expected=years,
                seniority_expected=level,
            )
        )
    return tuple(checked), lost


def _states_years(quote: str, years: float) -> bool:
    number = f"{years:g}"
    if re.search(rf"(?<![\d.]){re.escape(number)}(?![\d])", quote):
        return True
    word = _NUMBER_WORDS.get(int(years)) if years.is_integer() else None
    return word is not None and re.search(rf"\b{word}\b", quote) is not None


def _states_level(haystack: str, level: str) -> bool:
    words = _LEVEL_WORDS.get(level, ())
    return any(re.search(rf"\b{re.escape(w)}\b", haystack) for w in words)


def _text_of(
    proposal: ProposedChunk, by_number: Mapping[int, NumberedLine], text: str
) -> str:
    start = by_number[proposal.first_line].start_offset
    return text[start : by_number[proposal.last_line].end_offset]


def _norm(value: str) -> str:
    """Collapse whitespace and case. Not fuzzy: the words must all be there."""
    return " ".join(value.split()).casefold()


def _runs(numbers: Sequence[int]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for n in numbers:
        if runs and runs[-1][1] == n - 1:
            runs[-1] = (runs[-1][0], n)
        else:
            runs.append((n, n))
    return runs


def _missing_message(run: tuple[int, int]) -> str:
    first, last = run
    if first == last:
        return f"Line {first} is not in any chunk."
    return f"Lines {first}-{last} are not in any chunk."
