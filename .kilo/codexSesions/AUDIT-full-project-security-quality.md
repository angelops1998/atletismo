# Auditoría integral de seguridad y calidad — Atletismo Web

**Fecha:** 15 de noviembre de 2026  
**Repositorio auditado:** `C:\Archivos.Diego\atletismoWeb\atletismo`  
**Rama:** `Baruc+Kilo`  
**HEAD:** `2a448f71e5b9ddbade9cece7336692bb46fab051` (`codex commit 7`)  
**Modo:** auditoría de lectura; no se modificó código ni configuración.

## 1. Resumen ejecutivo

El repositorio local está en la rama esperada, coincide con `origin/Baruc+Kilo` y estaba limpio antes de ejecutar la auditoría. La implementación del registro estructurado del entrenamiento principal existe en modelo, servicio, router y plantilla. La suite completa da **469 PASS, 8 FAIL y 5 SKIP**. Los ocho fallos reproducen expectativas de la interfaz antigua de sesiones individuales que se retiró; no prueban por sí solos una regresión de la funcionalidad nueva. Sin embargo, la suite queda roja y esos tests deben actualizarse para que la validación automatizada refleje el producto vigente.

Se identificó un defecto de integridad **MEDIO**: el fingerprint usado por el token de edición del parte diario omite los campos de `EntrenamientoPrincipal`. Por eso, un cambio concurrente exclusivamente en esa estructura no invalida el token y puede ser sobrescrito. También se identificó una exención CSRF en el POST de login (**MEDIO**) y defectos menores de logout y de duplicación de índice.

**Evaluación:** se puede continuar el desarrollo local. No recomiendo integrar o desplegar antes de corregir la huella de concurrencia y dejar la suite de regresión alineada y verde. No se validó una conexión PostgreSQL real ni el despliegue de Render/Supabase.

## 2. Estado del repositorio

| Comprobación | Resultado |
|---|---|
| Rama | `Baruc+Kilo` |
| HEAD | `2a448f71e5b9ddbade9cece7336692bb46fab051` |
| Upstream | `origin/Baruc+Kilo` |
| Divergencia | 0 commits adelante, 0 atrás |
| Árbol antes de pytest | Limpio (`git status --short` sin salida) |
| Árbol al terminar | Sin cambios rastreados ni otros archivos; se agrega únicamente este informe |
| Commit/push/merge/deploy | No realizados |

La revisión se hizo sobre el código local en ese commit, no sobre una suposición del estado remoto. Los informes previos en `.kilo/codexSesions/` fueron consultados para entender el antecedente de las ocho pruebas fallidas.

## 3. Resumen de hallazgos

| Severidad | Cantidad |
|---|---:|
| CRÍTICO | 0 |
| ALTO | 0 |
| MEDIO | 2 |
| BAJO | 2 |
| INFORMATIVO | 3 |

## 4. Hallazgos

### AUD-001 — MEDIO — El token de edición no cubre el entrenamiento principal

**Ubicación:** `app/services/parte_diaria.py:285-287`; `app/services/parte_diaria.py:207-239`; `app/services/parte_diaria_tokens.py:155-188`.

`serialize_parte()` devuelve todos los campos de `entrenamiento_principal`, pero `current_fingerprint()` llama a `record_state_fingerprint()` y esta función solo normaliza los campos del parte, `entreno_hoy` y las sesiones individuales. La estructura principal no participa en el hash.

**Escenario:** dos formularios cargan el mismo token; una petición cambia series/distancia/descansos y otra envía el token anterior. Si no cambió ningún otro campo que sí entra al fingerprint, la segunda edición puede pasar la verificación y reemplazar la estructura más reciente sin responder 409.

**Impacto:** pérdida silenciosa de una edición del entrenamiento principal por concurrencia; contradice el control de estado descrito por el servicio.

**Recomendación:** incluir la representación canónica completa del entrenamiento principal en el fingerprint y añadir una prueba de concurrencia/estado obsoleto que altere únicamente ese objeto.

### AUD-002 — MEDIO — El POST de inicio de sesión no aplica CSRF

**Ubicación:** `app/main.py:35-36`, `app/main.py:62`; `app/routers/auth.py:96-97`; el formulario incluye token en `app/templates/auth/login.html`.

El middleware excluye `/auth/login` de la validación CSRF. Aunque el formulario renderiza un token, el servidor no lo valida en ese endpoint. Un sitio externo puede enviar un formulario cross-site con credenciales controladas por el atacante; si la víctima lo abre, su navegador puede quedar conectado a esa cuenta controlada por el atacante (login CSRF).

**Impacto:** la víctima podría introducir datos de entrenamiento o información privada dentro de una cuenta que no controla.

**Recomendación:** proteger el POST de login con un mecanismo CSRF válido para la sesión anónima o una defensa equivalente (por ejemplo, validar origen y token asociado a una cookie pre-login). Añadir prueba HTTP que envíe el POST sin token/origen válido y espere rechazo.

### AUD-003 — BAJO — Logout modifica sesión mediante GET

**Ubicación:** `app/routers/auth.py:145-149`.

`GET /auth/logout` borra la cookie de autenticación. Los GET pueden dispararse desde enlaces, prefetch o contenido cross-site; además, el método no pasa por el middleware CSRF, que solo protege POST/PUT/PATCH/DELETE.

**Impacto:** un tercero puede forzar el cierre de sesión. No se observó revocación de token del lado servidor; el efecto principal es borrar la cookie del navegador que hizo la petición.

**Recomendación:** convertir el cierre de sesión en POST protegido por CSRF y conservar GET únicamente como página informativa si se necesita.

### AUD-004 — BAJO — Restricción e índice único duplican la unicidad

**Ubicación:** `app/models/entrenamiento_principal.py:18`; `alembic/versions/b67a104e9c32_estructura_parte_principal.py:21,37`.

El modelo configura `unique=True, index=True`; la migración crea `parte_diaria_id` con `unique=True` y además crea explícitamente un índice único sobre la misma columna. En PostgreSQL la restricción única ya crea un índice de soporte, por lo que el índice adicional duplica almacenamiento y mantenimiento de escrituras.

**Impacto:** coste innecesario de esquema y posible diferencia entre metadata y migración.

**Recomendación:** elegir una sola forma de imponer unicidad y comprobar equivalencia con `alembic check` en una base PostgreSQL desechable.

### AUD-005 — INFORMATIVO — El control de fuerza bruta es local a cada proceso

**Ubicación:** `app/routers/auth.py:24-28,60-78`; `render.yaml` configura dos workers.

Los intentos fallidos se guardan en un diccionario de proceso. Cada worker tiene contador separado y reiniciar un worker limpia su historial. El comentario del código ya reconoce este límite.

**Impacto:** el bloqueo por IP/usuario es una mitigación básica, no un límite global persistente frente a ataques distribuidos o a múltiples workers. No se confirmó una explotación ni una exposición de credenciales.

**Recomendación:** si el riesgo o volumen crece, mover la cuota a un almacén compartido con expiración y evaluar límites a nivel de proxy. Mantener mensajes de error genéricos.

### AUD-006 — INFORMATIVO — Validación de dependencias con CVE no disponible

**Ubicación:** `requirements-prod.txt`.

Las dependencias de producción están fijadas a versiones concretas. `.venv\Scripts\python.exe -m pip check` informó `No broken requirements found`. La herramienta `pip-audit` no está instalada (`No module named pip_audit`), por lo que no se consultó una base de avisos de vulnerabilidad. `bandit` tampoco está instalado. No se instalaron herramientas ni dependencias durante esta auditoría.

**Impacto:** no es posible afirmar que el conjunto esté libre de vulnerabilidades conocidas. La comprobación de compatibilidad de dependencias no equivale a una auditoría CVE.

**Recomendación:** ejecutar `pip-audit -r requirements-prod.txt` en un entorno de auditoría autorizado y conservar el resultado con fecha; añadir un escaneo automatizado al flujo de integración.

### AUD-007 — INFORMATIVO — No se validó PostgreSQL real ni configuración efectiva del despliegue

**Ubicación:** `tests/conftest.py:1-7`; `tests/test_parte_diaria_concurrency_pg.py`; `render.yaml:19,44-58`.

La suite normal fija `DATABASE_URL=sqlite://` y declara que no usa red ni PostgreSQL. Cinco pruebas quedaron omitidas; corresponden al bloque que requiere PostgreSQL. `render.yaml` declara `branch: main`, mientras la rama auditada es `Baruc+Kilo`; eso puede ser una decisión deliberada, pero no se inspeccionó el panel ni el entorno efectivo de Render/Supabase. No se consultaron `.env`, secretos ni una base compartida.

**Impacto:** migración/constraints PostgreSQL, bloqueo `FOR UPDATE`, transacciones reales, TLS, variables efectivas y compatibilidad del despliegue permanecen sin confirmar.

**Recomendación:** usar una instancia PostgreSQL de pruebas aislada y desechable para probar `upgrade`, round-trip, constraints y concurrencia; confirmar aparte qué rama y variables tiene configuradas el servicio de despliegue, sin revelar valores secretos.

## 5. Estado por módulo

| Área | Estado observado | Límite de auditoría |
|---|---|---|
| Autenticación y sesiones | JWT en cookie `HttpOnly`, expiración, renovación deslizante, huella derivada de contraseña, desactivación y cambio obligatorio de contraseña implementados. | Hallazgos AUD-002/003; no se probó contra un navegador real ni un proxy. |
| Roles y aislamiento | Routers de profesor consultan `get_current_profesor`; `/parte` y vistas personales se vinculan al ID del usuario autenticado. Tests cubren permisos básicos. | No se hizo fuzzing exhaustivo de todos los IDs/roles. |
| CSRF y cabeceras | Middleware verifica métodos de escritura; cookie CSRF `HttpOnly`/`SameSite=Strict`; CSP, `nosniff`, `frame-ancestors` y `Referrer-Policy`. | Login está exento; logout usa GET. HSTS depende de la capa TLS externa y no se verificó. |
| XSS / SQL injection / redirecciones | Jinja2 renderiza plantillas HTML con escape automático; no se hallaron usos de `|safe`, `eval` o SQL dinámico en las búsquedas realizadas; las consultas inspeccionadas usan SQLAlchemy parametrizado. `ruta_interna` filtra destinos tras login. | Inspección estática dirigida, no análisis formal ni escaneo dinámico. |
| Usuarios y atletas | Alta/edición/ficha/estado/reset de contraseña existen; operaciones administrativas requieren rol profesor; contraseñas se hashean con bcrypt. | La política de longitud mínima no está centralizada para todas las operaciones; se crea contraseña provisoria y se fuerza cambio. |
| Parte diario y semanal | Coexisten `ParteDiaria` y `ParteSemanal`; unicidad por atleta/fecha y validaciones de bienestar. El parte semanal sigue alimentando varias pantallas históricas. | La coexistencia implica dos modelos temporales; no se validó migración sobre PostgreSQL. |
| Entrenamiento | `EntrenamientoPrincipal` separado de sesiones individuales, relación uno-a-uno con cascada ORM/FK; formulario estructurado y validación servidor para tipo, cantidades y tiempos; tiempos se almacenan en segundos. | AUD-001; pruebas específicas de metadata/migración del modelo principal son insuficientes y no hubo validación PostgreSQL. |
| Bienestar, cargas y alertas | Servicios de bienestar, carga derivada de sesiones, alertas individuales/de club y reportes están implementados. | Las cargas agregadas observadas se basan en sesiones individuales, no en el plan principal; no se verificó su semántica con usuarios. |
| Marcas y pruebas deportivas | Registro de marcas, catálogo de pruebas, mejores marcas y tendencias implementados. | Solo comprobación automatizada local; sin evaluación funcional manual. |
| Asistencia | Registro por atleta/fecha con restricción única y autorización de profesor. | Sin PostgreSQL real ni prueba concurrente. |
| Pagos | Registro, borrado, unicidad por atleta/período y cálculo de deuda implementados. | No se probaron flujos con datos reales ni reglas contables externas. |
| Estadísticas | Router protegido por profesor y servicios de agregación/graficado presentes. | No se verificaron fórmulas con un conjunto de referencia del club. |
| Página pública | `/` y `/club` están implementadas y la suite contiene pruebas de landing. | No se comprobó contenido/links en navegador ni configuración real del dominio. |
| Infraestructura | Blueprint de Render define Python 3.12.13, migración en build, Gunicorn 2 workers, HTTPS_ONLY, SECRET_KEY generada y DB URL no versionada. | No se leyó configuración privada ni se verificó un deploy. AUD-007. |

## 6. Análisis individual de los ocho fallos de Commit 7

Ejecución actual: `.venv\Scripts\python.exe -m pytest -q`  
Resultado total: **469 passed, 8 failed, 5 skipped, 1 warning** en 78.90 s.

Los ocho casos concretos fallaron así:

| Prueba | Expectativa probada | Clasificación y evidencia |
|---|---|---|
| `tests/test_parte.py::TestCreacionYActualizacion::test_entreno_hoy_sin_sesiones_es_422` | Espera rechazo cuando `entreno_hoy=si` y no hay sesiones individuales. | **Expectativa antigua.** El formulario actual requiere `EntrenamientoPrincipal`; las sesiones individuales son otra entidad y no son requisito para describir el bloque principal. |
| `tests/test_parte.py::TestInputParsing::test_repeated_sessions_fields_se_preservan` | Espera que reaparezca el textarea `sessions` después de 422. | **Prueba obsoleta.** El textarea fue retirado de la interfaz; el HTML ya no tiene ese campo. |
| `tests/test_parte.py::TestInputParsing::test_repeated_sessions_fields_surviven_409` | Espera que el textarea esté presente y preserve campos enviados tras 409. | **Prueba obsoleta.** El control 409 sigue devolviendo conflicto, pero ese control UI dejó de existir. |
| `tests/test_parte.py::TestInputParsing::test_newline_sessions_textarea_survives_422` | Espera el textarea y restauración de texto multilínea. | **Prueba obsoleta.** Corresponde al parser/formulario delimitado por líneas eliminado. |
| `tests/test_parte.py::TestInputParsing::test_repeated_delete_ids_survive_422` | Espera el input para IDs de borrado tras 422. | **Prueba obsoleta.** La interfaz actual ya no presenta borrado de sesiones individuales. |
| `tests/test_parte.py::TestInputParsing::test_repeated_delete_ids_survive_409` | Espera el input de IDs tras 409. | **Prueba obsoleta.** Mismo contrato de UI eliminado; el 409 se devuelve. |
| `tests/test_parte.py::TestRenderizado::test_form_renderiza_campos_diarios_obligatorios` | Exige `name="sessions"` y `name="delete_session_ids"`. | **Expectativa antigua.** La plantilla actual contiene los campos estructurados del principal y excluye expresamente esos controles obsoletos. |
| `tests/test_parte_diaria_service.py::TestServiceCRUD::test_entreno_hoy_true_requires_session_and_saves_multi` | Espera que el servicio rechace entrenamiento sin sesión individual. | **Expectativa antigua.** El payload de la prueba contiene la estructura principal válida; ya no debe requerirse una `SesionEntrenamiento` para marcar entrenamiento principal. |

No hay evidencia en estos ocho resultados de que las sesiones individuales legítimas se borren por el simple hecho de retirar esos elementos visuales. Sí constituyen una suite desactualizada que debe revisarse: mantener pruebas de CRUD/propiedad/descarte de sesiones donde la lógica siga soportándolas, y sustituir pruebas de UI/validación por casos del formulario principal.

## 7. Pruebas y comprobaciones realizadas

| Estado | Comando/procedimiento | Resultado |
|---|---|---|
| PASS | `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, `git log -5 --oneline --decorate` | Rama y commit indicados; upstream alineado; árbol limpio al inicio. |
| PASS | `.venv\Scripts\python.exe -m pytest -q` | 469 aprobadas, 8 fallidas, 5 omitidas, 1 warning. Fallos listados en sección 6. |
| PASS | AST sin escritura: parseo de `app/**/*.py` en UTF-8-SIG | 37 archivos Python parseados correctamente. |
| PASS | `.venv\Scripts\python.exe -m pip check` | `No broken requirements found.` |
| NOT RUN | `.venv\Scripts\python.exe -m pip_audit -r requirements-prod.txt` | No disponible: módulo `pip_audit` no instalado. No se instalaron paquetes. |
| NOT RUN | `.venv\Scripts\python.exe -m bandit --version` | No disponible: módulo `bandit` no instalado. |
| SKIP | Cinco pruebas PostgreSQL de la suite | Requieren URL PostgreSQL explícita; no se habilitaron para evitar escrituras o crear infraestructura fuera de una base aislada autorizada para este modo de solo lectura. |
| NOT TESTED | `alembic upgrade/current/check` en PostgreSQL | No ejecutados; una migración podría modificar el esquema. |
| NOT TESTED | Persistencia/constraints en PostgreSQL, migración downgrade, concurrencia real | Requieren una base PostgreSQL de pruebas y operaciones de escritura. |
| NOT TESTED | Login manual y flujos de los módulos en navegador | No se ejecutó navegador ni prueba manual de interfaz. |
| NOT TESTED | Render, Supabase, secretos/configuración efectiva, logs de despliegue | No se consultaron servicios ni archivos de secretos. |
| PASS | Estado Git final | No hay cambios de código ni modificaciones rastreadas. El único archivo nuevo es este informe autorizado. |

La advertencia de pytest fue `StarletteDeprecationWarning`: `httpx` con `starlette.testclient` está deprecado y se recomienda `httpx2`. No bloqueó la ejecución.

## 8. Riesgos de integridad y persistencia

- La tabla `entrenamientos_principales` tiene FK con `ON DELETE CASCADE`, cantidades positivas, tipo restringido y checks de rangos; `ParteDiaria` declara relación ORM `uselist=False` y `delete-orphan`.
- La garantía de uno-a-uno descansa en unicidad de `parte_diaria_id`; la definición de migración duplica el índice único (AUD-004).
- Los intervalos son `Integer` en segundos y las restricciones de dominio se aplican en servicio. La base limita no-negatividad y orden de intervalos, pero no refleja el tope de 86400 segundos impuesto por servicio. No se comprobó si ese tope debe ser idéntico en PostgreSQL.
- El token de edición sí incluye bienestar y sesiones individuales, pero no el principal (AUD-001).
- Los tests normales usan SQLite en memoria. La equivalencia de `CheckConstraint`, FK/cascade, arrays/JSON y DDL de Alembic en PostgreSQL queda pendiente.
- Existe coexistencia de parte semanal histórico y parte diario nuevo; se observaron comentarios de código que indican conservación del histórico. No se encontraron pruebas de migración PostgreSQL que prueben toda la transición.

## 9. Recomendaciones priorizadas

1. **Antes de integrar:** cubrir todos los campos de `EntrenamientoPrincipal` en el fingerprint y probar dos ediciones concurrentes donde solo cambie el principal.
2. **Antes de exponer login públicamente:** eliminar la exención CSRF del POST de login con un diseño compatible con usuario anónimo y añadir regresiones negativas.
3. **Antes de declarar la suite verde:** sustituir las ocho pruebas antiguas según el flujo vigente, sin borrar pruebas de autorización y descarte para sesiones legítimas.
4. Mover logout a POST con CSRF.
5. Corregir la definición redundante de unicidad en el modelo/migración y comparar metadata con el esquema migrado.
6. Ejecutar `pip-audit` y un análisis estático de seguridad en un entorno autorizado; fijar y revisar dependencias según los hallazgos.
7. Validar la migración y restricciones en PostgreSQL aislado, incluyendo el caso aeróbico, velocidad, edición, `No entrené`, rollback y concurrencia.
8. Confirmar rama y configuración real de Render, y revisar cookies seguras/HSTS/proxy en entorno desplegado sin imprimir secretos.

## 10. Evaluación final

- **¿Puede continuar el proyecto?** Sí, para desarrollo y revisión local.
- **¿Hay problemas antes de integrar o desplegar?** Sí. AUD-001 debe corregirse antes de confiar en la protección de concurrencia. AUD-002 debe resolverse antes de considerar robusta la seguridad del login. Las ocho pruebas fallidas deben actualizarse y la suite debe quedar verde antes de integrar.
- **¿Qué pruebas adicionales hacen falta?** Pruebas de concurrencia del principal, login CSRF, PostgreSQL aislado con upgrade/constraints/round-trip y autorización negativa en todos los módulos sensibles; luego una pasada de navegador con roles profesor/atleta.
- **¿Qué no pudo verificarse?** PostgreSQL real, estado aplicado de Alembic, persistencia en servidor, Render/Supabase, vulnerabilidades CVE mediante auditor, pruebas de navegador y configuración efectiva de producción.

**No se implementaron correcciones.** Este informe registra evidencia y recomendaciones para revisión y autorización del usuario.