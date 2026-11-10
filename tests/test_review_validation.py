from types import SimpleNamespace

import pytest

from agents.graph import qa_graph


@pytest.mark.parametrize(
    ("review_text", "expected_reason"),
    [
        (
            "A review without required markers",
            "missing required section markers",
        ),
        (
            "---REVIEW_SUMMARY---\nOne change.\n---RISK_AREAS---\n   ",
            "nonempty summary and risk areas",
        ),
    ],
    ids=["missing-markers", "empty-risk-areas"],
)
def test_malformed_review_skips_generation_and_docker(
    monkeypatch, review_text, expected_reason
):
    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) > 1:
            raise AssertionError("Test generation must not run")
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=review_text)
                )
            ]
        )

    monkeypatch.setattr(
        "agents.nodes.code_review.litellm.completion",
        fake_completion,
    )

    result = qa_graph.invoke({
        "pr_url": "https://example.invalid/pull/1",
        "pr_sha": "a" * 40,
        "pr_title": "Malformed review fixture",
        "pr_desc": "",
        "raw_diff": "+return 3",
        "changed_files": {"widget.py": "def value():\n    return 3\n"},
    })

    assert len(calls) == 1
    assert result["classification"]["code"] == "INVALID_REVIEW"
    assert expected_reason in result["classification"]["reason"]
    assert expected_reason in result["final_report"]
    assert "Pytest execution was skipped." in result["final_report"]
    assert "## Risk Areas Identified by Code Review" not in result["final_report"]
    assert "execution_result" not in result
    assert "test_cases" not in result