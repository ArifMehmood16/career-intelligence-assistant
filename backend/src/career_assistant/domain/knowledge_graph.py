"""The knowledge graph a document's validated chunks produce (ADR 013).

Asserted edges come from a chunk and cite its first line. Inferred edges come
from general knowledge — the chunker's canonical spellings, the taxonomy call —
cite nothing, and may only widen a search.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from career_assistant.domain.chunking import Chunk, TechTermProposal
from career_assistant.domain.experience import ExperienceFact, experience_from
from career_assistant.domain.recency import DateRange


class NodeKind(StrEnum):
    DOCUMENT = "document"
    ROLE = "role"
    EMPLOYER = "employer"
    TECHNOLOGY = "technology"
    SKILL = "skill"
    CATEGORY = "category"
    REQUIREMENT = "requirement"


class Relation(StrEnum):
    USED = "USED"
    AT = "AT"
    REQUIRES = "REQUIRES"
    MENTIONS = "MENTIONS"
    IS_A = "IS_A"
    EXTENDS = "EXTENDS"
    ALIAS_OF = "ALIAS_OF"


INFERRED_RELATIONS = frozenset({Relation.IS_A, Relation.EXTENDS, Relation.ALIAS_OF})


@dataclass(frozen=True, slots=True)
class NodeKey:
    kind: NodeKind
    name: str


@dataclass(frozen=True, slots=True)
class GraphNode:
    key: NodeKey
    dates: DateRange | None = None
    properties: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source: NodeKey
    target: NodeKey
    relation: Relation
    cites_line: int | None

    def __post_init__(self) -> None:
        if self.inferred and self.cites_line is not None:
            raise ValueError(f"an inferred {self.relation} edge must cite nothing")
        if not self.inferred and self.cites_line is None:
            raise ValueError(f"an asserted {self.relation} edge must cite a chunk")

    @property
    def inferred(self) -> bool:
        return self.relation in INFERRED_RELATIONS


@dataclass(frozen=True, slots=True)
class DocumentGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


DOCUMENT_NODE = NodeKey(NodeKind.DOCUMENT, "document")


def graph_from_chunks(chunks: Sequence[Chunk]) -> DocumentGraph:
    """Nodes and edges from one document's validated chunks.

    Only evidence-eligible chunks produce USED or MENTIONS edges, so a contact
    line, a summary or a cover-letter aspiration never becomes a fact.
    """
    builder = _Builder()
    roles = {c.first_line: builder.role(c) for c in chunks if c.kind == "role_heading"}
    for chunk in chunks:
        if chunk.evidence_eligible:
            source = roles.get(chunk.role_ref) if chunk.role_ref else None
            builder.used(source, chunk)
        for requirement in chunk.atomic_requirements:
            builder.required(requirement.statement, requirement.tech_terms, chunk)
    return builder.graph()


def experience_with(graph: DocumentGraph, name: str, *, as_of: date) -> ExperienceFact:
    """Years with `name` as written. An alias or an inferred edge adds nothing."""
    term = normalise_term(name)
    using = {
        e.source
        for e in graph.edges
        if e.relation is Relation.USED and e.target.name == term
    }
    dates = {n.key: n.dates for n in graph.nodes if n.key in using}
    return experience_from(
        [dates.get(key) for key in sorted(using, key=str)], as_of=as_of
    )


def normalise_term(value: str) -> str:
    return " ".join(value.split()).casefold()


class _Builder:
    def __init__(self) -> None:
        self._nodes: dict[NodeKey, GraphNode] = {}
        self._edges: dict[GraphEdge, None] = {}

    def graph(self) -> DocumentGraph:
        return DocumentGraph(
            nodes=tuple(self._nodes.values()), edges=tuple(self._edges)
        )

    def role(self, chunk: Chunk) -> NodeKey:
        role = chunk.role
        title = role.title if role else None
        employer = role.employer if role else None
        label = " at ".join(p for p in (title, employer) if p) or "role"
        key = NodeKey(
            NodeKind.ROLE, normalise_term(f"{label} (line {chunk.first_line})")
        )
        properties = {
            name: value
            for name, value in (
                ("title", title),
                ("employer", employer),
                ("date_text", role.date_text if role else None),
                ("seniority_level", role.seniority_level if role else None),
            )
            if value
        }
        self._add_node(GraphNode(key, role.dates if role else None, properties))
        if employer:
            target = self._node(NodeKind.EMPLOYER, employer)
            self._edge(key, target, Relation.AT, chunk.first_line)
        return key

    def used(self, source: NodeKey | None, chunk: Chunk) -> None:
        relation = Relation.USED if source else Relation.MENTIONS
        origin = source or self._add_node(GraphNode(DOCUMENT_NODE))
        for term in chunk.tech_terms:
            target = self._technology(term.surface, term.canonical)
            self._edge(origin, target, relation, chunk.first_line)
        for skill in chunk.skills:
            target = self._node(NodeKind.SKILL, skill)
            self._edge(origin, target, relation, chunk.first_line)

    def required(
        self, statement: str, terms: Sequence[TechTermProposal], chunk: Chunk
    ) -> None:
        source = self._node(NodeKind.REQUIREMENT, statement)
        for term in terms:
            target = self._technology(term.surface, term.canonical)
            self._edge(source, target, Relation.REQUIRES, chunk.first_line)

    def _technology(self, surface: str, canonical: str) -> NodeKey:
        written = self._node(NodeKind.TECHNOLOGY, surface)
        if normalise_term(canonical) != written.name:
            spelled = self._node(NodeKind.TECHNOLOGY, canonical)
            self._edge(written, spelled, Relation.ALIAS_OF, None)
        return written

    def _node(self, kind: NodeKind, name: str) -> NodeKey:
        return self._add_node(GraphNode(NodeKey(kind, normalise_term(name))))

    def _add_node(self, node: GraphNode) -> NodeKey:
        self._nodes.setdefault(node.key, node)
        return node.key

    def _edge(
        self, source: NodeKey, target: NodeKey, relation: Relation, line: int | None
    ) -> None:
        self._edges.setdefault(GraphEdge(source, target, relation, line), None)
