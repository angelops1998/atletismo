# Corrección del arranque de demo y error del seed

**Fecha local:** 15 de noviembre de 2026  
**Proyecto:** `C:\Archivos.Diego\atletismoWeb\atletismo`  
**Tipo:** registro de petición y acciones realizadas estilo Kilo/Codex

---

## Petición

El usuario reportó que `scripts/iniciar_demo.ps1` fallaba durante el seed: PostgreSQL devolvía `UndefinedColumn` para `sesiones_entrenamiento.estructura_tipo` mientras el ORM intentaba insertar también columnas estructurales.

## Estado inicial

- Rama `Baruc+Kilo`, HEAD `cddd13b` al iniciar esta corrección.
- El esquema de `atletismo_demo` tenía revisión `c4b8e2d91f07`; la tabla `sesiones_entrenamiento` no incluía columnas `estructura_*`.
- El modelo ORM sí declaraba esas columnas, mientras `b67a104e9c32` creaba una tabla separada `entrenamientos_principales`.
- Causa: divergencia entre modelo y migración que provocaba que SQLAlchemy insertara columnas inexistentes al sembrar sesiones existentes.

## Cambios

- `app/models/sesion_entrenamiento.py`: retiré las 10 columnas estructurales que pertenecían a la nueva entidad y no a la tabla de sesiones. Se conservan los campos históricos requeridos de sesión.
- `scripts/iniciar_demo.ps1`: configuré la decodificación/salida UTF-8 para que PowerShell 5.1 presente correctamente los mensajes españoles emitidos por Python.

No se cambió `.env`, no se usaron credenciales reales y no se realizaron commits ni pushes.

## Ejecución y validación

- **PASS:** `scripts/iniciar_demo.ps1` — verificó identidad PostgreSQL, ejecutó Alembic, completó el seed y arrancó Uvicorn en `http://127.0.0.1:8002`.
- **PASS:** identidad con `scripts/demo_db_identity.py --verify-connection` — `DB_OK` para `atletismo_demo` local.
- **PASS:** `python -m alembic current` — `b67a104e9c32 (head)`.
- **PASS:** inspección PostgreSQL — la tabla `entrenamientos_principales` existe; `sesiones_entrenamiento` no tiene columnas estructurales divergentes; las 2 sesiones seed existentes se conservan.
- **PASS:** pytest enfocado: `tests/test_demo_environment.py tests/test_parte.py tests/test_parte_diaria_service.py tests/test_parte_diaria_schema.py` — 147 passed, 1 advertencia deprecada Starlette/httpx.
- **PASS:** solicitud HTTP a `/auth/login` — 200.
- **PASS:** parseo PowerShell de `scripts/iniciar_demo.ps1` y `git diff --check`.

## Estado Git final

Archivos modificados sin commit:

- `app/models/sesion_entrenamiento.py`
- `scripts/iniciar_demo.ps1`

No se hicieron commits, pushes, merges ni despliegues.

## Límite pendiente

Esta corrección resuelve el error de arranque/seed. La interfaz estructurada y el guardado de la entidad `EntrenamientoPrincipal` siguen sin implementarse; no debe interpretarse este arreglo como entrega terminada del formulario de entrenamiento principal.
