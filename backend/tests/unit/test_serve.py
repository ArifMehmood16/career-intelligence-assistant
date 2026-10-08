"""Container startup migrates successfully before replacing its process."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError

from career_assistant.adapters.persistence import startup as serve


def test_startup_migrates_before_executing_uvicorn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        serve, "DatabaseSettings", lambda: SimpleNamespace(database_url="isolated")
    )
    monkeypatch.setattr(
        serve, "upgrade_head", lambda url: calls.append(f"migrate:{url}")
    )

    def execute(executable: str, arguments: tuple[str, ...]) -> None:
        assert executable == serve.sys.executable
        assert arguments == (
            executable,
            "-m",
            "uvicorn",
            "career_assistant.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        )
        calls.append("serve")

    monkeypatch.setattr(serve.os, "execv", execute)
    serve.main()
    assert calls == ["migrate:isolated", "serve"]


def test_failed_migration_never_serves_or_logs_its_payload(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        serve, "DatabaseSettings", lambda: SimpleNamespace(database_url="isolated")
    )

    def fail(url: str) -> None:
        raise OperationalError(
            "private statement", {}, RuntimeError("private credentials")
        )

    def execute(executable: str, arguments: tuple[str, ...]) -> None:
        pytest.fail("a failed migration must not start the server")

    monkeypatch.setattr(serve, "upgrade_head", fail)
    monkeypatch.setattr(serve.os, "execv", execute)
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as stopped:
        serve.main()
    assert stopped.value.code == 1
    assert "startup.migration_failed" in caplog.text
    assert "OperationalError" in caplog.text
    assert "private" not in caplog.text
