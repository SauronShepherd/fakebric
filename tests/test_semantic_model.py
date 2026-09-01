from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from fakebric.powerbi.common import LifecycleState, feature_enabled
from fakebric.powerbi.repository import ConflictError, InMemoryRevisionRepository
from fakebric.semantic_model import SemanticModel


def payload(**overrides):
    base = {
        "version": "1.0",
        "id": "sales",
        "name": "Sales",
        "description": "Day 1 model",
        "revision": 1,
        "state": "Draft",
        "createdAt": datetime(2026, 9, 1, tzinfo=timezone.utc).isoformat(),
        "updatedAt": datetime(2026, 9, 1, tzinfo=timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


def test_minimum_contract_round_trip_is_stable():
    model = SemanticModel.model_validate(payload())
    encoded = model.model_dump(mode="json", by_alias=True)
    assert SemanticModel.model_validate(encoded).model_dump(mode="json", by_alias=True) == encoded
    assert model.canonical_json() == SemanticModel.model_validate(encoded).canonical_json()


def test_unknown_version_is_rejected():
    with pytest.raises(ValidationError, match="unsupported schema version"):
        SemanticModel.model_validate(payload(version="2.0"))


@pytest.mark.parametrize("state", ["Draft", "Published", "Archived"])
def test_valid_states(state):
    assert SemanticModel.model_validate(payload(state=state)).state == LifecycleState(state)


def test_invalid_state_is_rejected():
    with pytest.raises(ValidationError):
        SemanticModel.model_validate(payload(state="Deleted"))


def test_etag_conflict_and_immutable_revision_history():
    repo = InMemoryRevisionRepository[SemanticModel]()
    created = repo.create(SemanticModel.model_validate(payload()))
    replacement = created.resource.model_copy(update={"description": "changed"})
    updated = repo.update("sales", replacement, if_match=created.etag)
    assert updated.resource.revision == 2
    assert len(repo.revisions("sales")) == 2
    with pytest.raises(ConflictError, match="ETag mismatch"):
        repo.update("sales", replacement, if_match=created.etag)


def test_feature_flag_defaults_off_and_accepts_true():
    assert feature_enabled({}) is False
    assert feature_enabled({"FAKEBRIC_POWERBI_EMULATION": "true"}) is True
