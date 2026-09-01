from __future__ import annotations

import time


class QueryCancelled(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class QueryCancellationToken:
    def __init__(self, timeout_ms: int, clock=time.perf_counter) -> None:
        self.clock = clock
        self.deadline = clock() + timeout_ms / 1000
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def check(self) -> None:
        if self.cancelled:
            raise QueryCancelled("QUERY_CANCELLED", "Query was cancelled")
        if self.clock() > self.deadline:
            raise QueryCancelled("QUERY_TIMEOUT", "Query exceeded timeout")
