"""Verify Week 4 repair traces and a controlled local Git change in QA Copilot."""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch


LOCAL_URL = "http://localhost:3000"
REVIEW = "---REVIEW_SUMMARY---\nInspect the changed function.\n---RISK_AREAS---\nCheck whether the expected return value of 4 is preserved."
INVALID = "def test_value(:\n    pass"
VALID = "from widget import value\n\ndef test_value():\n    assert value() == 4"
CASES = (
    ("repair_recovers", (INVALID, VALID), "PYTEST_OK"),
    ("repair_exhausted", (INVALID, INVALID, ""), "INVALID_GEN"),
    ("controlled_local_pr", (VALID,), "TEST_FAILURE"),
)


def local_pr_fixture():
    """Create a base and head commit, then read the exact head bytes and diff."""
    with TemporaryDirectory(prefix="qa-week4-pr-") as folder:
        repo = Path(folder)

        def git(*args):
            return subprocess.check_output(
                ["git", "-c", "user.name=QA Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                cwd=repo,
                text=True,
            )

        git("init", "--quiet", "--template=", "--initial-branch=fixture-base")
        file = repo / "widget.py"
        file.write_text("def value():\n    return 4\n", encoding="utf-8")
        git("add", "--", file.name)
        git("commit", "--quiet", "-m", "Define the expected value")
        base = git("rev-parse", "HEAD").strip()
        git("switch", "--quiet", "-c", "fixture-change")
        file.write_text("def value():\n    return 3\n", encoding="utf-8")
        git("add", "--", file.name)
        git("commit", "--quiet", "-m", "Introduce a controlled regression")
        head = git("rev-parse", "HEAD").strip()
        state = {
            "pr_url": "https://example.invalid/widget/pull/1",
            "pr_sha": head,
            "pr_title": "Controlled local PR fixture",
            "pr_desc": "The expected behavior from the base revision is to return 4.",
            "raw_diff": git("diff", "--no-ext-diff", "--no-textconv", f"{base}...{head}"),
            "changed_files": {file.name: git("show", f"{head}:{file.name}")},
        }
    return state, base


def run_case(graph, completion_module, handler, name, replies, expected_outcome, initial_state):
    state = dict(initial_state)
    state["pr_title"] = name
    responses = [
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])
        for text in (REVIEW, *replies)
    ]
    trace_name = f"qa-copilot-week4-{name}"
    config = {"callbacks": [handler], "run_name": trace_name}
    route = []
    validations = []
    with patch.object(completion_module, "completion", side_effect=responses):
        for updates in graph.stream(state, config=config, stream_mode="updates"):
            for node, update in updates.items():
                state.update(update)
                route.append(node)
                if node == "validate_tests":
                    validations.append(update["validation_result"])

    execution = state.get("execution_result")
    attempts = len(replies) - 1
    expected_route = ["code_review", "generate_tests", "validate_tests"]
    expected_route += ["repair_tests", "validate_tests"] * attempts
    if expected_outcome != "INVALID_GEN":
        expected_route.append("test_runner")
    expected_route += ["classify", "report"]
    return {
        "trace_name": trace_name,
        "trace_id": handler.last_trace_id,
        "expected_outcome": expected_outcome,
        "classification": state["classification"],
        "pr_head_sha": state["pr_sha"],
        "repair_attempts": state.get("repair_attempts", 0),
        "expected_repair_attempts": attempts,
        "expected_route": expected_route,
        "route": route,
        "validation_results": validations,
        "runner_exit_code": execution["exit_code"] if execution else None,
        "runner_duration_ms": execution["duration_ms"] if execution else None,
        "report": state["final_report"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("week4_closeout"))
    args = parser.parse_args()
    if not Path("agents/graph.py").is_file():
        parser.error("Run this from the QA Copilot repository root.")

    os.environ["LANGFUSE_BASE_URL"] = LOCAL_URL
    for env_name, label in (
        ("LANGFUSE_PUBLIC_KEY", "Local Langfuse public key"),
        ("LANGFUSE_SECRET_KEY", "Local Langfuse secret key"),
    ):
        value = os.environ.get(env_name) or getpass(f"{label}: ").strip()
        if not value:
            parser.error(f"{label} is required.")
        os.environ[env_name] = value

    sys.path.insert(0, str(Path.cwd()))
    from langfuse import get_client
    from langfuse.langchain import CallbackHandler

    from agents.graph import qa_graph
    from agents.nodes import test_runner

    client = get_client()
    if not client.auth_check():
        parser.error("Langfuse rejected the credentials or is unavailable at " + LOCAL_URL)

    pr_state, base_sha = local_pr_fixture()
    repair_state = {
        **pr_state,
        "pr_desc": "Synthetic repair fixture with a known passing assertion.",
        "raw_diff": "+def value():\n+    return 4\n",
        "pr_sha": "a" * 40,
        "changed_files": {"widget.py": "def value():\n    return 4\n"},
    }
    traces = []
    try:
        for name, replies, expected in CASES:
            state = pr_state if name == "controlled_local_pr" else repair_state
            row = run_case(qa_graph, test_runner.litellm, CallbackHandler(), name, replies, expected, state)
            traces.append(row)
            print(f"{row['trace_name']}: {row['classification']['code']} | trace {row['trace_id']}")
            print("  " + " -> ".join(row["route"]))
    finally:
        client.flush()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = traces[-1]["report"]
    (args.output_dir / "controlled_local_pr_report.md").write_text(report + "\n", encoding="utf-8")
    evidence = {
        "controlled_pr_base_sha": base_sha,
        "controlled_pr_diff": pr_state["raw_diff"],
        "runs": traces,
    }
    (args.output_dir / "trace_evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8",
    )
    print(f"Report and trace evidence saved to {args.output_dir}. Confirm all three traces in Langfuse.")
    return 0 if all(
        row["trace_id"]
        and row["classification"]["code"] == row["expected_outcome"]
        and row["repair_attempts"] == row["expected_repair_attempts"]
        and row["route"] == row["expected_route"]
        for row in traces
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
