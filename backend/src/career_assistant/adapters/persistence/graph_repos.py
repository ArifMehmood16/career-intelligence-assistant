"""SQL adapter for the knowledge graph port (ADR 013, PLAN 18.5).

Nodes are stored per document, so one technology may have a node in the CV and
another in a cover letter. Queries therefore meet on canonical_name within the
workspace. Only related_terms follows inferred edges, and only two hops.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session, aliased

from career_assistant.adapters.persistence.models_v2 import (
    ChunkRow,
    KgEdgeRow,
    KgNodeRow,
)
from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.application.ports.graph import RelatedTerm, TermUse
from career_assistant.domain.knowledge_graph import (
    DocumentGraph,
    GraphNode,
    NodeKind,
    Relation,
    normalise_term,
)
from career_assistant.domain.recency import DateRange

MAX_DEPTH = 2
_USE_RELATIONS = (Relation.USED.value, Relation.MENTIONS.value)
_TERM_KINDS = (NodeKind.TECHNOLOGY.value, NodeKind.SKILL.value)
_ASSERTED = "asserted"
_INFERRED = "inferred"
_RELATED_SQL = f"""
WITH RECURSIVE walk(name, kind, depth, path) AS (
  SELECT CAST(:term AS text), CAST(NULL AS text), 0, ARRAY[CAST(:term AS text)]
  UNION ALL
  SELECT other.canonical_name, other.kind, walk.depth + 1,
         walk.path || other.canonical_name
  FROM walk
  JOIN {APP_SCHEMA}.kg_nodes here
    ON here.workspace_id = :ws AND here.canonical_name = walk.name
  JOIN {APP_SCHEMA}.kg_edges edge
    ON edge.workspace_id = :ws AND edge.provenance = '{_INFERRED}'
   AND (edge.source_id = here.id OR edge.target_id = here.id)
  JOIN {APP_SCHEMA}.kg_nodes other
    ON other.id = CASE WHEN edge.source_id = here.id
                       THEN edge.target_id ELSE edge.source_id END
  WHERE walk.depth < :depth AND other.canonical_name <> ALL(walk.path)
)
SELECT name, kind, min(depth) AS depth FROM walk
WHERE depth > 0
GROUP BY name, kind
ORDER BY depth, name
"""


class SqlKnowledgeGraphRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_document_graph(
        self, workspace_id: str, document_id: str, graph: DocumentGraph
    ) -> None:
        ws, doc = uuid.UUID(workspace_id), uuid.UUID(document_id)
        self._session.execute(delete(KgEdgeRow).where(KgEdgeRow.document_id == doc))
        self._session.execute(delete(KgNodeRow).where(KgNodeRow.document_id == doc))
        nodes = {node.key: _node_row(ws, doc, node) for node in graph.nodes}
        self._session.add_all(nodes.values())
        self._session.flush()
        chunks = self._chunk_ids(ws, doc)
        for edge in graph.edges:
            chunk_id = None
            if edge.cites_line is not None:
                chunk_id = chunks.get(edge.cites_line)
                if chunk_id is None:
                    raise ValueError(f"line {edge.cites_line} has no stored chunk")
            self._session.add(
                KgEdgeRow(
                    workspace_id=ws,
                    document_id=doc,
                    source_id=nodes[edge.source].id,
                    target_id=nodes[edge.target].id,
                    relation=edge.relation.value,
                    provenance=_INFERRED if edge.inferred else _ASSERTED,
                    chunk_id=chunk_id,
                )
            )
        self._session.flush()

    def known_technologies(self, workspace_id: str) -> frozenset[str]:
        names = self._session.scalars(
            select(KgNodeRow.canonical_name).where(
                KgNodeRow.workspace_id == uuid.UUID(workspace_id),
                KgNodeRow.kind == NodeKind.TECHNOLOGY.value,
            )
        )
        return frozenset(names)

    def term_uses(self, workspace_id: str, term: str) -> tuple[TermUse, ...]:
        source, target = aliased(KgNodeRow), aliased(KgNodeRow)
        rows = self._session.execute(
            select(KgEdgeRow.relation, KgEdgeRow.chunk_id, source)
            .join(target, target.id == KgEdgeRow.target_id)
            .join(source, source.id == KgEdgeRow.source_id)
            .where(
                KgEdgeRow.workspace_id == uuid.UUID(workspace_id),
                KgEdgeRow.provenance == _ASSERTED,
                KgEdgeRow.relation.in_(_USE_RELATIONS),
                target.kind.in_(_TERM_KINDS),
                target.canonical_name == normalise_term(term),
            )
            .order_by(KgEdgeRow.chunk_id)
        ).all()
        return tuple(_use(relation, chunk, node) for relation, chunk, node in rows)

    def related_terms(
        self, workspace_id: str, term: str, *, depth: int = MAX_DEPTH
    ) -> tuple[RelatedTerm, ...]:
        if not 1 <= depth <= MAX_DEPTH:
            raise ValueError(f"depth must be between 1 and {MAX_DEPTH}")
        rows = self._session.execute(
            text(_RELATED_SQL),
            {"ws": workspace_id, "term": normalise_term(term), "depth": depth},
        ).all()
        return tuple(
            RelatedTerm(name=name, kind=NodeKind(kind), depth=found)
            for name, kind, found in rows
        )

    def _chunk_ids(self, ws: uuid.UUID, doc: uuid.UUID) -> dict[int, uuid.UUID]:
        rows = self._session.execute(
            select(ChunkRow.first_line, ChunkRow.id).where(
                ChunkRow.workspace_id == ws, ChunkRow.document_id == doc
            )
        ).all()
        return {line: chunk_id for line, chunk_id in rows}


def _node_row(ws: uuid.UUID, doc: uuid.UUID, node: GraphNode) -> KgNodeRow:
    properties: dict[str, Any] = dict(node.properties)
    if node.dates is not None:
        end = node.dates.end
        properties["dates"] = {
            "start": node.dates.start.isoformat(),
            "end": None if end is None else end.isoformat(),
        }
    return KgNodeRow(
        id=uuid.uuid4(),
        workspace_id=ws,
        document_id=doc,
        kind=node.key.kind.value,
        canonical_name=node.key.name,
        properties=properties,
    )


def _use(relation: str, chunk_id: uuid.UUID, source: KgNodeRow) -> TermUse:
    is_role = source.kind == NodeKind.ROLE.value
    properties = source.properties
    return TermUse(
        relation=Relation(relation),
        chunk_id=str(chunk_id),
        role_id=str(source.id) if is_role else None,
        role_title=properties.get("title"),
        employer=properties.get("employer"),
        dates=_dates(properties.get("dates")),
    )


def _dates(stored: object) -> DateRange | None:
    if not isinstance(stored, dict) or not stored.get("start"):
        return None
    end = stored.get("end")
    return DateRange(
        start=date.fromisoformat(stored["start"]),
        end=None if end is None else date.fromisoformat(end),
    )
