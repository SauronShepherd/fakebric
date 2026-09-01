from fastapi import APIRouter, FastAPI, HTTPException

from fakebric.dax import DaxError, DaxEvaluationError
from fakebric.query import ModelQueryEnvelope, QueryCancelled, QueryPlanningError, QueryResponse, QueryService
from fakebric.semantic_model.schema import SemanticModel
from fakebric.semantic_model.validator import ValidationIssue, ValidationReport, validate_model

router = APIRouter(prefix="/api/v1/models", tags=["semantic-model"])
app = FastAPI(title="Fakebrick Semantic Model API", version="0.1.0")
query_service = QueryService()


@router.post("/{model_id}/validate", response_model=ValidationReport)
def validate_semantic_model(model_id: str, model: SemanticModel) -> ValidationReport:
    report = validate_model(model)
    if model.id != model_id:
        report.issues.insert(0, ValidationIssue(severity="error", code="MODEL_ID_MISMATCH", location="id", message=f"Payload model id {model.id!r} does not match route id {model_id!r}", suggestedFix="Use the same model id in the route and payload."))
        report.valid = False
    return report


@router.post("/{model_id}/query", response_model=QueryResponse)
def query_semantic_model(model_id: str, envelope: ModelQueryEnvelope) -> QueryResponse:
    if envelope.model.id != model_id:
        raise HTTPException(status_code=400, detail={"code": "MODEL_ID_MISMATCH", "message": "Route and payload model ids must match"})
    try:
        return query_service.query(envelope.model, envelope.tables, envelope.query, data_revision=envelope.data_revision)
    except QueryCancelled as exc:
        raise HTTPException(status_code=408, detail={"code": exc.code, "message": exc.message}) from exc
    except QueryPlanningError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc
    except DaxError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.diagnostic.code, "message": exc.diagnostic.message}) from exc
    except DaxEvaluationError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc


app.include_router(router)
