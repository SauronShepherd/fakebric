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
| DAX parser | partial | Día 4: lexer, precedencia, AST inmutable/serializable, diagnósticos, límites y catálogo | ampliar gramática según niveles posteriores |
| DAX evaluation N1 | implemented | Día 5: agregaciones/lógica, BLANK, Decimal, contexto de fila y medidas | endurecimiento y cobertura final Días 11–13 |
| DAX filter context N2 | partial | Día 6: CALCULATE/FILTER/ALL/ALLEXCEPT/REMOVEFILTERS/KEEPFILTERS/VALUES/DISTINCT/SELECTEDVALUE/HASONEVALUE/ISFILTERED, transición de contexto, filtros por capa y propagación activa 1:N/N:M | compatibilidad DAX completa no pretendida; endurecimiento y más combinaciones en Días 11–13 |
| Query engine Power BI | unsupported | todavía sin planner/ejecutor/caché | Día 7 |
| Reports Power BI | partial | contrato base `Report` | páginas/visuales/runtime Días 8–9 |
| CI/release | partial | tests focalizados y checks estáticos definidos | suite completa, Parquet runtime y gates Días 10–13 |
| E2E/performance/chaos/backup | partial | E2E previo del control plane | Power BI E2E/load/chaos/restore |

## Gate actual

Antes del commit funcional del Día 6, una reconstrucción focalizada del diseño ejecutó 51 tests correctamente e incluyó regresión de parser/seguridad/N1 más los escenarios N2. La versión compacta finalmente publicada se volvió a comprobar con un smoke integrado de CALCULATE, KEEPFILTERS, propagación y `compileall`. La suite histórica completa y el E2E Power BI siguen pendientes de CI/gates posteriores; no se consideran validados por esta ejecución local.
