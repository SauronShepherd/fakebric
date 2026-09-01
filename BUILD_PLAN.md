# Fakebrick V2 — plan de construcción y validación

Este plan separa los requisitos de las especificaciones DOCX de las instrucciones operativas del usuario. Los DOCX definen el producto; el usuario solicita convertirlos en software ejecutable, corregir defectos y validar cada entrega.

## Gates de cada fase

Cada fase debe aportar implementación, pruebas automatizadas, documentación de evidencia y una ejecución verde del gate anterior. Un requisito no implementado debe aparecer como `unsupported` o `planned`, nunca como soportado.

## Fases

1. **Baseline reproducible**: toolchain, lockfiles, matriz de requisitos, perfiles local/server, Docker y Minikube.
2. **Control plane**: WorkspaceItem extensible, PostgreSQL/Alembic, contratos camelCase, authz/IDOR, ETag, errores, operaciones idempotentes, sesiones y métricas.
3. **Data plane**: runtime Spark 3.5.5/Java 11/Python 3.11/Delta 3.2.1, notebooks nbformat stateful, SQL, outputs, magics, `%pip`, FakeLake Files/Tables y Delta DML.
4. **Kubernetes**: namespaces por workspace, ServiceAccount mínimo, driver Service, reconciliación/watch, estados accionables, cleanup y recuperación.
5. **UX**: shell/rutas canónicas, inventario, editor notebook, autosave, conflictos, estado de sesión, explorer Files/Tables, accesibilidad y responsive.
6. **Debugger e Inspector**: handshake DAP/debugpy, breakpoints, pause/continue, Spark plans, Native/JVM/Unknown y evidencia Gluten/Velox con fallback.
7. **Testing y operaciones**: unit/property, API, runtime, K8s, Playwright/axe, seguridad, chaos, rendimiento, backup/restore, compatibilidad y quality report.
8. **Release gate**: Minikube completo, imágenes por digest, SBOM, escaneo, manifests, smoke/E2E, regresión y checklist de producción.

## Hallazgos incorporados

- Contratos internos SQLite no se exponen directamente: `displayName`, `itemId`, `updatedAt` y `timeoutSeconds`.
- El controller exige el registro JSON de éxito del runtime antes de marcar `COMPLETED`.
- Se deben reemplazar tags mutable/dev por digests en el perfil servidor.
- `nativeExecution` no puede declararse efectivo sin evidencia de plan/build.
- Deben cubrirse traversal, IDOR, roles, uploads, notebooks inválidos, conflictos ETag, carreras de sesión y cleanup.
- Minikube no se considera validado si Docker/Kubernetes no está disponible; el fallo debe conservar diagnóstico.

## Estado inicial

El repositorio contiene un MVP local con API FastAPI, SQLite, runtime OCI, controller Kubernetes, Files/Tables JSONL y UI estática. La suite actual es un smoke/contract suite; no cubre todavía el catálogo completo V2.
