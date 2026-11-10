
from typing import Literal, Optional, TypedDict


class ValidationResult(TypedDict):
    valid: bool
    message: str


class ExecutionResult(TypedDict):
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool


OutcomeCode = Literal["INVALID_GEN", "PYTEST_OK", "TEST_FAILURE", "NO_TESTS", "TIMEOUT", "EXECUTION_ERROR"]


class ExecutionClassification(TypedDict):
    code: OutcomeCode
    reason: str


class QAInput(TypedDict):
    """Pull request data available when the workflow starts."""

    pr_url: str
    pr_sha: str
    pr_title: str
    pr_desc: str
    raw_diff: str
    changed_files: dict[str, str]


class QAState(QAInput, total=False):
    """Shared state with outputs added by nodes as they run."""
    review_error: str
    review_summary: str
    risk_areas: str
    review_summary: str
    risk_areas: str
    test_cases: str
    repair_attempts: int
    validation_result: ValidationResult
    execution_result: ExecutionResult
    classification: ExecutionClassification
    test_results: str
    final_report: str
