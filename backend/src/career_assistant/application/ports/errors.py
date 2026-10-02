"""Provider failure types shared across adapters. No vendor error classes."""

from __future__ import annotations


class ProviderError(Exception):
    """Base for provider failures that use cases may translate to safe API errors."""


class ProviderRefusedError(ProviderError):
    """The provider declined to answer (safety/refusal)."""


class ProviderInputTooLargeError(ProviderError):
    """Input exceeds the provider's accepted size."""


class ProviderUnavailableError(ProviderError):
    """Provider cannot be used (missing key, down, breaker open)."""


class EgressNotPermittedError(ProviderError):
    """Hosted provider requested while the egress gate is closed."""


class ProviderTransientError(ProviderError):
    """Retryable upstream failure (429/5xx after local classification).

    A 429 sets `rate_limited`. `retry_after_seconds` is the vendor's wait, already
    capped, or None when the response did not say — a spend cap is that case, and
    it must not be retried in a loop.
    """

    retry_after_seconds: float | None
    rate_limited: bool

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
        rate_limited: bool = False,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.rate_limited = rate_limited


class JobCancelled(Exception):
    """The job this work belongs to was deleted or stopped: end it quietly.

    Raised when a role or the CV is deleted mid-analysis. It is not a failure, so
    nothing is recorded against the job.
    """


class StructuredOutputError(Exception):
    """The model replied, but not with a usable contract object."""

    def __init__(self, message: str, *, contract_version: str) -> None:
        super().__init__(message)
        self.contract_version = contract_version


class StructuredOutputInvalidError(StructuredOutputError):
    """Still invalid after one repair call. Carries a count, never the reply."""

    def __init__(
        self, message: str, *, contract_version: str, error_count: int
    ) -> None:
        super().__init__(message, contract_version=contract_version)
        self.error_count = error_count


class StructuredOutputTruncatedError(StructuredOutputError):
    """Cut by the output limit. The caller retries a smaller remainder, once."""

    def __init__(
        self,
        message: str,
        *,
        contract_version: str,
        output_tokens: int | None = None,
    ) -> None:
        super().__init__(message, contract_version=contract_version)
        self.output_tokens = output_tokens
