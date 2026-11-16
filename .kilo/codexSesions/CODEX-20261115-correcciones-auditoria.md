# Implementación de correcciones de auditoría AUD-001 a AUD-004

**Fecha:** 15 de noviembre de 2026  
**Repositorio:** `C:\Archivos.Diego\atletismoWeb\atletismo`  
**Rama / HEAD:** `Baruc+Kilo` / `5102718072c2580754561d6927f88fdb8bc86245` (`codex commit 9`)  
**Estado:** implementado; sin commit.

## Resumen

Se corrigió el fingerprint de concurrencia para incluir el entrenamiento principal completo, se activó CSRF también para el login anónimo, se trasladó logout a POST protegido por CSRF y se añadió una migración correctiva que retira únicamente el índice explícito redundante. Las ocho pruebas antiguas se adaptaron al formulario estructurado actual, conservando las pruebas de CRUD, autorización, integridad y descarte de sesiones individuales.

## Correcciones

### AUD-001 — Fingerprint

- `app/services/parte_diaria_tokens.py`: normaliza e incluye tipo, series, repeticiones, distancia y los seis valores de tiempo en segundos; representa explícitamente la ausencia del principal.
- Se mantiene intacta la función y el protocolo de fingerprint de sesiones individuales/descarte.
- `tests/test_parte_diaria_service.py`: pruebas parametrizadas para los diez campos, ausencia del principal y token obsoleto ante cambio solo de distancia.
- `tests/test_parte.py`: edición obsoleta del principal produce HTTP 409, conserva el principal vigente y no elimina sesiones individuales.

### AUD-002 — CSRF en login

- `app/main.py`: se eliminó la excepción CSRF de `/auth/login`. El GET anónimo existente emite cookie y el formulario ya renderiza el token firmado.
- `tests/test_seguridad.py`: login válido sin sesión previa, CSRF ausente, token manipulado y comportamiento de `next`; se verifica que los casos inválidos no autentiquen.

### AUD-003 — Logout POST

- `app/routers/auth.py`: `/auth/logout` ahora responde a POST; GET devuelve 405 y no borra la sesión.
- `app/templates/_nav.html`, `app/templates/_menu_movil.html`, `app/templates/cuenta.html`: enlaces cambiados por formularios POST con token CSRF y botón con estilo equivalente.
- `app/static/css/main.css`: conserva el aspecto de navegación lateral y móvil.
- `tests/test_seguridad.py`: token ausente/inválido, cierre correcto mediante login real, GET inocuo y formularios en la navegación.

### AUD-004 — Unicidad y migración

- `app/models/entrenamiento_principal.py`: se mantiene `unique=True` sin `index=True`, conservando una única restricción uno-a-uno en metadata.
- Nueva migración `alembic/versions/e8a4f670c11d_remove_duplicate_principal_workout_index.py`, hija de `b67a104e9c32`: verifica tabla y restricción UNIQUE, elimina solo `ix_entrenamientos_principales_parte_diaria_id`; el downgrade recrea ese índice. No se reescribió `b67a104e9c32`.
- `tests/test_parte_diaria_schema.py`: comprueba restricción, ausencia del índice redundante en metadata, FK/cascada ORM y unicidad de la tabla.

### Pruebas antiguas del parte

`tests/test_parte.py` y `tests/test_parte_diaria_service.py` reemplazan las expectativas del textarea y de “al menos una sesión individual” por validación, preservación de campos y concurrencia de la estructura principal. Los casos actualizados de 422/409 también comprueban que sesiones existentes sobrevivan. Las pruebas separadas de ownership, borrado explícito, conservación por omisión y protocolo de descarte se mantienen.

## PostgreSQL y migraciones

La inspección de solo lectura del contenedor `atletismo-demo-db` verificó que está ligado a `127.0.0.1:5433`, usa PostgreSQL 15.19 y que `atletismo_demo` estaba en `b67a104e9c32`, con la restricción UNIQUE y el índice redundante presentes.

No se modificó `atletismo_demo`. Se creó una base nueva y vacía `atletismo_audit_test_20261115_7f31` en ese contenedor local; no se eliminó al terminar. En ella:

1. `alembic upgrade head` alcanzó `e8a4f670c11d`; permaneció la restricción UNIQUE y desapareció el índice explícito redundante.
2. `alembic downgrade -1` volvió a `b67a104e9c32` y restauró el índice nombrado.
3. `alembic upgrade head` volvió a `e8a4f670c11d`; índice redundante ausente y restricción UNIQUE presente.
4. `alembic check` informó `No new upgrade operations detected.`

El `alembic heads` del repositorio señala `e8a4f670c11d (head)`. Una consulta posterior confirmó que `atletismo_demo` permanece intacta en `b67a104e9c32` y todavía conserva ambos índices/garantía original; la corrección pendiente se aplicará allí cuando se ejecute el upgrade demo autorizado.

## Validación ejecutada

| Comando | Resultado |
|---|---|
| `.venv\Scripts\python.exe -m pytest -q tests\test_parte_diaria_service.py tests\test_parte.py tests\test_seguridad.py tests\test_parte_diaria_schema.py` | **169 passed**, 1 warning. |
| `.venv\Scripts\python.exe -m pytest -q` | **499 passed, 5 skipped, 1 warning** en 86.03 s. |
| `alembic upgrade head` en `atletismo_audit_test_20261115_7f31` | PASS, `e8a4f670c11d`. |
| `alembic downgrade -1` en base aislada nueva | PASS, vuelta a `b67a104e9c32`; índice restaurado. |
| Segundo `alembic upgrade head` | PASS; restricción UNIQUE conservada e índice redundante ausente. |
| `.venv\Scripts\python.exe -m alembic check` | PASS, metadata y esquema sin operaciones pendientes. |
| `.venv\Scripts\python.exe -m alembic heads` | PASS, head `e8a4f670c11d`. |
| `git diff --check` | PASS, sin errores de whitespace. Git mostró solo advertencias normales de conversión LF/CRLF en Windows. |

Las cinco pruebas omitidas pertenecen al módulo de concurrencia PostgreSQL: su barrera exige `PARTE_DIARIA_TEST_DATABASE_URL` y un contenedor desechable verificado con imagen/etiquetas concretas (`postgres:16`). El contenedor disponible es PostgreSQL 15.19 y no cumple ese gate. Por ello, la migración sí se validó en PostgreSQL local, pero la serialización concurrente real con `SELECT FOR UPDATE` no se probó en PostgreSQL; sí pasó su cobertura SQLite y HTTP.

El único warning fue `StarletteDeprecationWarning` sobre el uso de `httpx` con `starlette.testclient`; no afectó el resultado.

## Archivos afectados

- `app/main.py`
- `app/models/entrenamiento_principal.py`
- `app/routers/auth.py`
- `app/services/parte_diaria_tokens.py`
- `app/static/css/main.css`
- `app/templates/_menu_movil.html`
- `app/templates/_nav.html`
- `app/templates/cuenta.html`
- `alembic/versions/e8a4f670c11d_remove_duplicate_principal_workout_index.py` (nuevo)
- `tests/test_parte.py`
- `tests/test_parte_diaria_schema.py`
- `tests/test_parte_diaria_service.py`
- `tests/test_seguridad.py`

## Pendientes y estado final

- No se hizo verificación manual en navegador.
- No se ejecutaron los cinco tests de concurrencia PostgreSQL por el gate de aislamiento descrito.
- Aplicar `alembic upgrade head` al entorno local de demo solo cuando se desee actualizarlo; no se modificó durante esta validación.
- No hubo commits, pushes, merges, PR ni despliegue.
- Los cambios de implementación permanecen en el working tree para revisión.