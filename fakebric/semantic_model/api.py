from fastapi import APIRouter, FastAPI

from fakebric.semantic_model.schema import SemanticModel
from fakebric.semantic_model.validator import ValidationIssue, ValidationReport, validate_model

router = APIRouter(prefix="/api/v1/models", tags=["semantic-model"])
app = FastAPI(title="Fakebrick Semantic Model API", version="0.1.0")


@router.post("/{model_id}/validate", response_model=ValidationReport)
def validate_semantic_model(model_id: str, model: SemanticModel) -> ValidationReport:
    report = validate_model(model)
    if model.id != model_id:
        report.issues.insert(
            0,
            ValidationIssue(
                severity="error",
                code="MODEL_ID_MISMATCH",
                location="id",
                message=f"Payload model id {model.id!r} does not match route id {model_id!r}",
                suggestedFix="Use the same model id in the route and payload.",
            ),
        )
        report.valid = False
    return report


app.include_router(router)
