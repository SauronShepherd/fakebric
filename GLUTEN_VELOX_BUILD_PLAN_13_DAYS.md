# Fakebrick — Plan de construcción y pruebas Gluten + Velox en 13 días

## Datos

- **Fechas:** 1–13 de septiembre de 2026.
- **Días 1–10:** implementación y tests básicos.
- **Días 11–13:** solo pruebas, correcciones derivadas y release gate.
- **Especificación:** `GLUTEN_VELOX_EMULATION_SPEC.md`.
- **Regla:** native permanece desactivado por defecto hasta completar el día 13.

## Día 1 — 1 septiembre: matriz de versiones y contratos

### Implementación

- Seleccionar combinaciones compatibles de Spark, Scala, Java, Gluten y Velox.
- Crear `native-runtime-matrix.json` con versión, arquitectura, URL y checksum.
- Versionar contrato `NativeExecutionConfig`.
- Definir modos `jvm`, `native`, `auto` y `compare`.
- Definir códigos de error y respuesta de diagnósticos.
- Añadir feature flag global y por sesión.

### Tests básicos

- Validar versiones obligatorias y checksums.
- Rechazar combinaciones incompletas.
- Verificar que el modo por defecto sea `jvm`.
- Verificar que configuraciones inseguras sean rechazadas.

## Día 2 — 2 septiembre: runtime base reproducible

### Implementación

- Crear variante Docker del runtime con Java, Spark y dependencias nativas fijadas.
- Separar artefactos JVM y native para diagnosticar fallos.
- Añadir SBOM preliminar y checksums.
- Configurar usuario no root, tini, límites y directorios temporales.
- Añadir comando `runtime --version`.

### Tests básicos

- Construcción limpia de imagen.
- Arranque JVM sin plugin.
- Verificación de usuario, Java, Spark y Python.
- Verificación de arquitectura y librerías cargadas.

## Día 3 — 3 septiembre: carga del plugin y backend Velox

### Implementación

- Integrar Gluten plugin de la matriz aprobada.
- Configurar Velox como backend.
- Añadir `native-smoke.py`.
- Exponer configuración efectiva sin secretos.
- Implementar fallo controlado si el plugin no puede inicializarse.

### Tests básicos

- Inicialización native en la imagen compatible.
- Detección de plugin ausente.
- Detección de backend incorrecto.
- JVM sigue arrancando cuando native está desactivado.

## Día 4 — 4 septiembre: analizador de planes

### Implementación

- Capturar plan lógico/físico.
- Crear catálogo versionado de operadores compatibles.
- Clasificar `supported`, `fallback` y `blocked`.
- Detectar UDF, funciones externas y configuraciones no permitidas.
- Generar explicación de selección de backend.

### Tests básicos

- Planes scan/filter/project compatibles.
- UDF marcada como fallback.
- Operador desconocido rechazado o enviado a JVM.
- Explicación estable y serializable.

## Día 5 — 5 septiembre: política de ejecución y fallback

### Implementación

- Implementar selector `jvm/native/auto/compare`.
- Fallback una sola vez por consulta.
- Preservar filtros, parámetros, límites y orden.
- Devolver backend solicitado y efectivo.
- Persistir razón del fallback.

### Tests básicos

- JVM forzado nunca usa native.
- Auto usa native en plan soportado.
- Auto usa JVM en plan no soportado.
- Fallo native recuperable ejecuta JVM.
- Fallo native no recuperable devuelve diagnóstico.

## Día 6 — 6 septiembre: ejecución Nivel A

### Implementación

- Validar scan Parquet, projection, filter, cast, join y aggregate.
- Activar `SUM`, `COUNT`, `MIN`, `MAX` y `AVG` donde la matriz lo permita.
- Configurar null semantics.
- Añadir límites de memoria, timeout y cancelación.

### Tests básicos

- Dataset pequeño con tipos numéricos, strings, fechas y nulls.
- Cada operador Nivel A en JVM y native.
- Timeout y cancelación.
- OOM simulado y fallback/error controlado.

## Día 7 — 7 septiembre: comparador JVM/native

### Implementación

- Comparar esquema, columnas, filas, nulls y cardinalidad.
- Añadir tolerancias floating point.
- Hash de entrada y salida.
- Muestra redacted de mismatches.
- Endpoint de comparación.

### Tests básicos

- Resultados idénticos.
- Diferencias de tipos.
- Diferencias de nulls.
- Diferencias numéricas dentro y fuera de tolerancia.
- Consultas sin orden declarado.

## Día 8 — 8 septiembre: integración con sesiones y API

### Implementación

- Pasar configuración native de modelo/sesión al runtime.
- Integrar diagnósticos en la respuesta de ejecución.
- Añadir métricas y trace IDs.
- Mantener compatibilidad con notebooks existentes.
- Bloquear configuraciones Spark no permitidas.

### Tests básicos

- Sesión JVM existente no cambia de comportamiento.
- Sesión auto recibe backend efectivo.
- Usuario sin permiso no activa native.
- Diagnóstico persiste tras completar la sesión.

## Día 9 — 9 septiembre: Kubernetes y operación

### Implementación

- Actualizar PodSpec, Deployment y ConfigMap.
- Añadir digest de imagen, limits y feature flag.
- Comprobar securityContext y service account.
- Añadir cleanup tras éxito, fallo, timeout y OOM.
- Añadir logs redacted y métricas Prometheus.

### Tests básicos

- `kubectl apply --dry-run --validate=strict`.
- Pod no root y sin token montado.
- Imagen por digest en perfil productivo.
- Cleanup de Pod native.
- Recuperación tras reinicio del controller.

## Día 10 — 10 septiembre: benchmark inicial y cierre de implementación

### Implementación

- Crear datasets de benchmark pequeño, medio y grande.
- Añadir queries representativas de Nivel A.
- Automatizar medición JVM/native.
- Documentar operadores excluidos.
- Actualizar README y `REQUIREMENTS_MATRIX.md` sin sobreafirmar soporte.
- Preparar imágenes versionadas para la campaña final.

### Tests básicos

- Benchmark reproducible.
- Native no degrada por encima del umbral acordado sin diagnóstico.
- Resultados comparables.
- Registro de memoria, duración, filas y bytes.

## Día 11 — 11 septiembre: pruebas funcionales exhaustivas

> No se añade funcionalidad nueva.

- Ejecutar todos los golden tests de operadores.
- Ejecutar queries con joins, agregados, nulls, casts y fechas.
- Ejecutar modos JVM/native/auto/compare.
- Verificar fallback y diagnósticos.
- Probar notebooks reales y API.
- Repetir cada caso al menos tres veces.
- Corregir únicamente defectos reproducibles y añadir regresión.

### Salida

- Cero defectos críticos/altos.
- Catálogo de compatibilidad coherente con los resultados.
- Informe funcional archivado.

## Día 12 — 12 septiembre: seguridad, rendimiento y resiliencia

### Seguridad

- Intentos de inyección de configuración Spark.
- Escape de workspace y rutas.
- UDF y acceso de red no autorizado.
- RLS antes de comparar/cachear/exportar.
- Pruebas RBAC e IDOR.
- Escaneo de dependencias, JARs, imagen y SBOM.

### Rendimiento

- 10k, 100k, 1M y 10M filas.
- 1, 10 y 50 consultas concurrentes.
- JVM frente a native frente a auto.
- Memoria, CPU, p50, p95 y p99.
- Caché fría y caliente.

### Resiliencia

- plugin ausente;
- incompatibilidad de operador;
- OOM;
- timeout;
- reinicio de Pod;
- reinicio de controller;
- pérdida temporal de storage;
- mismatch de resultados.

### Salida

- Sin vulnerabilidades críticas/altas.
- Umbrales de rendimiento documentados.
- Fallback probado sin pérdida de seguridad.

## Día 13 — 13 septiembre: release gate final

### Pruebas

- Checkout limpio y construcción desde cero.
- Repetir suite completa y cobertura.
- Ejecutar smoke JVM, smoke native y smoke auto.
- Ejecutar comparación JVM/native de todos los operadores Nivel A.
- Ejecutar Minikube E2E tres veces.
- Ejecutar upgrade, rollback y cleanup.
- Verificar digest, SBOM y checksums.
- Validar documentación y matriz de compatibilidad.

### Gate

```text
runtime JVM smoke                         PASS
runtime native smoke                      PASS
native Nivel A equality                   PASS
fallback suite                            PASS
security/RLS/IDOR                         PASS
compileall + JS syntax                    PASS
coverage                                  PASS
Docker build reproducible                 PASS
Kubernetes strict validation              PASS
Minikube E2E x3                           PASS
benchmark report                          ARCHIVED
SBOM/checksums                            PASS
image digest                              PASS for production
documentation/matrix                     UPDATED
```

### Decisión de release

- Si hay igualdad y estabilidad para Nivel A: marcar Nivel A como `partial` o
  `implemented` según la evidencia.
- Si falla cualquier igualdad: dejar native desactivado y mantener fallback JVM.
- Si el plugin no compila en la matriz aprobada: no publicar la integración.
- Ninguna función de Nivel B se anuncia hasta tener sus propios golden tests.

## Entregables

- `GLUTEN_VELOX_EMULATION_SPEC.md`.
- Este plan de 13 días.
- Matriz de versiones y checksums.
- Dockerfile/runtime native.
- Catálogo de operadores.
- Selector y fallback.
- Comparador JVM/native.
- Diagnósticos y métricas.
- Golden tests y benchmarks.
- Evidencia Docker/Minikube.
- SBOM y reporte de seguridad.
- Actualización de `REQUIREMENTS_MATRIX.md`.
