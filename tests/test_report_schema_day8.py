import json
from pathlib import Path


def test_report_schema_is_versioned_and_contains_visual_contracts():
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "report.schema.json").read_text())
    assert schema["properties"]["version"]["default"] == "1.0"
    assert "ReportPage" in schema["$defs"]
    for name in ["CardVisual", "TableVisual", "MatrixVisual", "BarVisual", "ColumnVisual", "LineVisual", "PieVisual", "DonutVisual", "ScatterVisual", "SlicerVisual"]:
        assert name in schema["$defs"]
