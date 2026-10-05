"""Named technologies used by deterministic fixtures, never model quality rules."""

from __future__ import annotations

from career_assistant.domain.judging import find_term

_TERMS = (
    "dbt",
    "SQL",
    "Python",
    "CUDA",
    "Looker",
    "Snowflake",
    "Airflow",
    "Power BI",
    "Tableau",
    "PostgreSQL",
    "pgvector",
    "Qdrant",
    "Kafka",
    "Kubernetes",
    "Terraform",
    "JavaScript",
    "TypeScript",
    "Docker",
    "AWS",
)


def named_terms(text: str) -> list[dict[str, str]]:
    return [
        {"surface": surface, "canonical": term.casefold()}
        for term in _TERMS
        if (surface := find_term(text, term)) is not None
    ]
