from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class DaxDiagnostic:
    code: str
    message: str
    line: int
    column: int
    token: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class DaxError(ValueError):
    def __init__(self, diagnostic: DaxDiagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(
            f"{diagnostic.code} at {diagnostic.line}:{diagnostic.column}: "
            f"{diagnostic.message} (token={diagnostic.token!r})"
        )


class DaxEvaluationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
