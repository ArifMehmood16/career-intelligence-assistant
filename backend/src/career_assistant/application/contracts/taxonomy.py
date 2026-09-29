"""Taxonomy contract: general knowledge about technology terms (ADR 013).

These become inferred graph edges. They may widen a search and are never evidence.
"""

from __future__ import annotations

from pydantic import Field

from career_assistant.application.contracts.base import (
    Contract,
    NonEmpty,
    VersionedContract,
)


class TermRelations(Contract):
    term: NonEmpty = Field(description="The canonical term you were asked about.")
    is_a: list[NonEmpty] = Field(
        default_factory=list, description="Categories, e.g. vector database."
    )
    extends: list[NonEmpty] = Field(
        default_factory=list, description="Technologies it is built on."
    )
    aliases: list[NonEmpty] = Field(
        default_factory=list, description="Other common spellings."
    )


class TaxonomyResponse(VersionedContract):
    contract_version = "taxonomy-v1"
    terms: list[TermRelations]
