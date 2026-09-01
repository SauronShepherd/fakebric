from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def _capture(*command: str) -> str:
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())


def main() -> None:
    native_lock = Path("/opt/gluten/FAKEBRIC_RUNTIME_LOCK")
    payload = {
        "python": platform.python_version(),
        "java": _capture("java", "-version"),
        "spark": _capture("spark-submit", "--version"),
        "architecture": platform.machine(),
        "uid": os.getuid(),
        "gid": os.getgid(),
        "nativeExecutionEnabled": os.getenv("FAKEBRIC_NATIVE_EXECUTION_ENABLED", "false"),
        "nativeRuntimePresent": native_lock.is_file(),
        "nativeRuntimeLock": native_lock.read_text(encoding="utf-8").splitlines() if native_lock.is_file() else [],
        "executable": sys.executable,
    }
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
