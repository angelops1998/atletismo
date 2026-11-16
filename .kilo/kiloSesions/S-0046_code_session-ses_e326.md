# One-command local demo environment setup

**Session ID:** ses_e3263162fffecs4s10fwaxSYwC
**Created:** 11/11/2026, 10:36:15 PM
**Updated:** 11/11/2026, 10:55:22 PM

---

## User

# ATLETISMO WEB — ONE-COMMAND LOCAL DEMO ENVIRONMENT

## SESSION CONFIGURATION

- **Mode:** Code.
- **New Session:** YES.
- **Task:** CREATE.
- **Repository:** https://github.com/angelops1998/atletismo
- **Target branch:** `Baruc+Kilo`.
- **Local workspace:** `C:\Archivos.Diego\atletismoWeb\atletismo`
- **Primary objective:** Implement a safe, isolated, repeatable local demonstration environment started with one PowerShell command.

## 1. EXECUTION RULES

You are authorized to inspect, implement, and test the local demo environment within the scope below.

Before editing:

1. Verify the workspace root and repository identity.
2. Inspect the current Git branch and working tree.
3. Identify all pre-existing modified, staged, and untracked files.
4. Preserve every existing user modification.
5. Inspect the actual application architecture and current database schema.
6. Identify the current Alembic migration head.

Do not discard, overwrite, reset, or revert existing work.

Do not commit, push, merge, create PRs, or deploy.

Treat the repository implementation as the source of truth. Do not assume that the supplied paths, model fields, roles, or authentication behavior are unchanged.

## 2. DATABASE SAFETY — CRITICAL

The application currently uses PostgreSQL, SQLAlchemy, Alembic, and PostgreSQL-specific concurrency behavior.

The owner has XAMPP enabled. XAMPP's MariaDB/MySQL service must not be treated as a PostgreSQL replacement.

Inspect the actual available database infrastructure.

Preferred order:

1. Existing usable local PostgreSQL installation.
2. Docker with an operational engine, using an isolated PostgreSQL container.
3. If neither is available, implement the necessary scripts but report the missing prerequisite and provide a safe setup recommendation.

Do not install system-wide services or change Windows services without authorization.

Mandatory restrictions:

- Never connect to Supabase.
- Never connect to production.
- Never change the application's database engine.
- Never modify production configuration.
- Never reuse an unidentified database.
- Never execute destructive SQL against an unidentified database.

Use a dedicated database named `atletismo_demo` or another clearly identifiable dedicated demo database.

Before migrations or seeding:

- Parse and validate the effective database URL.
- Verify the database engine is PostgreSQL.
- Verify the database name matches the dedicated demo database.
- Verify the connection target belongs to the approved local PostgreSQL instance or isolated demo container.
- Reject production hosts, Supabase hosts, unexpected database names, and unsupported connection targets.
- Display the verified database identity and connection target before proceeding.

If identity cannot be positively established, stop immediately.

## 3. INITIAL INSPECTION

Inspect these paths when they exist:

- `README.md`
- `.env.example`
- `app/config.py`
- `app/database.py`
- `app/main.py`
- `run.py`
- `scripts/crear_profesor.py`
- `scripts/seed.py`
- `app/models/`
- `app/services/parte_diaria.py`
- `app/routers/parte.py`
- `tests/conftest.py`
- Alembic configuration and migration files.
- Authentication and authorization modules.
- Existing requirements or dependency manifests.

Also inspect:

- Python version requirements.
- Existing virtual environment conventions.
- How settings and environment variables are loaded.
- Password hashing implementation.
- Account creation and role validation.
- Current daily-report schema.
- Attendance, marks, payments, and outstanding-balance models.
- Foreign keys and required relationships.
- Current test database isolation strategy.

Identify whether the existing demo or seed infrastructure can be reused safely.

Do not reuse destructive workflows.

Specifically, inspect `scripts/seed.py`, but NEVER execute `scripts/seed.py --borrar`.

## 4. IMPLEMENTATION — ONE-COMMAND STARTUP

Create a Windows PowerShell startup script, preferably:

`scripts/iniciar_demo.ps1`

The intended user experience is:

```powershell
.\scripts\iniciar_demo.ps1
```

The script must:

1. Verify the repository root.
2. Check the current Python installation.
3. Locate or create the project's virtual environment following repository conventions.
4. Verify dependencies and install missing project dependencies only when necessary.
5. Detect a usable local PostgreSQL server or supported Docker environment.
6. Initialize or reuse the isolated demo PostgreSQL database.
7. Configure the demo connection without overwriting `.env`.
8. Generate a local development secret when required.
9. Run `alembic upgrade head`.
10. Execute an idempotent demo-data initializer.
11. Start the FastAPI application on `127.0.0.1:8002`.
12. Print the demo credentials and useful application URLs.

Use process-scoped environment variables wherever practical.

Do not persist credentials or secrets unnecessarily.

Do not expose database passwords or application secrets in console output.

If a dedicated Docker container is needed:

- Use a stable container name.
- Use a dedicated volume.
- Bind PostgreSQL to localhost only.
- Avoid exposing the database to external interfaces.
- Reuse an existing verified demo container.
- Never remove unrelated containers or volumes.
- Never automatically destroy existing demo data.

If an existing PostgreSQL installation requires credentials, use a secure, non-logging input mechanism.

Do not assume administrator privileges.

### Repeatability

Repeated execution must:

- Avoid duplicate users.
- Avoid duplicate athletes.
- Avoid duplicate payments.
- Avoid duplicate attendance records.
- Avoid duplicate marks.
- Avoid duplicate daily reports and sessions.
- Preserve unrelated records.
- Update only records explicitly owned by the demo initializer.

Implement explicit demo ownership, preferably through a stable marker or dedicated demo account identifiers, using the current schema and existing abstractions.

Do not identify ownership by broad assumptions such as usernames alone if the implementation can provide a stronger ownership mechanism.

## 5. DEMO ACCOUNTS

Create the following local-only accounts.

### Professor

- Username: `demo_profesor`
- Password: `DemoProfe2026!`
- Role: `profesor`

### Athletes

- `demo_atleta1`
- `demo_atleta2`
- `demo_atleta3`

Shared password:

`DemoAtleta2026!`

Requirements:

- Use the application's actual password hashing mechanism.
- Use valid model fields and existing role values.
- Inspect the authentication flow before creating accounts.
- Mark demo accounts clearly using supported fields or a safe dedicated mechanism.
- Make initialization idempotent.
- Do not modify unrelated accounts.
- Do not introduce invented application roles.
- Do not weaken authentication globally.
- Do not expose demo credentials outside local demo documentation and startup output.

Inspect whether the application requires password changes at first login.

If necessary, use an existing supported demo-only setting. Otherwise preserve the current authentication contract and explain any usability limitation.

## 6. DEMO DATASET

Create realistic but fictional data sufficient to demonstrate the existing application.

The dataset should cover:

- Professor dashboard.
- Athlete list.
- Athlete details.
- Attendance.
- Marks.
- Payments.
- Outstanding balances.
- Daily training reports.
- Multiple training sessions per day.
- Wellness values.
- Reported discomfort.
- Symptoms.

For daily tracking, include:

1. One athlete with a completed daily report and multiple sessions.
2. One athlete with a report indicating no training.
3. One athlete reporting discomfort.
4. One athlete reporting symptoms.
5. One athlete without a report for the current day.

Use the actual daily-tracking schema and services.

Inspect `app/services/parte_diaria.py` and `app/routers/parte.py` before designing the dataset.

Determine valid enums, limits, relationships, and business rules from the implementation.

Do not invent values that violate application validation.

Use the current local date consistently when generating current-day examples.

Make sample data useful for the current professor and athlete interfaces.

Use a dedicated initializer, for example:

`scripts/seed_demo.py`

Choose the actual implementation location based on repository conventions.

Do not modify the existing weekly seed workflow.

## 7. DATA ISOLATION AND RESET

The demo environment must remain isolated from production.

Prefer:

- Dedicated PostgreSQL database.
- Dedicated database URL.
- Dedicated demo environment configuration.
- Explicit demo-owned records.
- Process-scoped environment variables.

Do not modify `.env`, `.env.example`, production configuration, or deployment settings unless strictly necessary and explicitly justified.

If implementing a reset operation, it must:

- Require an explicit confirmation argument.
- Validate the exact demo database identity again.
- Affect only explicitly demo-owned records.
- Never delete unrelated records.
- Never drop an unidentified database.
- Never run automatically during startup.

If a safe reset cannot be guaranteed, do not implement it.

## 8. DOCUMENTATION

Create a concise guide, preferably:

`docs/DEMO_LOCAL.md`

Document:

- Requirements.
- PostgreSQL and Docker alternatives.
- First-time setup.
- One-command startup.
- Local application URL.
- Demo account credentials.
- Available roles.
- Useful application routes.
- How to stop the application.
- How to restart it.
- How to safely reset demo data, if implemented.
- How database isolation works.
- Common setup errors and their resolution.

Make clear that XAMPP MySQL/MariaDB is not the application's PostgreSQL database.

Do not document unsafe manual SQL deletion as a normal reset procedure.

## 9. VALIDATION

Perform the checks supported by the available environment.

### Static checks

- PowerShell script syntax.
- Python syntax.
- Import checks.
- Dependency compatibility.

### Database checks

- PostgreSQL connection.
- Verified database identity.
- Alembic migration reaches current head.
- Demo accounts are created correctly.
- Password hashes are valid.
- Demo records satisfy foreign keys and constraints.

### Idempotency

Run the initializer twice.

Compare relevant record counts and identifiers.

Verify that the second execution creates no duplicate accounts or sample records.

### Authentication and application checks

Verify:

- Professor login.
- Athlete login.
- Role-based redirects.
- Authorization restrictions.
- `/`
- `/club`
- `/auth/login`
- `/panel`
- `/parte`

Verify that the relevant endpoints return the expected results for their supported roles.

Inspect daily reports and associated training sessions.

### Regression

Run the existing automated test suite using repository conventions.

Compare failures against the initial repository state where possible.

Do not modify unrelated tests to make the demo implementation pass.

Do not claim browser verification unless an actual browser was used.

Distinguish:

- PASS
- FAIL
- BLOCKED
- NOT RUN

A successful build alone does not establish functional correctness.

## 10. STRICT SCOPE

Prefer isolated scripts and documentation.

Only modify existing application code if absolutely necessary.

Do not modify:

- Daily tracking business rules.
- Global authentication security.
- Production database configuration.
- Historical migrations.
- Weekly data consumers.
- Phase 5 functionality.
- Production deployment configuration.
- Unrelated tests or modules.

Explain and justify every necessary application-code modification.

## 11. FINAL REPORT

Provide:

1. Initial Git branch and working-tree state.
2. Files created and modified.
3. PostgreSQL installation or Docker environment detected.
4. Database identity and isolation mechanism.
5. Exact startup command.
6. Demo accounts and passwords.
7. Sample records created.
8. Idempotency verification results.
9. Migration status.
10. Authentication and endpoint validation.
11. Automated test results.
12. Browser verification performed or pending.
13. Remaining prerequisites and limitations.
14. Any changes outside the originally requested scope.

For every validation, report the actual command and result.

Never claim a test passed unless it was executed successfully.

## FINAL ACCEPTANCE CRITERIA

The implementation is acceptable when:

- The owner can start the application with one PowerShell command.
- No manual account creation or SQL population is necessary.
- The application uses isolated PostgreSQL.
- Production and Supabase are never accessed.
- Demo accounts authenticate using the real authentication system.
- Sample data demonstrates the current application features.
- Repeated startup does not duplicate demo records.
- Existing user data and configuration remain untouched.
- Existing application tests remain compatible.
- Setup limitations are explicitly documented.

Begin with repository inspection. Implement only after verifying the current architecture and preserving all pre-existing changes.

---

## Assistant

I'll start by inspecting the repository structure and current state.


**Tool: bash**

**Tool: bash**

**Tool: bash**

---

## Assistant

Workspace is clean on branch `Baruc+Kilo`. Let me inspect the project structure and key files.


**Tool: read**

**Tool: bash**

---

## Assistant

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Now let me inspect the app structure, config, database, and key modules.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me look at the models, scripts, and remaining key files.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Now let me inspect the daily tracking models and the remaining models.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Now let me look at the services and routers for parte_diaria and related.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me inspect the routers and migrations to understand auth flows and schema.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me look at the alembic migrations and the services for cobranza, bienestar, pruebas, bienestar.


**Tool: bash**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me look at the alembic migration versions and check remaining infrastructure.


**Tool: glob**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me read the migration files to understand the schema head.


**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Now let me check the environment: Python, venv, PostgreSQL, Docker availability.


**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: read**

**Tool: read**

---

## Assistant

PowerShell aliases `ls` differently. Let me use proper commands.


**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: read**

---

## Assistant

Let me check Docker daemon status, the venv Python, and installed packages.


**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: read**

---

## Assistant

I now have a complete picture. Let me set up a todo list and check if Docker can be started.


**Tool: todowrite**

---

## Assistant

**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

Docker Desktop is installed. Let me try to start it so we can run an isolated PostgreSQL container.


**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

Docker daemon isn't up yet. Let me wait longer for Docker Desktop to initialize.


**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

Docker Desktop didn't start headlessly (likely needs interactive setup). Let me try launching it visibly once.


**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

Docker processes are running but the daemon isn't ready yet. Let me wait for initialization to complete.


**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

Docker Desktop processes are running but the daemon API still isn't responding (likely waiting on interactive WSL2 setup). I've made a genuine effort to start Docker. I'll proceed with implementation — the script will auto-detect Docker/PostgreSQL, and I'll retry Docker during validation. Let me update todos and create the demo seed script.


**Tool: todowrite**

---

## Assistant

**Tool: write**

---

## Assistant

Let me clean up the awkward `__import__("random")` by adding a proper import.


**Tool: edit**

---

## Assistant

**Tool: edit**

---

## Assistant

Now let me verify the Python syntax of seed_demo.py.


**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

seed_demo.py syntax is valid. Now let me create the PowerShell startup script.


**Tool: write**

---

## Assistant

Let me refine the PowerShell script — set working directory to repo root and read DATABASE_URL from env (not embedded in command line) for robustness.


**Tool: write**

---

## Assistant

Let me validate the PowerShell script syntax.


**Tool: bash**

---

## Assistant

There's a PowerShell parse error: `$pgHostPort:5432` and `$host:$port` are interpreted as scope-qualified variable references. Let me rewrite the connection-string construction using concatenation to avoid `$var:` patterns.


**Tool: write**

---

## Assistant

**Tool: bash**

---

## Assistant

PowerShell syntax is valid. Let me check Docker status again before writing docs and proceeding to validation.


**Tool: bash**

---

## Assistant

Docker daemon still isn't responding. Let me check whether it's still initializing and try once more.


**Tool: bash**

---

## Assistant

Docker Desktop processes are running but the daemon API isn't responding (stuck on first-run/WSL2 initialization). I've made a genuine effort (launched Docker, waited several minutes). Per the rules, I'll implement everything and report the missing prerequisite clearly. Let me write the documentation now.


**Tool: todowrite**

---

## Assistant

**Tool: write**

---

## Assistant

Now let me run validation. First, the existing test suite (SQLite, doesn't need PostgreSQL) and import checks.


**Tool: todowrite**

---

## Assistant

**Tool: bash**

---

## Assistant

Imports pass. Now let me run the existing test suite.


**Tool: bash**

---

## Assistant

Test suite: **413 passed, 5 skipped, 0 failed** (the 5 skips are PostgreSQL-concurrency tests that skip without PG). Let me verify alembic head statically and confirm `.env` was not touched.


**Tool: bash**

---

## Assistant

Alembic head is `c4b8e2d91f07` with a clean linear chain. Let me confirm `.env` was not created and review git status.


**Tool: bash**

---

## Assistant

Only my new files are untracked; `.env` not created; existing work untouched. Let me make one more attempt at Docker (it's been several minutes since launch).


**Tool: bash**

---

## Assistant

Docker daemon remains unresponsive after ~10 minutes (stuck on initialization). I'll stop attempting and report it as a prerequisite limitation. Let me do a functional smoke test of the key endpoints on SQLite (supported in this environment) to validate auth/routing behavior.


**Tool: bash**

---

## Assistant

Nested quotes are problematic in PowerShell. Let me write the smoke test to a temp file instead.


**Tool: write**

---

## Assistant

**Tool: edit**

---

## Assistant

**Tool: bash**

---

## Assistant

`StaticPool` is in `sqlalchemy.pool` in SQLAlchemy 2.0. Let me fix and rerun.


**Tool: edit**

---

## Assistant

**Tool: bash**

---

## Assistant

Excellent! All endpoint checks pass with expected results:
- `GET /` (anon): 200 landing
- `GET /club`: 200
- `GET /auth/login`: 200
- Profesor login → `/panel`: 200; profesor `/parte`: **403** (role restriction works)
- Atleta login → `/inicio`: 200; atleta `/parte`: 200
- `GET /` authenticated: 200 (role-based redirect)

Auth mechanism, role-based redirects, and authorization restrictions are verified. Let me clean up the temp file and finalize.


**Tool: bash**

---

## Assistant

**Tool: todowrite**

---

## Assistant

## Informe de implementación — Entorno de demo local (atletismo)

### 1. Estado inicial de Git
- Rama: `Baruc+Kilo` (actualizada con `origin/Baruc+Kilo`)
- Árbol de trabajo: limpio, sin modificaciones preexistentes que preservar (no hubo cambios de usuario que descartar).

### 2. Archivos creados y modificados
- **Creados:** `scripts/seed_demo.py`, `scripts/iniciar_demo.ps1`, `docs/DEMO_LOCAL.md`
- **Modificados:** ninguno (no se tocó código de aplicación existente)

### 3. Infraestructura de base de datos detectada
- **PostgreSQL local:** no instalado (no hay `psql`, `pg_ctl`, `createdb` ni servicio de PostgreSQL).
- **Docker:** Docker Desktop 29.9.2 instalado; se lanzó el ejecutable, pero tras ~10 min de espera la API del daemon aún no responde (pipe `dockerDesktopLinuxEngine` no disponible — probablemente configuración de primera ejecución de WSL2 pendiente). No se pudo usar para validación real.
- **XAMPP:** presente, pero es MariaDB/MySQL; **no es la base de esta app** (PostgreSQL) y no se usó.

### 4. Identidad y aislamiento de la base de datos
- Base dedicada: `atletismo_demo`
- URL dedicada inyectada solo como variable de entorno del **proceso** (`DATABASE_URL`), nunca escrita en `.env` ni `.env.example`
- `app/config.py` lee `DATABASE_URL` del entorno (sobrescribe cualquier `.env`), por lo que el `.env` del usuario queda intacto (se confirmó: no existe `.env`)
- Guard de seguridad `_es_entorno_demo()` en `seed_demo.py`: rechaza cualquier base que no sea `atletismo_demo` en `localhost`/`127.0.0.1` antes de escribir
- Docker (cuando el motor esté disponible): contenedor `atletismo-demo-db`, volumen `atletismo-demo-pgdata`, publicado solo en `127.0.0.1:5433`, reutilizable, sin eliminar contenedores/volúmenes ajenos, sin destruir datos demo automáticamente
- Titularidad demo: dominio de email dedicado `@atletismo.demo.local` + nombres de usuario estables (doble chequeo, nunca solo por username)

### 5. Comando de arranque exacto
Desde la raíz del repositorio:
```powershell
.\scripts\iniciar_demo.ps1
```

### 6. Cuentas de demostración (contraseñas hasheadas con `app.auth.hash_password` / bcrypt)
| Rol | Usuario | Contraseña | `debe_cambiar_password` |
|-----|---------|------------|-------------------------|
| Profesor | `demo_profesor` | `DemoProfe2026!` | false |
| Atleta | `demo_atleta1` | `DemoAtleta2026!` | false |
| Atleta | `demo_atleta2` | `DemoAtleta2026!` | false |
| Atleta | `demo_atleta3` | `DemoAtleta2026!` | false |

Contraseñas reales de demo, sin cambio forzado al entrar. Las credenciales se imprimen al arrancar; la contraseña de la DB y la `SECRET_KEY` nunca se imprimen ni persisten.

### 7. Muestra de datos (seed_demo.py, aún no ejecutada contra PG real)
- `parte_diarios` de hoy:
  1. `demo_atleta1`: parte completo, entrenó, **múltiples sesiones** (velocidad_sprint + fuerza) + **molestia** (rodillas, 6/10)
  2. `demo_atleta2`: parte sin entrenamiento (`entreno_hoy=false`)
  3. `demo_atleta3`: **sin parte hoy** (falta de reporte); reportó **síntomas** (fiebre y tos) ayer
- Partes semanales (4 semanas), marcas, asistencias (lun/mié/vie), pagos (`demo_atleta2` debe el mes en curso → deuda visible)

### 8. Idempotencia
- **Ejecución:** BLOCKED (requiere PostgreSQL para correr `seed_demo.py`)
- **Mecanismo:** `seed_demo.py` hace upsert de usuarios (username estable) y borra/sobreescribe solo registros de atletas demo (identificados por dominio de email) antes de recrear partes, marcas, asistencias, pagos. Re-ecutar no duplica cuentas ni registros. No se ejecuta borrado automático al arranque.

### 9. Estado de migraciones
- Cabezal estático verificado con `alembic heads`/`history`: **`c4b8e2d91f07`**, cadena lineal `base → d61e48816ec5 → a3f1c9e27b04 → c4b8e2d91f07 (head)`
- `alembic upgrade head` sobre `atletismo_demo`: **BLOCKED** (no hay PostgreSQL disponible)

### 10. Autenticación y endpoints
Validado con TestClient sobre SQLite (entorno disponible), creando las 4 cuentas demo con contraseñas hasheadas por la app:

| Endpoint | Resultado esperado | Resultado obtenido |
|----------|-------------------|--------------------|
| `GET /` (anon) | 200 landing | 200 ✓ |
| `GET /club` | 200 público | 200 ✓ |
| `GET /auth/login` | 200 | 200 ✓ |
| profesor login → `/panel` | 200 | 200 ✓ |
| profesor `GET /parte` | 403 (solo atletas) | 403 ✓ |
| atleta login → `/inicio` | 200 | 200 ✓ |
| atleta `GET /parte` | 200 | 200 ✓ |
| `GET /` autenticado | 200 (redirige por rol) | 200 ✓ |

Autenticación real, redirecciones por rol y restricciones de autorización verificadas. Login de las cuentas demo contra la app en ejecución sobre PG: **BLOCKED** (sin PG).

### 11. Pruebas automatizadas del repositorio
Comando: `.venv\Scripts\python.exe -m pytest`
Resultado: **413 passed, 5 skipped, 0 failed** (en 74.93s)
- Las 5 skipped son `test_parte_diaria_concurrency_pg.py`, que requieren PostgreSQL y saltan sin él.
- Ningún test modificado. Compatibilidad preservada.

### 12. Verificación por navegador
**NOT RUN** (no se usó navegador real; no se afirma verificación de browser).

### 13. Requisitos previos pendientes y limitaciones
- Se requiere una instalación local de PostgreSQL o Docker Desktop con el motor en ejecución para correr el demo completo. En esta sesión Docker Desktop se instaló/lanzó pero su daemon no respondió (bloqueado en inicialización). El script `iniciar_demo.ps1` está listo para usar Docker/PG en cuanto estén disponibles; de lo contrario informa el requisito faltante y la recomendación (instalar PostgreSQL local o iniciar Docker Desktop).
- La app escucha en `127.0.0.1:8002` (solo loopback).
- No se implementó un restablecimiento destructivo automático (no se garantizaba seguro); el restablecimiento es explícito: `python scripts/seed_demo.py --borrar-demo --confirmar-borrar-demo`, solo sobre registros demo, tras validar identidad de la base.

### 14. Cambios fuera del alcance solicitado
Ninguno. No se modificó código de aplicación, migraciones, reglas de negocio, autenticación global, configuración de producción, tests ni consumers semanales.

---

**Resumen:** El entorno de demo está implementado (`scripts/iniciar_demo.ps1`, `scripts/seed_demo.py`, `docs/DEMO_LOCAL.md`), con estática y tests del repositorio aprobados (413 passed, 0 failed). La validación contra PostgreSQL real (conexión, identidad, `alembic upgrade head`, creación de cuentas/datos, idempotencia ejecutada, login vs app en ejecución) queda **BLOCKED** hasta que esté disponible una instalación local de PostgreSQL o Docker con el motor operativo; el informe distingue claramente PASS / BLOCKED / NOT RUN y nunca afirma validaciones no realizadas.


**Tool: goal_report**

---

## Assistant

El entorno de demostración local está implementado. Resumen del trabajo:

## Archivos creados (sin modificar nada existente)
- `scripts/seed_demo.py` — inicializador idempotente de datos demo sobre `atletismo_demo`
- `scripts/iniciar_demo.ps1` — arranque de un comando (repo root, Python, venv `.venv`, dependencias, PostgreSQL/Docker, `alembic upgrade head`, seed, uvicorn en `127.0.0.1:8002`)
- `docs/DEMO_LOCAL.md` — guía de requisitos, arranque, cuentas, URLs, aislamiento y reset

## Cuentas demo (hash real con `app.auth.hash_password`/bcrypt, sin cambio forzado)
| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Profesor | `demo_profesor` | `DemoProfe2026!` |
| Atleta | `demo_atleta1` | `DemoAtleta2026!` |
| Atleta | `demo_atleta2` | `DemoAtleta2026!` |
| Atleta | `demo_atleta3` | `DemoAtleta2026!` |

Titularidad demo: dominio de email `@atletismo.demo.local` + usuarios estables (doble chequeo, nunca solo username).

## Validación realizada
- PowerShell `iniciar_demo.ps1`: sintaxis OK (parser de PowerShell)
- Python `seed_demo.py`: compila e importa; `DEMO_EMAIL_DOMAIN` y usuarios demo correctos
- Endpoints/auth sobre SQLite (TestClient): `/`, `/club`, `/auth/login`, profesor→`/panel` (200), profesor `/parte` (403), atleta→`/inicio` y `/parte` (200). Rol y autorización verificados.
- Suite del repositorio: `413 passed, 5 skipped, 0 failed` (5 skips = tests de concurrencia que requieren PG). Ningún test modificado.
- Alembic head estático: `c4b8e2d91f07` (cadena lineal limpia). `.env` no creado ni tocado; git working tree limpio salvo los 3 archivos nuevos.

## Queda BLOCKED (requiere PostgreSQL real, no disponible en esta sesión)
No hay PostgreSQL local instalado y Docker Desktop se lanzó pero su daemon no respondió tras ~10 min (inicialización de WSL2 pendiente). Por eso no se ejecutaron contra `atletismo_demo`: conexión + verificación de identidad, `alembic upgrade head`, creación de cuentas/datos demo, idempotencia ejecutada dos veces, y login contra la app en ejecución. XAMPP (MariaDB/MySQL) no se usó (la app es PostgreSQL).

El script `iniciar_demo.ps1` está listo para usarse en cuanto haya PostgreSQL local o Docker con el motor operativo; de lo contrario informa el requisito faltante y la recomendación de setup. Nunca toca `.env`, ni producción, ni Supabase.

---

