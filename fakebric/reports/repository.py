from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from .schema import Report


class ReportNotFound(KeyError):
    pass


class ReportConflict(RuntimeError):
    pass


class ReportRepository:
    def __init__(self) -> None:
        self._items = {}

    def list(self):
        return [deepcopy(self._items[key]) for key in sorted(self._items)]

    def create(self, report: Report):
        key = report.id.casefold()
        if key in self._items:
            raise ReportConflict("REPORT_ALREADY_EXISTS")
        self._items[key] = deepcopy(report)
        return deepcopy(report)

    def get(self, report_id: str):
        try:
            return deepcopy(self._items[report_id.casefold()])
        except KeyError as exc:
            raise ReportNotFound(report_id) from exc

    def update(self, report_id: str, report: Report, if_match: str | None = None):
        current = self.get(report_id)
        if current.id.casefold() != report.id.casefold():
            raise ReportConflict("REPORT_ID_MISMATCH")
        if if_match is not None and if_match != current.etag():
            raise ReportConflict("ETAG_MISMATCH")
        data = report.model_dump()
        data["revision"] = current.revision + 1
        data["created_at"] = current.created_at
        data["updated_at"] = datetime.now(timezone.utc)
        updated = Report.model_validate(data)
        self._items[report_id.casefold()] = deepcopy(updated)
        return deepcopy(updated)

    def delete(self, report_id: str, if_match: str | None = None) -> None:
        current = self.get(report_id)
        if if_match is not None and if_match != current.etag():
            raise ReportConflict("ETAG_MISMATCH")
        del self._items[report_id.casefold()]
