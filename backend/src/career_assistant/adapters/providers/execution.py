"""Translate the provider catalogue's operational tuning into application policy."""

from __future__ import annotations

from career_assistant.application.ports.types import ModelProfile
from career_assistant.application.providers.execution import ExecutionProfile


def execution_profile(profile: ModelProfile) -> ExecutionProfile:
    return ExecutionProfile(
        completion_concurrency=profile.completion_concurrency,
        embedding_concurrency=profile.embedding_concurrency,
        document_output_tokens=profile.document_output_tokens,
        judge_output_tokens=profile.judge_output_tokens,
        tokens_per_verdict=profile.tokens_per_verdict,
        max_document_split_depth=profile.max_document_split_depth,
    )
