# Fakebrick V2 — matriz de trazabilidad

Estados: `implemented` = evidencia automatizada o de runtime; `partial` = contrato/base presente pero falta parte observable; `unsupported` = no se debe anunciar como disponible.

| Área de las especificaciones | Estado | Evidencia actual | Falta |
|---|---|---|---|
| Workspace/Item extensible | partial | `GET/POST /api/v1/workspaces`, Items y enum Notebook/Lakehouse/Environment/SemanticModel/Report; `tests/test_api.py` | miembros, folders, tenant scope, rename/duplicate y rutas canónicas |
| Contratos públicos y errores | implemented | camelCase, trace ID, envelope, validación Pydantic; tests API; contratos Power BI v1 y códigos estándar | OpenAPI versionado y matriz formal de compatibilidad por endpoint |
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
| SemanticModel contracts | partial | Días 1–2: contratos versionados; `Table`/`Column`/`Measure`/`DataSource`; tipos escalares; JSON Schema; duplicados y columnas inexistentes validados | relaciones, jerarquías, columnas calculadas, perspectivas y validación de grafo (día 3+) |
| Power BI data sources | partial | CSV, JSONL, Parquet vía `pyarrow` y tablas Fakebrick registradas; path traversal bloqueado; credenciales inline rechazadas; inferencia revisable y perfiles básicos | SQL registrado, Delta e integración durable según especificación/fases posteriores |
| DAX Power BI | unsupported | catálogo previsto en especificación, todavía sin parser/evaluador | días 4–6 |
| Query engine Power BI | unsupported | arquitectura prevista, todavía sin planner/ejecutor/caché | día 7 |
| Reports Power BI | partial | contrato base `Report` del día 1 | páginas/visuales/queries/filtros/runtime (días 8–9) |
| Observabilidad | partial | health/ready/metrics y trace IDs; perfiles de datasets Power BI incluyen filas/nulls/min/max/cardinalidad | métricas Power BI por consulta/render, logs estructurados, diagnostics bundle, retention y alertas |
| CI/release | partial | pytest, builds y dry-run definidos en CI; production gate; tests Power BI focalizados | ejecutar suite completa con dependencia Parquet en CI y gates de días 10–13 |
| E2E/performance/chaos/backup | partial | E2E Minikube previo del control plane | Power BI E2E, Playwright/axe, load, chaos, restore y upgrade evidence |

## Gate actual

La suite histórica del control plane tenía 26 tests verdes con cobertura total del 82,41%. La verificación focalizada acumulada de los contratos Power BI de días 1–2 ejecutó 24 tests correctamente; el test Parquet quedó omitido en el runtime de verificación anticipada porque `pyarrow` no estaba instalado allí. `pyarrow` se ha añadido a `requirements.txt`, por lo que CI debe ejecutar ese caso al instalar dependencias. No se considera validada todavía la suite completa histórica ni el E2E Power BI.
