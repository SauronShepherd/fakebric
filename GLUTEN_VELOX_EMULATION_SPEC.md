# Fakebrick — Especificación funcional y técnica de Gluten + Velox

## 1. Objetivo

Integrar en el runtime de Fakebrick una ruta de ejecución nativa basada en Gluten y
Velox para acelerar consultas Spark SQL, manteniendo compatibilidad y fallback
automático al motor Spark JVM cuando una operación no sea soportada.

La funcionalidad debe ser opt-in hasta completar la validación de igualdad funcional,
estabilidad, rendimiento y seguridad. En ningún caso se deben devolver resultados
parciales o silenciosamente distintos por utilizar la ruta nativa.

## 2. Alcance

### Incluido

- imagen runtime reproducible con Spark, Gluten y Velox;
- selección configurable de backend `jvm`, `native` o `auto`;
- detección de operadores soportados;
- fallback por consulta o fragmento de plan;
- métricas de selección, fallback y rendimiento;
- comparación automática de resultados JVM/native;
- configuración por sesión y por modelo;
- pruebas funcionales, de igualdad, rendimiento y resiliencia;
- desactivación global inmediata mediante configuración.

### No incluido en la primera versión

- soporte de todas las funciones Spark SQL;
- igualdad bit a bit de agregados floating point sin tolerancia;
- soporte universal de UDF Python/Scala;
- ejecución native obligatoria;
- compatibilidad con cualquier versión arbitraria de Spark, Gluten o Velox;
- uso de binarios no reproducibles descargados manualmente.

## 3. Contrato funcional

### 3.1 Modos de ejecución

| Modo | Comportamiento |
|---|---|
| `jvm` | Fuerza Spark JVM; nunca usa Gluten/Velox. |
| `native` | Intenta ruta nativa; falla con diagnóstico si no puede hacer fallback. |
| `auto` | Usa native cuando el plan es compatible y fallback JVM cuando no lo es. |
| `compare` | Ejecuta JVM y native sobre muestra o dataset controlado y compara resultados. |

El valor por defecto será `jvm` hasta completar el release gate. Después podrá ser
`auto`, nunca `native` por defecto sin evidencia aprobada.

### 3.2 Configuración

```json
{
  "nativeExecution": {
    "mode": "auto",
    "enabled": false,
    "glutenVersion": "<pinned>",
    "veloxVersion": "<pinned>",
    "fallback": "jvm",
    "compareResults": false,
    "maxMemoryFraction": 0.6,
    "timeoutSeconds": 1200
  }
}
```

La configuración no podrá modificar seguridad, secretos, acceso de red, identidad de
la sesión ni límites de recursos del Pod.

### 3.3 Diagnósticos públicos

Cada ejecución debe devolver:

- backend solicitado y backend efectivo;
- versión de Spark, Gluten, Velox, Java y Python;
- plan original y plan convertido, con información sensible redactada;
- operadores native y JVM utilizados;
- motivo de fallback, si existe;
- duración por fase;
- filas y bytes procesados;
- warnings y compatibilidad.

Códigos mínimos:

```text
NATIVE_DISABLED
NATIVE_PLAN_UNSUPPORTED
NATIVE_INIT_FAILED
NATIVE_EXECUTION_FAILED
NATIVE_RESULT_MISMATCH
NATIVE_TIMEOUT
NATIVE_OOM
NATIVE_SECURITY_POLICY
```

### 3.4 Comportamiento ante errores

- En modo `auto`, cualquier fallo nativo recuperable ejecuta JVM una sola vez.
- El fallback debe conservar filtros, parámetros, orden y límites.
- Un mismatch de resultados invalida la ruta native para esa consulta.
- En modo `native`, los errores se devuelven como error explícito y trazable.
- Nunca se debe marcar una consulta como native si realmente terminó en JVM.

## 4. Compatibilidad funcional

### Nivel A — obligatorio inicial

- scan Parquet;
- projection;
- filter básico;
- cast seguro;
- hash join y broadcast join controlados;
- group by;
- `SUM`, `COUNT`, `MIN`, `MAX`, `AVG`;
- sort y limit;
- expresiones aritméticas y booleanas;
- null semantics documentada.

### Nivel B — posterior

- joins complejos;
- ventanas;
- fechas y timestamps;
- distinct y aggregates complejos;
- particionamiento y pruning;
- subqueries controladas.

### Siempre JVM inicialmente

- Python UDF y pandas UDF;
- Scala/Java UDF no auditada;
- operaciones externas;
- acceso a red o sistema de archivos desde expresiones;
- funciones no presentes en el catálogo de compatibilidad;
- tipos o semánticas sin prueba de igualdad.

## 5. Arquitectura técnica

```text
Notebook / Query API
        ↓
Execution Policy
        ↓
Spark SQL logical plan
        ↓
Compatibility Analyzer
        ├── unsupported → Spark JVM
        └── supported → Gluten plugin → Velox native backend
                                ↓
                       Result Comparator / Metrics
```

### 5.1 Runtime

La imagen debe fijar:

- versión exacta de Spark;
- versión exacta de Gluten;
- commit o versión exacta de Velox;
- Java y Scala compatibles;
- arquitectura CPU soportada;
- wheels/JARs y checksums;
- configuración de native plugin;
- fallback y límites de memoria.

No se debe mezclar una distribución Spark duplicada con la distribución de PySpark.
Los artefactos deben ser verificables mediante SHA-256 y SBOM.

### 5.2 Configuración Spark orientativa

La configuración final dependerá de la matriz de versiones aprobada, pero deberá
modelar al menos:

```text
spark.plugins=io.glutenproject.GlutenPlugin
spark.gluten.sql.columnar.backend Velox
spark.gluten.enabled=true
spark.gluten.fallback.enabled=true
spark.sql.adaptive.enabled=<validated>
```

Estos valores no deben copiarse a producción sin comprobar compatibilidad con la
versión concreta de Spark y la imagen construida.

### 5.3 Analizador de planes

El analizador debe:

- obtener el plan lógico y físico;
- identificar operadores y expresiones;
- consultar una tabla de compatibilidad versionada;
- detectar UDF, funciones no soportadas y tipos peligrosos;
- producir una razón de fallback legible;
- no cambiar el resultado del plan por analizarlo.

### 5.4 Comparador de resultados

Debe comparar JVM/native por:

- nombres y orden de columnas;
- tipos;
- cardinalidad;
- nulls;
- valores exactos para enteros, strings y booleanos;
- tolerancia absoluta/relativa configurable para floating point;
- orden solo cuando la consulta lo garantice.

Un mismatch debe conservar muestras de filas redacted, hashes de datasets, planes,
versiones y parámetros no secretos.

### 5.5 Kubernetes

Los Pods runtime deben tener:

- imagen fijada por digest en producción;
- requests/limits de CPU y memoria;
- `runAsNonRoot` y `seccompProfile`;
- `automountServiceAccountToken: false`;
- límites de tiempo;
- métricas y logs redacted;
- feature flag para desactivar native;
- cleanup incluso después de OOM o timeout.

## 6. APIs y métricas

```text
POST /api/v1/models/{id}/query
GET  /api/v1/models/{id}/native-compatibility
POST /api/v1/models/{id}/native/compare
GET  /api/v1/sessions/{id}/execution-diagnostics
```

Métricas:

```text
fakebric_native_attempts_total{backend,mode}
fakebric_native_success_total{backend}
fakebric_native_fallback_total{reason}
fakebric_native_mismatch_total{query_hash}
fakebric_query_duration_seconds{backend}
fakebric_query_rows_total{backend}
fakebric_native_memory_bytes
```

## 7. Seguridad

- No permitir configuración native desde un usuario sin permiso de Contributor.
- Validar allowlist de configuraciones Spark.
- Bloquear `master`, credenciales, tokens, endpoints arbitrarios y rutas fuera del
  workspace.
- Redactar SQL, parámetros y resultados sensibles en diagnósticos.
- No ejecutar código arbitrario para instalar plugins durante una sesión.
- Firmar imágenes y verificar digest antes del despliegue productivo.
- Aplicar RLS antes de comparar, cachear o exportar resultados.

## 8. Criterios de aceptación

La capacidad podrá marcarse como `partial` cuando:

- el runtime compile y arranque con la matriz de versiones fijada;
- el modo JVM siga funcionando sin el plugin native;
- `auto` haga fallback determinista;
- el Nivel A tenga pruebas de igualdad;
- los diagnósticos indiquen backend efectivo;
- existan benchmarks reproducibles;
- no haya secretos ni privilegios adicionales.

Solo podrá marcarse como `implemented` para un nivel concreto cuando todos sus
operadores tengan igualdad funcional, pruebas de regresión, rendimiento medido,
documentación y evidencia en Docker y Minikube.

## 9. Estado actual

Fakebrick no tiene actualmente integración real Gluten + Velox. El runtime solo
declara metadata compatible y mantiene native desactivado. Este documento define el
trabajo necesario sin presentar la capacidad como disponible.
