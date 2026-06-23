# So report_agent becomes a plain Python function — no litellm.completion(), just string templating.
# it's safer to write two separate regex searches — one specifically looking for "X failed", one specifically
# looking for "Y passed" — rather than trying to match the whole line in one pattern.

# write two regex patterns, one to capture the failed count and one to capture the passed count, with
# a sensible default (like 0) if either isn't found in the text.

from agents.state import QAState
import re
class ReportAgent:
    """
    This agent takes the outputs from the code review and test runner agents, and compiles them into a final report.
    """
    def __call__(self, state: QAState) -> dict:
        pr_title = state.get("pr_title", "N/A")
        review_summary = state.get("review_summary", "N/A")
        risk_areas = state.get("risk_areas", "N/A")
        test_cases = state.get("test_cases", "N/A")
        test_results = state.get("test_results", "N/A")

        # Use regex to extract failed and passed counts
        failed_count = re.search(r"(\d+)\s+failed", test_results)
        passed_count = re.search(r"(\d+)\s+passed", test_results)

        failed_count = int(failed_count.group(1)) if failed_count else 0
        passed_count = int(passed_count.group(1)) if passed_count else 0

        # Write an if/elif/else block that sets a verdict variable to a clear
        # string for each of these three cases, then we'll restructure the report template around it.
        if failed_count > 0:
            verdict = "Failed"
        elif passed_count == 0 and failed_count == 0:
            verdict = "No Tests Found"
        elif passed_count > 0 and failed_count == 0:
            verdict = "Passed"

        # Write the full final_report Markdown template with the four sections in order: verdict → risk areas → test summary → full test log


        verdict_emoji = "❌" if verdict == "Failed" else ("⚠️" if verdict == "No Tests Found" else "✅")

        final_report = f"""# QA Pipeline Report — {pr_title}

## Verdict
### {verdict_emoji} {verdict}

**Tests Passed:** {passed_count} &nbsp;|&nbsp; **Tests Failed:** {failed_count}

---

## Risk Areas Identified by Code Review

{risk_areas}

---

## Test Summary

This pipeline auto-generated **{passed_count + failed_count} test case(s)** targeting the risk areas above.

- ✅ Passed: **{passed_count}**
- ❌ Failed: **{failed_count}**

---

## Full Test Log
```
{test_results}
```

---
*This report was generated automatically by an AI-powered QA pipeline (LangGraph + Groq/LLaMA 3.3 70B). 
Findings above are based on automated static review and live pytest execution — please verify manually before merging.*
"""
        return {"final_report": final_report.strip()}
    