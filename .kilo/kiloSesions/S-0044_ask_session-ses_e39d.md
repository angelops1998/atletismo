# Daily Tracking Phase 4 acceptance test runbook

**Session ID:** ses_e39d72f95ffeYzdgIeuLsrFJPT
**Created:** 11/10/2026, 11:52:05 AM
**Updated:** 11/10/2026, 11:55:46 AM

---

## User

# DAILY TRACKING — PHASE 4 MANUAL ACCEPTANCE TEST RUNBOOK

## OBJECTIVE

Prepare a practical, reproducible manual browser acceptance-testing runbook for Phase 4 of the Daily Tracking implementation.

The repository owner will execute the tests personally using an installed browser. Kilo must investigate the actual repository implementation and document exact procedures, expected outcomes, and evidence requirements.

This is a READ-ONLY investigation. The deliverable must be provided in the final report, not written into the repository.

## PROJECT CONTEXT

Repository: atletismoWeb
Known local workspace:
`C:\Archivos.Diego\atletismoWeb\atletismo`

Verify the actual workspace root before relying on this path.

### Initial context

Inspect these files first:

- `.kilo/kiloSesions/S-0043_plan_session-ses_e39e.md`
- `.kilo/kiloSesions/S-0042_code_session-ses_e3c4.md`
- `.kilo/plans/1794275057816-phase4-ui-implementation-readiness.md`
- `app/routers/parte.py`
- `app/templates/atleta/parte.html`
- `tests/test_parte.py`
- `README.md`
- `run.py`

You may inspect additional files only when required to establish an actual dependency, authentication contract, database procedure, or test scenario.

### Established findings from S-0043

- Phase 4 remains BLOCKED.
- Interactive browser tooling is unavailable in the current Kilo environment.
- The local application was not started.
- No manual browser acceptance tests were executed.
- No repository changes were made.

Treat these as historical findings from S-0043, not as proof of the current repository state.

Do not repeat the previous investigation unnecessarily.

## INSPECTION

Perform a focused, read-only investigation.

### 1. Environment and startup

Identify:

- Exact local application startup procedure.
- Required Python version and dependencies.
- Virtual environment requirements.
- Required environment variables.
- Required local configuration.
- Database connection requirements.
- Safe database creation and initialization procedure.
- Required Alembic migration commands, if applicable.

Use actual README instructions, configuration files, scripts, and application initialization code.

Distinguish:
- Commands verified against repository documentation.
- Commands inferred from implementation.
- Commands requiring owner confirmation.

Never expose secrets, credentials, connection strings, or personal information.

Do not assume that a development database already exists.

### 2. Authentication and navigation

Trace:

- Athlete login route and authentication mechanism.
- Required athlete role and account state.
- Session or cookie requirements.
- CSRF requirements.
- Navigation procedure to `/parte`.
- Any prerequisites for accessing the daily form.

Document how the owner can obtain or create a safe test athlete account using existing supported functionality.

Never invent credentials.

### 3. Daily form contract

Inspect the actual template, router, schemas, validation logic, and relevant models.

Document:

- Every relevant form field.
- Required and optional fields.
- Default values.
- Accepted value ranges.
- Conditional wellness fields.
- Conditional discomfort fields.
- Conditional illness fields.
- Daily scale interpretation.
- Training session fields.
- Multiple-session behavior.
- Stable session identifiers.
- Session deletion and omission semantics.
- Save, discard, and cancellation behavior.

Do not infer UI behavior from backend tests alone.

### 4. HTTP 422 restoration

Trace the actual validation and form-state restoration implementation.

Identify:

- All three binary fields.
- Their actual names and accepted values.
- How submitted values are serialized.
- How the application restores values after HTTP 422.
- Whether restoration preserves the submitted value or falls back to an incorrect default.

Determine a safe way to reproduce HTTP 422 through existing application functionality.

Do not modify source code or invent invalid payloads without verifying the actual validation contract.

### 5. HTTP 409 conflict handling

Trace the actual concurrency and conflict-detection mechanism.

Determine:

- What conditions produce HTTP 409.
- Whether the application uses timestamps, versions, revisions, or another mechanism.
- What the user sees when a conflict occurs.
- Whether submitted changes are preserved.
- Whether a conflict requires refreshing or reloading the form.

Identify a reproducible two-browser-tab procedure using the existing implementation.

If the mechanism cannot be safely reproduced through the browser, document the limitation.

### 6. Test data preparation

Identify the minimum isolated test data required.

Prefer supported application workflows for creating test records.

If database-level preparation is necessary, provide exact SQL or migration-backed instructions only after verifying the schema and relationships.

Test records must:

- Belong exclusively to a test athlete.
- Be isolated from production data.
- Have clearly documented initial states.
- Avoid modifying existing real athlete records.
- Be identifiable for subsequent cleanup.

Never suggest running destructive SQL against an unverified database.

## DELIVERABLE

Produce an ordered manual acceptance-testing runbook in the final response.

The guide must be sufficiently precise that the repository owner can follow it without needing to inspect source code independently.

### Section 1 — Environment preparation

Include:

- Required software and versions.
- Workspace preparation.
- Virtual environment activation.
- Dependency verification.
- Environment variable preparation.
- Safe local database creation.
- Migration procedure.
- Test athlete creation.

Provide exact commands where verified.

Use placeholders for secret values rather than displaying actual credentials.

### Section 2 — Application startup

Document:

- Exact startup command.
- Expected successful startup indicators.
- Local URL.
- How to identify startup or database failures.
- Safe shutdown procedure.

Do not start the application yourself.

### Section 3 — Initial browser preparation

Explain:

- How to log in as the test athlete.
- How to navigate to `/parte`.
- How to identify the correct date and daily record.
- How to open browser developer tools when needed.
- How to configure a mobile viewport of approximately 375px.
- How to configure a desktop viewport of at least 1024px.

### Section 4 — Ordered acceptance scenarios

Create a separate test case for each scenario.

For every test case include:

1. Test ID.
2. Objective.
3. Preconditions.
4. Initial data state.
5. Exact browser actions.
6. Expected visible result.
7. Expected persisted result, when applicable.
8. Evidence to capture.
9. Cleanup or reset requirements.

Cover all the following scenarios:

**A. Responsive interface**
- Mobile viewport around 375px.
- Desktop viewport at least 1024px.
- Layout integrity.
- No unintended horizontal overflow.
- Controls remain accessible and usable.

**B. Daily wellness and scale interpretation**
- Required wellness inputs.
- Minimum and maximum values.
- Actual scale interpretation.
- Correct labels and displayed values.
- Persistence after saving and reloading.

**C. Conditional fields**
- Discomfort-related fields.
- Illness-related fields.
- Visibility and requiredness under each relevant condition.
- Correct omission or clearing behavior when conditions change.

**D. Multiple training sessions**
- Add multiple sessions.
- Edit individual sessions.
- Preserve stable session IDs.
- Verify that editing one session does not modify another.
- Verify persistence after reload.

**E. Session deletion and omission**
- Explicitly delete a session.
- Save the form.
- Verify that the deleted session is removed.
- Separately test omission behavior when a session is absent from submitted form data.
- Distinguish explicit deletion from accidental omission.

**F. Signed discard confirmation**
- Trigger the discard confirmation.
- Verify the exact signed confirmation protocol.
- Cancel the operation.
- Confirm that existing data remains intact.
- Confirm the behavior when the user actually confirms discarding changes.

Use the actual wording and behavior implemented by the application.

**G. HTTP 422 binary restoration**
Test all three binary fields individually.

For each field:
- Set its value explicitly.
- Trigger a reproducible validation failure.
- Observe the returned form.
- Verify the original binary value is restored correctly.
- Verify that other submitted form values are not unexpectedly lost.

Capture the HTTP status and visible form state.

**H. HTTP 409 concurrent modification**
Use two browser tabs authenticated as the same test athlete.

- Open the same daily record in both tabs.
- Submit a change from the first tab.
- Submit a conflicting or outdated change from the second tab.
- Observe the actual HTTP 409 handling.
- Verify the displayed conflict message.
- Determine whether the second tab preserves its submitted changes.
- Verify the persisted record and document the recovery procedure.

Do not assume the application has automatic conflict resolution.

**I. Keyboard accessibility**
- Navigate using Tab and Shift+Tab.
- Verify visible focus indicators.
- Test relevant controls using keyboard interaction.
- Check logical focus order.
- Confirm that conditional controls remain keyboard-accessible.
- Verify that confirmation interactions do not trap focus unexpectedly.

### Section 5 — Evidence collection

Specify exactly what the owner should capture:

- Browser screenshots.
- Viewport dimensions.
- Relevant network requests and HTTP statuses.
- Console errors, if any.
- Before-and-after form states.
- Persisted test record state.
- Conflict messages.
- Relevant server log excerpts.

Explain how to avoid including credentials, personal data, session cookies, or CSRF tokens in evidence.

### Section 6 — Cleanup

Provide a safe cleanup procedure for:

- Test athlete.
- Daily records.
- Training sessions.
- Associated test data.

Use verified foreign-key relationships and deletion order.

Prefer application-supported deletion when available.

If database deletion is necessary, require confirmation of the active database identity and restrict operations to identifiable test records.

Never clean production data.

### Section 7 — Results table

Provide a results table with these columns:

| Test ID | Scenario | Result | Evidence | Notes |
|---|---|---|---|---|

Allowed results:

- PASS
- FAIL
- BLOCKED
- NOT RUN

Leave all test results as NOT RUN because Kilo cannot execute the manual browser tests.

Include a short explanation of how the owner should record each result.

## STRICT CONSTRAINTS

This task is strictly read-only.

- Do not modify application source files.
- Do not modify templates.
- Do not modify tests.
- Do not modify migrations.
- Do not modify configuration.
- Do not create or modify repository documentation.
- Do not install dependencies.
- Do not install browser tools.
- Do not start the local application.
- Do not run browser tests.
- Do not modify production data.
- Do not expose credentials or personal data.
- Do not create commits.
- Do not push, merge, or open pull requests.
- Do not deploy.
- Do not begin Phase 5.

Preserve all existing user changes.

If any requested scenario cannot be reproduced safely using existing functionality, document the limitation and explain what additional capability or preparation would be required.

Do not introduce implementation changes to make testing easier.

## VALIDATION AND REPORTING

Before producing the runbook:

1. Verify every documented route and form field against current source.
2. Verify every command against actual project configuration or documentation.
3. Verify database preparation against the actual models and migrations.
4. Verify HTTP 422 and HTTP 409 reproduction procedures against their implementation.
5. Check that the test scenarios do not depend on invented functionality.
6. Identify prerequisites and blockers explicitly.
7. Confirm that no files were modified and no application was started.

For every finding, distinguish:

- VERIFIED: Directly supported by current source or documentation.
- INFERRED: Reasonable conclusion that has not been independently verified.
- BLOCKED: Cannot be established with available evidence.

## FINAL REPORT

Deliver:

1. A concise summary of the current Phase 4 testing readiness.
2. Exact environment preparation and startup instructions.
3. Safe test-data preparation instructions.
4. The complete ordered browser acceptance runbook.
5. Expected outcomes and evidence requirements.
6. Cleanup instructions.
7. A results table with all tests initially marked NOT RUN.
8. Known limitations and unresolved prerequisites.
9. Confirmation of the actual files inspected.
10. Confirmation that no repository changes or runtime tests were performed.

IMPORTANT:

Phase 4 remains BLOCKED until the owner executes the manual acceptance tests and reviews the evidence.

Do not mark Phase 4 ACCEPTED.

Do not begin Phase 5.

Your final recommendation must identify the precise next action required from the repository owner.

---

## Assistant

I'll start by inspecting the repository structure and the initial context files mentioned in the task.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Now let me inspect the template, static assets, conftest, and other key files.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Now let me inspect the models, services, auth, database configuration, and environment files.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me inspect more supporting files: main.py, auth router, config, tiempo, scripts, and migrations.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me check the migrations, user model, templates config, CSRF module, base template, login template, and scripts directory.


**Tool: glob**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me check the migrations, login template, and seed scripts to understand data creation.


**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me verify the current git state and check the virtual environment.


**Tool: bash**

**Tool: bash**

**Tool: bash**

---

## Assistant

Let me run individual git commands that are permitted.


**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: bash**

---

## Assistant

**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: bash**

---

## Assistant

**Tool: bash**

**Tool: bash**

**Tool: read**

---

## Assistant

I now have a complete understanding of the repository. Let me compile the final runbook report.

---

# DAILY TRACKING — PHASE 4 MANUAL ACCEPTANCE TEST RUNBOOK

**Status:** Read-only investigation deliverable. No repository changes were made. No application was started. All test results are NOT RUN.

**Repository:** `atletismoWeb`  
**Workspace root (verified):** `C:\Archivos.Diego\atletismoWeb\atletismo`  
**Branch (verified):** `Baruc+Kilo`, working tree clean, up to date with `origin/Baruc+Kilo`  
**HEAD commit (verified):** `cb266cb` — `kilo markdown: S-0043_plan_session-ses_e39e.md`  
**Python version (inferred from venv/render.yaml):** 3.12.x  
**Virtual environment (verified):** `.venv/` exists with `python.exe`, `pip.exe`, `pytest.exe`, `alembic.exe`, `uvicorn.exe`, `activate.bat`, `Activate.ps1`

---

## PHASE 4 TESTING READINESS — SUMMARY

Phase 4 is **BLOCKED** until the repository owner executes the manual browser acceptance tests described in this runbook. Kilo cannot execute browser-based tests because interactive browser tooling is unavailable in this environment, and the local application was not started.

**Static verification completed (read-only, source inspection only):**
- Binary restoration precedence (submitted-first → persisted → default) is implemented in `app/templates/atleta/parte.html` for all three binary fields (`entreno_hoy`, `hay_molestia`, `sintomas_enfermedad`).
- Section A wording is neutral: "Contestá pensando en hoy. Cada indicador tiene su propia interpretación; revisá la guía de valores debajo de cada escala."
- Regression tests exist in `tests/test_parte.py` (`TestBinaryRestorationPrecedence` with `_is_radio_checked` helper).
- HTTP 409 conflict handling, signed discard confirmation, session explicit deletion vs omission, and conditional fields are all implemented in the router (`app/routers/parte.py`) and service (`app/services/parte_diaria.py`).
- All 66 focused tests and 413 full-suite tests were reported as passing in S-0042 (historical, not re-executed by this session).

**Browser verification status:** NOT RUN (all scenarios). No interactive browser available. No running app instance.

---

## SECTION 1 — ENVIRONMENT PREPARATION

### 1.1 Required software and versions

| Item | Requirement | Verification basis |
|------|-------------|-------------------|
| Python | 3.12 (inferred) | `render.yaml` sets `PYTHON_VERSION: "3.12.13"`; venv contains `pip3.12.exe` |
| pip | bundled with venv | `.venv\Scripts\pip.exe` present |
| PostgreSQL | Local server required for dev (not for tests) | `.env.example` shows `postgresql://...@127.0.0.1:5432/atletismo`; `database.py` uses `settings.database_url` |
| Alembic | 1.18.4 | `requirements.txt`; `.venv\Scripts\alembic.exe` present |
| Web browser | Any modern browser (Chrome, Firefox, Edge, Safari) | Not available in Kilo environment; owner must supply |

**Not required:** Node.js, npm, front-end build tools, Docker, Redis.

### 1.2 Workspace preparation

**VERIFIED:** Repository root is `C:\Archivos.Diego\atletismoWeb\atletismo`. Working tree is clean. No uncommitted changes.

1. Open a terminal (PowerShell) at the repository root: `C:\Archivos.Diego\atletismoWeb\atletismo`
2. Confirm `.venv` exists (verified present).
3. Confirm no `.env` file exists (it is in `.gitignore` and must be created locally).

### 1.3 Virtual environment activation

**VERIFIED:** `.venv\Scripts\Activate.ps1` and `.venv\Scripts\activate.bat` exist.

**PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
```

**cmd.exe:**
```cmd
.venv\Scripts\activate.bat
```

After activation, `python`, `pip`, `pytest`, `alembic`, and `uvicorn` resolve to the venv executables.

### 1.4 Dependency verification

**INFERRED:** Dependencies are installed in the venv (executables present: `pytest.exe`, `alembic.exe`, `uvicorn.exe`, `fastapi.exe`). Do not run `pip install` — this task is read-only and dependency installation is prohibited.

To verify (owner may run, read-only):
```powershell
python -m pytest --version
alembic --version
```

### 1.5 Environment variable preparation

**VERIFIED from `.env.example`:** A `.env` file must be created at the repository root. `.env` is gitignored and does not exist yet.

Required variables (placeholders — do not display actual credentials):

| Variable | Purpose | Example placeholder |
|----------|---------|-------------------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://atletismo:<PASSWORD>@127.0.0.1:5432/atletismo` |
| `SECRET_KEY` | JWT signing + CSRF signing | 128-char hex (generate with `python -c "import secrets; print(secrets.token_hex(64))"`) |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session lifetime | `86400` |
| `HTTPS_ONLY` | Cookie Secure flag | `false` (local dev over HTTP) |
| `CLUB_NOMBRE` | Club name for templates | `Club de Atletismo` |
| `CLUB_TELEFONO`, `CLUB_WHATSAPP`, `CLUB_EMAIL`, `CLUB_DIRECCION`, `CLUB_INSTAGRAM`, `CLUB_FACEBOOK` | Public page data | optional, may be empty |

**Procedure (owner executes):**
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Edit `.env` and replace `DATABASE_URL` with a local PostgreSQL connection string.
3. Replace `SECRET_KEY=REEMPLAZAR_POR_UNA_CLAVE_NUEVA_DE_128_HEX` with a newly generated 128-hex secret.
4. Set `HTTPS_ONLY=false` (required for local HTTP; browsers discard Secure cookies over HTTP).

**Never commit `.env`.** It is gitignored.

### 1.6 Safe local database creation

**VERIFIED from README:** `createdb atletismo` creates the database. The app connects via `DATABASE_URL` from `.env`.

**Owner procedure (commands verified against README; actual execution requires PostgreSQL running locally):**

```powershell
createdb atletismo
```

If `createdb` is not available, use `psql`:
```powershell
psql -U postgres -c "CREATE DATABASE atletismo;"
```

**Do not use `--borrar` or destructive SQL.** Do not point `DATABASE_URL` at a production/Supabase database for local testing.

### 1.7 Migration procedure

**VERIFIED from README and alembic.ini:** Alembic migrations are at `alembic/versions/` (3 versions: initial schema, fatiga/rpe change, partes_diarios/sesiones additive). `alembic/env.py` reads `DATABASE_URL` from `.env` via `get_settings()`.

**Owner procedure:**
```powershell
alembic upgrade head
```

This creates all tables including `partes_diarios` and `sesiones_entrenamiento` additively (no existing tables are dropped).

### 1.8 Test athlete creation

**VERIFIED:** There is no public registration. Athletes are created by the professor via `/panel` (professor-only route), or via the `crear_profesor.py` script which creates the professor account first.

**Supported workflow (owner executes, application-supported):**

1. Create the professor account (one-time):
```powershell
python scripts/crear_profesor.py
```
   - Prompts for name, username, email (optional), password (min 8 chars).
   - Creates a `role="profesor"` user.

2. Log in as professor at `/auth/login`, navigate to the athlete management panel (`/panel` or `/atletas`), and create a test athlete account with:
   - Role: `atleta`
   - `debe_cambiar_password` must be `false` (or the athlete must change the provisional password at first login via `/cuenta?cambiar=1`)
   - `is_active` must be `true`

3. **Alternative (database-level, only if application UI is unavailable):** Insert a `users` row directly with `role='atleta'`, `is_active=true`, `debe_cambiar_password=false`, and a bcrypt-hashed password. This requires confirming the active database identity first and should be restricted to an isolated test athlete.

**Never invent credentials for existing real athlete records.** Never modify `profe` or seeded athlete records. Use a clearly identifiable test username (e.g., `atleta_test_fase4`) so test records can be identified and cleaned up later.

---

## SECTION 2 — APPLICATION STARTUP

### 2.1 Exact startup command

**VERIFIED from `run.py` and README:**

```powershell
.venv\Scripts\python run.py
```

This runs `uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=True)`.

### 2.2 Expected successful startup indicators

- Uvicorn banner showing `Application startup complete.`
- Listening on `http://0.0.0.0:8002` (accessible locally at `http://127.0.0.1:8002`)
- `reload=True` means file changes trigger restart (not relevant for read-only testing)

### 2.3 Local URL

- Base: `http://127.0.0.1:8002`
- Login: `http://127.0.0.1:8002/auth/login`
- Daily form: `http://127.0.0.1:8002/parte`

### 2.4 How to identify startup or database failures

| Symptom | Likely cause |
|---------|-------------|
| `SystemExit: No se pudo cargar la configuración` / missing variables | `.env` missing or `DATABASE_URL`/`SECRET_KEY` not set |
| `password authentication failed` | Wrong `DATABASE_URL` credentials |
| `Can't load plugin: sqlalchemy.dialects:postgres` | `DATABASE_URL` starts with `postgres://` instead of `postgresql://` |
| Connection refused on port 8002 | App not started or wrong port |
| Database tables missing | `alembic upgrade head` not run |

### 2.5 Safe shutdown procedure

Press `Ctrl+C` in the terminal running uvicorn. Do not kill the PostgreSQL server unless you are certain no other process needs it.

**Do not start the application yourself (Kilo restriction).** The owner executes startup.

---

## SECTION 3 — INITIAL BROWSER PREPARATION

### 3.1 How to log in as the test athlete

1. Open `http://127.0.0.1:8002/auth/login` in the browser.
2. Enter the test athlete's username and password (created in Section 1.8).
3. Click "Entrar".
4. If prompted to change a provisional password (`debe_cambiar_password=true`), complete the change at `/cuenta?cambiar=1` before proceeding.
5. Successful login redirects to `/inicio` (athlete dashboard).

**Authentication mechanism (VERIFIED):** JWT session cookie `access_token` (httpOnly, SameSite=Lax, Secure flag controlled by `HTTPS_ONLY`). Sliding session renewal via `SesionDeslizanteMiddleware`. CSRF token cookie `csrf_token` (httpOnly, SameSite=Strict) is auto-injected by `CSRFMiddleware` on first request and signed into each form via `csrf_input(request)`.

### 3.2 How to navigate to `/parte`

1. From `/inicio`, use the navigation rail (desktop ≥1024px) or bottom tabbar / floating menu (mobile) to reach the daily part screen.
2. Or directly open `http://127.0.0.1:8002/parte`.
3. The router enforces `_athlete_required`: professors receive 403; unauthenticated users are redirected to `/auth/login?next=/parte`.

### 3.3 How to identify the correct date and daily record

- The server date authority is `app.tiempo.hoy()` (America/La_Paz timezone).
- The form header shows `{{ fecha|fecha_corta }}` (e.g., "10/11/26").
- One record per (atleta, fecha). If a record exists for today, the form pre-fills with persisted values and shows "Ya cargaste hoy. Si algo cambió, corregilo y volvé a guardar."
- If no record exists, the form is blank (create mode).

### 3.4 How to open browser developer tools

- Press `F12` or `Ctrl+Shift+I` (Chrome/Edge/Firefox) or `Cmd+Option+I` (Safari).
- Use the **Network** tab to observe HTTP requests and statuses (200, 302, 422, 409, 403, 404).
- Use the **Console** tab to capture JavaScript errors.
- Use the **Elements** tab to inspect form fields, radio states, and conditional block visibility.

### 3.5 Mobile viewport (~375px)

1. Open Developer Tools.
2. Click the "Toggle device toolbar" icon (or `Ctrl+Shift+M`).
3. Set dimensions to approximately **375 × 812** (iPhone SE/12 mini class) or choose a mobile preset.
4. Confirm the page renders single-column, no horizontal overflow (`overflow-x: hidden` is set on `body`).

### 3.6 Desktop viewport (≥1024px)

1. Close device toolbar or resize browser window to at least **1024 × 768**.
2. At ≥1024px, the CSS media query activates the left rail navigation and hides the bottom tabbar.
3. Confirm the `.escala-10` grids expand to 10 columns and layout remains intact.

---

## SECTION 4 — ORDERED ACCEPTANCE SCENARIOS

### Field contract reference (VERIFIED from source)

| Field | HTML name | Type | Required | Range / values | Conditional |
|-------|-----------|------|----------|----------------|-------------|
| Sleep quality | `sueno_calidad` | radio 1-10 | Yes | 1-10 | Always |
| Fatigue | `fatiga` | radio 1-10 | Yes | 1-10 | Always |
| Muscle pain | `dolor_muscular` | radio 1-10 | Yes | 1-10 | Always |
| Stress | `estres` | radio 1-10 | Yes | 1-10 | Always |
| Mood | `animo` | radio 1-10 | Yes | 1-10 | Always |
| Sleep hours | `horas_sueno` | number | Yes | 0-24, step 0.5 | Always |
| Trained today | `entreno_hoy` | radio si/no | Yes | si/no | Always (controls training block) |
| Discomfort present | `hay_molestia` | radio si/no | Yes | si/no | Always (controls discomfort block) |
| Discomfort zones | `molestia_zona` | text + datalist | If hay_molestia=si | Comma-separated whitelist (MOLESTIA_ZONAS) | Shown when hay_molestia=si |
| Other zone | `molestia_zona_otra` | text | If "otro" in zones | ≤120 chars | Shown when "otro" selected |
| Discomfort pain | `molestia_dolor` | radio 1-10 | If hay_molestia=si | 1-10 | Shown when hay_molestia=si |
| Affects training | `afecta_entrenamiento` | radio 0-3 | If hay_molestia=si | 0-3 | Shown when hay_molestia=si |
| Illness symptoms | `sintomas_enfermedad` | radio si/no | Yes | si/no | Always (controls symptoms block) |
| Symptom details | `detalle_sintomas` | textarea | No | Optional text | Shown when sintomas_enfermedad=si |
| Comments | `comentarios` | textarea | No | ≤1000 chars | Always |
| Sessions | `sessions` | textarea | If entreno_hoy=si (≥1) | Pipe lines `id\|orden\|tipo\|min\|rpe\|comentarios` | Shown when entreno_hoy=si |
| Delete session IDs | `delete_session_ids` | text | No | Comma-separated positive ints | Always (inside training block) |
| CSRF token | `csrf_token` | hidden | Yes | signed token | Always |
| Edit state token | `edit_state_token` | hidden | Yes (existing record) | signed token | Always |
| Discard token | `discard_token` | hidden | When discard intent | signed token | When discard_token present |
| Confirm discard | `confirm_discard_sessions` | radio si/no | When discard_token | si/no | When discard_token present |

**Three binary fields:** `entreno_hoy`, `hay_molestia`, `sintomas_enfermedad` — each accepts `si` or `no`.

**Scale interpretation (Section A, VERIFIED):** "Cada indicador tiene su propia interpretación; revisá la guía de valores debajo de cada escala." Descriptors per field are in `DAILY_DESCRIPTORES` (router). Wellness 1-10: 1-3 = low/poor, 4-6 = regular/moderate, 7-8 = good/high, 9-10 = very good/extreme (varies by field).

**Daily scale values (VERIFIED from `DAILY_DESCRIPTORES`):**
- `sueno_calidad`: 1-3 Muy mala, 4-6 Regular, 7-8 Buena, 9 Muy buena, 10 Excelente
- `fatiga`: 1-3 Ninguna, 4-6 Moderada, 7-8 Elevada, 9-10 Extrema
- `dolor_muscular`: 1-3 Ninguno, 4-6 Moderado, 7-8 Fuerte, 9 Muy fuerte, 10 Extremo
- `estres`: 1-3 Ninguno, 4-6 Moderado, 7-8 Elevado, 9 Muy elevado, 10 Extremo
- `animo`: 1-3 Muy bajo/Bajo, 4-5 Bajo/Regular, 7-8 Bueno, 9-10 Excelente

**Multiple-session behavior (VERIFIED):** Sessions have stable integer `id` (PK). New sessions omit `id`. Existing sessions are referenced by `id`. Default: omission ≠ deletion (sessions not in submitted `sessions` are preserved unless explicitly in `delete_session_ids` or `allow_full_session_replacement=1`). `entreno_hoy=false` forces zero sessions.

**Save/discard/cancellation (VERIFIED):** `entreno_hoy=true→false` with existing sessions → 422 with `discard_token`, message "Confirmá explícitamente el descarte de las sesiones existentes antes de guardar sin entrenamiento." Sessions preserved. Confirm with `confirm_discard_sessions=si` + valid `discard_token` + `edit_state_token` → 302, sessions deleted, `entreno_hoy=false`. Cancel (change `entreno_hoy` back to `si` or navigate away) → sessions preserved.

---

### Test Case A1 — Responsive interface: Mobile (~375px)

**Objective:** Verify layout integrity and usability at mobile viewport.

**Preconditions:** App running, logged in as test athlete, at `/parte`.

**Initial data state:** No existing daily record for today (blank form) OR existing record (pre-filled).

**Exact browser actions:**
1. Open DevTools, toggle device toolbar, set width ≈375px.
2. Load `/parte`.
3. Scroll through the entire form.
4. Check for horizontal overflow (page should not scroll horizontally).
5. Tap each radio group (wellness scales, binary controls).
6. Tap the textarea (sessions) and text inputs.
7. Tap the submit button.

**Expected visible result:**
- Single-column card layout.
- No unintended horizontal overflow (`overflow-x: hidden` on body).
- Text readable at 16px (prevents iOS zoom).
- Touch targets ≥44px (`.btn`, `.escala label`, `.binario label`).
- Conditional blocks (`.condicional`) show/hide correctly via `main.js` `[data-abre]` toggle.
- Submit button accessible at bottom.

**Expected persisted result:** N/A (layout only).

**Evidence to capture:** Screenshot at 375px showing full form, DevTools device dimensions, console errors (if any).

**Cleanup:** N/A.

**Test ID:** A1 | Result: NOT RUN

---

### Test Case A2 — Responsive interface: Desktop (≥1024px)

**Objective:** Verify layout integrity at desktop viewport.

**Preconditions:** App running, logged in as test athlete, at `/parte`.

**Exact browser actions:**
1. Resize browser to ≥1024px width (or disable device toolbar).
2. Load `/parte`.
3. Verify left rail navigation appears, bottom tabbar hidden.
4. Verify `.escala-10` expands to 10 columns.
5. Verify `fila-3` grids show 3 columns.
6. Scroll through form, verify no horizontal overflow.

**Expected visible result:** Two-column layout with rail, scales expand horizontally, all controls usable.

**Evidence to capture:** Screenshot at ≥1024px, viewport dimensions.

**Test ID:** A2 | Result: NOT RUN

---

### Test Case B1 — Daily wellness: Required fields and ranges

**Objective:** Verify required wellness inputs, min/max values, and scale interpretation.

**Preconditions:** Logged in as test athlete, at `/parte`, blank form (no existing record).

**Exact browser actions:**
1. Leave all wellness radios unselected.
2. Leave `horas_sueno` empty.
3. Click submit.
4. Observe 422 response with error summary.
5. Select valid values: all five wellness radios (1-10), `horas_sueno` = 7.5.
6. Try `horas_sueno` = 25 (out of range) → submit → 422.
7. Try `horas_sueno` = -1 → submit → 422.
8. Restore `horas_sueno` = 7.5.
9. Submit valid form → 302 redirect.

**Expected visible result:**
- HTML5 `required` on first radio of each mandatory scale group (browser may prevent submit).
- Server 422 with "Corregí los errores antes de guardar" summary if required values missing.
- `horas_sueno` input has `min="0"`, `max="24"`, `step="0.5"`.
- Scale descriptors visible below each 1-10 scale (e.g., "Muy mala", "Excelente", "Ninguna", "Extrema").

**Expected persisted result:** ParteDiaria created with all wellness values, `entreno_hoy=false` (default), zero sessions.

**Evidence to capture:** Screenshot of 422 error summary, screenshot of successful submit redirect to `/parte?ok=1`.

**Cleanup:** Mark the test athlete's today record for cleanup (Section 6).

**Test ID:** B1 | Result: NOT RUN

---

### Test Case B2 — Daily wellness: Scale labels and persistence

**Objective:** Verify correct labels, displayed values, and persistence after save/reload.

**Preconditions:** Test athlete's today record exists (from B1 or created fresh).

**Exact browser actions:**
1. Load `/parte` (GET).
2. Verify each wellness radio shows the correct selected value (persisted).
3. Verify `horas_sueno` input shows persisted value.
4. Change one wellness value (e.g., `animo` from 8 to 3).
5. Submit → 302 redirect.
6. Reload `/parte`.
7. Verify the changed value is persisted and displayed.

**Expected visible result:** Persisted values displayed on GET. Updated value shown after reload.

**Expected persisted result:** Database reflects updated wellness values.

**Evidence to capture:** Screenshot of form with selected values, screenshot after reload.

**Cleanup:** Mark record for cleanup.

**Test ID:** B2 | Result: NOT RUN

---

### Test Case C1 — Conditional fields: Discomfort (hay_molestia)

**Objective:** Verify discomfort-related fields visibility and requiredness.

**Preconditions:** Logged in, at `/parte`, blank or existing record.

**Exact browser actions:**
1. Ensure `hay_molestia=no` (default).
2. Verify discomfort block (`#bloque-molestia`) is hidden (`display: none`).
3. Select `hay_molestia=si`.
4. Verify discomfort block opens (`.abierto`).
5. Verify `molestia_zona`, `molestia_dolor`, `afecta_entrenamiento` visible.
6. Submit with `hay_molestia=si` but no zone → 422 ("Seleccioná al menos una zona de molestia").
7. Enter `molestia_zona=rodillas`, `molestia_dolor=7`, `afecta_entrenamiento=1`.
8. Submit → 302.
9. Reload → verify values persisted.
10. Change `hay_molestia` back to `no`.
11. Submit → 302.
12. Reload → verify discomfort fields cleared in DB (`molestia_zona=null`, `molestia_dolor=null`, `afecta_entrenamiento=null`).

**Expected visible result:** Conditional block toggles via JS. Required fields enforced when visible. Values cleared server-side when hidden.

**Expected persisted result:** Discomfort fields set when `hay_molestia=si`, cleared (NULL) when `hay_molestia=no`.

**Evidence to capture:** Screenshot of discomfort block open, 422 error if applicable, persisted state after reload.

**Cleanup:** Mark record for cleanup.

**Test ID:** C1 | Result: NOT RUN

---

### Test Case C2 — Conditional fields: Discomfort "otra" zone

**Objective:** Verify `molestia_zona_otra` behavior when "otro" selected vs not.

**Preconditions:** Logged in, at `/parte`.

**Exact browser actions:**
1. Set `hay_molestia=si`.
2. Enter `molestia_zona=otro` and `molestia_zona_otra=espalda baja`.
3. Submit → 302.
4. Reload → verify both persisted.
5. Edit: change `molestia_zona` to `rodillas` (remove "otro"), keep `molestia_zona_otra=espalda baja`.
6. Submit → 302.
7. Reload → verify `molestia_zona_otra` cleared (server clears when "otro" not in zones).

**Expected visible result:** "otra" field visible always (labeled "Solo si elegiste 'otro'"). Server clears it when not "otro".

**Expected persisted result:** `molestia_zona_otra` set only when "otro" in zones; otherwise NULL.

**Evidence to capture:** Screenshots of both states.

**Test ID:** C2 | Result: NOT RUN

---

### Test Case C3 — Conditional fields: Illness (sintomas_enfermedad)

**Objective:** Verify illness-related fields visibility and clearing.

**Preconditions:** Logged in, at `/parte`.

**Exact browser actions:**
1. Ensure `sintomas_enfermedad=no` (default).
2. Verify symptoms block (`#bloque-sintomas`) hidden.
3. Select `sintomas_enfermedad=si`.
4. Verify `detalle_sintomas` textarea visible.
5. Enter `detalle_sintomas=fiebre y tos`.
6. Submit → 302.
7. Reload → verify persisted.
8. Change `sintomas_enfermedad` to `no`.
9. Submit → 302.
10. Reload → verify `detalle_sintomas` cleared (NULL).

**Expected visible result:** Conditional block toggles. Detail textarea optional when "si".

**Expected persisted result:** `detalle_sintomas` set when `sintomas_enfermedad=si`, cleared (NULL) when `sintomas_enfermedad=no`.

**Test ID:** C3 | Result: NOT RUN

---

### Test Case D1 — Multiple training sessions: Add multiple sessions

**Objective:** Add multiple training sessions and verify persistence.

**Preconditions:** Logged in, at `/parte`, `entreno_hoy=si`.

**Exact browser actions:**
1. Open training block (`#bloque-entrenamiento`).
2. In `sessions` textarea, enter two lines:
   ```
   |1|resistencia|45|6|calentamiento
   |2|fuerza|30|8|sentadillas
   ```
3. Submit → 302.
4. Reload `/parte`.
5. Verify both sessions shown in "Sesiones actuales" list with stable IDs.
6. Verify `carga_sesion` computed (45×6=270, 30×8=240).

**Expected visible result:** Two sessions listed, IDs assigned by database.

**Expected persisted result:** Two `SesionEntrenamiento` rows linked to the ParteDiaria.

**Test ID:** D1 | Result: NOT RUN

---

### Test Case D2 — Multiple training sessions: Edit individual sessions, stable IDs

**Objective:** Edit one session without modifying another; verify stable IDs.

**Preconditions:** Record with two sessions (IDs s1 and s2 from D1).

**Exact browser actions:**
1. GET `/parte`, obtain `edit_state_token`.
2. In `sessions` textarea, edit session s1: change `tipo_entrenamiento` to `velocidad_sprint`, keep id=s1. Leave session s2 line unchanged.
3. Submit → 302.
4. Reload → verify s1 updated (tipo=velocidad_sprint), s2 unchanged (tipo=fuerza).
5. Verify IDs s1 and s2 unchanged.

**Expected visible result:** Only edited session changed; other session intact.

**Expected persisted result:** Database reflects selective update.

**Test ID:** D2 | Result: NOT RUN

---

### Test Case D3 — Multiple training sessions: Persistence after reload

**Objective:** Verify sessions persist across page reloads.

**Preconditions:** Record with sessions from D2.

**Exact browser actions:**
1. Reload `/parte` (browser refresh).
2. Verify `sessions_form` textarea shows the current session lines.
3. Verify "Sesiones actuales" list matches.

**Expected visible result:** Form reflects persisted state.

**Test ID:** D3 | Result: NOT RUN

---

### Test Case E1 — Session deletion: Explicit delete

**Objective:** Explicitly delete a session and verify removal.

**Preconditions:** Record with two sessions (IDs s1, s2).

**Exact browser actions:**
1. GET `/parte`, obtain `edit_state_token`.
2. In `sessions` textarea, keep only s2 line (remove s1 line from textarea).
3. In `delete_session_ids` input, enter `s1`.
4. Submit → 302.
5. Reload → verify only s2 remains; s1 gone.

**Expected visible result:** Deleted session removed from list.

**Expected persisted result:** s1 row deleted; s2 row intact.

**Test ID:** E1 | Result: NOT RUN

---

### Test Case E2 — Session omission: Not silently deleted

**Objective:** Verify omission (not listing a session) does not delete it.

**Preconditions:** Record with one session (ID s1).

**Exact browser actions:**
1. GET `/parte`, obtain `edit_state_token`.
2. In `sessions` textarea, enter a NEW session line (no id) but do NOT include s1.
3. Do NOT add s1 to `delete_session_ids`.
4. Do NOT set `allow_full_session_replacement=1`.
5. Submit → 302.
6. Reload → verify BOTH s1 (original) and new session exist.

**Expected visible result:** Original session preserved despite omission from textarea.

**Expected persisted result:** Original session not deleted; new session added.

**Test ID:** E2 | Result: NOT RUN

---

### Test Case F1 — Signed discard confirmation: Trigger and cancel

**Objective:** Trigger discard confirmation, verify protocol, cancel, confirm data intact.

**Preconditions:** Record with existing sessions and `entreno_hoy=true`.

**Exact browser actions:**
1. GET `/parte`, obtain `edit_state_token`.
2. Change `entreno_hoy` to `no`, clear `sessions` textarea.
3. Submit → 422 (discard intent).
4. Verify `discard_token` hidden input present in form.
5. Verify message: "Confirmá explícitamente el descarte de las sesiones existentes antes de guardar sin entrenamiento."
6. Verify `entreno_hoy=no` radio selected (submitted value restored).
7. Cancel: change `entreno_hoy` back to `si`, restore sessions, OR navigate away.
8. Reload → verify sessions still intact, `entreno_hoy=true`.

**Expected visible result:** 422 with discard confirmation card. Submitted `no` restored. Sessions preserved after cancel.

**Expected persisted result:** No change to database (sessions intact, `entreno_hoy=true`).

**Evidence to capture:** Screenshot of 422 discard card with `discard_token` hidden input (blur token value in evidence).

**Test ID:** F1 | Result: NOT RUN

---

### Test Case F2 — Signed discard confirmation: Confirm discard

**Objective:** Complete the signed discard protocol and verify deletion.

**Preconditions:** Record with existing sessions, `entreno_hoy=true`, discard intent 422 just triggered (from F1).

**Exact browser actions:**
1. On the 422 page, keep `entreno_hoy=no`.
2. Set `confirm_discard_sessions=si`.
3. Ensure `discard_token` and `edit_state_token` hidden inputs are present.
4. Submit → 302.
5. Reload → verify `entreno_hoy=false`, zero sessions.

**Expected visible result:** Success redirect, discard confirmation card gone.

**Expected persisted result:** Sessions deleted, `entreno_hoy=false`.

**Test ID:** F2 | Result: NOT RUN

---

### Test Case G1 — HTTP 422 binary restoration: entreno_hoy

**Objective:** Verify submitted `entreno_hoy=no` overrides persisted `true` on 422.

**Preconditions:** Record with `entreno_hoy=true` persisted.

**Exact browser actions:**
1. GET `/parte`, obtain `edit_state_token`.
2. Set `entreno_hoy=no`, `sessions=""`.
3. Introduce a validation error elsewhere (e.g., `animo=abc` or omit a required wellness field).
4. Submit → 422.
5. Inspect rendered form: verify `entreno_hoy` **No** radio is checked (not Yes).
6. Verify other submitted values restored.
7. Capture HTTP status 422.

**Expected visible result:** `entreno_hoy=No` selected despite persisted `true`. Other submitted values present.

**Expected persisted result:** Database unchanged (422 = no write).

**Evidence to capture:** Screenshot of 422 form showing No selected, Network tab showing 422 status, console errors.

**Test ID:** G1 | Result: NOT RUN

---

### Test Case G2 — HTTP 422 binary restoration: hay_molestia

**Objective:** Verify submitted `hay_molestia=no` overrides persisted `true` on 422.

**Preconditions:** Record with `hay_molestia=true` (and complete discomfort data).

**Exact browser actions:**
1. GET `/parte`, obtain `edit_state_token`.
2. Set `hay_molestia=no`.
3. Introduce validation error (e.g., `animo=abc`).
4. Submit → 422.
5. Verify `hay_molestia=No` radio checked.

**Expected visible result:** No selected despite persisted true.

**Test ID:** G2 | Result: NOT RUN

---

### Test Case G3 — HTTP 422 binary restoration: sintomas_enfermedad

**Objective:** Verify submitted `sintomas_enfermedad=no` overrides persisted `true` on 422.

**Preconditions:** Record with `sintomas_enfermedad=true` (and detalle_sintomas).

**Exact browser actions:**
1. GET `/parte`, obtain `edit_state_token`.
2. Set `sintomas_enfermedad=no`, keep `detalle_sintomas`.
3. Introduce validation error.
4. Submit → 422.
5. Verify `sintomas_enfermedad=No` radio checked.

**Expected visible result:** No selected despite persisted true.

**Test ID:** G3 | Result: NOT RUN

---

### Test Case H1 — HTTP 409 concurrent modification: Two-tab procedure

**Objective:** Reproduce HTTP 409 conflict using two browser tabs.

**Preconditions:** Two browser tabs (or two browser windows) both logged in as the same test athlete. Record exists.

**Exact browser actions:**
1. Tab A: Load `/parte`. Record shown with `edit_state_token` A.
2. Tab B: Load `/parte`. Same record, `edit_state_token` B (same as A initially).
3. Tab A: Change `animo` to 9, submit → 302 (saved). Record now has `animo=9`, new fingerprint, new `edit_state_token`.
4. Tab B: `edit_state_token` B is now stale. Change `animo` to 5 (different from A's 9), submit with stale token B → 409.
5. Observe Tab B: HTTP 409 response.
6. Verify conflict message displayed ("Tu información está desactualizada...").
7. Verify Tab B form shows submitted value (`animo=5`) in inputs.
8. Verify "Registro actual en el servidor (autoritativo)" card shows `animo=9`.
9. Verify database: `animo=9` (Tab A's value persisted, Tab B's value NOT saved).
10. Recovery: Tab B clicks "Recargar datos actuales" (GET `/parte`) → fresh form with `animo=9`, new tokens.

**Expected visible result:** 409 page with conflict message, submitted values in form, authoritative server values in separate card.

**Expected persisted result:** Only Tab A's change persisted. Tab B's stale submission discarded.

**Evidence to capture:** Screenshot of 409 page in Tab B, Network tab showing 409, console errors, database state.

**Test ID:** H1 | Result: NOT RUN

---

### Test Case I1 — Keyboard accessibility

**Objective:** Verify keyboard navigation, focus indicators, logical focus order.

**Preconditions:** Logged in, at `/parte`, desktop viewport.

**Exact browser actions:**
1. Press `Tab` repeatedly through the entire form.
2. Verify visible focus indicator on each focused element (`border-color: var(--tartan)`, `box-shadow`).
3. Verify logical focus order (top to bottom, matching DOM order).
4. Test radio groups: use arrow keys within a wellness scale group.
5. Test binary controls: Tab to `entreno_hoy`, use arrow keys to toggle si/no.
6. Toggle `hay_molestia` to `si` via keyboard, then Tab into the discomfort block.
7. Verify conditional controls remain keyboard-accessible when revealed.
8. Submit form via keyboard (Enter on submit button or Tab to it + Enter).
9. If 422/409 appears, verify focus is not trapped and error summary is reachable.

**Expected visible result:** Visible focus ring on every interactive element. Logical order. Radio groups operable with arrow keys. No focus trap.

**Evidence to capture:** Screenshot showing focused element with focus ring, console errors.

**Test ID:** I1 | Result: NOT RUN

---

## SECTION 5 — EVIDENCE COLLECTION

The owner should capture the following for each test case:

1. **Browser screenshots:** Full-page screenshots of the form at key states (initial, 422, 409, success, after reload). Include viewport dimensions in the filename or caption.
2. **Viewport dimensions:** Record exact width/height (e.g., 375×812, 1024×768, 1920×1080).
3. **Network requests and HTTP statuses:** From DevTools Network tab, capture the POST `/parte` request and its status (200, 302, 422, 409, 403, 404, 500).
4. **Console errors:** From DevTools Console tab, capture any JavaScript errors (copy text, screenshot).
5. **Before-and-after form states:** Screenshot of form values before submit and after reload/persistence.
6. **Persisted test record state:** If database access is available, capture the ParteDiaria and SesionEntrenamiento rows for the test athlete (or describe observed UI state).
7. **Conflict messages:** Copy the exact conflict/409 message text.
8. **Server log excerpts:** If available, capture uvicorn/terminal output during the test session.

### How to avoid exposing sensitive data in evidence

- **Credentials:** Never include username/password in screenshots. If login screen is captured, blur or crop the password field.
- **Personal data:** Do not include real athlete names, phone numbers, emails, or addresses. Use the test athlete only.
- **Session cookies:** Do not include `access_token` or `csrf_token` cookie values. If the login form HTML is shown, the `csrf_token` hidden input value should be blurred.
- **CSRF tokens:** Blur the `value` attribute of any `csrf_token`, `edit_state_token`, or `discard_token` hidden inputs in screenshots.
- **Database connection strings:** Do not include `DATABASE_URL` with passwords in evidence.

---

## SECTION 6 — CLEANUP

### Cleanup procedure

**Order of operations (foreign-key safe):**

1. **Delete test training sessions** (`sesiones_entrenamiento`) belonging to the test athlete's ParteDiaria records — via application (explicit delete) or direct SQL.
2. **Delete test daily records** (`partes_diarios`) belonging to the test athlete — via application or direct SQL.
3. **Delete the test athlete** (`users`) — via application (professor panel) or direct SQL.

**Foreign-key relationships (VERIFIED from schema):**
- `sesiones_entrenamiento.parte_diaria_id` → `partes_diarios.id` (ON DELETE CASCADE)
- `partes_diarios.atleta_id` → `users.id` (ON DELETE CASCADE)
- Deleting the user cascades to partes_diarios, which cascades to sesiones_entrenamiento.

**Preferred method:** Application-supported deletion. The athlete can delete their own records via the form (entreno_hoy=false + discard confirmation, or explicit session deletion). The professor can delete the athlete from the panel.

**If database-level deletion is necessary:**

1. Confirm the active database identity: connect to the local `atletismo` database (not production/Supabase).
2. Identify the test athlete by username (e.g., `atleta_test_fase4`).
3. Delete only rows identifiable as test data:
```sql
-- Delete sessions for test athlete's parte records
DELETE FROM sesiones_entrenamiento
WHERE parte_diaria_id IN (
    SELECT id FROM partes_diarios WHERE atleta_id = (
        SELECT id FROM users WHERE username = '<TEST_ATLETA_USERNAME>'
    )
);
-- Delete daily records for test athlete
DELETE FROM partes_diarios
WHERE atleta_id = (
    SELECT id FROM users WHERE username = '<TEST_ATLETA_USERNAME>'
);
-- Delete test athlete
DELETE FROM users
WHERE username = '<TEST_ATLETA_USERNAME>' AND role = 'atleta';
```

**Never:**
- Run `DELETE FROM users` without a WHERE clause.
- Run `scripts/seed.py --borrar` (destroys all data).
- Modify production or seeded athlete records.
- Point `DATABASE_URL` at Supabase/production for cleanup.

---

## SECTION 7 — RESULTS TABLE

| Test ID | Scenario | Result | Evidence | Notes |
|---------|----------|--------|----------|-------|
| A1 | Responsive interface — Mobile ~375px | NOT RUN | | |
| A2 | Responsive interface — Desktop ≥1024px | NOT RUN | | |
| B1 | Daily wellness — Required fields and ranges | NOT RUN | | |
| B2 | Daily wellness — Scale labels and persistence | NOT RUN | | |
| C1 | Conditional fields — Discomfort (hay_molestia) | NOT RUN | | |
| C2 | Conditional fields — Discomfort "otra" zone | NOT RUN | | |
| C3 | Conditional fields — Illness (sintomas_enfermedad) | NOT RUN | | |
| D1 | Multiple sessions — Add multiple sessions | NOT RUN | | |
| D2 | Multiple sessions — Edit individual sessions, stable IDs | NOT RUN | | |
| D3 | Multiple sessions — Persistence after reload | NOT RUN | | |
| E1 | Session deletion — Explicit delete | NOT RUN | | |
| E2 | Session omission — Not silently deleted | NOT RUN | | |
| F1 | Signed discard — Trigger and cancel | NOT RUN | | |
| F2 | Signed discard — Confirm discard | NOT RUN | | |
| G1 | HTTP 422 binary restoration — entreno_hoy | NOT RUN | | |
| G2 | HTTP 422 binary restoration — hay_molestia | NOT RUN | | |
| G3 | HTTP 422 binary restoration — sintomas_enfermedad | NOT RUN | | |
| H1 | HTTP 409 concurrent modification — Two-tab | NOT RUN | | |
| I1 | Keyboard accessibility | NOT RUN | | |

**How to record results:** After executing each test case, the owner replaces `NOT RUN` with `PASS`, `FAIL`, or `BLOCKED`:
- **PASS:** All expected visible and persisted results observed, evidence captured.
- **FAIL:** Any expected result not observed; record defect details.
- **BLOCKED:** Test cannot be executed safely (e.g., browser unavailable, database issue); document the blocker.

---

## KNOWN LIMITATIONS AND UNRESOLVED PREREQUISITES

1. **Interactive browser tooling unavailable (BLOCKED):** Kilo cannot launch or control a browser. All scenarios A–I require the repository owner to execute manually in an installed browser.

2. **Local application not started:** The owner must start the app with `.venv\Scripts\python run.py` (port 8002) before any browser test.

3. **Local PostgreSQL database not provisioned:** The owner must create the `atletismo` database, run `alembic upgrade head`, and configure `.env` with `DATABASE_URL` and `SECRET_KEY`.

4. **Test athlete account not created:** The owner must create a professor account (via `crear_profesor.py`) and then a test athlete account via the professor panel.

5. **HTTP 409 two-tab reproduction:** Requires two browser tabs authenticated as the same athlete. The conflict mechanism (edit-state token fingerprint mismatch) is implemented server-side and is reproducible through the browser. However, if the owner cannot maintain two simultaneous authenticated tabs (e.g., cookie sharing issues), this scenario may be BLOCKED.

6. **Signed discard confirmation (F1/F2):** Requires completing the two-step protocol. Step 2 (confirm) actually deletes sessions — this is destructive to test data only (safe if performed on an isolated test athlete's record).

7. **Database-level cleanup:** Requires confirmation of the active database identity (local `atletismo`, not production/Supabase). Direct SQL must be restricted to identifiable test records.

8. **No secrets exposed:** This report uses placeholders for all credential values. No actual credentials, connection strings, or personal data are included.

---

## FILES INSPECTED (CONFIRMATION)

The following files were read during this read-only investigation:

| File | Role |
|------|------|
| `README.md` | Installation and startup documentation |
| `run.py` | Uvicorn startup script (port 8002) |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies |
| `render.yaml` | Production blueprint (Python 3.12.13) |
| `alembic.ini` | Alembic configuration |
| `alembic/env.py` | Alembic environment (reads DATABASE_URL from .env) |
| `alembic/versions/c4b8e2d91f07_add_partes_diarios_sesiones.py` | Migration creating partes_diarios and sesiones_entrenamiento |
| `app/main.py` | FastAPI app, CSRF middleware, session middleware, security headers |
| `app/config.py` | Pydantic settings, loads `.env` |
| `app/database.py` | SQLAlchemy engine/session, PostgreSQL pool options |
| `app/auth.py` | JWT authentication, password hashing, session cookie |
| `app/csrf.py` | CSRF token validation |
| `app/templates_config.py` | Jinja2 templates, globals (csrf_input, static, club, filters) |
| `app/tiempo.py` | Server date authority (America/La_Paz) |
| `app/routers/parte.py` | Phase 3 router: GET/POST `/parte`, form parsing, token handling, 422/409 mapping |
| `app/routers/auth.py` | Login/logout routes, brute-force protection |
| `app/services/parte_diaria.py` | Phase 2 domain service: validation, locking, tokens, discard, sessions |
| `app/services/parte_diaria_tokens.py` | HMAC-SHA256 edit-state and discard tokens, fingerprints |
| `app/models/parte_diaria.py` | ParteDiaria model, MOLESTIA_ZONAS, check constraints |
| `app/models/sesion_entrenamiento.py` | SesionEntrenamiento model, TIPOS_ENTRENAMIENTO |
| `app/models/user.py` | User model, roles, atleta/profesor distinction |
| `app/templates/base.html` | Base template, viewport meta, CSS/JS includes |
| `app/templates/atleta/parte.html` | Daily form template (VERIFIED: binary restoration precedence, section A wording) |
| `app/templates/_campos.html` | Form macros (escala_num, binario, escala, escala_rpe) |
| `app/templates/auth/login.html` | Login template |
| `app/static/css/main.css` | Mobile-first CSS, scales, conditionals, focus states |
| `app/static/js/main.js` | Conditional block toggles via `[data-abre]` |
| `tests/test_parte.py` | Route tests including TestBinaryRestorationPrecedence |
| `tests/conftest.py` | Test fixtures (client, db, crear_usuario, entrar, con_csrf) |
| `scripts/crear_profesor.py` | Professor account creation script |
| `scripts/seed.py` | Sample data script (--borrar is destructive) |
| `scripts/seed_5_atletas.py` | Additional atletas script |
| `.gitignore` | Excludes .env, .venv, *.db, etc. |
| `.kilo/kiloSesions/S-0043_plan_session-ses_e39e.md` | Phase 4 session plan (historical) |
| `.kilo/kiloSesions/S-0042_code_session-ses_e3c4.md` | Binary restoration fix session (historical) |
| `.kilo/plans/1794275057816-phase4-ui-implementation-readiness.md` | Phase 4 implementation plan |

---

## CONFIRMATION OF READ-ONLY STATUS

**CONFIRMED:**
- No repository source files were modified.
- No templates were modified.
- No tests were modified.
- No migrations were modified.
- No configuration was modified.
- No repository documentation was created or modified.
- No dependencies were installed.
- No browser tools were installed.
- The local application was not started.
- No browser tests were executed.
- No production data was modified.
- No credentials or personal data were exposed.
- No commits were created.
- No pushes, merges, or pull requests were performed.
- No deployment was performed.
- Phase 5 was not begun.
- All existing user changes are preserved (working tree is clean).

**Git status verified:** `nothing to commit, working tree clean`, branch `Baruc+Kilo` up to date with `origin/Baruc+Kilo`.

---

## FINAL RECOMMENDATION

**Phase 4 remains BLOCKED.** It cannot be ACCEPTED until the repository owner executes the manual browser acceptance tests.

**The precise next action required from the repository owner:**

1. Complete environment preparation (Section 1): create `.env`, provision local PostgreSQL database, run `alembic upgrade head`, create a test athlete account.
2. Start the application: `.venv\Scripts\python run.py`
3. Execute all 17 test cases (A1 through I1) in an installed browser, following Section 4 exactly.
4. Capture evidence per Section 5.
5. Record results in the Section 7 table (replace NOT RUN with PASS/FAIL/BLOCKED).
6. Perform cleanup per Section 6.
7. Review evidence and determine Phase 4 acceptance:
   - **ACCEPTED:** All critical functional checks pass, no blocking responsive/accessibility defects.
   - **NOT ACCEPTED:** One or more acceptance requirements fail → report defects under a separately authorized fix task.
   - **BLOCKED:** Essential verification cannot be completed due to environmental limitations.

**Phase 5 (migration of weekly consumers and visualizations) must remain untouched until Phase 4 acceptance is established. Do not begin Phase 5.**

---

