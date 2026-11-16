# Validación PostgreSQL de la migración c4b8e2d91f07

**Fecha:** 2026-11-08  
**Resultado:** Validación PostgreSQL real completada. Docker Desktop y su Engine están operativos. Se creó y retiró un entorno PostgreSQL desechable aislado.

## Estado de Windows, WSL y Docker al reanudar

- Windows 11 Pro, build 26300; CPU Intel Core i5-12400F.
- La primera sesión de inspección no había heredado el PATH actualizado y no localizó Docker. En esta reanudación se encontró el Docker CLI instalado en `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`; no fue necesario reinstalar Docker Desktop.
- Docker Desktop 4.98.0; Docker CLI y Engine 29.9.2; Compose 5.6.1; contexto `desktop-linux`. `docker desktop status` reportó `running`; `docker info` mostró el servidor Linux y kernel `6.18.54.1-microsoft-standard-WSL2`; `docker version` mostró Client y Server sin error.
- WSL usa versión predeterminada 2. La distribución `docker-desktop` estaba `Running`, versión 2. No se instaló Ubuntu: la distribución backend de Docker Desktop proporcionó el entorno necesario para esta validación.
- `Win32_ComputerSystem.HypervisorPresent=True`, y el backend WSL 2 y Docker Engine funcionaron. Al mismo tiempo, los campos WMI del procesador `VirtualizationFirmwareEnabled`, `VMMonitorModeExtensions` y `SecondLevelAddressTranslationExtensions` continuaron reportando `False`. No se cambió firmware; se registra esta discrepancia sin afirmar que se modificó BIOS/UEFI.
- La consulta administrativa del estado exacto de `Microsoft-Windows-Subsystem-Linux` y `VirtualMachinePlatform` seguía requiriendo elevación y no se pudo completar desde esta consola. Su necesidad operativa sí quedó cubierta por la distribución WSL 2 activa y el Engine funcionando.
- No se instaló software ni se modificaron características de Windows en esta ejecución.

## PostgreSQL temporal

- Imagen oficial usada: `postgres:16`; versión del servidor: **PostgreSQL 16.15**.
- Contenedor `codex-migval-20261108`, puerto publicado solo en `127.0.0.1:55439`; base y credenciales desechables. La conexión del proyecto fue protegida con una guarda que exigía host `127.0.0.1`, puerto `55439` y base `migration_validation`. No se accedió a producción, staging, Supabase ni Render.
- El proyecto fija `psycopg2-binary==2.9.12`, SQLAlchemy 2.0.50 y Alembic 1.18.4. No fija una versión de servidor PostgreSQL; se eligió PostgreSQL 16 para la prueba.

## Ejecución de Alembic

Se confirmó estáticamente la cadena `d61e48816ec5` → `a3f1c9e27b04` → `c4b8e2d91f07`. No se modificaron las migraciones históricas.

1. `python -m alembic upgrade a3f1c9e27b04` aplicó únicamente la migración inicial y la migración histórica padre.
2. `python -m alembic current` confirmó `a3f1c9e27b04`.
3. `python -m alembic upgrade c4b8e2d91f07` ejecutó la migración solicitada.
4. `python -m alembic current` y la consulta PostgreSQL a `alembic_version` confirmaron `c4b8e2d91f07`.

No se ejecutó `alembic upgrade head`.

## Validación real del esquema y ORM

Un chequeo de integración ejecutado contra PostgreSQL confirmó:

- Existencia de `partes_diarios`, `sesiones_entrenamiento` y `partes_semanales`.
- `molestia_zona` como `ARRAY(VARCHAR)` de PostgreSQL.
- Columnas timestamp con zona horaria; defaults PostgreSQL `now()` en `partes_diarios.enviado` y `sesiones_entrenamiento.creado`.
- Restricción única `uq_parte_diaria_atleta_fecha` exactamente sobre `(atleta_id, fecha)`.
- Claves foráneas esperadas y `ON DELETE CASCADE` desde atleta a parte diario y desde parte diario a sesión.
- Ocho checks de `partes_diarios`, cuatro de `sesiones_entrenamiento` e índices esperados en ambas tablas.
- PostgreSQL rechazó una fila duplicada `(atleta_id, fecha)` y un valor inválido de `sueno_calidad`.
- ORM insertó, leyó, actualizó y eliminó un parte diario y su sesión; se verificó la relación y el roundtrip del array.
- El borrado ORM eliminó la sesión relacionada; un borrado SQL directo del parte también activó el cascade de la base.
- `partes_semanales` permaneció presente y aceptó una inserción/lectura ORM. No se ejecutó ninguna migración que la elimine.

## Pruebas automatizadas

Comando: `.venv\Scripts\python.exe -m pytest -q tests\test_parte_diaria_schema.py`

Resultado final: **7 passed**, 1 advertencia de deprecación Starlette/httpx. Estas pruebas usan SQLite/metadata; las comprobaciones PostgreSQL anteriores fueron una ejecución de integración separada sobre el servidor real desechable.

## Limpieza y cambios

- Se verificaron el ID y las etiquetas propias del contenedor, además de que el volumen anónimo estaba adjunto exclusivamente a ese contenedor. Se retiraron el contenedor y su volumen de datos.
- Se verificó el ID de imagen `postgres:16`, descargada durante esta ejecución, y que ningún contenedor la usaba; se retiró esa imagen.
- No quedaron contenedor, volumen, credenciales ni script de integración temporal de esta ejecución. Docker Desktop y Engine quedaron encendidos.
- No se modificó código, migraciones ni datos persistentes del proyecto; no hubo cambios de base de datos real. El único archivo nuevo en el repositorio es este informe; no se hizo commit.

## Limitación de diagnóstico

La consulta de las dos características opcionales requiere una consola elevada, por lo que sus estados administrativos individuales no constan. La prueba funcional solicitada sí terminó: el backend WSL 2 estaba corriendo y Docker Server atendió consultas durante toda la migración y la integración.
