"""Phase 10.9 — persist generated artefacts with provenance (Postgres)."""

from __future__ import annotations

import uuid

import pytest
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.persistence import NewGeneratedDraft
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.groundedness import GroundednessVerdict
from career_assistant.domain.jobs import RoleStatus

pytestmark = pytest.mark.integration


def _seed_role_with_span(uow: SqlUnitOfWork) -> tuple[str, str, str]:
    workspace_id = str(uuid.uuid4())
    role_id = str(uuid.uuid4())
    cv = make_document(kind=DocumentKind.CV, text="Owned dbt models in production.")
    jd = make_document(
        kind=DocumentKind.JOB_DESCRIPTION,
        text="Need dbt.",
        is_active=False,
    )
    with uow:
        uow.workspaces.ensure(workspace_id)
        uow.documents.save_admitted(workspace_id, cv)
        stored_jd = uow.documents.save_admitted(workspace_id, jd)
        uow.roles.create(
            workspace_id=workspace_id,
            role_id=role_id,
            title="Analytics Engineer",
            company="Acme",
            job_description_document_id=stored_jd.id,
            status=RoleStatus.READY,
        )
        uow.commit()
    return workspace_id, role_id, cv.spans[0].id


def test_save_draft_persists_body_citations_and_provenance(
    uow: SqlUnitOfWork,
) -> None:
    workspace_id, role_id, span_id = _seed_role_with_span(uow)
    draft_id = str(uuid.uuid4())
    with uow:
        stored = uow.drafts.save(
            NewGeneratedDraft(
                id=draft_id,
                workspace_id=workspace_id,
                role_id=role_id,
                kind="bullets",
                body="- Owned dbt models in production.",
                analysis_version=1,
                citation_span_ids=(span_id,),
                provider="hermetic",
                model_tag="rules-v1",
                left_machine=False,
                groundedness=GroundednessVerdict.PASS,
                used_template_fallback=True,
                regeneration_count=1,
            )
        )
        uow.commit()

    assert stored.version == 1
    assert stored.groundedness is GroundednessVerdict.PASS
    assert stored.used_template_fallback is True
    with uow:
        fetched = uow.drafts.get(workspace_id, draft_id)
        assert fetched is not None
        assert fetched.body.startswith("- Owned dbt")
        assert fetched.citation_span_ids == (span_id,)
        assert fetched.provider == "hermetic"
        assert fetched.left_machine is False


def test_regeneration_creates_new_immutable_version(uow: SqlUnitOfWork) -> None:
    workspace_id, role_id, span_id = _seed_role_with_span(uow)
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())
    with uow:
        first = uow.drafts.save(
            NewGeneratedDraft(
                id=first_id,
                workspace_id=workspace_id,
                role_id=role_id,
                kind="cover-letter",
                body="Version one letter.",
                analysis_version=1,
                citation_span_ids=(span_id,),
                provider="hermetic",
                model_tag="rules-v1",
                left_machine=False,
                groundedness=GroundednessVerdict.PASS,
                used_template_fallback=False,
                regeneration_count=0,
            )
        )
        second = uow.drafts.save(
            NewGeneratedDraft(
                id=second_id,
                workspace_id=workspace_id,
                role_id=role_id,
                kind="cover-letter",
                body="Version two letter.",
                analysis_version=1,
                citation_span_ids=(span_id,),
                provider="hermetic",
                model_tag="rules-v1",
                left_machine=False,
                groundedness=GroundednessVerdict.PASS,
                used_template_fallback=True,
                regeneration_count=1,
            )
        )
        uow.commit()

    assert first.version == 1
    assert second.version == 2
    with uow:
        versions = uow.drafts.list_for_role(workspace_id, role_id, kind="cover-letter")
        assert [d.version for d in versions] == [1, 2]
        assert versions[0].body == "Version one letter."
        assert versions[1].body == "Version two letter."
        latest = uow.drafts.get_latest(workspace_id, role_id, kind="cover-letter")
        assert latest is not None
        assert latest.id == second_id


def test_reject_ungrounded_draft_at_save(uow: SqlUnitOfWork) -> None:
    workspace_id, role_id, span_id = _seed_role_with_span(uow)
    with uow:
        with pytest.raises(ValueError, match="groundedness"):
            uow.drafts.save(
                NewGeneratedDraft(
                    id=str(uuid.uuid4()),
                    workspace_id=workspace_id,
                    role_id=role_id,
                    kind="bullets",
                    body="Invented Kubernetes experience.",
                    analysis_version=1,
                    citation_span_ids=(span_id,),
                    provider="hermetic",
                    model_tag="rules-v1",
                    left_machine=False,
                    groundedness=GroundednessVerdict.FAIL,
                    used_template_fallback=False,
                    regeneration_count=0,
                )
            )
        uow.rollback()
