from agents import state
import litellm
#In this class we will :
# Read diff and pr_metadata from state
# Send them to LLaMA 3.3 70B with a prompt asking for a code review
# Parse the response into review summary and risk areas
# Return {"review_summary": ..., "risk_areas": ...}
class PRReviewerNode:
    """
    LangGraph Node that handles structural code reviews using LLaMA 3.3 70B on Groq.
    Ingests raw PR context and outputs a structured summary and risk assessment.
    """
    def __init__(self, model_id: str = "groq/llama-3.3-70b-versatile"):
        self.model_id = model_id

    def __call__(self, state: state.QAState) -> dict:
        pr_url = state.get("pr_url", "No URL provided.")
        pr_title = state.get("pr_title", "Untitled PR")
        pr_desc = state.get("pr_desc", "No description provided.")
        raw_diff = state.get("raw_diff", "")
        changed_files = state.get("changed_files", {})
        if not raw_diff:
            return {
                "review_summary": "Skipped: No code changes detected in the diff.",
                "risk_areas": "None"
            }

        system_prompt = (
            "You are an expert Senior QA Engineer and Code Reviewer. Your job is to analyze "
            "incoming GitHub Pull Request diffs. Identify logical flaws, edge cases, security vulnerabilities, "
            "and structural risks. Be concise, direct, and actionable."
        )


#         Read changed_files from state
# Format it into the prompt somehow — since it's a dict of {filename: content}, you'll need to loop through it and build a readable string

        
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
            files_summary = "\n".join([f"Filename: {filename}\nContent:\n{content}\n---" for filename, content in changed_files.items()])
            user_prompt += f"\n\nThe following files were changed in this PR:\n{files_summary}"
                

        # 3. Send them to LLaMA 3.3 70B via LiteLLM
        response = litellm.completion(
            model=self.model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        raw_text = response.choices[0].message.content

        # 4. Parse the response into review summary and risk areas
        review_summary = "Could not parse review summary."
        risk_areas = "Could not parse risk areas."
        try:
            if "---REVIEW_SUMMARY---" in raw_text and "---RISK_AREAS---" in raw_text:
                parts = raw_text.split("---RISK_AREAS---")
                summary_part = parts[0].replace("---REVIEW_SUMMARY---", "").strip()
                risks_part = parts[1].strip()
                
                review_summary = summary_part
                risk_areas = risks_part
            else:
                # Fallback if the LLM didn't strictly follow the header format
                review_summary = raw_text
                risk_areas = "Could not cleanly isolate specific risk markers. Review the full text summary."
        except Exception as e:
            review_summary = f"Error processing LLM output parsing: {str(e)}"

        # 5. Return the updates to the state
        return {
            "review_summary": review_summary,
            "risk_areas": risk_areas
        }

  

    