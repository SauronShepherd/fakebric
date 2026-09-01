from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fakebric.semantic_model import (
    Column,
    ConversionError,
    DataSource,
    DataType,
    MissingColumnError,
    SemanticModel,
    SourceLoader,
    SourceSecurityError,
    Table,
    convert_value,
    dataset_statistics,
    infer_schema,
)


FIXTURES = Path(__file__).parent / "fixtures" / "powerbi" / "day2"


def source(kind: str, path: str) -> DataSource:
    return DataSource(type=kind, path=path)


def test_day2_entities_duplicate_names_and_credentials():
    table = Table(
        name="Sales",
        source=source("csv", "sales.csv"),
        columns=[Column(name="Amount", type="decimal")],
        measures=[{"name": "Total", "expression": "SUM(Sales[Amount])"}],
    )
    model = SemanticModel(id="m1", name="Model", tables=[table])
    assert model.table("sales").column("amount").type == DataType.DECIMAL

    with pytest.raises(ValidationError, match="duplicate column"):
        Table(
            name="Sales",
            source=source("csv", "sales.csv"),
            columns=[
                Column(name="Amount", type="decimal"),
                Column(name="amount", type="integer"),
            ],
        )
    with pytest.raises(ValidationError, match="duplicate table"):
        SemanticModel(id="m1", name="Model", tables=[table, table])
    with pytest.raises(ValidationError, match="credentialRef"):
        DataSource(type="csv", path="sales.csv", options={"api_token": "plaintext"})
    assert DataSource(
        type="csv",
        path="sales.csv",
        credentialRef="workspace-credential-1",
    ).credential_ref == "workspace-credential-1"


def test_csv_read_explicit_conversion_and_statistics():
    loader = SourceLoader(FIXTURES)
    table = Table(
        name="Sales",
        source=source("csv", "sales.csv"),
        columns=[
            Column(name="id", type="integer", nullable=False),
            Column(name="amount", type="decimal"),
            Column(name="active", type="boolean"),
            Column(name="sold_at", type="date", nullable=False),
            Column(name="note", type="string"),
        ],
    )
    loaded = loader.load_table(table)
    assert loaded.rows[0]["id"] == 1
    assert loaded.rows[0]["amount"] == Decimal("10.50")
    assert loaded.rows[1]["note"] is None
    stats = dataset_statistics(loaded)
    expected = json.loads((FIXTURES / "expected_stats.json").read_text(encoding="utf-8"))
    assert stats.model_dump(mode="json", by_alias=True) == expected


def test_jsonl_inference_is_a_reviewable_suggestion():
    loader = SourceLoader(FIXTURES)
    loaded = loader.load(source("jsonl", "sales.jsonl"))
    suggestions = infer_schema(loaded)
    expected = json.loads((FIXTURES / "expected_inference.json").read_text(encoding="utf-8"))
    assert [item.model_dump(mode="json", by_alias=True) for item in suggestions] == expected
    profile = loader.profile(source("jsonl", "sales.jsonl"))
    assert profile.statistics.row_count == 2
    assert profile.inference == suggestions


def test_fakebrick_local_table_and_empty_dataset(tmp_path):
    loader = SourceLoader(tmp_path, fakebrick_tables={"sales": [{"id": 1}, {"id": None}]})
    loaded = loader.load(source("fakebrick", "sales"))
    assert loaded.fields == ("id",)
    assert dataset_statistics(loaded).columns["id"].nulls == 1

    empty = tmp_path / "empty.csv"
    empty.write_text("id,amount\n", encoding="utf-8")
    empty_loaded = loader.load(source("csv", "empty.csv"))
    assert empty_loaded.rows == ()
    assert [item.name for item in infer_schema(empty_loaded)] == ["id", "amount"]
    assert all(item.confidence == 0.0 for item in infer_schema(empty_loaded))


def test_missing_source_column_is_rejected():
    loader = SourceLoader(FIXTURES)
    table = Table(
        name="Sales",
        source=source("csv", "sales.csv"),
        columns=[Column(name="does_not_exist", type="string")],
    )
    with pytest.raises(MissingColumnError, match="does_not_exist"):
        loader.load_table(table)


@pytest.mark.parametrize(
    ("raw", "target", "expected"),
    [
        ("hello", DataType.STRING, "hello"),
        ("42", DataType.INTEGER, 42),
        ("10.5", DataType.DECIMAL, Decimal("10.5")),
        ("true", DataType.BOOLEAN, True),
        ("2026-09-01", DataType.DATE, date(2026, 9, 1)),
        (
            "2026-09-01T10:30:00+00:00",
            DataType.DATETIME,
            datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc),
        ),
        ("aGk=", DataType.BINARY, b"hi"),
    ],
)
def test_explicit_conversion_for_each_supported_type(raw, target, expected):
    assert convert_value(raw, target) == expected


def test_invalid_conversion_is_rejected():
    with pytest.raises(ConversionError, match="integer"):
        convert_value("1.25", DataType.INTEGER)
    with pytest.raises(ConversionError, match="boolean"):
        convert_value("perhaps", DataType.BOOLEAN)


def test_path_traversal_and_outside_workspace_are_rejected(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "secret.csv"
    outside.write_text("value\nsecret\n", encoding="utf-8")
    loader = SourceLoader(workspace)

    with pytest.raises(SourceSecurityError):
        loader.load(source("csv", "../secret.csv"))
    with pytest.raises(SourceSecurityError):
        loader.load(source("csv", str(outside)))


def test_parquet_read_round_trip(tmp_path):
    pa = pytest.importorskip("pyarrow")
    parquet = pytest.importorskip("pyarrow.parquet")
    path = tmp_path / "sales.parquet"
    parquet.write_table(pa.Table.from_pylist([{"id": 1, "amount": 2.5}]), path)
    loaded = SourceLoader(tmp_path).load(source("parquet", "sales.parquet"))
    assert loaded.fields == ("id", "amount")
    assert loaded.rows[0]["id"] == 1
