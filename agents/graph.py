from langgraph.graph import END, START, StateGraph

from .nodes.classify import classify_execution
from .nodes.code_review import PRReviewerNode
from .nodes.report import ReportAgent
from .nodes.test_runner import TestGeneratorNode, TestRunnerNode
from .state import QAState
from .validation import validate_generated_tests


def route_after_validation(state: QAState) -> str:
    return "test_runner" if state["validation_result"]["valid"] else "classify"


builder = StateGraph(QAState)
builder.add_node("code_review", PRReviewerNode())
builder.add_node("generate_tests", TestGeneratorNode())
builder.add_node("validate_tests", validate_generated_tests)
builder.add_node("test_runner", TestRunnerNode())
builder.add_node("classify", classify_execution)
builder.add_node("report", ReportAgent())

builder.add_edge(START, "code_review")
builder.add_edge("code_review", "generate_tests")
builder.add_edge("generate_tests", "validate_tests")
builder.add_conditional_edges(
    "validate_tests",
    route_after_validation,
    {"test_runner": "test_runner", "classify": "classify"},
)
builder.add_edge("test_runner", "classify")
builder.add_edge("classify", "report")
builder.add_edge("report", END)

qa_graph = builder.compile()
