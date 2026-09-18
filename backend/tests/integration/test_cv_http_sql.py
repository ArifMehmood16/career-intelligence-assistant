"""Phase 11.8 — CV HTTP routes against SqlCvStore (PostgreSQL)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.main import create_app

pytestmark = pytest.mark.integration


def test_cv_http_routes_persist_via_sql_cv_store(
    session_factory: sessionmaker[Session],
) -> None:
    store = SqlCvStore(lambda: SqlUnitOfWork(session_factory))
    client = TestClient(create_app(cv_store=store))

    created = client.post(
        "/api/cv",
        json={
            "text": "Owned dbt models in production.",
            "filename": "cv.txt",
        },
    )
    assert created.status_code == 201
    doc_id = created.json()["id"]

    fetched = client.get("/api/cv")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == doc_id

    active = store.get_active(client.cookies["workspace"])
    assert active is not None
    span_id = active.spans[0].id
    evidence = client.get(f"/api/spans/{span_id}")
    assert evidence.status_code == 200
    assert evidence.json()["spanId"] == span_id

    deleted = client.delete("/api/cv")
    assert deleted.status_code == 204
    assert client.get("/api/cv").json() is None
