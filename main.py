# That's clean and correct. The graph is wired up properly — builder pattern, nodes registered, linear edges from START to END, compiled into a runnable.
# Now let's write main.py — the entry point that ties everything together. Think about what it needs to do:

# Get a PR URL (from where?)
# Fetch PR data using github_utils.py
# Feed that data as the initial state into qa_graph
# Print or display the results

# Give it a shot.
import sys
from dotenv import load_dotenv

load_dotenv(override=True)
from agents.graph import qa_graph
from config.settings import GITHUB_TOKEN
from tools.github_utils import get_PR_data_from_url, post_report_to_pr


def main():
    # 1. Get the PR URL from command-line arguments
    # sys.argv[0] is the script name itself, sys.argv[1] is the first argument passed
    if len(sys.argv) != 2:
        print("Usage: python main.py <GitHub_PR_URL>")
        return

    pr_url = sys.argv[1]

    # 2. Fetch PR data using github_utils.py
    try:
            initial_state = get_PR_data_from_url(pr_url, GITHUB_TOKEN)        
    except Exception as e:
        print(f"Error fetching PR data: {e}")
        return

    # 3. Feed that data as the initial state into qa_graph
    final_state = qa_graph.invoke(initial_state)
    try:
        post_report_to_pr(pr_url, final_state.get("final_report", "No report generated."), GITHUB_TOKEN)
    except Exception as e:
        print(f"Error posting report to PR: {e}")
        return
    # 4. Print or display the results
    print("\n--- Final QA Report ---")
    print(f"PR Title: {final_state.get('pr_title', 'N/A')}")
    print(f"PR Description: {final_state.get('pr_desc', 'N/A')}")
    print(f"Review Summary: {final_state.get('review_summary', 'N/A')}")
    print(f"Risk Areas: {final_state.get('risk_areas', 'N/A')}")
    print(f"Test Cases: {final_state.get('test_cases', 'N/A')}")
    print(f"Test Results: {final_state.get('test_results', 'N/A')}")
    print(f"Final Report: {final_state.get('final_report', 'N/A')}")

if __name__ == "__main__":
    main()