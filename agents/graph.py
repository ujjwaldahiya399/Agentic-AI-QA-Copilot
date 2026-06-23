# this is where you wire everything together with LangGraph. Think about what you learned in the course:

# Create a StateGraph with your QAState
# Add your nodes
# Add edges connecting them: START → code_review → test_runner → report → END
# Compile the graph

# You only have the code_review node built so far, but you can stub the other two. Write graph.py — give it a shot.

from langgraph.graph import StateGraph, START, END
from .state import QAState
from .nodes.code_review import PRReviewerNode
from .nodes.test_runner import TestRunnerNode
from .nodes.report import ReportAgent
# 1. INITIALIZE BUILDER WITH STATE SCHEME
builder = StateGraph(QAState)

# 2. DEFINE AND REGISTER NODES
code_review_node = PRReviewerNode()

# 3. define and register test runner node
test_runner_node = TestRunnerNode()
report_node = ReportAgent()

# Register them into the builder
builder.add_node("code_review", code_review_node)
builder.add_node("test_runner", test_runner_node)
builder.add_node("report", report_node)

# 3. DEFINE WORKFLOW PATHWAYS (EDGES)
builder.add_edge(START, "code_review")
builder.add_edge("code_review", "test_runner")
builder.add_edge("test_runner", "report")
builder.add_edge("report", END)

# 4. COMPILE INTO A RUNNABLE GRAPH
qa_graph = builder.compile()
