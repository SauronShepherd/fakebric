import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location("production_gate", Path(__file__).parents[1] / "tools" / "production_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_local_profile_is_explicitly_permissive(monkeypatch, capsys):
    monkeypatch.setenv("FAKEBRIC_PROFILE", "local")
    assert gate.main() == 0
    assert "LOCAL PROFILE" in capsys.readouterr().out


def test_jwks_production_requires_issuer_audience_and_native_evidence(monkeypatch, capsys):
    monkeypatch.setenv("FAKEBRIC_PROFILE", "production")
    monkeypatch.setenv("FAKEBRIC_AUTH_MODE", "required")
    monkeypatch.setenv("FAKEBRIC_JWKS_URL", "https://issuer.example/jwks")
    monkeypatch.setenv("FAKEBRIC_OBJECT_STORE_URL", "s3://bucket")
    assert gate.main() == 1
    output = capsys.readouterr().out
    assert "OIDC_ISSUER" in output
    assert "NATIVE_EVIDENCE_URL" not in output
