"""Method tracing with content-free summaries (spec 013, FR-003 to FR-005)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import pytest

from career_assistant import tracing
from career_assistant.tracing import summarize, traced

_PRIVATE = "Led the Kubernetes migration for a private client"
_UUID = "7a797ad4-746f-41ac-9472-12504755fc5b"


class Stage(StrEnum):
    SCORING = "scoring"


@dataclass(frozen=True)
class Inner:
    id: str
    text: str


@dataclass(frozen=True)
class Job:
    id: str
    role_id: str
    stage: Stage
    text: str
    chunks: tuple[Inner, ...]
    inner: Inner
    score: float | None = None


class Summarised:
    def log_summary(self) -> str:
        return "verdicts=2 met=1 missing=1"


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        pytest.param("x", None, "None", id="none"),
        pytest.param("x", True, "True", id="bool"),
        pytest.param("x", 73, "73", id="int"),
        pytest.param("x", 61.25, "61.25", id="float"),
        pytest.param("x", Stage.SCORING, "scoring", id="enum"),
        pytest.param("x", date(2026, 10, 13), "2026-10-13", id="date"),
        pytest.param("x", _UUID, _UUID, id="uuid"),
        pytest.param("key", "ab" * 32, "ab" * 32, id="hex-digest"),
        pytest.param("model_tag", "gpt-5-mini", "gpt-5-mini", id="id-suffix"),
        pytest.param("phase", "repair", "repair", id="safe-name"),
        pytest.param("text", _PRIVATE, f"str[len={len(_PRIVATE)}]", id="free-text"),
        pytest.param(
            "role_id", _PRIVATE, f"str[len={len(_PRIVATE)}]", id="id-with-text"
        ),
        pytest.param("x", b"\x00" * 9, "bytes[len=9]", id="bytes"),
        pytest.param("x", {"a": 1, "b": 2}, "dict[len=2]", id="mapping"),
        pytest.param("x", (), "tuple[0]", id="empty"),
        pytest.param("x", [Inner("i", "t")] * 3, "list[3 Inner]", id="list"),
        pytest.param("x", Summarised(), "verdicts=2 met=1 missing=1", id="own-summary"),
        pytest.param("x", object(), "object", id="other"),
    ],
)
def test_values_are_summarised_by_type(name: str, value: object, expected: str) -> None:
    assert summarize(name, value) == expected


def test_a_dataclass_shows_ids_and_shapes_but_not_its_text() -> None:
    job = Job(
        _UUID,
        "r-1",
        Stage.SCORING,
        _PRIVATE,
        (Inner("c1", _PRIVATE),),
        Inner("c2", _PRIVATE),
    )

    summary = summarize("job", job)

    assert summary == (
        f"Job(id={_UUID},role_id=r-1,stage=scoring,text=str[len={len(_PRIVATE)}],"
        "chunks=tuple[1 Inner],inner=Inner,score=None)"
    )
    assert _PRIVATE not in summary


def test_a_long_summary_is_clipped() -> None:
    many = {f"field_{i}": i for i in range(200)}
    wide = type("Wide", (), {"log_summary": lambda self: " ".join(map(str, many))})()

    assert len(summarize("x", wide)) <= 190


@traced
def _score(job_id: str, text: str, *, weight: float = 1.0) -> float:
    del job_id, text
    return 61.25 * weight


@traced
def _explode(job_id: str) -> None:
    del job_id
    raise ValueError(_PRIVATE)


@traced
class _Service:
    def run(self, job: Job) -> Inner:
        return job.inner

    def _private(self) -> int:
        return 1


def _messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records]


def test_a_traced_call_logs_start_and_done_with_summaries(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        assert _score(_UUID, _PRIVATE, weight=2.0) == 122.5

    start, done = _messages(caplog)
    assert start == (
        f"call.start fn=_score job_id={_UUID} text=str[len={len(_PRIVATE)}] weight=2.0"
    )
    assert done.startswith("call.done fn=_score duration_ms=")
    assert done.endswith("result=122.5")
    assert all(r.levelno == logging.DEBUG for r in caplog.records)


def test_a_failure_is_logged_by_type_and_re_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG), pytest.raises(ValueError):
        _explode("job-1")

    start, error = _messages(caplog)
    assert start == "call.start fn=_explode job_id=job-1"
    assert error.startswith("call.error fn=_explode duration_ms=")
    assert error.endswith("error=ValueError")
    assert _PRIVATE not in caplog.text


def test_a_traced_class_traces_its_public_methods_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    job = Job(_UUID, "r-1", Stage.SCORING, _PRIVATE, (), Inner("c2", _PRIVATE))
    service = _Service()
    with caplog.at_level(logging.DEBUG):
        service.run(job)
        service._private()

    start, done = _messages(caplog)
    assert start.startswith(f"call.start fn=_Service.run job=Job(id={_UUID},")
    assert done.endswith("result=Inner(id=c2,text=str[len=49])")


def test_nothing_is_summarised_above_debug(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(name: str, value: object) -> str:
        raise AssertionError("summarised above DEBUG")

    monkeypatch.setattr(tracing, "summarize", refuse)
    with caplog.at_level(logging.INFO):
        assert _score("job-1", _PRIVATE) == 61.25

    assert caplog.records == []
