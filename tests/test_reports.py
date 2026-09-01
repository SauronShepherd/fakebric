import pytest
from pydantic import ValidationError

from fakebric.reports import Report


def test_report_contract_and_aliases_round_trip():
    report = Report.model_validate({"id": "r1", "name": "Executive", "modelId": "m1"})
    dumped = report.model_dump(mode="json", by_alias=True)
    assert dumped["modelId"] == "m1"
    assert dumped["version"] == "1.0"
    assert Report.model_validate(dumped).model_dump(mode="json", by_alias=True) == dumped


def test_report_rejects_extra_fields_and_unknown_version():
    with pytest.raises(ValidationError):
        Report.model_validate({"id": "r1", "name": "R", "mystery": True})
    with pytest.raises(ValidationError, match="unsupported schema version"):
        Report.model_validate({"id": "r1", "name": "R", "version": "9.9"})
