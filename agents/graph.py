from langgraph.graph import END, START, StateGraph

from .nodes.classify import classify_execution
from .nodes.code_review import PRReviewerNode
from .nodes.report import ReportAgent
from .nodes.test_runner import TestGeneratorNode, TestRunnerNode
from .state import QAState
from .validation import validate_generated_tests


MAX_REPAIR_ATTEMPTS = 2

def route_after_review(state: QAState) -> str:
    return "classify" if state.get("review_error") else "generate_tests"


def route_after_validation(state: QAState) -> str:
    if state["validation_result"]["valid"]:
        return "test_runner"
    if state.get("repair_attempts", 0) < MAX_REPAIR_ATTEMPTS:
        return "repair_tests"
    return "classify"


builder = StateGraph(QAState)
builder.add_node("code_review", PRReviewerNode())
builder.add_node("generate_tests", TestGeneratorNode())
builder.add_node("validate_tests", validate_generated_tests)
builder.add_node("repair_tests", TestGeneratorNode(repair=True))
builder.add_node("test_runner", TestRunnerNode())
builder.add_node("classify", classify_execution)
builder.add_node("report", ReportAgent())

builder.add_edge(START, "code_review")
builder.add_conditional_edges(
    "code_review",
    route_after_review,
    {"generate_tests": "generate_tests", "classify": "classify"},
)
builder.add_edge("generate_tests", "validate_tests")
builder.add_conditional_edges(
    "validate_tests",
    route_after_validation,
    {"test_runner": "test_runner", "repair_tests": "repair_tests", "classify": "classify"},
)
builder.add_edge("repair_tests", "validate_tests")
builder.add_edge("test_runner", "classify")
builder.add_edge("classify", "report")
builder.add_edge("report", END)

qa_graph = builder.compile()
