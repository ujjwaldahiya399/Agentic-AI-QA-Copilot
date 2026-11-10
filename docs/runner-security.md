# Test runner security audit

Generated pytest code runs in the `qa-copilot-runner` Docker image as user `65534:65534`, without a host directory or Docker socket mount.

The runner disables external networking, mounts its root filesystem read-only, drops Linux capabilities, and prevents privilege escalation. It provides a 64 MiB temporary filesystem and limits the container to 256 MiB RAM, 256 MiB total RAM and swap, one CPU, and 64 processes. The host enforces a 30-second timeout and attempts to remove a timed-out container.

The in-container script writes normal pytest stdout and stderr to temporary files and sends at most 64 KiB from each stream to the host.

Verification: the runner image reported user `65534:65534`; the real-Docker repair suite passed 4/4 after adding the swap limit. These checks establish that the tested workflow still runs. They do not constitute a complete container escape or denial-of-service assessment.

Remaining limits: input payload size is not explicitly capped; unusual runner errors are outside the normal pytest log cap; Docker and its daemon remain trusted infrastructure.