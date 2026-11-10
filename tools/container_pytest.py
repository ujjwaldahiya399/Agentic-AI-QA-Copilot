"""Run pytest on the input files inside the test container."""

import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
from tempfile import TemporaryDirectory, TemporaryFile


def write_log(source, destination):
    source.seek(0)
    limit = 64 * 1024
    data = source.read(limit + 1)
    destination.write(data[:limit])
    if len(data) > limit:
        destination.write(b"\n[Output truncated at 64 KiB]\n")


def main() -> int:
    payload = json.load(sys.stdin)
    with TemporaryDirectory() as directory, TemporaryFile() as stdout, TemporaryFile() as stderr:
        workspace = Path(directory)
        for filename, content in payload["changed_files"].items():
            path = PurePosixPath(filename)
            if path.is_absolute() or not path.parts or ".." in path.parts or path.parts[0] == "test_generated.py":
                raise ValueError(f"Invalid source path {filename!r}")
            target = workspace.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        (workspace / "test_generated.py").write_text(payload["test_code"], encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--disable-warnings", "."],
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
        )
        write_log(stdout, sys.stdout.buffer)
        write_log(stderr, sys.stderr.buffer)
        return result.returncode


if __name__ == "__main__":
    try:
        exit_code = main()
    except (ValueError, OSError) as error:
        print(f"Runner setup failed: {error}", file=sys.stderr)
        exit_code = 70
    raise SystemExit(exit_code)
