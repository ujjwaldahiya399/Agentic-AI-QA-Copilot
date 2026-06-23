
from typing import TypedDict

class QAState(TypedDict):
    """
    A class represting the state of a QA pipeline agent. It contains the following fields:

    """
    pr_url: str
    pr_title: str
    pr_desc: str
    raw_diff: str
    changed_files: dict[str, str]  # filename to content mapping

    # code review agent output
    review_summary: str
    risk_areas: str

    # Test Runner Agent output
    test_cases: str
    test_results: str

    # Report Agent output
    final_report: str



