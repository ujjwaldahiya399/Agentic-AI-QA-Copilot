"""Run a test container and capture its execution evidence."""

import json
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from uuid import uuid4

from agents.state import ExecutionResult


def run_tests_in_docker(changed_files: dict[str, str], test_code: str) -> ExecutionResult:
    docker = shutil.which("docker") or shutil.which(str(Path.home() / ".docker/bin/docker")) or "docker"
    container = f"qa-copilot-test-{uuid4().hex}"
    payload = json.dumps({"changed_files": changed_files, "test_code": test_code})
    command = [
        docker, "run", "--rm", "-i", "--pull=never", "--name", container,
        "--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--memory=256m", "--memory-swap=256m", "--cpus=1", "--pids-limit=64",
        "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,mode=1777,size=64m",
        "qa-copilot-runner",
    ]

    start = perf_counter()
    exit_code = None
    stdout = ""
    stderr = ""
    timed_out = False
    try:
        result = subprocess.run(
            command, input=payload, capture_output=True, encoding="utf-8", errors="replace", timeout=30,
        )
        exit_code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = (error.stdout or b"").decode("utf-8", errors="replace")
        stderr = (error.stderr or b"").decode("utf-8", errors="replace")
        stderr += "\nDocker test execution timed out after 30 seconds."
        try:
            subprocess.run([docker, "rm", "-f", container], capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired) as cleanup_error:
            stderr += f"\nDocker cleanup failed: {cleanup_error}"
    except OSError as error:
        stderr = f"Could not start Docker: {error}"

    return {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": round((perf_counter() - start) * 1000),
        "timed_out": timed_out,
    }
