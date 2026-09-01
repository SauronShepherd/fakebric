from __future__ import annotations

import sys
from pathlib import Path

import yaml


def validate_manifest(path: Path) -> None:
    documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    if not documents:
        raise ValueError(f"{path}: no YAML documents")
    for index, document in enumerate(documents, start=1):
        if document is None:
            continue
        if not isinstance(document, dict):
            raise ValueError(f"{path} document {index}: Kubernetes object must be a mapping")
        missing = [key for key in ("apiVersion", "kind", "metadata") if key not in document]
        if missing:
            raise ValueError(f"{path} document {index}: missing {', '.join(missing)}")
        metadata = document["metadata"]
        if not isinstance(metadata, dict):
            raise ValueError(f"{path} document {index}: metadata must be a mapping")
        if not metadata.get("name") and not metadata.get("generateName"):
            raise ValueError(f"{path} document {index}: metadata.name or generateName is required")


def main(args: list[str]) -> int:
    if not args:
        raise ValueError("at least one Kubernetes manifest is required")
    for raw_path in args:
        path = Path(raw_path)
        validate_manifest(path)
        print(f"validated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
