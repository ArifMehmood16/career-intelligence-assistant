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
    """Retryable upstream failure (429/5xx after local classification)."""
