# 🤖 Agentic AI QA Copilot

An end-to-end, multi-agent AI system that autonomously reviews GitHub Pull Requests, generates and executes real tests against the actual code, and posts a complete QA report back to the PR — **without any human involvement** beyond providing the PR URL.

Built with **LangGraph** for deterministic agent orchestration, **Groq (LLaMA 3.3 70B)** for fast LLM inference, and **PyGithub** for GitHub integration.

![Demo](./demo.gif)

---

## What It Does

Give it a GitHub PR URL, and it will:

1. **Fetch** the PR's title, description, diff, and full content of every changed file
2. **Review** the code with an AI agent that identifies concrete risk areas — edge cases, missing validation, security gaps
3. **Generate and execute** real `pytest` test cases targeting those exact risk areas, in an isolated sandbox
4. **Compile** a clean, structured QA report with a clear verdict
5. **Post** that report as a comment directly on the original PR

All of this happens automatically, in a single command.

---

## Why This Exists

Most "AI code review" tools generate *opinions*. This pipeline generates *evidence*. The test_runner agent doesn't just ask an LLM "is this code correct?" — it writes real test code, runs it in an isolated environment with `pytest`, and reports the actual pass/fail results. If a test fails, it's because the code genuinely has a bug, not because a language model said so.

**Proof:** in real test runs against this repo's demo PR, the pipeline independently surfaced multiple confirmed defects, including:
- `login()` raising an unhandled `TypeError` when passed `None` instead of failing gracefully
- An email-validation regex that simultaneously rejected valid addresses (with `+`, quoted parts) and accepted clearly invalid ones
- No input sanitization — a SQL-injection-shaped string was silently accepted

---

## Architecture

```
PR URL
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  GitHub API (PyGithub + requests)                       │
│  → PR metadata, diff, full content of changed files      │
└───────────────────────────┬───────────────────────────────┘
                            ▼
                  ┌──────────────────┐
   START ───────► │  code_review     │  Identifies risk areas
                  │  agent (LLM)     │  from diff + file content
                  └────────┬─────────┘
                           ▼
                  ┌──────────────────┐
                  │  test_runner     │  Generates pytest tests,
                  │  agent (LLM +    │  runs them in an isolated
                  │  pytest exec)    │  temp directory
                  └────────┬─────────┘
                           ▼
                  ┌──────────────────┐
                  │  report          │  Deterministic Markdown
                  │  agent (no LLM)  │  report from real results
                  └────────┬─────────┘
                           ▼
                         END ──────► Posted as a PR comment
```

The pipeline is built as a **LangGraph `StateGraph`** — the *order* of execution (review → test → report) is hardcoded in Python and cannot be skipped or reordered by the LLM. Each agent reads from and writes to a shared, typed state object, only ever modifying its own fields.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM inference | Groq (LLaMA 3.3 70B) via [LiteLLM](https://github.com/BerriAI/litellm) |
| GitHub integration | [PyGithub](https://github.com/PyGithub/PyGithub) + `requests` |
| Test execution | `pytest`, sandboxed via `tempfile` + `subprocess` |
| Containerization | Docker |
| CI | GitHub Actions |

---

## Project Structure

```
.
├── agents/
│   ├── state.py              # Shared QAState schema
│   ├── graph.py               # LangGraph StateGraph wiring
│   └── nodes/
│       ├── code_review.py     # Agent 1: risk analysis
│       ├── test_runner.py     # Agent 2: generate + execute tests
│       └── report.py          # Agent 3: deterministic report builder
├── tools/
│   └── github_utils.py        # PR fetching, file content, comment posting
├── config/
│   └── settings.py             # API keys & model config
├── main.py                     # CLI entry point
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── .github/workflows/ci.yml    # CI: import + Docker build sanity checks
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- A [Groq API key](https://console.groq.com)
- A GitHub [personal access token](https://github.com/settings/tokens) with `repo` scope

### Local Setup

```bash
git clone <this-repo>
cd Agentic-AI-QA-Copilot

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_key_here
GITHUB_TOKEN=your_github_token_here
```

### Run It

```bash
python main.py https://github.com/<owner>/<repo>/pull/<number>
```

### Run It With Docker

```bash
docker build -t qa-pipeline .
docker run --env-file .env qa-pipeline https://github.com/<owner>/<repo>/pull/<number>

docker pull dahiyaujjwal/agentic-ai-qa-copilot:latest
docker run --env-file .env dahiyaujjwal/agentic-ai-qa-copilot:latest https://github.com/<owner>/<repo>/pull/<number>
```

---

## Example Output

```markdown
# QA Pipeline Report — feat: add email validation to login

## Verdict
### ❌ Failed

**Tests Passed:** 4  |  **Tests Failed:** 3

---

## Risk Areas Identified by Code Review
1. Email Validation Pattern: regex may reject valid formats...
2. Input Sanitization: no protection against SQL-injection-shaped input...
...

## Test Summary
This pipeline auto-generated 7 test case(s) targeting the risk areas above.
- ✅ Passed: 4
- ❌ Failed: 3

## Full Test Log
[real pytest output, including tracebacks for each failure]
```

This report is posted directly as a comment on the originating PR.

---

## Design Decisions & Known Limitations

This project favors pragmatic, well-documented trade-offs over premature complexity:

- **Test sandboxing:** generated test code runs via `subprocess` inside a `tempfile.mkdtemp()`-isolated directory with a timeout, rather than a full Docker-per-test-run sandbox. This was a deliberate v1 trade-off given timeline constraints; full per-run containerized isolation is a planned hardening step.
- **`report_agent` is deterministic, not an LLM call.** Formatting structured data into Markdown doesn't need generative reasoning — using plain Python here is faster, free, and fully predictable.
- **CI does not run the live pipeline.** GitHub Actions verifies the code imports correctly and the Docker image builds — it does not call live LLM/GitHub APIs on every push, to avoid spamming real PRs and burning API credits on commits unrelated to pipeline logic.
- **Edge cases not yet handled:** deleted files in a PR, and binary (non-text) file content, during the changed-files fetch step.

## Roadmap

- [ ] Conditional graph edges (e.g., skip test generation if review finds zero risk areas)
- [ ] Full Docker-per-test-run sandboxing for generated code execution
- [ ] Security scanning (Bandit / OWASP ZAP) integrated into the review agent
- [ ] Support for multi-file, cross-file risk analysis at scale

---

## License

MIT