"""Review a PR diff and validate the model's response."""

import litellm
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agents.state import QAState


class ReviewOutput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    review_summary: str = Field(min_length=1)
    risk_areas: str = Field(min_length=1)


def parse_review(raw_text: str | None) -> ReviewOutput:
    summary_marker = "---REVIEW_SUMMARY---"
    risks_marker = "---RISK_AREAS---"
    text = raw_text.strip() if isinstance(raw_text, str) else ""

    if (
        not text.startswith(summary_marker)
        or text.count(summary_marker) != 1
        or text.count(risks_marker) != 1
    ):
        raise ValueError("Code review response is missing required section markers.")

    summary, _, risks = text[len(summary_marker):].partition(risks_marker)
    try:
        return ReviewOutput.model_validate({
            "review_summary": summary.strip(),
            "risk_areas": risks.strip(),
        })
    except ValidationError as error:
        raise ValueError(
            "Code review response requires a nonempty summary and risk areas."
        ) from error


class PRReviewerNode:
    """Review a PR change with an LLM and return validated review fields."""

    def __init__(self, model_id: str = "groq/llama-3.3-70b-versatile"):
        self.model_id = model_id

    def __call__(self, state: QAState) -> dict[str, str]:
        pr_url = state.get("pr_url", "No URL provided.")
        pr_title = state.get("pr_title", "Untitled PR")
        pr_desc = state.get("pr_desc", "No description provided.")
        raw_diff = state.get("raw_diff", "")
        changed_files = state.get("changed_files", {})

        if not raw_diff:
            return {
                "review_summary": "Skipped: No code changes detected in the diff.",
                "risk_areas": "None",
            }

        system_prompt = (
            "You are an expert Senior QA Engineer and Code Reviewer. Your job is to analyze "
            "incoming GitHub Pull Request diffs. Identify logical flaws, edge cases, security "
            "vulnerabilities, and structural risks. Be concise, direct, and actionable."
        )

        user_prompt = f"""
Pull Request Title: {pr_title}
Description: {pr_desc}
Pull Request URL: {pr_url}
--- RAW GIT DIFF ---
{raw_diff}
--------------------

Review the diff above. Provide your analysis strictly in the following format:
---REVIEW_SUMMARY---
[Provide a clear, high-level summary of what this code changes and its apparent intent in human terms.]

---RISK_AREAS---
[List specific, actionable risk areas, fragile boundaries, or edge cases that a QA engineer must target with testing.]
"""
        if changed_files:
            files_summary = "\n".join(
                f"Filename: {filename}\nContent:\n{content}\n---"
                for filename, content in changed_files.items()
            )
            user_prompt += (
                f"\n\nThe following files were changed in this PR:\n{files_summary}"
            )

        response = litellm.completion(
            model=self.model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )

        raw_text = response.choices[0].message.content
        try:
            review = parse_review(raw_text)
        except ValueError as error:
            return {"review_error": str(error)}

        return {
            "review_summary": review.review_summary,
            "risk_areas": review.risk_areas,
        }