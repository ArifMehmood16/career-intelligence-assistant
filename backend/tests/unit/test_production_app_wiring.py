"""Phase 13 carry-forward — production app wires SQL supporting cover letters."""

from __future__ import annotations

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.supporting_store import (
    SqlSupportingDocumentStore,
)
from career_assistant.application.documents.cv import InMemoryCvStore
from career_assistant.application.documents.supporting import (
    InMemorySupportingDocumentStore,
)
from career_assistant.application.roles.store import InMemoryRoleStore
from career_assistant.main import app, create_app


def test_module_app_wires_sql_cv_role_and_supporting_stores() -> None:
    assert isinstance(app.state.cv_store, SqlCvStore)
    assert isinstance(app.state.role_store, SqlRoleStore)
    assert isinstance(app.state.supporting_store, SqlSupportingDocumentStore)


def test_create_app_default_stays_hermetic_for_api_tests() -> None:
    hermetic = create_app()
    assert isinstance(hermetic.state.cv_store, InMemoryCvStore)
    assert isinstance(hermetic.state.role_store, InMemoryRoleStore)
    assert isinstance(hermetic.state.supporting_store, InMemorySupportingDocumentStore)
