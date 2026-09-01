# Fakebrick V2 — matriz de trazabilidad

Estados: `implemented` = evidencia automatizada o de runtime; `partial` = contrato/base presente pero falta parte observable; `unsupported` = no se debe anunciar como disponible.

| Área de las especificaciones | Estado | Evidencia actual | Falta |
|---|---|---|---|
| Workspace/Item extensible | partial | `GET/POST /api/v1/workspaces`, Items y enum Notebook/Lakehouse/Environment/SemanticModel/Report; `tests/test_api.py` | miembros, folders, tenant scope, rename/duplicate y rutas canónicas |
| Contratos públicos y errores | implemented | camelCase, trace ID, envelope, validación Pydantic; tests API | OpenAPI versionado y matriz formal de compatibilidad |
| Notebook nbformat/ETag | partial | creación, validación, GET/PUT definition, conflicto y resultado persistido; tests API | import/export completo, attachments, autosave y operaciones de celdas |
| Sesión/lifecycle | partial | start/stop/restart con generación de Pod, timeout, queue, Pod/Service, controller diagnostics | reattach stateful, interrupt, startup timeline y estados completos |
| Runtime Spark/Jupyter | partial | Dockerfile optimizado sin duplicar Spark, lock manifest, `execute_notebook.py`, smoke notebook y E2E Minikube `fakebrick-ci` | digest publicado y evidencia de release |
| `%%configure` | partial | parser y metadata; tests runtime | allowlist, precedencia, diff estructural y restart controlado |
| `%%sql` | partial | traducción controlada a `spark.sql`; tests runtime | catálogo Delta, resultados tabulares y métricas/plan |
| `%pip` | partial | transformación controlada, metadata y rechazo de índices; tests runtime | overlay/venv aislado, lock/resolution y reinicio explícito |
| Lakehouse Files | partial | list/upload/download, límites, traversal, colisión y creación de carpetas; tests API | provider abstraction, paginación, carpetas gestionadas y mount POSIX |
| Lakehouse Tables/Delta | partial | catálogo local, schema/rows JSONL, append/overwrite/pagination/delete y formato Delta exigido | Delta real, SQL DML, history, reconcile y atomicidad |
| Environment | partial | Draft, ETag, publish con digest y revisión inmutable; tests API | librerías/conf/resources, clone/revisión, build/validation y lock result |
| Seguridad/authz | partial | JWT/JWKS, roles, WebSocket, IDOR de rutas, non-root, RBAC, NetworkPolicies y redacción de logs | secret manager, broker executor y scans |
| Kubernetes | partial | Deployments, PVC, quota, limits, RBAC, Pod/Service, cleanup, diagnósticos de Pod y E2E `state=COMPLETED` en Minikube `fakebrick-ci` | namespace por workspace, watches/rate limit, executor services y recovery E2E |
| Debugger DAP | unsupported | debugpy incluido y puerto declarado | handshake, breakpoints, pause/continue/scopes y UI integrada |
| Spark Inspector/native | unsupported | manifest marca native disabled/unknown sin evidencia | Gluten/Velox build, plan evidence, fallback y equality harness |
| UI shell | partial | UI estática, inventario, creación y ejecución con polling; JS syntax check | editor notebook, rutas, panes, explorer, diagnostics, responsive y a11y |
| SemanticModel/Report | unsupported | tipos reservados en enum | TMDL/FakeDAX/PBIR, editor y conformance |
| Observabilidad | partial | health/ready/metrics y trace IDs | logs estructurados, diagnostics bundle, retention y alertas |
| CI/release | partial | pytest, builds y dry-run definidos en CI; production gate | SBOM, firmas, vulnerability gate, image digests y quality report |
| E2E/performance/chaos/backup | partial | E2E Minikube completo verificado en perfil `fakebrick-ci` con ejecución `COMPLETED` y resultado persistido | Playwright/axe, load, chaos, restore y upgrade evidence |

## Gate actual

La suite local actual tiene 26 tests verdes con cobertura total del 82,41%. El E2E Minikube se ha ejecutado correctamente en el perfil `fakebrick-ci`; esto demuestra el camino crítico local, pero no sustituye las pruebas de carga, chaos, restore, upgrade ni la validación de producción.
