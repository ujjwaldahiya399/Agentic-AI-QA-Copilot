import re

from agents.state import OutcomeCode, QAState


_VERDICTS: dict[OutcomeCode, str] = {
    "INVALID_REVIEW": "⚠️ Code review response failed validation",
    "INVALID_GEN": "⚠️ Generated tests failed validation",
    "PYTEST_OK": "✅ Pytest completed successfully",
    "TEST_FAILURE": "❌ Test failure reported",
    "NO_TESTS": "⚠️ No tests collected",
    "TIMEOUT": "⚠️ Execution timed out",
    "EXECUTION_ERROR": "⚠️ Execution error",
}


class ReportAgent:
    """Render the classification and supporting evidence as Markdown."""

    def __call__(self, state: QAState) -> dict[str, str]:
        classification = state["classification"]
        code = classification["code"]
        pr_title = state.get("pr_title", "N/A")
        pr_sha = state.get("pr_sha", "Unknown")
        execution = state.get("execution_result")

        sections = [
            f"# QA Pipeline Report — {pr_title}",
            f"Reviewed PR head commit `{pr_sha}`.",
            f"## Verdict\n### {_VERDICTS[code]}",
            classification["reason"],
        ]

        repair_attempts = state.get("repair_attempts", 0)
        if repair_attempts:
            sections.append(f"Repair attempts used: {repair_attempts}.")

        if code in ("INVALID_REVIEW", "INVALID_GEN"):
            sections.append("Pytest execution was skipped.")
        elif execution is not None:
            exit_code = execution["exit_code"]
            code_label = "unavailable" if exit_code is None else str(exit_code)
            sections.append(
                f"Runner exit code `{code_label}`. "
                f"Duration `{execution['duration_ms']} ms`."
            )

            if code in ("PYTEST_OK", "TEST_FAILURE"):
                lines = execution["stdout"].strip().splitlines()
                summary = lines[-1] if lines else ""
                counts = re.findall(
                    r"\b\d+\s+(?:passed|failed|skipped|errors?)\b",
                    summary,
                )
                if counts:
                    sections.append("**Pytest summary** " + ", ".join(counts))

        if code != "INVALID_REVIEW":
            risk_areas = state.get("risk_areas", "N/A")
            sections.append(
                f"## Risk Areas Identified by Code Review\n\n{risk_areas}"
            )

        if execution is not None and code not in ("INVALID_REVIEW", "INVALID_GEN"):
            sections.append(
                f"## Full Test Log\n\n```\n{state.get('test_results', '')}\n```"
            )

        return {"final_report": "\n\n".join(sections)}