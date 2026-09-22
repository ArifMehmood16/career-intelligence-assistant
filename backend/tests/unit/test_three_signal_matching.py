"""PLAN 13C.5 — relatedness is three signals; the domain combines them."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from career_assistant.application.analysis.relatedness import (
    disagreement_pairs,
    map_role_requirements,
)
from career_assistant.application.ports.adjudication import AdjudicationPair
from career_assistant.application.scoring.rubric_loader import load_mapping_config
from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import MappingStatus, map_requirement
from career_assistant.domain.relatedness import RelatednessSignals, combine_relatedness
from career_assistant.domain.requirements import Requirement

ROOT = Path(__file__).resolve().parents[3]
RUBRIC_PATH = ROOT / "config" / "scoring_rubric.toml"


def _req(
    *,
    id: str = "r1",
    text: str,
    competency: str,
) -> Requirement:
    return Requirement(
        id=id,
        text=text,
        competency=competency,
        seniority_signal=None,
        must_have=True,
        source_span_id=f"span-{id}",
        extraction_confidence=0.9,
        is_vague=False,
    )


def _claim(
    *,
    id: str = "c1",
    competency: str,
    context: str,
) -> Claim:
    return Claim(
        id=id,
        competency=competency,
        context=context,
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=(f"cspan-{id}",),
        extraction_confidence=0.9,
    )


@dataclass
class _RecordingAdjudicator:
    decisions: dict[tuple[str, str], bool]
    calls: list[tuple[AdjudicationPair, ...]] = field(default_factory=list)

    def adjudicate(
        self, pairs: list[AdjudicationPair] | tuple[AdjudicationPair, ...]
    ) -> dict[tuple[str, str], bool]:
        self.calls.append(tuple(pairs))
        return {
            (pair.requirement_id, pair.claim_id): self.decisions[key]
            for pair in pairs
            if (key := (pair.requirement_id, pair.claim_id)) in self.decisions
        }


def test_combine_agreement_does_not_need_adjudication() -> None:
    both = combine_relatedness(
        lexical=True,
        lexical_overlap=2,
        embedding=True,
        embedding_similarity=0.8,
        adjudication=None,
    )
    neither = combine_relatedness(
        lexical=False,
        lexical_overlap=0,
        embedding=False,
        embedding_similarity=0.1,
        adjudication=True,
    )
    assert both.related is True
    assert both.adjudication is None
    assert neither.related is False


def test_xor_without_adjudication_falls_back_to_or() -> None:
    embedding_only = combine_relatedness(
        lexical=False,
        lexical_overlap=0,
        embedding=True,
        embedding_similarity=0.9,
        adjudication=None,
    )
    assert embedding_only.related is True
    lexical_only = combine_relatedness(
        lexical=True,
        lexical_overlap=1,
        embedding=False,
        embedding_similarity=0.1,
        adjudication=None,
    )
    assert lexical_only.related is True


def test_xor_adjudication_can_veto_or_confirm() -> None:
    vetoed = combine_relatedness(
        lexical=False,
        lexical_overlap=0,
        embedding=True,
        embedding_similarity=0.9,
        adjudication=False,
    )
    confirmed = combine_relatedness(
        lexical=True,
        lexical_overlap=1,
        embedding=False,
        embedding_similarity=0.1,
        adjudication=True,
    )
    assert vetoed.related is False
    assert confirmed.related is True


def test_mapping_records_lexical_signal_on_the_justifying_claim() -> None:
    req = _req(text="Production dbt experience", competency="dbt")
    claim = _claim(competency="dbt", context="Owned dbt models in production.")
    result = map_requirement(req, (claim,))
    assert result.status is MappingStatus.MET
    assert result.signals.lexical is True
    assert result.signals.lexical_overlap >= 1
    assert result.signals.embedding is False
    assert result.signals.adjudication is None
    assert result.signals.related is True


def test_mapping_records_embedding_signal_when_cosine_clears_the_floor() -> None:
    req = _req(text="Kubernetes cluster autoscaling", competency="kubernetes")
    claim = _claim(
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    result = map_requirement(req, (claim,), similarities={("r1", "c1"): 0.9})
    assert result.status is not MappingStatus.MISSING
    assert result.signals.lexical is False
    assert result.signals.embedding is True
    assert result.signals.embedding_similarity == 0.9
    assert result.signals.adjudication is None
    assert result.signals.related is True


def test_similarity_floor_is_read_from_configuration() -> None:
    config = load_mapping_config(RUBRIC_PATH)
    assert config.similarity_floor == 0.55
    req = _req(text="Kubernetes cluster autoscaling", competency="kubernetes")
    claim = _claim(
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    below = map_requirement(
        req,
        (claim,),
        similarities={("r1", "c1"): config.similarity_floor - 0.01},
        similarity_floor=config.similarity_floor,
    )
    at_floor = map_requirement(
        req,
        (claim,),
        similarities={("r1", "c1"): config.similarity_floor},
        similarity_floor=config.similarity_floor,
    )
    assert below.status is MappingStatus.MISSING
    assert at_floor.status is not MappingStatus.MISSING


def test_adjudicator_is_only_called_for_disagreements() -> None:
    overlap_and_sim = _req(
        id="agree", text="Production dbt experience", competency="dbt"
    )
    overlap_claim = _claim(
        id="agree-c", competency="dbt", context="Owned dbt models in production."
    )
    xor_req = _req(
        id="xor", text="Kubernetes cluster autoscaling", competency="kubernetes"
    )
    xor_claim = _claim(
        id="xor-c",
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    neither_req = _req(id="none", text="CUDA kernel authoring", competency="cuda")
    similarities = {
        ("agree", "agree-c"): 0.9,
        ("xor", "xor-c"): 0.9,
        ("none", "xor-c"): 0.1,
    }
    pairs = disagreement_pairs(
        (overlap_and_sim, xor_req, neither_req),
        (overlap_claim, xor_claim),
        similarities=similarities,
        similarity_floor=0.55,
    )
    ids = {(pair.requirement_id, pair.claim_id) for pair in pairs}
    assert ("xor", "xor-c") in ids
    assert ("agree", "agree-c") not in ids
    assert ("none", "xor-c") not in ids


def test_adjudicator_veto_makes_embedding_only_unrelated() -> None:
    req = _req(text="Kubernetes cluster autoscaling", competency="kubernetes")
    claim = _claim(
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    adjudicator = _RecordingAdjudicator(decisions={("r1", "c1"): False})
    mappings = map_role_requirements(
        (req,),
        (claim,),
        similarities={("r1", "c1"): 0.9},
        adjudicator=adjudicator,
        similarity_floor=0.55,
    )
    assert mappings[0].status is MappingStatus.MISSING
    assert mappings[0].signals.embedding is True
    assert mappings[0].signals.adjudication is False
    assert mappings[0].signals.related is False
    assert len(adjudicator.calls) == 1
    assert adjudicator.calls[0][0].requirement_id == "r1"
    assert adjudicator.calls[0][0].claim_id == "c1"


def test_hermetic_null_adjudicator_does_not_veto_embedding_only() -> None:
    req = _req(text="Kubernetes cluster autoscaling", competency="kubernetes")
    claim = _claim(
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    mappings = map_role_requirements(
        (req,),
        (claim,),
        similarities={("r1", "c1"): 0.9},
        adjudicator=_RecordingAdjudicator(decisions={}),
        similarity_floor=0.55,
    )
    assert mappings[0].status is not MappingStatus.MISSING
    assert mappings[0].signals.embedding is True
    assert mappings[0].signals.adjudication is None
    assert mappings[0].signals.related is True


def test_relatedness_signals_round_trip_through_payload() -> None:
    original = RelatednessSignals(
        lexical=False,
        lexical_overlap=0,
        embedding=True,
        embedding_similarity=0.9,
        adjudication=False,
        related=False,
    )
    restored = RelatednessSignals.from_payload(original.as_payload())
    assert restored == original
    assert RelatednessSignals.from_payload(None) == RelatednessSignals()
