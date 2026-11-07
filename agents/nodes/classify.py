from typing import Optional

from agents.state import ExecutionClassification, OutcomeCode, QAState


_RUNNER_OUTCOMES: dict[Optional[int], tuple[OutcomeCode, str]] = {
    0: ("PYTEST_OK", "Pytest completed without reporting a test failure."),
    1: ("TEST_FAILURE", "Pytest reported a test failure. Review the test and its output."),
    5: ("NO_TESTS", "Pytest collected zero tests."),
    None: ("EXECUTION_ERROR", "The runner could not provide an exit code. See the captured output."),
}


def classify_execution(state: QAState) -> dict[str, ExecutionClassification]:
    validation = state.get("validation_result")
    if validation is not None and not validation["valid"]:
        return {"classification": {"code": "INVALID_GEN", "reason": validation["message"]}}

    execution = state.get("execution_result")
    if execution is None:
        return {"classification": {"code": "EXECUTION_ERROR", "reason": "The workflow has no runner result."}}
    if execution["timed_out"]:
        return {"classification": {"code": "TIMEOUT", "reason": "The Docker run exceeded its time limit."}}

    exit_code = execution["exit_code"]
    code, reason = _RUNNER_OUTCOMES.get(exit_code, (
        "EXECUTION_ERROR", f"The runner exited with code {exit_code}. See the captured output.",
    ))
    return {"classification": {"code": code, "reason": reason}}
