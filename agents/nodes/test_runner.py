# So here's the full flow for test_runner_node:

# Generate — send review_summary, risk_areas, and the actual file content (from changed_files) to the LLM, asking it to write pytest test code
# Extract — strip the LLM's response down to just the raw Python code (it'll probably wrap it in markdown code fences)
# Write to disk — write the actual source file (e.g., login.py) and the generated test file into a temporary directory so pytest can import and run them together
# Execute — use subprocess to run pytest against that temp directory, with a timeout, and capture the output
# Return — test_cases (the generated code) and test_results (the pytest output)


from ast import pattern
import re
import subprocess
import litellm
import tempfile
from pathlib import Path
class TestRunnerNode:
    
    def __init__(self):
        self.model_id = "groq/llama-3.3-70b-versatile"

    def __call__(self, state):
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
        generated_test_code = response.choices[0].message.content
       


        # strip the LLM's response down to just the raw Python code (it'll probably wrap it in markdown code fences)
        pattern = r'```(?:python)?\n(.*?)```'
        match = re.search(pattern, generated_test_code, re.DOTALL)
        if match:
            generated_test_code = match.group(1)
        else:
            generated_test_code = generated_test_code.strip()        

        # write the actual source file (e.g., login.py) and the generated test file into a temporary directory so
        #  pytest can import and run them together

        # use subprocess to run pytest against that temp directory, with a timeout, and capture the output
        # With pathlib, you'd do something like creating the parent directory before writing the file — using Path(...).parent.mkdir(parents=True, exist_ok=True).

        
        temporary_directory = tempfile.mkdtemp(prefix="qa_agent_tests_")
        # Now let's build the rest. You need three more things:
        # Write each file from changed_files into that temp directory — loop through the dict, write each filename with its content
        # Write the generated test code into its own file in the same directory (e.g., test_generated.py)
        # Run pytest via subprocess against that directory, with a timeout, and capture stdout/stderr

        for filename, content in changed_files.items():
            target_path = Path(temporary_directory) / filename
            target_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directories exist
            with open(target_path, "w") as f:
                f.write(content)

        # Write the generated test code into its own file in the same directory (e.g., test_generated.py)
        with open(f"{temporary_directory}/test_generated.py", "w") as f:

            f.write(generated_test_code)

        # Run pytest via subprocess against that directory, with a timeout, and capture stdout/stderr
        try:
            result = subprocess.run(
                ["pytest", temporary_directory, "--disable-warnings"],
                capture_output=True,
                text=True,
                timeout=30  # seconds
            )
            test_results = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            test_results = "Test execution timed out after 30 seconds."

        # Return test_cases (the generated code) and test_results (the pytest output)
        return {
            "test_cases": generated_test_code,
            "test_results": test_results
        }
