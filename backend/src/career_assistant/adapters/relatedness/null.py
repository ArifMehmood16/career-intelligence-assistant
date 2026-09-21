"""Hermetic adjudication — never calls a model; domain falls back to OR."""

from career_assistant.application.analysis.relatedness import NullAdjudicator

__all__ = ["NullAdjudicator"]
