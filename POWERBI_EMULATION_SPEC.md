# Fakebrick — Especificación funcional y técnica de emulación de Power BI

## 1. Objetivo

Construir una plataforma Linux nativa que reproduzca, con un subconjunto explícito,
las capacidades principales de Power BI Desktop y Power BI Service:

- modelado semántico;
- relaciones y medidas;
- consultas y expresiones DAX;
- creación y visualización de informes;
- filtros, segmentaciones y navegación;
- seguridad por filas;
- exportación e interoperabilidad con herramientas externas.

La emulación no debe prometer compatibilidad total. Toda función no soportada debe
declararse en el contrato, rechazarse de forma determinista y producir un diagnóstico
accionable.

## 2. Principios de diseño

1. Linux first: el producto debe funcionar sin Power BI Desktop ni Windows.
2. Contratos versionados: modelos, informes, consultas y resultados deben tener
   esquemas versionados y migraciones explícitas.
3. Resultados deterministas: misma fuente, modelo, consulta y contexto deben producir
   el mismo resultado.
4. Compatibilidad progresiva: implementar primero un núcleo pequeño y correcto antes
   de ampliar DAX o el catálogo de visualizaciones.
5. Separación de responsabilidades: ingestión, almacenamiento, modelo semántico,
   cálculo, renderizado y publicación deben ser módulos independientes.
6. Seguridad por defecto: aislamiento por workspace, validación de expresiones,
   control de acceso y no exposición de credenciales.
7. Observabilidad: cada consulta y render debe disponer de trace ID, duración,
   bytes procesados, caché utilizada y diagnóstico.

## 3. Alcance funcional

### 3.1 SemanticModel

El sistema debe permitir crear, editar, versionar, validar, publicar y clonar modelos
semánticos con:

- tablas físicas y virtuales;
- columnas, tipos, formato y descripción;
- columnas calculadas;
- medidas con expresión DAX;
- relaciones entre tablas;
- cardinalidad one-to-one, one-to-many y many-to-many;
- dirección de filtrado;
- claves y columnas ocultas;
- jerarquías;
- carpetas de visualización;
- perspectivas;
- roles y filtros RLS;
- parámetros de consulta;
- fuentes y credenciales referenciadas, nunca embebidas en texto plano.

Cada cambio debe generar una revisión inmutable con autor, fecha, diff, validación y
estado `Draft`, `Published` o `Archived`.

### 3.2 Importación de datos

El MVP debe soportar:

- Parquet;
- CSV;
- JSONL;
- tablas Fakebrick;
- consultas SQL sobre fuentes registradas.

La plataforma debe inferir tipos solo como sugerencia. El usuario o API debe poder
confirmar el esquema y conservarlo versionado.

### 3.3 Modelo de datos

Debe soportar:

- claves primarias y foráneas;
- relaciones activas e inactivas;
- filtros unidireccionales y bidireccionales;
- tablas de fechas;
- relaciones ambiguas detectadas durante validación;
- valores nulos, errores y conversiones de tipo explícitas.

El validador debe detectar ciclos de relaciones, columnas inexistentes, tipos
incompatibles, relaciones ambiguas y medidas con dependencias inválidas.

### 3.4 DAX compatible

La compatibilidad debe publicarse por niveles.

#### Nivel 1 — agregación y lógica

`SUM`, `COUNT`, `COUNTA`, `COUNTROWS`, `DISTINCTCOUNT`, `AVERAGE`, `MIN`, `MAX`,
`DIVIDE`, `IF`, `SWITCH`, `COALESCE`, operadores aritméticos y comparaciones.

#### Nivel 2 — contexto y filtros

`CALCULATE`, `FILTER`, `ALL`, `ALLEXCEPT`, `REMOVEFILTERS`, `KEEPFILTERS`,
`VALUES`, `DISTINCT`, `SELECTEDVALUE`, `HASONEVALUE` y `ISFILTERED`.

#### Nivel 3 — fechas y tiempo

`DATE`, `YEAR`, `MONTH`, `DAY`, `TODAY`, `EOMONTH`, `DATESYTD`, `TOTALYTD`,
`DATEADD`, `SAMEPERIODLASTYEAR` y calendario marcado.

#### Nivel 4 — funciones avanzadas

Funciones de texto, ranking, tablas virtuales, iteradores y funciones estadísticas.

El motor debe implementar explícitamente:

- contexto de filtro;
- contexto de fila;
- transición de contexto;
- propagación de relaciones;
- precedencia de filtros;
- semántica de valores en blanco;
- división segura por cero;
- dependencias y evaluación de medidas.

Las expresiones deben analizarse con un parser propio o una gramática controlada.
Nunca se debe ejecutar DAX como código Python, JavaScript o SQL sin compilación y
validación previa.

### 3.5 Informes

Un informe debe contener:

- páginas y orden de páginas;
- tamaño y orientación del lienzo;
- visualizaciones;
- posición, tamaño y z-index;
- consultas asociadas;
- filtros de visual, página e informe;
- segmentadores;
- interacciones entre visualizaciones;
- títulos, subtítulos y textos alternativos;
- tema y paleta;
- bookmarks y navegación;
- estado de selección y drill-down.

Visualizaciones mínimas:

- tarjeta/KPI;
- tabla;
- matriz;
- barras y columnas;
- líneas y áreas;
- circular/anillo;
- dispersión;
- slicer;
- texto e imagen.

Cada visual debe tener un esquema de propiedades validado, consulta declarativa,
estado de carga, estado vacío, estado de error y descripción accesible.

### 3.6 Interacción

Debe soportar:

- filtros por selección;
- cross-filtering;
- cross-highlighting, si el visual lo permite;
- drill-down;
- tooltips;
- ordenación;
- paginación de tablas;
- exportación de datos resumidos y subyacentes según permisos;
- actualización manual y programada.

### 3.7 Seguridad

- RBAC de workspace: Viewer, Contributor, Member y Admin.
- RLS aplicado antes de devolver cualquier fila o agregado.
- Aislamiento entre workspaces y tenants.
- Auditoría de lectura, edición, publicación y exportación.
- Límites de filas, bytes, tiempo y concurrencia.
- Redacción de secretos y datos sensibles en logs.
- Validación de URLs, fuentes y conectores.
- No permitir que DAX o SQL accedan al sistema de archivos o red arbitrariamente.

### 3.8 Publicación e interoperabilidad

Formato nativo versionado:

```text
report/
  manifest.json
  model.json
  report.json
  theme.json
  queries/
  assets/
```

El formato debe poder exportarse como un paquete reproducible y verificable mediante
hash. La compatibilidad TMDL/PBIR será progresiva y debe declarar qué propiedades se
han perdido o transformado.

No se debe intentar escribir `.pbix` directamente como formato primario: es un
artefacto propietario. La integración con Power BI Desktop se realizará mediante
exportación, SQL/ODBC, Parquet, APIs y, opcionalmente, un entorno Windows remoto.

## 4. Arquitectura técnica

```text
Web UI
  ↓
API Gateway / Auth / Trace ID
  ↓
Report Service ── Semantic Model Service ── DAX Compiler/Evaluator
  ↓                         ↓
Query Planner ─────── Cache / Metadata Catalog
  ↓
DuckDB + Apache Arrow + Parquet/Delta/Object Storage
  ↓
Execution Controller / Kubernetes Runtime
```

### 4.1 Servicios

- `api`: API pública, autenticación, workspaces y contratos.
- `model-service`: modelos, revisiones, relaciones, medidas y validación.
- `query-service`: planificación, ejecución, caché y paginación.
- `dax-service`: lexer, parser, AST, validación, compilación y evaluación.
- `report-service`: páginas, visuales, consultas y exportaciones.
- `metadata-catalog`: esquemas, estadísticas y lineage.
- `session-controller`: ejecución aislada en Kubernetes.
- `frontend`: editor web y runtime de informes.

El primer MVP puede mantener estos módulos dentro del API como paquetes Python, pero
las interfaces deben estar separadas para permitir extraer servicios posteriormente.

### 4.2 Almacenamiento

- SQLite solo para desarrollo y metadatos locales.
- PostgreSQL para metadatos multiusuario.
- Parquet/Arrow para datasets analíticos.
- Delta Lake para tablas transaccionales.
- S3/MinIO/Azure Blob para almacenamiento durable.
- Redis opcional para caché distribuida y locks.

El catálogo debe conservar esquema, estadísticas, particiones, propietario, versión,
permisos y ubicación física. Las escrituras deben ser atómicas y soportar rollback.

### 4.3 API mínima

```text
POST   /api/v1/models
GET    /api/v1/models/{id}
PUT    /api/v1/models/{id}/definition
POST   /api/v1/models/{id}/validate
POST   /api/v1/models/{id}/publish

POST   /api/v1/models/{id}/query
POST   /api/v1/models/{id}/dax/validate
POST   /api/v1/models/{id}/dax/explain

POST   /api/v1/reports
GET    /api/v1/reports/{id}
PUT    /api/v1/reports/{id}/definition
POST   /api/v1/reports/{id}/render
GET    /api/v1/reports/{id}/export
```

Todas las operaciones mutables deben usar ETag/If-Match, devolver trace ID y aplicar
validación de esquema. Las consultas deben devolver columnas, tipos, filas, métricas
de ejecución y advertencias de compatibilidad.

### 4.4 Contratos de ejemplo

```json
{
  "version": "1.0",
  "name": "Sales Model",
  "tables": [
    {
      "name": "Sales",
      "source": {"type": "parquet", "path": "lake/sales"},
      "columns": [
        {"name": "Amount", "type": "decimal"},
        {"name": "Date", "type": "date"}
      ],
      "measures": [
        {"name": "Total Sales", "expression": "SUM(Sales[Amount])"}
      ]
    }
  ],
  "relationships": []
}
```

## 5. Rendimiento y escalabilidad

Objetivos iniciales del MVP local:

- validación de modelo: <500 ms para modelos pequeños;
- consulta simple: <2 s sobre 10 millones de filas Parquet;
- render de informe: <3 s con 8 visuales;
- caché por modelo, revisión, consulta y contexto de filtros;
- cancelación de consultas excedidas;
- límites de memoria y tiempo por usuario.

Debe medirse y registrarse:

- tiempo de parseo DAX;
- tiempo de planificación;
- tiempo de lectura;
- tiempo de agregación;
- filas y bytes leídos;
- uso de memoria;
- aciertos de caché;
- visuales lentos.

## 6. Pruebas obligatorias

### Unitarias

- lexer/parser DAX;
- precedencia de operadores;
- contexto de filtro y fila;
- propagación de relaciones;
- tipos y valores nulos;
- validación de modelos;
- serialización y migraciones;
- cada visual y su esquema.

### Contrato/API

- autorización por rol;
- RLS e IDOR;
- ETag y conflictos;
- consultas inválidas;
- límites de paginación;
- exportaciones;
- errores y trace IDs.

### Golden tests

Cada expresión DAX compatible debe tener dataset, contexto, resultado esperado y
diagnóstico. Los resultados se compararán contra casos de referencia documentados.

### Integración

- Parquet, CSV, JSONL y Delta;
- DuckDB/Arrow;
- PostgreSQL y MinIO;
- caché y concurrencia;
- publicación y rollback.

### UI/E2E

- creación de modelo e informe;
- edición de medidas;
- filtros y cross-filtering;
- render de cada visual;
- responsive;
- teclado y lector de pantalla;
- Playwright y axe.

### Operación

- Minikube E2E;
- reinicio de sesiones;
- fallos de imagen y recursos;
- carga concurrente;
- chaos controlado;
- backup/restore;
- upgrade y rollback;
- escaneo de dependencias e imágenes.

## 7. Fases de implementación

### Fase 0 — contratos

Crear esquemas JSON versionados, migraciones, endpoints base y matriz de
compatibilidad.

### Fase 1 — modelo semántico

Tablas, columnas, relaciones, medidas simples, validación y persistencia.

### Fase 2 — motor de consultas

DuckDB/Arrow, filtros, agregaciones, caché, paginación y métricas.

### Fase 3 — DAX nivel 1 y 2

Parser controlado, contexto de evaluación, `CALCULATE` y funciones de filtros.

### Fase 4 — runtime de informes

Páginas, visuales básicos, filtros, temas y exportación.

### Fase 5 — seguridad y publicación

RLS, auditoría, revisiones, permisos, paquetes reproducibles y storage durable.

### Fase 6 — interoperabilidad

TMDL/PBIR experimental, SQL/ODBC, Parquet y conexión con Power BI Service/Desktop
mediante entorno Windows remoto.

### Fase 7 — endurecimiento

Rendimiento, accesibilidad, carga, chaos, backup/restore, SBOM, firmas, digests y
release gate.

## 8. Criterios de aceptación del MVP

El MVP podrá marcarse como `implemented` cuando:

- cree y publique un modelo con al menos tres tablas relacionadas;
- ejecute medidas de los niveles DAX 1 y 2;
- aplique filtros y RLS correctamente;
- renderice al menos ocho tipos de visual;
- guarde y recupere informes versionados;
- exporte datos y el paquete nativo;
- funcione en Linux y Minikube;
- tenga cobertura mínima del 85% en módulos de cálculo;
- disponga de golden tests para todas las funciones soportadas;
- pase Playwright/axe básico;
- no anuncie compatibilidad con funciones no implementadas.

## 9. Estado actual de Fakebrick

La implementación actual contiene los tipos reservados `SemanticModel` y `Report`,
pero todavía no contiene el modelo semántico, el motor DAX ni el diseñador de
informes. Este documento define el trabajo necesario para convertir ese alcance de
`unsupported` a `partial` y posteriormente a `implemented` con evidencia.
