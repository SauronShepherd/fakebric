# Fakebrick V2 — matriz de trazabilidad

Estados: `implemented` = evidencia automatizada o de runtime; `partial` = contrato/base presente pero falta parte observable; `unsupported` = no se debe anunciar como disponible.

| Área de las especificaciones | Estado | Evidencia actual | Falta |
|---|---|---|---|
| Workspace/Item extensible | partial | workspaces/items y tipos SemanticModel/Report existentes | miembros, folders, tenant scope y rutas canónicas |
| Contratos públicos y errores | implemented | contratos versionados y errores estándar | OpenAPI versionado por endpoint |
| Runtime Spark/Jupyter | partial | runtime reproducible y E2E previo | digest publicado/release evidence |
| Lakehouse Files/Tables | partial | facade local, traversal y límites | provider durable, Delta real y SQL DML |
| Seguridad/authz | partial | JWT/JWKS, roles, IDOR, non-root y RBAC | secret manager, scans y RLS Power BI |
| SemanticModel contracts | partial | Días 1–3: tablas/columnas/medidas/fuentes, relaciones 1:1/1:N/N:M, PK/date table, validador estructurado | jerarquías/perspectivas y semántica completa |
| Model validation | partial | ciclos, ambigüedad, duplicados, tipos incompatibles y endpoint `/api/v1/models/{id}/validate` | integración persistida completa y validación DAX más profunda |
| Power BI data sources | partial | CSV, JSONL, Parquet y tablas Fakebrick; inferencia/perfiles | SQL registrado y storage durable |
| DAX parser | partial | Día 4: lexer, precedencia, AST inmutable/serializable, referencias calificadas, literales, diagnósticos, límites, catálogo y golden/security tests | evaluación y semántica de contexto Días 5–6 |
| DAX evaluation | unsupported | no se ejecuta AST todavía | Día 5 Nivel 1 y Día 6 contexto/filtros |
| Query engine Power BI | unsupported | todavía sin planner/ejecutor/caché | Día 7 |
| Reports Power BI | partial | contrato base `Report` | páginas/visuales/runtime Días 8–9 |
| CI/release | partial | tests focalizados y checks estáticos definidos | suite completa, Parquet runtime y gates Días 10–13 |
| E2E/performance/chaos/backup | partial | E2E previo del control plane | Power BI E2E/load/chaos/restore |

## Gate actual

La batería reconstruida del Día 4 ejecutó 32 tests correctamente incluyendo parser, golden/security tests y regresión semántica local. `compileall` y `git diff --check` fueron PASS en ese incremento. El commit remoto del parser conserva el alcance de Día 4 sin afirmar ejecución DAX. No se considera validada todavía la suite histórica completa ni el E2E Power BI.
