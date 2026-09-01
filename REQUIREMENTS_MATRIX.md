# Fakebrick V2 — matriz de trazabilidad

Estados: `implemented` = evidencia automatizada o de runtime; `partial` = contrato/base presente pero falta parte observable; `unsupported` = no se debe anunciar como disponible.

| Área de las especificaciones | Estado | Evidencia actual | Falta |
|---|---|---|---|
| Workspace/Item extensible | partial | `GET/POST /api/v1/workspaces`, Items y enum Notebook/Lakehouse/Environment/SemanticModel/Report; `tests/test_api.py` | miembros, folders, tenant scope, rename/duplicate y rutas canónicas |
| Contratos públicos y errores | implemented | camelCase, trace ID, envelope, validación Pydantic; contratos Power BI v1 y códigos estándar | OpenAPI versionado y matriz formal por endpoint |
| Notebook nbformat/ETag | partial | creación, validación, GET/PUT definition, conflicto y resultado persistido | import/export completo, attachments, autosave |
| Runtime Spark/Jupyter | partial | runtime reproducible, smoke notebook y E2E previo | digest publicado y evidencia de release |
| Lakehouse Files/Tables | partial | Files y Tables locales, traversal y límites | provider durable, Delta real y SQL DML |
| Seguridad/authz | partial | JWT/JWKS, roles, IDOR de rutas, non-root, RBAC y NetworkPolicies | secret manager, scans y RLS Power BI |
| Kubernetes | partial | Deployments, RBAC, cleanup y E2E previo | namespace por workspace y recovery E2E |
| UI shell | partial | UI estática existente | editor Power BI, diagnostics, responsive y a11y |
| SemanticModel contracts | partial | Días 1–3: contratos versionados; tablas/columnas/medidas/fuentes; relaciones 1:1/1:N/N:M; single/both; activas/inactivas; PK/date table; dependencias explícitas; validador estructurado | jerarquías/perspectivas y dependencias extraídas de DAX |
| Model validation | partial | ciclos, caminos ambiguos, duplicados, tipos incompatibles, tablas/columnas/dependencias inexistentes; endpoint `/api/v1/models/{id}/validate`; 12 tests focalizados | integración con control plane persistido y validación derivada del parser DAX |
| Power BI data sources | partial | CSV, JSONL, Parquet vía `pyarrow` y tablas Fakebrick; traversal bloqueado; inferencia y perfiles | SQL registrado, Delta e integración durable |
| DAX Power BI | unsupported | todavía sin lexer/parser/evaluador | días 4–6 |
| Query engine Power BI | unsupported | todavía sin planner/ejecutor/caché | día 7 |
| Reports Power BI | partial | contrato base `Report` | páginas/visuales/queries/filtros/runtime días 8–9 |
| Observabilidad | partial | health/ready/metrics y trace IDs; perfiles y diagnósticos semánticos | métricas por consulta/render y diagnostics bundle |
| CI/release | partial | pytest, builds y dry-run definidos en CI; tests Power BI focalizados | suite completa con Parquet y gates días 10–13 |
| E2E/performance/chaos/backup | partial | E2E Minikube previo del control plane | Power BI E2E, load, chaos, restore y upgrade |

## Gate actual

La verificación focalizada del incremento del Día 3 ejecutó 12 tests correctamente, incluyendo regresión de contratos de Días 1–2. `compileall` y `git diff --check` sobre el incremento reconstruido fueron PASS. El test Parquet acumulado sigue sin ejecutarse en este runtime porque `pyarrow` no está instalado aquí, aunque permanece declarado en `requirements.txt`. No se considera validada todavía la suite histórica completa ni el E2E Power BI.
