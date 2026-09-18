"""Dedicated PostgreSQL schema name for application tables."""

from __future__ import annotations

# Application tables live here — never in public. Extensions (vector) stay in public.
APP_SCHEMA = "career_assistant"
