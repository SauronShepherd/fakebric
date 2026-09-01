from fastapi import APIRouter, FastAPI, Header, HTTPException, Response

from .repository import ReportConflict, ReportNotFound, ReportRepository
from .runtime import RenderedReport, ReportRuntime
from .schema import Report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
app = FastAPI(title="Fakebrick Reports API", version="0.1.0")
repository = ReportRepository()
runtime = ReportRuntime()


def missing(exc):
    return HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND", "message": str(exc)})


def conflict(exc):
    return HTTPException(status_code=409, detail={"code": str(exc), "message": str(exc)})


@router.get("", response_model=list[Report])
def list_reports():
    return repository.list()


@router.post("", response_model=Report, status_code=201)
def create_report(report: Report, response: Response):
    try:
        item = repository.create(report)
    except ReportConflict as exc:
        raise conflict(exc)
    response.headers["ETag"] = item.etag()
    return item


@router.get("/{report_id}", response_model=Report)
def get_report(report_id: str, response: Response):
    try:
        item = repository.get(report_id)
    except ReportNotFound as exc:
        raise missing(exc)
    response.headers["ETag"] = item.etag()
    return item


@router.put("/{report_id}", response_model=Report)
def update_report(report_id: str, report: Report, response: Response, if_match: str | None = Header(default=None, alias="If-Match")):
    try:
        item = repository.update(report_id, report, if_match)
    except ReportNotFound as exc:
        raise missing(exc)
    except ReportConflict as exc:
        raise conflict(exc)
    response.headers["ETag"] = item.etag()
    return item


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: str, if_match: str | None = Header(default=None, alias="If-Match")):
    try:
        repository.delete(report_id, if_match)
    except ReportNotFound as exc:
        raise missing(exc)
    except ReportConflict as exc:
        raise conflict(exc)


@router.post("/{report_id}/render", response_model=RenderedReport)
def render_report(report_id: str, results: dict[str, dict[str, object]]):
    try:
        report = repository.get(report_id)
    except ReportNotFound as exc:
        raise missing(exc)
    return runtime.render(report, results)


app.include_router(router)
