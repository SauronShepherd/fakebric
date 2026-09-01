"""Fail-fast checks for a production Fakebric configuration."""
import json
import os
import sys
import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Fakebric deployment profile")
    parser.add_argument("--profile", choices=("local", "production"), default=None)
    args, _unknown = parser.parse_known_args()
    if (args.profile or os.getenv("FAKEBRIC_PROFILE", "production")) == "local":
        print("LOCAL PROFILE: external production integrations are intentionally not required")
        return 0
    errors = []
    if os.getenv("FAKEBRIC_AUTH_MODE") != "required":
        errors.append("FAKEBRIC_AUTH_MODE must be 'required'")
    jwks_url = os.getenv("FAKEBRIC_JWKS_URL")
    if not (jwks_url or os.getenv("FAKEBRIC_JWT_SECRET")):
        errors.append("configure FAKEBRIC_JWKS_URL or FAKEBRIC_JWT_SECRET")
    if jwks_url and (not os.getenv("FAKEBRIC_OIDC_ISSUER") or not os.getenv("FAKEBRIC_OIDC_AUDIENCE")):
        errors.append("FAKEBRIC_OIDC_ISSUER and FAKEBRIC_OIDC_AUDIENCE are required with JWKS")
    if os.getenv("FAKEBRIC_JWT_SECRET", "").lower().startswith(("dev-", "change", "test")):
        errors.append("development JWT secret detected")
    if not os.getenv("FAKEBRIC_OBJECT_STORE_URL"):
        errors.append("FAKEBRIC_OBJECT_STORE_URL is required for durable storage")
    manifest = json.loads((Path(__file__).resolve().parents[1] / "runtime-1.3.lock.json").read_text(encoding="utf-8"))
    digest = manifest.get("image", {}).get("digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        errors.append("runtime image must be pinned by sha256 digest")
    native = manifest.get("native", {})
    if native.get("enabledByDefault") and not os.getenv("FAKEBRIC_NATIVE_EVIDENCE_URL"):
        errors.append("FAKEBRIC_NATIVE_EVIDENCE_URL is required when native execution is enabled by default")
    if errors:
        print("PRODUCTION GATE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PRODUCTION GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
