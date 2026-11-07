import re
from typing import Union

import litellm

from agents.state import ExecutionResult, QAState
from tools.docker_runner import run_tests_in_docker


class TestGeneratorNode:
    """Generate pytest code from the review and changed files."""

    def __init__(self):
        self.model_id = "groq/llama-3.3-70b-versatile"

    def __call__(self, state: QAState) -> dict[str, str]:
        # 1. Generate test code using the review summary, risk areas, and changed files
        review_summary = state.get("review_summary", "")
        risk_areas = state.get("risk_areas", "")
        changed_files = state.get("changed_files", {})
        
        # For simplicity, we'll just concatenate these into a prompt for the LLM

        system_prompt = (
                    "You are an expert Senior QA Engineer and Test Case Developer. Your job is to create pytest test"
                    " cases based on a code review summary, identified risk areas, and the content of changed files"
                    " in a GitHub Pull Request. Focus on generating clear, concise, and effective test cases that target"
                    " the specific risks highlighted in the review."
                    
                )
        user_prompt = f"""
Review Summary: {review_summary}
Risk Areas: {risk_areas}
Based on the above information, generate pytest test cases that specifically target the identified risk areas.
Make sure to include necessary imports and use pytest conventions. Focus on quality and relevance of test cases.
Return ONLY the raw Python code. Do not include any explanation, commentary, or text before or after the code block.
"""
        if changed_files:
                    files_summary = "\n".join([f"Filename: {filename}\nContent:\n{content}\n---" for filename, content in changed_files.items()])
                    user_prompt += f"\n\nThe following files were changed in this PR:\n{files_summary}"
                        
        
        # Send them to LLaMA 3.3 70B via LiteLLM
        response = litellm.completion(
            model=self.model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            temperature=0.2
        )
        generated_test_code = response.choices[0].message.content or ""
       


        # strip the LLM's response down to just the raw Python code (it'll probably wrap it in markdown code fences)
        pattern = r'```(?:python)?\n(.*?)```'
        match = re.search(pattern, generated_test_code, re.DOTALL)
        if match:
            generated_test_code = match.group(1)
        else:
            generated_test_code = generated_test_code.strip()        

        return {"test_cases": generated_test_code}


class TestRunnerNode:
    """Run the validated test in Docker and save its execution evidence."""

    def __call__(self, state: QAState) -> dict[str, Union[ExecutionResult, str]]:
        result = run_tests_in_docker(state["changed_files"], state["test_cases"])
        return {
            "execution_result": result,
            "test_results": result["stdout"] + "\n" + result["stderr"],
        }
