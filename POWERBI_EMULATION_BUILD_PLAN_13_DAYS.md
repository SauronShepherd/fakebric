# Fakebrick — Plan exhaustivo de construcción de emulación Power BI

## 0. Datos del plan

- **Periodo:** 1–13 de septiembre de 2026.
- **Duración:** 13 días consecutivos.
- **Días 1–10:** implementación y tests básicos de cada incremento.
- **Días 11–13:** exclusivamente pruebas, correcciones derivadas de pruebas,
  endurecimiento y validación final.
- **Objetivo:** entregar un MVP Linux nativo de SemanticModel + DAX controlado +
  informes web, sin afirmar compatibilidad total con Power BI.
- **Documento rector:** `POWERBI_EMULATION_SPEC.md`.
- **Regla de parada:** una tarea no se considera terminada por existir código; debe
  tener contrato, test, diagnóstico y evidencia de ejecución.

## 1. Resultado esperado al finalizar el día 13

Fakebrick deberá poder:

1. Crear y versionar un modelo semántico.
2. Registrar tablas Parquet, CSV, JSONL y tablas Fakebrick.
3. Declarar columnas, tipos, relaciones, medidas y jerarquías.
4. Validar modelos y rechazar relaciones o dependencias inválidas.
5. Ejecutar un subconjunto documentado de DAX.
6. Aplicar contexto de filtros y seguridad por filas.
7. Crear informes con páginas, visuales, filtros y temas.
8. Consultar el modelo mediante API.
9. Renderizar informes desde la UI Linux.
10. Exportar datos y paquetes nativos reproducibles.
11. Ejecutar el flujo en Docker y Minikube.
12. Tener cobertura, regresión, seguridad, rendimiento básico y accesibilidad
    verificadas.

Las funciones no implementadas deben devolver `UNSUPPORTED_FEATURE` y aparecer en
la matriz de compatibilidad.

## 2. Convenciones de ejecución

### Ramas y cambios

- Rama de trabajo: `codex/powerbi-emulation`.
- Un commit por incremento funcional verificable.
- No mezclar cambios de infraestructura no relacionados.
- Cada commit debe dejar la suite básica verde.

### Estructura objetivo

```text
fakebric/
  semantic_model/
    schema.py
    validator.py
    repository.py
    migrations.py
  dax/
    lexer.py
    parser.py
    ast.py
    evaluator.py
    functions.py
    context.py
  query/
    planner.py
    executor.py
    cache.py
    result.py
  reports/
    schema.py
    validator.py
    renderer.py
    exporters.py
  static/
    app.js
    styles.css
tests/
  test_semantic_model.py
  test_dax_parser.py
  test_dax_evaluator.py
  test_query_engine.py
  test_reports.py
  test_security_model.py
  test_powerbi_e2e.py
```

### Definition of Done diaria

- código formateado y compilable;
- tests básicos nuevos ejecutados;
- errores negativos cubiertos;
- contrato/documentación actualizado;
- sin secretos, datos de usuario ni artefactos generados en Git;
- `pytest`, `compileall` y `git diff --check` verdes.

---

## Día 1 — 1 de septiembre: contratos, alcance y scaffolding

### Objetivo

Establecer la base de código y los contratos versionados sin implementar aún el
motor de cálculo.

### Implementación

- Crear modelos Pydantic/JSON Schema para `SemanticModel` y `Report`.
- Definir `version`, `id`, `name`, `description`, `revision`, `state`, `createdAt`
  y `updatedAt`.
- Definir estados `Draft`, `Published` y `Archived`.
- Definir errores estándar: `VALIDATION_ERROR`, `CONFLICT`, `NOT_FOUND`,
  `FORBIDDEN`, `UNSUPPORTED_FEATURE` y `QUERY_ERROR`.
- Crear migración y repositorio para modelos e informes.
- Añadir ETag/If-Match a operaciones mutables.
- Crear feature flag `FAKEBRIC_POWERBI_EMULATION`.
- Actualizar `REQUIREMENTS_MATRIX.md` y README con el alcance real.

### Tests básicos

- Validación de payload mínimo y campos obligatorios.
- Rechazo de versiones desconocidas.
- Serialización estable y round-trip JSON.
- Conflicto ETag.
- Estados válidos e inválidos.

### Evidencia

- `pytest -q tests/test_semantic_model.py tests/test_reports.py`.
- JSON Schema guardado y revisado.

---

## Día 2 — 2 de septiembre: tablas, columnas y fuentes

### Objetivo

Representar tablas y esquemas de datos sin cálculo DAX.

### Implementación

- Crear entidades `Table`, `Column`, `Measure` y `DataSource`.
- Soportar tipos string, integer, decimal, boolean, date, datetime y binary.
- Implementar conectores de lectura para Parquet, CSV, JSONL y tablas locales.
- Implementar inferencia de tipos como sugerencia revisable.
- Añadir validación de nombres duplicados y columnas inexistentes.
- Registrar estadísticas básicas: filas, nulls, min, max y cardinalidad.

### Tests básicos

- Lectura de cada formato soportado.
- Inferencia de tipos.
- Conversión explícita y rechazo de conversiones inválidas.
- Dataset vacío y valores nulos.
- Path traversal y fuentes fuera del workspace.

### Evidencia

- Dataset fixture pequeño y reproducible.
- Resultados de esquema y estadísticas almacenados como fixtures.

---

## Día 3 — 3 de septiembre: relaciones y validador de modelos

### Objetivo

Implementar el grafo semántico y sus reglas de consistencia.

### Implementación

- Relaciones one-to-one, one-to-many y many-to-many.
- Dirección de filtro single y both.
- Relaciones activas e inactivas.
- Claves primaria/foránea y tabla de fechas.
- Detección de ciclos, ambigüedad y relaciones duplicadas.
- Grafo de dependencias de tablas, columnas y medidas.
- Endpoint `POST /api/v1/models/{id}/validate`.

### Tests básicos

- Propagación válida one-to-many.
- Rechazo de columnas incompatibles.
- Detección de ciclos y caminos ambiguos.
- Relación inactiva no aplicada por defecto.
- Dependencia a tabla inexistente.

### Evidencia

- Informe de validación con severidad, código, ubicación y solución sugerida.

---

## Día 4 — 4 de septiembre: lexer, parser y AST DAX

### Objetivo

Crear un lenguaje DAX controlado, seguro y diagnosticable.

### Implementación

- Lexer para identificadores, referencias `Table[Column]`, strings, números,
  fechas, operadores y paréntesis.
- Parser con precedencia de operadores.
- AST inmutable y serializable.
- Diagnósticos con línea, columna, token y mensaje.
- Límite de longitud, profundidad y complejidad.
- Rechazo de funciones no soportadas y sintaxis ambigua.

### Tests básicos

- Expresiones aritméticas y booleanas.
- Referencias de tablas y columnas.
- Paréntesis y precedencia.
- Strings, números, fechas y blancos.
- Tokens inválidos, expresiones incompletas y profundidad excesiva.

### Evidencia

- Catálogo de funciones soportadas por nivel.
- AST golden tests.

---

## Día 5 — 5 de septiembre: contexto y agregaciones DAX nivel 1

### Objetivo

Ejecutar medidas simples sobre datasets locales.

### Implementación

- Contexto de filtro inicial.
- Contexto de fila para iteración básica.
- Evaluador de columnas y literales.
- `SUM`, `COUNT`, `COUNTA`, `COUNTROWS`, `DISTINCTCOUNT`, `AVERAGE`, `MIN` y
  `MAX`.
- `DIVIDE`, `IF`, `SWITCH` y `COALESCE`.
- Semántica documentada para `BLANK`, null y división por cero.

### Tests básicos

- Cada función con datos normales, vacíos y nulos.
- Medidas sobre una tabla.
- Tipos incompatibles.
- División segura.
- Resultado decimal estable y orden determinista.

### Evidencia

- Primer conjunto de golden tests con resultado esperado.

---

## Día 6 — 6 de septiembre: filtros, relaciones y CALCULATE

### Objetivo

Implementar el comportamiento central del contexto de filtros.

### Implementación

- `CALCULATE`, `FILTER`, `ALL`, `ALLEXCEPT`, `REMOVEFILTERS`, `KEEPFILTERS`,
  `VALUES`, `DISTINCT`, `SELECTEDVALUE`, `HASONEVALUE` e `ISFILTERED`.
- Propagación de filtros por relaciones.
- Precedencia entre filtros de visual, página, informe y usuario.
- Explicación del plan de evaluación.
- Rechazo de relaciones ambiguas en ejecución.

### Tests básicos

- Filtros directos y propagados.
- `CALCULATE` con reemplazo y conservación de filtros.
- Selección única y múltiple.
- Relaciones many-to-many controladas.
- Contexto sin filas y valores en blanco.

### Evidencia

- Golden tests comparables y plan textual de cada consulta.

---

## Día 7 — 7 de septiembre: motor de consultas y caché

### Objetivo

Convertir expresiones y modelos en resultados tabulares consultables por API.

### Implementación

- Planner de consulta con nodos scan, filter, join, aggregate y project.
- Ejecutor DuckDB/Arrow cuando sea aplicable.
- Adaptador de resultados con columnas, tipos, filas y warnings.
- Paginación y límite de filas.
- Cancelación por timeout.
- Caché por modelo, revisión, expresión y contexto.
- Métricas de filas, bytes, duración y cache hit.

### Tests básicos

- Planes simples y con relaciones.
- Paginación estable.
- Timeout y cancelación.
- Invalidación al publicar nueva revisión.
- Aislamiento de claves de caché entre usuarios.

### Evidencia

- `POST /api/v1/models/{id}/query` con respuesta versionada.

---

## Día 8 — 8 de septiembre: informes y visualizaciones

### Objetivo

Crear el contrato de informes y el primer runtime de visualización web.

### Implementación

- Modelo de informe, página, visual, consulta y filtro.
- Validación de posición, tamaño, tipo y propiedades.
- Visuales: tarjeta, tabla, matriz, barras, columnas, líneas, circular/anillo,
  dispersión y slicer.
- Estados loading, empty y error.
- Tema, colores, tipografías y formato numérico.
- API CRUD de informes.

### Tests básicos

- Validación de cada visual.
- Visual inválido o con consulta inexistente.
- Informe vacío, múltiples páginas y orden.
- Tema incompleto y valores por defecto.
- Serialización y recuperación sin pérdida.

### Evidencia

- Informe fixture renderizable con ocho visuales.

---

## Día 9 — 9 de septiembre: UI, interacción y exportación

### Objetivo

Integrar modelo, consultas e informes en la interfaz Linux.

### Implementación

- Navegación workspace → modelo → informe.
- Editor básico de tablas, relaciones y medidas.
- Lienzo de informe y panel de propiedades.
- Filtros, slicers, selección y cross-filtering.
- Tooltips y estado de error visible.
- Exportación de datos a CSV/Parquet.
- Exportación del paquete nativo `model.json` + `report.json` + assets.
- Primeras etiquetas ARIA, navegación por teclado y contraste base.

### Tests básicos

- Flujo crear modelo/informe desde UI.
- Añadir visual y ejecutar consulta.
- Filtro que cambia otro visual.
- Exportación y round-trip del paquete.
- Error de backend visible y no silencioso.

### Evidencia

- Smoke browser manual o Playwright mínimo, si el runner está disponible.

---

## Día 10 — 10 de septiembre: seguridad, publicación e integración Minikube

### Objetivo

Cerrar el incremento de implementación y dejarlo desplegable localmente.

### Implementación

- RLS por rol y workspace.
- Auditoría de consultas, publicación y exportaciones.
- Permisos por modelo e informe.
- Publicación inmutable de revisiones.
- Migración de modelos y reports.
- Integración con API, controller y runtime existente.
- Dockerfiles y manifiestos actualizados.
- Health/readiness/metrics para los nuevos componentes.
- Actualizar matriz de compatibilidad con cada función realmente implementada.

### Tests básicos

- Viewer, Contributor y Admin.
- RLS no evade filtros ni exportaciones.
- IDOR entre workspaces.
- Publicación y rollback.
- Arranque Docker, manifests dry-run y smoke API.
- Flujo completo local modelo → consulta → informe.

### Evidencia

- Imagen versionada del API/controller/runtime.
- Minikube preparado para la campaña de pruebas de los días 11–13.

---

## Día 11 — 11 de septiembre: pruebas funcionales completas

> Desde este día no se añade funcionalidad nueva. Solo se ejecutan pruebas y se
> corrigen defectos demostrados por ellas.

### Campaña

- Ejecutar todos los unit tests y golden tests DAX.
- Probar todos los tipos, relaciones, filtros y funciones soportadas.
- Probar modelos vacíos, grandes, corruptos y con dependencias complejas.
- Probar informes con cada visual, página, filtro e interacción.
- Ejecutar contratos OpenAPI y errores HTTP.
- Ejecutar import/export y migraciones desde revisiones anteriores.

### Criterios de salida

- Cero fallos críticos o altos.
- Golden tests deterministas.
- 100% de las funciones anunciadas con casos positivos y negativos.
- Ningún unsupported ejecutado silenciosamente.
- Correcciones acompañadas de test de regresión.

### Artefactos

- Informe `functional-test-report`.
- Lista de defectos reproducibles y resueltos.
- Matriz de compatibilidad actualizada.

---

## Día 12 — 12 de septiembre: seguridad, rendimiento, accesibilidad y resiliencia

### Campaña de seguridad

- IDOR por workspace, modelo, informe y exportación.
- RLS con combinaciones de roles.
- Inyección DAX/SQL, path traversal y URLs maliciosas.
- Límites de payload, filas, memoria y tiempo.
- Redacción de secretos y datos sensibles.
- Escaneo de dependencias e imágenes.

### Campaña de rendimiento

- 10k, 100k, 1M y 10M filas.
- 1, 10 y 50 consultas concurrentes.
- Caché fría y caliente.
- Modelo con muchas relaciones y medidas.
- Render de informe con ocho y veinte visuales.
- Registro de p50, p95, p99, memoria y bytes procesados.

### Campaña de UI/accesibilidad

- Playwright en Chromium.
- axe automático.
- teclado completo.
- foco, contraste, textos alternativos y errores.
- viewport móvil, portátil y escritorio.

### Campaña de resiliencia

- reinicio de API/controller;
- Pod pendiente, imagen ausente y OOM simulado;
- cancelación de consulta;
- pérdida temporal de storage;
- doble publicación y conflictos ETag.

### Criterios de salida

- Sin vulnerabilidades críticas/altas conocidas.
- p95 documentado y dentro de los objetivos del documento funcional.
- Sin regresiones de permisos.
- Accesibilidad sin violaciones críticas.

---

## Día 13 — 13 de septiembre: release gate y aceptación final

### Campaña final

- Ejecutar suite completa desde un checkout limpio.
- Construir API, controller y runtime desde cero.
- Validar hashes, tags y manifiestos.
- Ejecutar Minikube E2E completo:
  workspace → modelo → fuentes → relaciones → medida → informe → consulta →
  render → exportación.
- Ejecutar backup/restore del catálogo y artefactos.
- Ejecutar upgrade y rollback de deployment.
- Repetir el E2E al menos tres veces para detectar flakiness.
- Confirmar que no quedan procesos, Pods o artefactos temporales pendientes.
- Revisar changelog, matriz de compatibilidad y guía de operación.

### Release gate obligatorio

```text
pytest completo                         PASS
coverage >= 85% en cálculo              PASS
compileall y node --check               PASS
git diff --check                        PASS
dependencias sin vulnerabilidades altas PASS
imágenes por digest                     PASS para producción
manifests validate=strict               PASS
Docker smoke                            PASS
Minikube E2E x3                         PASS
Playwright + axe                        PASS
RLS/IDOR/security suite                 PASS
performance report                      PASS
backup/restore                          PASS
upgrade/rollback                        PASS
matriz/documentación                    ACTUALIZADA
```

### Criterios de aceptación final

- No quedan defectos críticos o altos abiertos.
- Los defectos medios restantes tienen issue, workaround y prioridad.
- La matriz distingue `implemented`, `partial` y `unsupported`.
- El MVP funciona en Linux sin Power BI Desktop.
- La documentación no afirma compatibilidad PBIX completa.
- El paquete nativo es reproducible y verificable por hash.
- El resultado de cada campaña de pruebas está archivado.

## 3. Backlog que queda fuera de estos 13 días

Estas capacidades no deben ocultarse dentro del MVP:

- compatibilidad DAX total;
- creación binaria nativa de `.pbix`;
- todos los visuales y custom visuals de Power BI;
- DirectQuery y composite models completos;
- gateway empresarial;
- refresh cloud multi-región;
- capacidades equivalentes completas de Power BI Service;
- motor Gluten/Velox con evidencia de igualdad;
- colaboración multiusuario avanzada.

Se podrán abordar después de cerrar el release gate y con suites de compatibilidad
específicas.

## 4. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| DAX tiene semántica distinta según contexto | Alto | niveles explícitos y golden tests |
| Diferencias con PBIX/TMDL | Alto | formato nativo y pérdida declarada |
| Consultas grandes consumen memoria | Alto | DuckDB, límites, timeout y métricas |
| RLS se aplica tarde | Crítico | filtro en planner antes de exportar |
| Visuales inconsistentes | Medio | contrato por visual y snapshots |
| Flakiness de Minikube | Medio | un controller, cleanup y E2E repetido |
| Dependencias vulnerables | Alto | lockfiles, auditoría y escaneo CI |
| Alcance excesivo | Alto | bloquear funciones fuera del MVP |

## 5. Entregables finales

- `POWERBI_EMULATION_SPEC.md`.
- Este plan de construcción.
- Código fuente modular.
- JSON Schemas versionados.
- Fixtures y golden tests.
- Informe de cobertura.
- Informe de seguridad.
- Informe de rendimiento.
- Evidencia Playwright/axe.
- Evidencia Minikube.
- Paquete de ejemplo reproducible.
- Matriz de compatibilidad y changelog.
