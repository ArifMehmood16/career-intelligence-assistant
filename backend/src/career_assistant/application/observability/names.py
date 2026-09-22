"""Allowlisted action, event and HTTP names for durable audit rows."""

from __future__ import annotations

ACTIONS = frozenset(
    {
        "cv.upload",
        "cv.delete",
        "cover_letter.upload",
        "cover_letter.delete",
        "role.create",
        "role.delete",
        "role.reanalyse",
        "ask.question",
        "generation.bullet",
        "generation.pack",
        "generation.letter",
        "settings.provider_changed",
        "messages.delete",
    }
)

OUTCOMES = frozenset({"succeeded", "failed", "accepted"})

ENTITY_TYPES = frozenset({"cv", "role", "cover_letter", "conversation", "settings"})

EVENT_LEVELS = frozenset({"info", "warning", "error"})

EVENTS = frozenset(
    {
        "request",
        "request_failed",
        "http.error",
        "cv.uploaded",
        "cv.deleted",
        "cover_letter.uploaded",
        "cover_letter.deleted",
        "role.created",
        "role.deleted",
        "worker.claimed",
        "worker.stage",
        "provider.constructed",
        "process_start",
        "sql.cv.insert",
        "sql.cv.delete",
        "sql.role.deleted",
        "sql.conversation.created",
        "sql.cover_letter.delete",
        "claims.batch",
        "assessment.batch",
        "action.unknown",
        "event.unknown",
    }
)

HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})

QUERY_ID_KEYS = frozenset({"roleId", "version", "role_id", "conversationId"})

ATTRIBUTE_KEY_PREFIXES = (
    "count_",
    "id_",
    "ms_",
    "stage_",
    "provider_",
    "code_",
    "flag_",
)

UNKNOWN_ACTION = "action.unknown"
UNKNOWN_EVENT = "event.unknown"
