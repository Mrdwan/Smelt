import json
from unittest.mock import MagicMock, patch

import pytest

from smelt.agents.plan_parser import ParsedStep, PlanParserAgent
from smelt.exceptions import PlanParseError


def _make_response(content: str) -> MagicMock:
    response = MagicMock()
    response.choices[0].message.content = content
    return response


def _steps_json(steps: list[dict]) -> str:
    return json.dumps(steps)


def test_parse_returns_steps() -> None:
    payload = [
        {"description": "Set up database", "done": False},
        {"description": "Add authentication", "done": False},
    ]

    with patch("litellm.completion", return_value=_make_response(_steps_json(payload))):
        result = PlanParserAgent(model="test/model").parse("some plan")

    assert result == [
        ParsedStep(description="Set up database", done=False),
        ParsedStep(description="Add authentication", done=False),
    ]


def test_parse_preserves_done_status() -> None:
    payload = [
        {"description": "Set up database", "done": True},
        {"description": "Add authentication", "done": False},
    ]

    with patch("litellm.completion", return_value=_make_response(_steps_json(payload))):
        result = PlanParserAgent(model="test/model").parse("some plan")

    assert result[0].done is True
    assert result[1].done is False


def test_parse_strips_whitespace() -> None:
    payload = [
        {"description": "  Add login page  ", "done": False},
        {"description": " Write tests ", "done": False},
    ]

    with patch("litellm.completion", return_value=_make_response(_steps_json(payload))):
        result = PlanParserAgent(model="test/model").parse("some plan")

    assert result[0].description == "Add login page"
    assert result[1].description == "Write tests"


def test_parse_filters_empty_descriptions() -> None:
    payload = [
        {"description": "Add login page", "done": False},
        {"description": "", "done": False},
        {"description": "  ", "done": False},
        {"description": "Write tests", "done": False},
    ]

    with patch("litellm.completion", return_value=_make_response(_steps_json(payload))):
        result = PlanParserAgent(model="test/model").parse("some plan")

    assert len(result) == 2
    assert result[0].description == "Add login page"
    assert result[1].description == "Write tests"


def test_parse_strips_markdown_code_fence() -> None:
    payload = [{"description": "Do something", "done": False}]
    fenced = f"```json\n{_steps_json(payload)}\n```"

    with patch("litellm.completion", return_value=_make_response(fenced)):
        result = PlanParserAgent(model="test/model").parse("some plan")

    assert result == [ParsedStep(description="Do something", done=False)]


def test_parse_strips_generic_code_fence() -> None:
    payload = [{"description": "Do something", "done": False}]
    fenced = f"```\n{_steps_json(payload)}\n```"

    with patch("litellm.completion", return_value=_make_response(fenced)):
        result = PlanParserAgent(model="test/model").parse("some plan")

    assert result == [ParsedStep(description="Do something", done=False)]


def test_parse_raises_on_invalid_json() -> None:
    with patch("litellm.completion", return_value=_make_response("not json at all")):
        with pytest.raises(PlanParseError, match="invalid JSON"):
            PlanParserAgent(model="test/model").parse("some plan")


def test_parse_raises_on_non_list_json() -> None:
    with patch("litellm.completion", return_value=_make_response('{"steps": []}')):
        with pytest.raises(PlanParseError, match="unexpected structure"):
            PlanParserAgent(model="test/model").parse("some plan")


def test_parse_raises_on_list_missing_fields() -> None:
    with patch(
        "litellm.completion",
        return_value=_make_response('[{"description": "only description"}]'),
    ):
        with pytest.raises(PlanParseError, match="unexpected structure"):
            PlanParserAgent(model="test/model").parse("some plan")


def test_parse_raises_on_llm_error() -> None:
    with patch("litellm.completion", side_effect=Exception("API timeout")):
        with pytest.raises(PlanParseError, match="LLM call failed"):
            PlanParserAgent(model="test/model").parse("some plan")


def test_default_retries_passed_to_litellm() -> None:
    payload = [{"description": "Do something", "done": False}]

    with patch(
        "litellm.completion", return_value=_make_response(_steps_json(payload))
    ) as mock:
        PlanParserAgent(model="test/model").parse("some plan")

    assert mock.call_args.kwargs["num_retries"] == 3


def test_custom_retries_passed_to_litellm() -> None:
    payload = [{"description": "Do something", "done": False}]

    with patch(
        "litellm.completion", return_value=_make_response(_steps_json(payload))
    ) as mock:
        PlanParserAgent(model="test/model", retries=5).parse("some plan")

    assert mock.call_args.kwargs["num_retries"] == 5
