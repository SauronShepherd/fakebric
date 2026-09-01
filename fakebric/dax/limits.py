from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DaxLimits:
    max_length: int = 4096
    max_tokens: int = 512
    max_depth: int = 32
    max_nodes: int = 256
