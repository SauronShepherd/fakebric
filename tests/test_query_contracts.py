import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load(name):
    return json.loads((ROOT / "schemas" / name).read_text())


def test_semantic_model_schema_catches_up_with_day3_contracts():
    schema = load("semantic-model.schema.json")
    assert "Relationship" in schema["$defs"] and "DependencyRef" in schema["$defs"]
    assert "isPrimaryKey" in schema["$defs"]["Column"]["properties"]
    assert "dependsOn" in schema["$defs"]["Measure"]["properties"]
    assert "isDateTable" in schema["$defs"]["Table"]["properties"]
    assert "relationships" in schema["properties"]


def test_query_request_and_response_schemas_are_versioned():
    request = load("query-request.schema.json")
    response = load("query-response.schema.json")
    assert "QueryRequest" in request["$defs"] and "dataRevision" in request["properties"]
    assert response["properties"]["version"]["const"] == "1.0"
    assert {"modelId", "revision", "columns", "rows", "warnings", "metrics", "pagination", "plan", "planText"} <= set(response["properties"])
