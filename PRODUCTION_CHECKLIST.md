# Production gate

Set `FAKEBRIC_PROFILE=local` for the self-contained Docker/Minikube profile.
It intentionally uses local SQLite/PVC storage and development authentication.
Use the default `production` profile only when promoting to shared infrastructure.

The Minikube profile is a local integration environment. Before promotion,
all of the following must be true:

- Set `FAKEBRIC_AUTH_MODE=required`, `FAKEBRIC_JWKS_URL`, issuer and audience;
  do not use the development HS256 secret.
- Replace `dev-only-change-me` and `dev-only-jwt-change-me` through an external
  Secret manager, and pin every image by digest.
- Store backups in versioned object storage, verify checksums, and run a
  restore drill from a clean namespace.
- Install a Prometheus-compatible scraper and alert on readiness failures,
  pod churn, execution failures and backup failures.
- Run notebook, security, compatibility, load and chaos suites at the target
  resource limits before release.
- Capture evidence for native Gluten/Velox execution before enabling the
  `native` capability in the runtime manifest.
