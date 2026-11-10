"""Verify the repair cap, revalidation, and preservation of failed assertions."""

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agents.graph import qa_graph
from agents.nodes import test_runner
from agents.validation import validate_test_code


REVIEW = "---REVIEW_SUMMARY---\nReturn 4.\n---RISK_AREAS---\nCheck the value."
INVALID = "def test_value(:\n    pass"
PASS = "from widget import value\n\ndef test_value():\n    assert value() == 4"
FAIL = "from widget import value\n\ndef test_value():\n    assert value() == 5"


def model_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.mark.parametrize(
    ("generated_tests", "attempts", "outcome", "exit_code"),
    [
        pytest.param([INVALID, PASS], 1, "PYTEST_OK", 0, id="repairs-on-first-attempt"),
        pytest.param([INVALID, "", PASS], 2, "PYTEST_OK", 0, id="repairs-on-second-attempt"),
        pytest.param([INVALID, INVALID, ""], 2, "INVALID_GEN", None, id="stops-after-two-attempts"),
        pytest.param([FAIL], 0, "TEST_FAILURE", 1, id="leaves-failed-assertion-intact"),
    ],
)
def test_repair_routing(generated_tests, attempts, outcome, exit_code):
    source = {"widget.py": "def value():\n    return 4\n"}
    state = {
        "pr_url": "https://example.invalid/widget/pull/1",
        "pr_sha": "a" * 40,
        "pr_title": "Repair test fixture",
        "pr_desc": "",
        "raw_diff": "+def value():\n+    return 4\n",
        "changed_files": source,
    }
    fixture_execution = {
        "exit_code": exit_code,
        "stdout": "1 passed" if exit_code == 0 else "1 failed\nassert 4 == 5",
        "stderr": "",
        "timed_out": False,
        "duration_ms": 1,
    }
    if os.getenv("QA_TEST_REAL_DOCKER") == "1":
        runner_options = {"wraps": test_runner.run_tests_in_docker}
    else:
        runner_options = {"return_value": fixture_execution}

    with (
        patch.object(
            test_runner.litellm,
            "completion",
            side_effect=[model_response(text) for text in [REVIEW, *generated_tests]],
        ) as completion,
        patch.object(test_runner, "run_tests_in_docker", **runner_options) as runner,
    ):
        route = []
        for updates in qa_graph.stream(state, stream_mode="updates"):
            for node, update in updates.items():
                route.append(node)
                state.update(update)

    expected_route = ["code_review", "generate_tests", "validate_tests"]
    expected_route += ["repair_tests", "validate_tests"] * attempts
    if exit_code is None:
        runner.assert_not_called()
        assert "The model returned no test code." in state["final_report"]
        assert "Pytest execution was skipped." in state["final_report"]
    else:
        expected_route.append("test_runner")
        runner.assert_called_once_with(source, generated_tests[-1])
        assert state["execution_result"]["exit_code"] == exit_code
    assert route == expected_route + ["classify", "report"]
    assert state["classification"]["code"] == outcome
    assert state.get("repair_attempts", 0) == attempts
    assert completion.call_count == 2 + attempts
    for call, previous_code in zip(completion.call_args_list[2:], generated_tests[:-1]):
        prompt = call.kwargs["messages"][-1]["content"]
        diagnostic = validate_test_code(previous_code)["message"]
        assert f"Validation error: {diagnostic}" in prompt
        assert f"Previous pytest code:\n{previous_code}" in prompt
    if attempts:
        assert f"Repair attempts used: {attempts}." in state["final_report"]
        assert state["test_cases"] == generated_tests[-1]
    if outcome == "TEST_FAILURE":
        assert "assert 4 == 5" in state["final_report"]
