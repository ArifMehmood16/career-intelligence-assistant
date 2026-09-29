"""A validation error becomes the text of one repair request (PLAN 18.2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_assistant.application.contracts.agent import AgentAnswer
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.contracts.repair import render_repair_message

_SENTINEL = "SECRET-CV-TEXT-7731"


def _error(
    contract: type[AgentAnswer] | type[JudgeResponse], payload: object
) -> ValidationError:
    with pytest.raises(ValidationError) as caught:
        contract.model_validate(payload)
    return caught.value


def _judge_with_score(score: int) -> dict[str, object]:
    return {
        "verdicts": [
            {
                "requirement_id": "r1",
                "verdict": "met",
                "match": {"score": score, "rationale": "ok", "evidence": []},
                "retrieval_feedback": {"sufficient": True},
            }
        ]
    }


def test_each_error_is_listed_with_its_json_path() -> None:
    message = render_repair_message(_error(JudgeResponse, _judge_with_score(7)))

    assert "- verdicts[0].match.score: " in message
    assert "less than or equal to 4" in message


def test_the_message_asks_for_the_complete_json_again() -> None:
    message = render_repair_message(_error(AgentAnswer, {"answer": "x"}))

    assert message.startswith(
        "Your previous response did not match the required JSON schema."
    )
    assert "Return the complete JSON object again" in message
    assert "- support: Field required" in message


def test_the_invalid_values_themselves_are_not_repeated() -> None:
    error = _error(
        AgentAnswer,
        {"answer": "x", "support": _SENTINEL, "extra_field": _SENTINEL},
    )

    message = render_repair_message(error)

    assert _SENTINEL not in message
    assert "- extra_field: Extra inputs are not permitted" in message


def test_a_long_error_list_is_capped() -> None:
    payload = {"verdicts": [_judge_with_score(9)["verdicts"][0] for _ in range(30)]}  # type: ignore[index]

    message = render_repair_message(_error(JudgeResponse, payload), max_errors=5)

    assert message.count("\n- ") == 5
    assert "and 25 more" in message


def test_invalid_json_is_reported_as_such() -> None:
    with pytest.raises(ValidationError) as caught:
        AgentAnswer.model_validate_json('{"answer": "x", "support": ')

    assert "- (root): Invalid JSON" in render_repair_message(caught.value)
