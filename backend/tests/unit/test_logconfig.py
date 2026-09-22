"""Phase 15B.2 — optional rotating log file, never document text or secrets."""

from __future__ import annotations

import logging
from pathlib import Path

from career_assistant.logconfig import configure_logging, log_event
from career_assistant.settings import LoggingSettings

_PLANTED_CV = "PLANTED_CV_PHRASE_MUST_NOT_APPEAR_IN_LOGS_9f3c2a"
_PLANTED_KEY = "sk-planted-secret-key-value-for-redaction"


def _flush_app_handlers() -> None:
    log = logging.getLogger("career_assistant")
    for handler in log.handlers:
        handler.flush()


def _file_handlers() -> list[logging.Handler]:
    log = logging.getLogger("career_assistant")
    return [
        handler for handler in log.handlers if isinstance(handler, logging.FileHandler)
    ]


def test_log_file_receives_event_when_configured(tmp_path: Path) -> None:
    path = tmp_path / "career-assistant.log"
    configure_logging(force=True, log_file=str(path), level=logging.DEBUG)
    log = logging.getLogger("career_assistant.test_file")

    log_event(log, "cv.uploaded", document_id="doc-file-1")
    _flush_app_handlers()

    text = path.read_text(encoding="utf-8")
    assert "cv.uploaded" in text
    assert "document_id=doc-file-1" in text


def test_log_file_redacts_planted_phrase_and_key_at_debug(tmp_path: Path) -> None:
    path = tmp_path / "career-assistant.log"
    configure_logging(
        force=True,
        log_file=str(path),
        level=logging.DEBUG,
        secret_values=(_PLANTED_KEY,),
    )
    log = logging.getLogger("career_assistant.test_file")

    log_event(
        log,
        "cv.uploaded",
        leaked="line1\n" + _PLANTED_CV,
        blob="x" * 500,
        document_id="doc-file-2",
    )
    log.debug("provider_constructed key=%s", _PLANTED_KEY)
    _flush_app_handlers()

    text = path.read_text(encoding="utf-8")
    assert "cv.uploaded" in text
    assert "document_id=doc-file-2" in text
    assert _PLANTED_CV not in text
    assert _PLANTED_KEY not in text
    assert "x" * 50 not in text
    assert "multiline" in text or "len=500" in text
    assert "redacted" in text.lower()


def test_empty_log_file_attaches_no_file_handler() -> None:
    configure_logging(force=True, log_file="")

    assert _file_handlers() == []


def test_unset_log_file_attaches_no_file_handler() -> None:
    configure_logging(force=True)

    assert _file_handlers() == []


def test_logging_settings_default_to_stderr_only() -> None:
    settings = LoggingSettings(_env_file=None)

    assert settings.log_file == ""
    assert settings.log_level == "INFO"
    assert settings.log_file_max_bytes == 10_485_760
    assert settings.log_file_backup_count == 5
    assert settings.resolved_level() == logging.INFO
