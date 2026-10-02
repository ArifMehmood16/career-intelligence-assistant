"""Execution policy supplied by the selected adapter, independent of vendor names."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionProfile:
    completion_concurrency: int = 1
    embedding_concurrency: int = 1
    # Zero uses the model's limit; positive values are explicit operational caps.
    document_output_tokens: int = 0
    judge_output_tokens: int = 0
    tokens_per_verdict: int = 400
    max_document_split_depth: int = 4

    def __post_init__(self) -> None:
        if self.completion_concurrency < 1 or self.embedding_concurrency < 1:
            raise ValueError("provider concurrency must be positive")
        if self.document_output_tokens < 0 or self.judge_output_tokens < 0:
            raise ValueError("provider output ceilings cannot be negative")
        if self.tokens_per_verdict < 1 or self.max_document_split_depth < 0:
            raise ValueError("provider batching limits are invalid")

    def document_output_limit(self, model_limit: int) -> int:
        return min(model_limit, self.document_output_tokens or model_limit)

    def judge_output_limit(self, model_limit: int) -> int:
        return min(model_limit, self.judge_output_tokens or model_limit)
