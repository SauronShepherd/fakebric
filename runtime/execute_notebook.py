"""Execute one notebook in the isolated runtime container.

The session controller invokes this process with a notebook path. A fresh
SparkSession is created for every invocation, while the container itself can
be kept alive by Jupyter for stateful interactive sessions.
"""
import argparse
import json
import os
from pathlib import Path

from nbclient import NotebookClient
from nbformat import read, write
from nbformat.validator import normalize
from notebook_contract import apply_fakebric_magics


def configure_debugger() -> None:
    if os.getenv("FAKEBRIC_DEBUG", "0").lower() not in {"1", "true", "yes"}:
        return
    import debugpy
    debugpy.listen(("0.0.0.0", int(os.getenv("FAKEBRIC_DEBUG_PORT", "5678"))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    configure_debugger()
    if not args.notebook.is_file():
        raise SystemExit(f"Notebook not found: {args.notebook}")
    with args.notebook.open(encoding="utf-8") as stream:
        notebook = read(stream, as_version=4)
    # Normalize legacy notebooks (including missing cell IDs) before execution
    # so the runtime remains compatible with stricter future nbformat releases.
    normalize(notebook)
    apply_fakebric_magics(notebook)
    metadata = notebook.setdefault("metadata", {}).setdefault("fakebric", {})
    metadata.update({"runtime": "1.3", "spark": "3.5.5", "delta": "3.2.1"})
    client = NotebookClient(notebook, timeout=args.timeout, kernel_name="python3")
    client.execute(cwd=str(args.notebook.parent))
    destination = args.output or args.notebook
    with destination.open("w", encoding="utf-8") as stream:
        write(notebook, stream)
    print(json.dumps({"status": "completed", "notebook": str(destination)}))


if __name__ == "__main__":
    main()
