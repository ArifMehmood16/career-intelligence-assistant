"""Dedicated PostgreSQL schema name for application tables."""

from __future__ import annotations

# Application tables live here — never in public.
APP_SCHEMA = "career_assistant"
# pgvector lives in `extensions`, where Supabase keeps extensions (PLAN 18.3).
EXTENSIONS_SCHEMA = "extensions"
SEARCH_PATH = f"{APP_SCHEMA}, {EXTENSIONS_SCHEMA}, public"
