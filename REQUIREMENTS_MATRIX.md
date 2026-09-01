# Fakebrick V2 — matriz de trazabilidad

Estados: `implemented` = evidencia automatizada o de runtime; `partial` = contrato/base presente pero falta parte observable; `unsupported` = no se debe anunciar como disponible.

| Área de las especificaciones | Estado | Evidencia actual | Falta |
|---|---|---|---|
| Workspace/Item extensible | partial | workspaces/items y tipos SemanticModel/Report existentes | miembros, folders, tenant scope y rutas canónicas |
| Contratos públicos y errores | implemented | contratos versionados y errores estándar; schemas de SemanticModel/query actualizados | integración OpenAPI completa del control plane |
| Runtime Spark/Jupyter | partial | runtime reproducible y E2E previo | digest publicado/release evidence |
| Lakehouse Files/Tables | partial | facade local, traversal y límites | provider durable, Delta real y SQL DML |
| Seguridad/authz | partial | JWT/JWKS, roles, IDOR, non-root y RBAC | secret manager, scans y RLS Power BI |
| SemanticModel contracts | partial | Días 1–3 y schema actualizado: tablas/columnas/medidas/fuentes, relaciones, PK/date table, dependencias | jerarquías/perspectivas y semántica completa |
| Model validation | partial | ciclos, ambigüedad, duplicados, tipos incompatibles y endpoint `/api/v1/models/{id}/validate` | integración persistida completa y validación DAX más profunda |
| Power BI data sources | partial | CSV, JSONL, Parquet y tablas Fakebrick; inferencia/perfiles | SQL registrado y storage durable |
| DAX parser | partial | Día 4: lexer, precedencia, AST inmutable/serializable, diagnósticos, límites y catálogo | ampliar gramática según niveles posteriores |
| DAX evaluation N1 | implemented | Día 5: agregaciones/lógica, BLANK, Decimal, contexto de fila y medidas | endurecimiento y cobertura final Días 11–13 |
| DAX filter context N2 | partial | Día 6: CALCULATE/FILTER/modificadores, transición de contexto, filtros por capa y propagación activa 1:N/N:M | compatibilidad DAX completa no pretendida; hardening Días 11–13 |
| Query engine Power BI | partial | Día 7: planner scan/filter/join/aggregate/project, endpoint query 1.0, paginación, límites, cancelación, cache revision/user/data, métricas y adapter DuckDB/Arrow | storage/catalog durable, pushdown a fuentes grandes y control-plane persistido Día 10; hardening Días 11–13 |
| Reports Power BI | partial | contrato base `Report` | páginas/visuales/runtime Días 8–9 |
| CI/release | partial | tests focalizados y checks estáticos definidos | suite completa y gates Días 10–13 |
| E2E/performance/chaos/backup | partial | E2E previo del control plane | Power BI E2E/load/chaos/restore |

## Gate actual

La reconstrucción acumulada del Día 7 ejecutó `41 passed, 1 skipped` sobre parser/golden/security, N1, N2 y query. El único skip fue el round-trip DuckDB/Arrow porque esas dependencias no estaban instaladas en el runtime local; ambas quedan declaradas en `requirements.txt` para CI. `compileall` y `git diff --check` pasaron antes de publicar. La suite histórica completa y E2E/Minikube siguen pendientes de gates posteriores.
