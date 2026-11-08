# Docker, WSL 2 y validación de migración PostgreSQL

**Fecha:** 2026-11-07  
**Estado:** Validación detenida antes de instalar/arrancar Docker: Windows no tiene virtualización por hardware disponible y requiere intervención de firmware; esta sesión tampoco está elevada.

## Entorno inicial y comprobaciones

- Repositorio local: `C:\Archivos.Diego\atletismoWeb\atletismo`; rama `Baruc+Kilo`, sin cambios locales reportados por `git status` al inicio.
- Windows: Windows 11 Pro, build 26300 (la CIM version indica 10.0.26300, producto Windows 11 Pro).
- CPU: Intel Core i5-12400F. Windows reporta `VirtualizationFirmwareEnabled=False`, `VMMonitorModeExtensions=False` y `SecondLevelAddressTranslationExtensions=False`. La virtualización de firmware no está disponible para el hipervisor. No se cambió el firmware.
- WSL: `wsl --status` indica versión predeterminada 2; `wsl --list --verbose` indica que no hay distribuciones. No se instaló una distribución ni se actualizó el kernel en esta ejecución.
- Características opcionales `Microsoft-Windows-Subsystem-Linux` y `VirtualMachinePlatform`: estado no verificado; la consulta `Get-WindowsOptionalFeature -Online` requiere elevación. La consola actual no tiene token administrativo elevado.
- Docker: `docker` no está en PATH ni se encontró ejecutable, servicio `com.docker.service`, entrada de instalación o carpeta de programa de Docker en las ubicaciones consultadas. Hay archivos de log bajo `%LOCALAPPDATA%\Docker`, lo que por sí solo no acredita una instalación utilizable. No se pudo comprobar Docker Desktop ni el Engine.

## Migración inspeccionada

- La revisión `c4b8e2d91f07` declara `down_revision = a3f1c9e27b04`.
- Inspección estática de `alembic/versions/c4b8e2d91f07_add_partes_diarios_sesiones.py`: crea `partes_diarios` y `sesiones_entrenamiento`, restricción única `(atleta_id, fecha)`, claves foráneas con `ON DELETE CASCADE`, checks e índices. Declara `molestia_zona` como `postgresql.ARRAY(sa.String())`; `enviado` y `creado` son timestamps con zona horaria y default `now()`. La migración no modifica `partes_semanales`.
- No se ejecutó Alembic, ni se creó base de datos o contenedor. Por tanto, revisiones aplicadas, esquema real, defaults, cascadas y roundtrip ORM en PostgreSQL quedan sin validar.

## Pruebas ejecutadas

Comando: `.venv\Scripts\python.exe -m pytest -q tests/test_parte_diaria_schema.py` desde la raíz del proyecto.

Resultado: **7 passed**, 1 warning deprecación de Starlette/httpx. La prueba focalizada usa SQLite/metadata; no demuestra compatibilidad PostgreSQL ni sustituye una migración real.

## Acciones y recursos

No se habilitaron características de Windows, no se instaló software, no se descargaron imágenes, no se crearon contenedores/volúmenes, no se tocaron datos reales ni se modificó código del proyecto. No hay recursos temporales de esta ejecución que limpiar. No se intentó `alembic upgrade head`.

## Acción requerida para continuar

1. En BIOS/UEFI, habilitar la virtualización del procesador Intel (suele llamarse **Intel Virtualization Technology**, **VT-x** o **Vanderpool**), guardar y reiniciar Windows. La señal actual de Windows es concluyente; no se puede activar por software desde esta sesión.
2. Después del reinicio, abrir una terminal elevada para verificar/habilitar solo `Microsoft-Windows-Subsystem-Linux` y `VirtualMachinePlatform` e instalar/configurar WSL 2 y Ubuntu LTS si todavía hace falta.
3. Reanudar comprobando la instalación real de Docker Desktop, instalar/reparar desde el instalador oficial si falta, iniciar el Engine y validar sus comandos antes de crear un PostgreSQL desechable ligado a localhost.
4. Ejecutar primero la cadena histórica hasta `a3f1c9e27b04`, luego únicamente `c4b8e2d91f07`, y verificar esquema/constraints/ORM. Mantener `partes_semanales` intacta.

**Limitación restante:** la condición de éxito principal —Engine funcional y migración aplicada/validada sobre PostgreSQL desechable— no se alcanzó debido a la virtualización de firmware desactivada y la necesidad de elevación para configuración de Windows. No se informa como completada.
