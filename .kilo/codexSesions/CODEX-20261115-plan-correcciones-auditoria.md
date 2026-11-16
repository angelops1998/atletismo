# Plan de correcciones — AUD-001 a AUD-004 y regresiones del parte

**Fecha:** 15 de noviembre de 2026  
**Proyecto:** `C:\Archivos.Diego\atletismoWeb\atletismo`  
**Rama verificada:** `Baruc+Kilo`  
**HEAD verificado:** `789686db142d85443277c537a82cdcbc980c9f59` (`codex commit 8`)  
**Modo:** planificación; sin cambios de código, migraciones, pruebas con escrituras ni commits.

## Estado inspeccionado

- `git status --porcelain=v2 --branch`: rama `Baruc+Kilo`, upstream `origin/Baruc+Kilo`, sin cambios locales; 0 commits adelante/atrás.
- Commit 8 solo agregó `.kilo/codexSesions/AUDIT-full-project-security-quality.md`; el código coincide con lo auditado en Commit 7.
- El informe anterior registra 469 aprobadas, 8 fallidas y 5 omitidas.
- El informe de preparación local de 2026-11-15 20:24 indica que `atletismo_demo` ya estaba en `b67a104e9c32`. No se inspeccionó una base en este paso. Dado que hay evidencia de aplicación en la base local y no se puede establecer el estado de todas las bases compartidas, el plan conserva el historial y añade una migración correctiva posterior.

## Diseño propuesto por hallazgo

### AUD-001 — Fingerprint del entrenamiento principal

**Archivos:**
- `app/services/parte_diaria_tokens.py`
- `app/services/parte_diaria.py`
- `tests/test_parte_diaria_service.py`
- `tests/test_parte.py`
- Opcional: `tests/test_parte_diaria_concurrency_pg.py` para el escenario real con PostgreSQL aislado.

**Cambio:** agregar al estado canónico una forma normalizada que incluya `estructura_tipo`, `series`, `repeticiones_por_serie`, `distancia_m` y los seis valores de descanso/tiempo en segundos. Incluir explícitamente `None` cuando no hay entrenamiento principal. Pasar esa estructura desde `current_fingerprint()` al cálculo del token. No cambiar el fingerprint específico de sesiones usado para el protocolo de descarte.

**Pruebas:** verificar que cambiar cada campo, de manera aislada, cambie el fingerprint; que el estado equivalente mantenga el mismo fingerprint; que una edición con token antiguo tras un cambio solo del principal dé conflicto 409 y conserve el valor más reciente en SQLite; añadir caso PostgreSQL si se dispone de una base de pruebas aislada.

### AUD-002 — CSRF del login anónimo

**Archivos:**
- `app/main.py`
- `app/templates/auth/login.html` (solo si las pruebas muestran que el token renderizado necesita ajuste; ya contiene `csrf_input(request)`)
- `app/csrf.py` (solo si se demuestra que la cookie anónima no se conserva entre GET y POST)
- `tests/test_seguridad.py`

**Cambio:** retirar `/auth/login` de la exención CSRF. El middleware ya crea cookie CSRF si no existe y la plantilla de login ya incluye el campo firmado. Mantener el flujo: primer GET anónimo entrega cookie y token; POST del login verifica ambos antes de autenticar. Evitar convertir CSRF en requisito de una cookie de autenticación.

**Pruebas HTTP:** GET inicial sin sesión y POST con token válido permite autenticación; POST sin token y con token manipulado reciben 403 y no emiten cookie `access_token`; POST repetido con token válido mantiene el destino interno permitido.

### AUD-003 — Logout POST

**Archivos:**
- `app/routers/auth.py`
- `app/templates/_nav.html`
- `app/templates/_menu_movil.html`
- `app/templates/cuenta.html`
- `tests/test_seguridad.py`
- Cualquier otra referencia a `/auth/logout` que revele `rg` antes de editar.

**Cambio:** cambiar la ruta de cierre de sesión a POST. Sustituir los enlaces de navegación por formularios POST con `csrf_input(request)` y conservar su presentación visual. El GET debe dejar de borrar la sesión (respuesta 405 si no hay ruta GET). No añadir revocación global de JWT como parte de este arreglo: el mecanismo actual invalida sesión al borrar la cookie del navegador.

**Pruebas HTTP:** GET no cierra sesión; POST sin token o con token inválido recibe 403 y conserva la cookie; POST con token válido borra `access_token`, redirige a login y deja al cliente sin acceso autenticado.

### AUD-004 — Índice único redundante

**Archivos:**
- `app/models/entrenamiento_principal.py`
- Nueva migración en `alembic/versions/`, hija de `b67a104e9c32` (nombre/revisión Alembic únicos)
- `tests/test_parte_diaria_schema.py`
- Nueva prueba de migración/esquema si la convención actual no permite extender la existente.

**Cambio:** conservar una sola garantía de uno-a-uno. Propuesta: modelar `parte_diaria_id` como único con restricción única (sin `index=True`); la migración correctiva elimina solamente el índice explícito `ix_entrenamientos_principales_parte_diaria_id`, manteniendo la restricción única creada por `unique=True`. No reescribir `b67a104e9c32`, porque existe evidencia de que se aplicó a `atletismo_demo` y no se probó que nunca se haya aplicado fuera de ella. La migración nueva debe revisar que tabla/índice/restricción esperados existan y fallar con mensaje claro ante un esquema inesperado; el downgrade recrea el índice explícito para volver al estado anterior.

**Pruebas:** verificar metadata ORM (una única restricción, sin índice explícito redundante), insertar dos principales para el mismo parte y comprobar rechazo, mantener FK y cascada, y ejecutar upgrade/downgrade/upgrade en una base PostgreSQL desechable. Comprobar también SQLite si el harness admite la operación de índice.

## Revisión de las ocho pruebas fallidas

No eliminaría en bloque las pruebas de sesiones individuales. Se reemplazarían las expectativas ligadas a la UI antigua por pruebas del flujo actual, conservando la cobertura de autorización, propiedad, borrado explícito, descarte confirmado e integridad de sesiones:

| Prueba registrada | Tratamiento propuesto |
|---|---|
| `tests/test_parte.py::TestCreacionYActualizacion::test_entreno_hoy_sin_sesiones_es_422` | Sustituir por: principal válido sin sesiones individuales guarda; principal ausente o inválido produce 422 sin crear parte. |
| `tests/test_parte.py::TestInputParsing::test_repeated_sessions_fields_se_preservan` | Sustituir textarea-preservación por conservación de los campos estructurados enviados cuando hay otro error de validación. |
| `tests/test_parte.py::TestInputParsing::test_repeated_sessions_fields_surviven_409` | Sustituir por prueba 409 que conserva valores principales enviados y muestra estado persistido; combinar con cambio concurrente del principal para AUD-001. |
| `tests/test_parte.py::TestInputParsing::test_newline_sessions_textarea_survives_422` | Sustituir por MM:SS inválido preservado y error de validación legible. |
| `tests/test_parte.py::TestInputParsing::test_repeated_delete_ids_survive_422` | Quitar solo la expectativa de un campo de borrado que ya no está en la interfaz; mantener comprobación de que error no borra sesiones ya persistidas y conservar pruebas de borrado explícito del servicio. |
| `tests/test_parte.py::TestInputParsing::test_repeated_delete_ids_survive_409` | Quitar expectativa del control visual obsoleto; verificar 409 y que las sesiones persistidas siguen intactas. |
| `tests/test_parte.py::TestRenderizado::test_form_renderiza_campos_diarios_obligatorios` | Cambiar `sessions`/`delete_session_ids` por todos los campos requeridos del entrenamiento principal; mantener los campos de bienestar/parte. |
| `tests/test_parte_diaria_service.py::TestServiceCRUD::test_entreno_hoy_true_requires_session_and_saves_multi` | Dividir en pruebas de principal obligatorio y persistencia del principal sin `SesionEntrenamiento`; conservar pruebas separadas de CRUD múltiple de sesiones individuales, propiedad y descarte. |

La implementación también debe reexaminar los demás tests relacionados con sesiones al actualizar la suite para evitar borrar cobertura aún válida.

## Dependencias y secuencia

1. Revisar de nuevo `git status`, archivos no rastreados y diff antes de cualquier edición.
2. Corregir función canónica y fingerprint; crear primero sus pruebas de regresión.
3. Corregir CSRF del login y añadir pruebas anónimas positivas/negativas.
4. Cambiar logout y actualizar todos los formularios/enlaces junto con pruebas.
5. Confirmar en modo de solo lectura la revisión aplicada en `atletismo_demo`; no conectar a producción/compartidas. Crear migración correctiva solo después de inspeccionar el esquema local y confirmar su identidad.
6. Actualizar los ocho tests obsoletos preservando tests válidos de sesiones individuales.
7. Ejecutar suite enfocada, pruebas completas y comprobaciones PostgreSQL exclusivamente sobre una base local aislada. Ningún test de integración debe usar una URL no verificada.
8. Comparar estado final de Git y registrar cambios sin commit.

La corrección del fingerprint es independiente del cambio de login/logout. La migración requiere confirmar identidad y estado del esquema antes de aplicarse. La actualización de las pruebas depende de los contratos ya corregidos.

## Riesgos y compatibilidad

- **Migración:** no modificar la revisión ya aplicada. Antes de `upgrade`, comprobar host local, nombre exacto de base y revisión Alembic; cancelar si la identidad no coincide con `atletismo_demo` o no puede determinarse. No borrar tabla ni datos.
- **CSRF en login:** navegador debe aceptar la cookie anónima en el GET inicial y devolverla en el POST; las pruebas deben cubrir `TestClient` y el formulario real. No añadir `SameSite=None`.
- **Logout:** cambiar enlaces a formularios POST puede requerir retoques de estilos, sin alterar el destino ni el comportamiento de otros menús.
- **Sesiones existentes:** actualizar pruebas visuales no debe eliminar sesiones ni cambiar su propiedad; solo se deben borrar cuando exista el protocolo explícito actual.
- **Regresión:** la suite completa puede tener fallos ajenos a estos ocho; reportar cada resultado real sin modificar funcionalidad fuera de alcance.

## Criterios verificables de aceptación

- Cada campo principal participa en el fingerprint; un token previo a una edición exclusiva del principal produce 409 y no revierte el dato actual.
- Primer acceso anónimo sigue funcionando: GET login + token/cookie nuevos + POST válido inicia sesión.
- Login sin CSRF y con token inválido devuelve 403 y no autentica.
- Logout GET no modifica sesión; logout POST requiere CSRF y elimina la cookie solo tras token válido.
- La relación uno-a-uno sigue impidiendo dos principales por parte; modelo y migración coinciden y no conservan el índice redundante.
- Los ocho tests dejan de fallar por expectativas antiguas y cubren el contrato actual; la cobertura útil de sesiones individuales sigue presente.
- Suite completa verde o fallos restantes clasificados con evidencia; pruebas PostgreSQL ejecutadas solo en una base aislada verificada.
- No hay cambios a producción, bases compartidas, datos, commits, pushes ni despliegues.

**Estado:** plan preparado; no se implementó nada. Se espera autorización expresa para pasar a Code.