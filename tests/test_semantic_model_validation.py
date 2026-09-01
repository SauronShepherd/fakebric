from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from fakebric.semantic_model.api import app
from fakebric.semantic_model.schema import SemanticModel
from fakebric.semantic_model.validator import propagated_tables, validate_model


def table(name, key_type="integer", primary=False, **extra):
    return {
        "name": name,
        "source": {"type": "fakebrick", "path": name},
        "columns": [
            {"name": "id", "type": key_type, "isPrimaryKey": primary},
            {"name": "parent_id", "type": key_type},
        ],
        **extra,
    }


def rel(name, left, right, **extra):
    payload = {
        "name": name,
        "fromTable": left,
        "fromColumn": "parent_id",
        "toTable": right,
        "toColumn": "id",
        "cardinality": "one-to-many",
        "filterDirection": "single",
        "active": True,
    }
    payload.update(extra)
    return payload


def codes(report):
    return {issue.code for issue in report.issues}


def test_valid_one_to_many_propagation_and_inactive_relationship():
    model = SemanticModel(
        id="m1",
        name="Model",
        tables=[table("Sales"), table("Date", primary=True), table("Hidden", primary=True)],
        relationships=[
            rel("sales-date", "Sales", "Date"),
            rel("sales-hidden", "Sales", "Hidden", active=False),
        ],
    )
    report = validate_model(model)
    assert report.valid
    assert propagated_tables(model, "Date") == ("Date", "Sales")
    assert propagated_tables(model, "Hidden") == ("Hidden",)
    assert report.filter_graph == {"Date": ["Sales"], "Hidden": [], "Sales": []}


def test_incompatible_relationship_columns_are_rejected():
    model = SemanticModel(
        id="m1",
        name="Model",
        tables=[table("Sales", key_type="string"), table("Date", primary=True)],
        relationships=[rel("bad", "Sales", "Date")],
    )
    report = validate_model(model)
    assert not report.valid
    assert "RELATIONSHIP_TYPE_MISMATCH" in codes(report)


def test_cycles_and_ambiguous_paths_are_reported():
    model = SemanticModel(
        id="m1",
        name="Model",
        tables=[table("A", primary=True), table("B", primary=True), table("C", primary=True)],
        relationships=[
            rel("ab", "A", "B"),
            rel("bc", "B", "C"),
            rel("ca", "C", "A"),
        ],
    )
    report = validate_model(model)
    assert not report.valid
    assert {"RELATIONSHIP_CYCLE", "AMBIGUOUS_FILTER_PATH"} <= codes(report)


def test_duplicate_relationship_is_reported():
    relationship = rel("ab", "A", "B")
    duplicate = {**relationship, "name": "ab-copy"}
    model = SemanticModel(
        id="m1",
        name="Model",
        tables=[table("A"), table("B", primary=True)],
        relationships=[relationship, duplicate],
    )
    assert "DUPLICATE_RELATIONSHIP" in codes(validate_model(model))


def test_dependency_to_missing_table_is_reported_without_parsing_dax():
    sales = table("Sales")
    sales["measures"] = [
        {
            "name": "Total",
            "expression": "SUM(Sales[id])",
            "dependsOn": [{"kind": "table", "table": "Missing"}],
        }
    ]
    model = SemanticModel(id="m1", name="Model", tables=[sales])
    report = validate_model(model)
    assert not report.valid
    assert "DEPENDENCY_TARGET_NOT_FOUND" in codes(report)
    assert "measure:Sales.Total" in report.dependency_graph


def test_date_table_contract_and_type_validation():
    valid = SemanticModel(
        id="m1",
        name="Model",
        tables=[
            {
                "name": "Date",
                "source": {"type": "fakebrick", "path": "Date"},
                "columns": [{"name": "Date", "type": "date", "isPrimaryKey": True}],
                "isDateTable": True,
                "dateColumn": "Date",
            }
        ],
    )
    assert validate_model(valid).valid

    invalid = SemanticModel(
        id="m2",
        name="Model",
        tables=[
            {
                "name": "Date",
                "source": {"type": "fakebrick", "path": "Date"},
                "columns": [{"name": "Date", "type": "string"}],
                "isDateTable": True,
                "dateColumn": "Date",
            }
        ],
    )
    assert "DATE_TABLE_COLUMN_TYPE" in codes(validate_model(invalid))


def test_validation_endpoint_returns_structured_diagnostics():
    response = TestClient(app).post(
        "/api/v1/models/m1/validate",
        json={
            "id": "m1",
            "name": "Model",
            "tables": [table("Sales"), table("Date", primary=True)],
            "relationships": [rel("sales-date", "Sales", "Date")],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["modelId"] == "m1"
    assert payload["valid"] is True
    assert payload["filterGraph"]["Date"] == ["Sales"]


def test_endpoint_model_id_mismatch_is_structured_error():
    response = TestClient(app).post(
        "/api/v1/models/route-id/validate",
        json={"id": "body-id", "name": "Model"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert payload["issues"][0]["code"] == "MODEL_ID_MISMATCH"


def test_one_to_one_many_to_many_and_both_direction_are_supported():
    one_to_one = SemanticModel(
        id="o2o",
        name="OneToOne",
        tables=[table("A", primary=True), table("B", primary=True)],
        relationships=[
            rel("ab", "A", "B", cardinality="one-to-one", filterDirection="both")
        ],
    )
    assert validate_model(one_to_one).filter_graph == {"A": ["B"], "B": ["A"]}

    many_to_many = SemanticModel(
        id="m2m",
        name="ManyToMany",
        tables=[table("A"), table("B")],
        relationships=[
            rel("ab", "A", "B", cardinality="many-to-many", filterDirection="single")
        ],
    )
    assert validate_model(many_to_many).filter_graph == {"A": ["B"], "B": []}


def test_missing_relationship_column_is_reported():
    relationship = rel("broken", "A", "B")
    relationship["fromColumn"] = "missing"
    model = SemanticModel(
        id="m1",
        name="Model",
        tables=[table("A"), table("B", primary=True)],
        relationships=[relationship],
    )
    assert "RELATIONSHIP_COLUMN_NOT_FOUND" in codes(validate_model(model))


def test_day2_contracts_remain_backwards_compatible():
    model = SemanticModel(
        id="m1",
        name="Model",
        tables=[
            {
                "name": "Sales",
                "source": {"type": "csv", "path": "sales.csv", "credentialRef": "cred-1"},
                "columns": [
                    {"name": "Amount", "type": "decimal"},
                    {"name": "When", "type": "datetime", "nullable": True},
                ],
                "measures": [{"name": "Total", "expression": "SUM(Sales[Amount])"}],
            }
        ],
    )
    dumped = model.model_dump(mode="json", by_alias=True)
    restored = SemanticModel.model_validate(dumped)
    assert restored.model_dump(mode="json", by_alias=True) == dumped
    assert restored.table("sales").column("amount").type.value == "decimal"


def test_day1_versioned_contract_regression():
    model = SemanticModel(id="m1", name="Model", state="Draft")
    dumped = model.model_dump(mode="json", by_alias=True)
    assert SemanticModel.model_validate(dumped).canonical_json() == model.canonical_json()
    with pytest.raises(ValidationError, match="unsupported schema version"):
        SemanticModel(id="m2", name="Model", version="9.9")
