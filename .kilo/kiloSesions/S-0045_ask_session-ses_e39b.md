# Correct Phase 4 acceptance runbook

**Session ID:** ses_e39b76764ffe8CNaD3Fp0kU4na
**Created:** 11/10/2026, 12:26:48 PM
**Updated:** 11/10/2026, 12:35:37 PM

---

## User

# DAILY TRACKING — PHASE 4 RUNBOOK CORRECTION

## KILO CODE
- Session: NEW.
- Mode: Ask.
- Reason: Correct concrete inaccuracies in the manual acceptance runbook before the repository owner executes it. This is a strictly read-only audit.
- Initial context:
  - `.kilo/kiloSesions/S-0044_ask_session-ses_e39d.md`
  - `.kilo/kiloSesions/S-0043_plan_session-ses_e39e.md`
  - `app/routers/parte.py`
  - `app/templates/atleta/parte.html`
  - `app/services/parte_diaria.py`
  - `app/templates/_campos.html`
  - `scripts/crear_profesor.py`
  - Relevant user creation, authentication, and login routes.

## OBJECTIVE

Review the S-0044 manual acceptance runbook against the current repository implementation.

Produce a corrected, executable manual acceptance procedure in your final report.

Do not modify repository files or runtime data.

## INSPECTION REQUIREMENTS

1. Inspect the current Git status before proceeding. Preserve all existing user changes.
2. Read S-0044 and S-0043 to understand the intended test scenarios and existing decisions.
3. Trace each test case through the actual router, template, service, authentication, and persistence logic.
4. Verify every expected result against current implementation rather than relying on previous reports.
5. Expand inspection only when required to resolve a specific uncertainty.

## REQUIRED CORRECTIONS

### 1. Session identifiers

Replace symbolic session IDs such as `s1` and `s2`.

Explain how the tester obtains actual positive integer session IDs from the rendered form or persisted test record.

Ensure every procedure uses valid identifiers and explains how to distinguish multiple sessions.

### 2. G1–G3: HTTP 422 validation

Reassess all three scenarios against:
- Browser-native HTML validation.
- Client-side JavaScript validation, if present.
- Backend request validation.
- Actual HTTP response behavior.

Determine whether each scenario can reproducibly produce an HTTP 422 through normal browser interaction.

Do not claim that an HTTP 422 occurs unless the request actually reaches the server and receives that response.

If browser validation prevents submission:
- Explain why the scenario cannot produce the expected backend response through ordinary browser interaction.
- Identify whether a safe browser-only alternative exists.
- If not, document a separately labeled alternative requiring direct HTTP/API testing.
- Do not execute that alternative.

### 3. E1/E2: session replacement semantics

Trace `allow_full_session_replacement`, explicit deletion IDs, and omitted sessions through the actual service implementation.

Determine precisely:
- Which existing records are retained.
- Which records are deleted.
- Whether omitted sessions are preserved or removed.
- How explicit deletion IDs affect replacement behavior.
- What should remain persisted after each operation.

Correct the expected results and manual steps accordingly.

Do not infer behavior from parameter names alone.

### 4. Cleanup procedure

Replace direct SQL user deletion as the default cleanup strategy.

Prefer:
- An isolated disposable local database.
- A documented, verified method for disposing of that database.
- A clear distinction between disposing of an isolated database and deleting individual records in a shared database.

Do not execute cleanup operations.

If safe cleanup cannot be established from the repository, explicitly identify the limitation and require owner confirmation before any destructive action.

### 5. Professor and athlete accounts

Verify the actual workflow for:
- Creating a professor.
- Creating or associating an athlete.
- Authentication and login.
- Any provisional-password or initial-password requirement.
- Password initialization or change requirements.

Inspect `scripts/crear_profesor.py` and the relevant routes and authentication logic.

Do not invent usernames, passwords, or credentials.

Document exactly which credentials must be obtained from the actual creation workflow and where the tester should obtain them.

### 6. Test inventory

Correct the final test count.

The current results table contains 19 test cases, not 17.

Preserve consistent test IDs throughout:
- Instructions.
- Expected results.
- Execution checklist.
- Final results table.

Do not silently omit or renumber existing scenarios.

### 7. Complete test-case verification

Check every remaining test action against:
- `app/templates/atleta/parte.html`
- `app/routers/parte.py`
- `app/services/parte_diaria.py`
- `app/templates/_campos.html`
- Relevant authentication and user-management code.

Correct unsupported assumptions about:
- Visible confirmation messages.
- Redirect destinations.
- HTTP status codes.
- Hidden fields and their values.
- Form submission behavior.
- Persisted database state.
- Validation and error presentation.
- Session selection and replacement.
- User permissions.

Only document behavior supported by inspected implementation.

## RESTRICTIONS

STRICT READ-ONLY MODE.

- Do not edit application code.
- Do not edit templates.
- Do not edit tests or migrations.
- Do not edit configuration.
- Do not edit repository documentation.
- Do not start the application.
- Do not execute browser tests.
- Do not install dependencies or tools.
- Do not connect to or modify any database.
- Do not create, modify, or delete runtime data.
- Do not commit, push, merge, or deploy.
- Do not begin Phase 5.
- Do not discard, reset, revert, or overwrite user changes.

You may inspect files, Git metadata, and existing documentation using available read-only capabilities.

If a required fact cannot be verified without executing the application or modifying runtime state, mark it BLOCKED and explain why.

## FINAL REPORT

Return the corrected runbook directly in your final response.

Organize it into the following sections:

### 1. Audit summary
- Scope inspected.
- Git status.
- Overall findings.

### 2. Corrections applied
For each required correction:
- Original inaccuracy.
- Verified implementation behavior.
- Corrected instruction or expected result.
- Source files and relevant functions/routes/templates.

### 3. Corrected manual acceptance runbook
Provide a complete, sequential, executable procedure for the repository owner.

Include:
- Preconditions.
- Database isolation and setup requirements.
- Professor and athlete account preparation.
- Login procedure.
- Test execution steps.
- Expected results for all 19 test cases.
- Safe cleanup instructions.
- Any separately identified non-browser alternative.

Clearly distinguish verified behavior from assumptions and prerequisites.

### 4. Verification classification

Use these classifications consistently:

- VERIFIED: Directly supported by inspected source code or repository evidence.
- INFERRED: Reasonable conclusion that cannot be conclusively established from static inspection.
- BLOCKED: Cannot be verified without prohibited execution or additional information.

Do not present inferred or blocked behavior as verified.

### 5. Test results

Retain all 19 test IDs.

Set every manual test result to:

`NOT RUN`

Do not imply that any browser, integration, or runtime test was executed.

### 6. Final safety confirmation

Explicitly confirm:
- No files were modified.
- No runtime data was modified.
- No database was accessed for modification.
- No application or browser tests were executed.
- No dependencies or tools were installed.
- No Git operations changed repository history or user changes.

## ACCEPTANCE CRITERIA

The audit is complete only if:

1. All 19 test cases are accounted for with consistent IDs.
2. Session identifiers are based on actual positive integer IDs.
3. G1–G3 accurately distinguish browser validation from backend HTTP 422 responses.
4. E1/E2 match the actual service replacement and deletion semantics.
5. Cleanup is safe and distinguishes disposable databases from shared databases.
6. Professor and athlete creation/login instructions match actual implementation.
7. Every remaining test action has been checked against current source code.
8. All unverified behavior is explicitly classified.
9. All manual results remain NOT RUN.
10. No repository or runtime modifications occurred.

If any criterion cannot be satisfied through read-only inspection, document the limitation instead of guessing.

---

## Assistant

I'll start by inspecting the repository structure, Git status, and reading the session files and source code in parallel.


**Tool: bash**

**Tool: read**

**Tool: read**

---

## Assistant

The output was truncated. Let me continue reading S-0044 and read the key source files in parallel.


**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Now let me read the templates, the professor creation script, and auth routes in parallel.


**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Now let me read the auth routes, user model, base template, and README to complete the picture.


**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me read the auth module, base template, and token service to verify authentication and token mechanics.


**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

Let me verify the password-change flow and confirm there are no other relevant routes I'm missing.


**Tool: grep**

**Tool: grep**

**Tool: grep**

---

## Assistant

Let me read the cuenta router and the atletas router (athlete creation by professor) to complete the account workflow verification.


**Tool: read**

**Tool: read**

---

## Assistant

Let me read the athlete creation section of atletas.py to understand the professor's workflow for creating athletes.


**Tool: read**

---

## Assistant

I now have a comprehensive understanding. Let me verify the current HEAD commit for the audit summary.


**Tool: bash**

---

## Assistant

**Tool: bash**

**Tool: bash**

---

## Assistant

I now have a complete, verified understanding of the codebase. I'll compose the corrected runbook as my final response.

# DAILY TRACKING — PHASE 4 CORRECTED MANUAL ACCEPTANCE RUNBOOK

## 1. Audit Summary

**Scope inspected:** S-0044 runbook and S-0043 plan session files; `app/routers/parte.py`; `app/services/parte_diaria.py`; `app/services/parte_diaria_tokens.py`; `app/templates/atleta/parte.html`; `app/templates/_campos.html`; `app/templates/base.html`; `app/routers/auth.py`; `app/auth.py`; `app/routers/cuenta.py`; `app/routers/atletas.py`; `app/models/user.py`; `app/models/parte_diaria.py`; `app/main.py`; `scripts/crear_profesor.py`; `README.md`; `run.py`; `.env.example`; `alembic/env.py`; `tests/test_parte.py`; `tests/conftest.py`.

**Git status (read-only, verified):** Branch `Baruc+Kilo`; HEAD `ed354cf61f856c9e361000814a2cc051623009f2` (`kilo markdown: S-0044_ask_session-ses_e39d.md`); working tree clean; up to date with `origin/Baruc+Kilo`; `git status --porcelain=v1` empty. No user changes to preserve beyond the clean tree.

**Overall findings:** The S-0044 runbook contains several concrete inaccuracies relative to the actual implementation: (1) it uses symbolic session IDs `s1`/`s2` though session IDs are database-assigned positive integers; (2) G1–G3 propose triggering HTTP 422 by omitting required wellness fields or typing `animo=abc`, but HTML5 `required` on wellness radios and `horas_sueno` blocks submission before it reaches the server, and radio inputs cannot accept `abc`; (3) E1/E2 correctly imply omission does not delete by default, but must reference actual integer IDs and the `allow_full_session_replacement` flag; (4) cleanup defaults to direct SQL deletion rather than an isolated disposable database; (5) account creation workflow omits that athletes are created by the professor via `/atletas/nuevo` with a single-shown provisional password and `debe_cambiar_password=true` forcing a change at `/cuenta?cambiar=1`; (6) the test count is correctly 19 (not 17) and all 19 must be preserved. All manual results remain `NOT RUN`; no tests were executed.

---

## 2. Corrections Applied

### Correction 1 — Session identifiers (replace symbolic `s1`/`s2`)

**Original inaccuracy:** S-0044 refers to sessions symbolically as `s1` and `s2` (D2, E1, E2 preconditions and actions), implying the tester knows session IDs in advance.

**Verified implementation behavior:** Session IDs are database-assigned primary keys (`SesionEntrenamiento.id`, auto-increment integer). The tester cannot know them before saving. They are obtained at render time from:
- The rendered form's **"Sesiones actuales"** list: `<li>Sesión {{ s.id }}: {{ s.tipo_entrenamiento }} · ...</li>` (`parte.html` lines 53-56 and 151-155).
- The `sessions_form` textarea content when re-rendered after save/422/409 (`parte.py` `_render_form`, `_serialize_sessions`).
- The `delete_session_ids` field, which `_serialize_delete_ids` pre-fills with current session IDs (`parte.py` line 143-144, `parte.html` line 145).

New sessions are created by leaving the `id` field blank (leading pipe, e.g. `|1|resistencia|45|6|calentamiento` where the first field is empty → `id=None`; `_parse_session_item` lines 115-118). Existing sessions are edited/referenced by their integer `id`.

**Corrected instruction:** Every procedure that references a session must first direct the tester to read the actual integer ID from the "Sesiones actuales" list (or the re-rendered `sessions_form`) and substitute that positive integer wherever `s1`/`s2` appears. Multiple sessions are distinguished by their distinct integer IDs shown in the list. Sources: `app/templates/atleta/parte.html`, `app/routers/parte.py` (`_serialize_sessions`, `_serialize_delete_ids`, `_parse_session_item`), `app/services/parte_diaria.py` (`serialize_session`).

---

### Correction 2 — G1–G3: HTTP 422 validation (browser vs backend)

**Original inaccuracy:** S-0044 suggests triggering 422 by entering `animo=abc` or by omitting required wellness fields.

**Verified implementation behavior:**
- Wellness scales (`sueno_calidad`, `fatiga`, `dolor_muscular`, `estres`, `animo`) are rendered by `escala_num(..., requerido=true)`, which adds HTML5 `required` to the **first** radio of each group (`_campos.html` line 27). `horas_sueno` has `required`, `min="0"`, `max="24"`, `step="0.5"` (`parte.html` lines 112-114).
- HTML5 constraint validation therefore **blocks submission in the browser** when any required wellness radio is unselected or `horas_sueno` is out of range/empty. The request never reaches the server, so **no HTTP 422 is produced** through normal browser interaction by those means.
- A radio input only offers values 1–10; `animo=abc` cannot be typed into it through the UI.
- The binary fields (`entreno_hoy`, `hay_molestia`, `sintomas_enfermedad`) are rendered by `binario()` with **no** `required` attribute (`_campos.html` lines 60-69), so they never block submission. Server-side validation in `validate_and_normalize_wellness` (`parte_diaria.py` lines 374-451) requires a zone when `hay_molestia=si` and requires `molestia_dolor`/`afecta_entrenamiento` then; none of those fields carry HTML5 `required`. A malformed `sessions` textarea line is rejected by `_session_payload` (`parte.py` lines 104-129, 147-177) before the service runs; the textarea has no HTML5 validation.
- Therefore HTTP 422 **is** reproducible through normal browser interaction, but only via server-only validation triggers that bypass HTML5: (a) `hay_molestia=si` with no `molestia_zona` selected → 422 `"Seleccioná al menos una zona de molestia."`; or (b) a malformed `sessions` line → 422 parse error.
- On any 422, `_render_form` re-renders with `status_code=422` and `form=form`; the router preserves submitted `sessions`/`delete_session_ids` (`parte.py` lines 262-270). The database is **not written** on 422 (wellness validation precedes `load_today_for_update`; parse errors return before `save_daily_record`; discard-intent 422 calls `db.rollback()`). `parte_diaria.py` lines 675-682, 760-775, 848-852.

**Corrected instruction:** For G1–G3, set the target binary field to `no` (overriding persisted `true`), then add a **separate server-only validation error** to force 422 through the browser:
- G1 (`entreno_hoy`): set `entreno_hoy=no`; also set `hay_molestia=si` with no zone → 422. Verify `entreno_hoy` **No** radio checked (submitted-first precedence: `parte.html` lines 126-132).
- G2 (`hay_molestia`): set `hay_molestia=no`; also keep `entreno_hoy=si` with one malformed session line → 422 parse error. Verify `hay_molestia` **No** checked (`parte.html` lines 169-175).
- G3 (`sintomas_enfermedad`): set `sintomas_enfermedad=no`; also set `hay_molestia=si` with no zone → 422. Verify `sintomas_enfermedad` **No** checked (`parte.html` lines 215-221).
Capture Network tab status 422. Do not claim 422 from omitted wellness fields (browser-blocked) or `animo=abc` (unenterable).

**Classification:** VERIFIED (template macros, router, service validation); end-to-end browser execution = NOT RUN.

---

### Correction 3 — E1/E2: session replacement semantics

**Original inaccuracy:** E1/E2 use symbolic IDs and rely on the parameter name `allow_full_session_replacement` without tracing the actual `_apply_sessions` logic.

**Verified implementation behavior (`app/services/parte_diaria.py`, `_apply_sessions`, lines 532-591):**
- Default (`allow_delete_omitted=False`): `to_delete = set(explicit_delete_ids)` only. Sessions present in the DB but **omitted from the submitted `sessions` list are PRESERVED**, not deleted. Only IDs explicitly listed in `delete_session_ids` are removed.
- `allow_full_session_replacement=True`: `to_delete = all current IDs − desired IDs`. Omitted sessions **are** deleted (full replacement).
- Ownership: every ID referenced in `desired_sessions` or `explicit_delete_ids` must belong to the locked record, else 422 `"Sesión N no pertenece al registro actual."` (lines 546-548).
- Upsert: desired sessions with existing `id` update that row; sessions with `id=None` are inserted as new rows (lines 568-588).
- `entreno_hoy=false`: `validate_and_normalize_sessions` forces `normalized=[]` (line 509); in `save_daily_record`, turning training off with existing sessions triggers the discard-confirmation 422 (F1/F2), not silent deletion (lines 753-807). With no existing sessions, `entreno_hoy=false` stores zero sessions.

**Corrected expected results:**
- E1 (explicit delete): read integer IDs from "Sesiones actuales"; remove s1's line from the textarea AND enter s1's integer ID in `delete_session_ids`; submit → 302; s1 removed, s2 preserved. Omission alone would NOT have deleted s1.
- E2 (omission): read integer IDs; remove s1's line from the textarea; do **not** add s1 to `delete_session_ids`; do **not** set `allow_full_session_replacement=1`; submit → 302; **s1 is preserved** and the new session is added. This is the key correction: omission ≠ deletion by default.

**Classification:** VERIFIED (`_apply_sessions` source).

---

### Correction 4 — Cleanup procedure (no direct SQL as default)

**Original inaccuracy:** S-0044 defaults to direct SQL `DELETE` against the shared `atletismo` database as the cleanup method.

**Verified implementation behavior:** Foreign-key cascade exists (`sesiones_entrenamiento.parte_diaria_id → partes_diarios.id ON DELETE CASCADE`; `partes_diarios.atleta_id → users.id ON DELETE CASCADE`, from S-0044 Section 6 and migration `c4b8e2d91f07`). Application-supported deletion is available via the form (explicit session delete, discard confirmation). The professor panel can deactivate/delete an athlete (`debe_cambiar_password`, `is_active`; `routers/atletas.py`).

**Corrected instruction:**
1. **Preferred (isolated disposable database):** Create a separate local PostgreSQL database used only for this test cycle (e.g. `createdb atletismo_fase4`), point `DATABASE_URL` at it, run `alembic upgrade head`, execute all tests, then dispose of the entire database with `dropdb atletismo_fase4` (or `DROP DATABASE`). This discards all test data at once without touching any shared/production database. Distinguish this from deleting individual records.
2. **If a shared database must be used:** delete only identifiable test records in FK-safe order (sessions → `partes_diarios` → `users`), restricted to a clearly identifiable test athlete username, and only after the owner confirms the active database identity is the local dev database (not production/Supabase). Application-supported deletion is preferred over raw SQL.
3. Never run `DELETE FROM users` without a WHERE clause; never run `scripts/seed.py --borrar`; never point `DATABASE_URL` at Supabase/production for cleanup.

**Limitation requiring owner confirmation:** Read-only inspection cannot confirm which database is "active" or that `dropdb`/`createdb` are available in the owner's environment. The owner must confirm the database identity before any destructive SQL or database drop. Do not execute cleanup in this session.

---

### Correction 5 — Professor and athlete accounts

**Original inaccuracy:** S-0044 does not detail how credentials are obtained and risks inventing usernames/passwords.

**Verified implementation behavior:**
- No public registration. Professor created once via `scripts/crear_profesor.py` (interactive prompts: name, username, optional email, password min 8 chars) → creates `role="profesor"` user; prints the username to use at `/auth/login` (`scripts/crear_profesor.py` lines 21-64).
- Athlete created **by the professor** via `/atletas/nuevo` (GET shows a suggested provisional password; POST creates `role="atleta"`, `debe_cambiar_password=True`, min 6-char provisional password) → redirect to the athlete's ficha which shows the provisional password **once** via a short-lived cookie (`routers/atletas.py` lines 193-284, `_password_provisoria`, `_ficha_con_password`).
- Login: `POST /auth/login` with `identificador` (username or email) + password. On success sets httpOnly `access_token` JWT cookie and redirects to `/panel` (profesor) or `/inicio` (`routers/auth.py` lines 96-142, `auth.py` `set_auth_cookie`).
- `get_current_user` raises `DebeCambiarPassword` if `debe_cambiar_password=true`, handled in `app/main.py` line 161-162 → redirect to `/cuenta?cambiar=1` (302). `/cuenta` shows the change-password form when `obligatorio=true`; requires current password + new password min 8 chars; changing password invalidates all other tokens (`routers/cuenta.py`, `auth.py` `huella_password`).
- `_athlete_required` in `parte.py` line 66-69: professors get 403; unauthenticated users redirect to `/auth/login?next=/parte` (`main.py` line 157).

**Corrected instruction (no invented credentials):**
1. Professor: run `python scripts/crear_profesor.py`; record the **username and password** you enter at the interactive prompts (these are created by you, not supplied by Kilo).
2. Log in as professor at `/auth/login`; go to `/atletas/nuevo`; create the test athlete with a clearly identifiable username (e.g. `atleta_test_fase4`); record the **username and the single-shown provisional password** from the ficha page.
3. Log in as the athlete at `/auth/login` with those credentials; you will be redirected to `/cuenta?cambiar=1`; change the password (min 8 chars, current = provisional) → `debe_cambiar_password=false`; then access `/parte`.
4. Do not invent credentials for existing/seeded athlete records; never modify `profe` or seeded records.

**Sources:** `scripts/crear_profesor.py`, `app/routers/atletas.py`, `app/routers/auth.py`, `app/auth.py`, `app/routers/cuenta.py`, `app/main.py`.

---

### Correction 6 — Test inventory (19, not 17; consistent IDs)

**Verified:** S-0044 Section 7 already lists exactly 19 test IDs: A1, A2, B1, B2, C1, C2, C3, D1, D2, D3, E1, E2, F1, F2, G1, G2, G3, H1, I1. The claim "17" is incorrect; the count is 19. All 19 are retained with identical IDs across instructions, expected results, execution checklist, and final results table. None are omitted or renumbered.

---

### Correction 7 — Complete test-case verification

Each remaining action was checked against `parte.html`, `_campos.html`, `parte.py`, `parte_diaria.py`, and auth code. Unsupported assumptions corrected:

| Assumption in S-0044 | Verified reality | Correction |
|---|---|---|
| B1 submit with empty wellness → 422 | HTML5 `required` blocks browser submit first; no server 422 via browser | Expected: browser blocks (validation tooltip); valid values → 302 |
| G1-G3 via `animo=abc` / omitted required | `abc` not enterable on radio; required fields HTML5-blocked | Use server-only triggers: `hay_molestia=si` no zona, or malformed session line |
| F1 discard card only appears after intent | `get_today_state` issues `discard_token` on every GET of an existing record → card renders (informational) always; becomes active confirmation prompt on discard-intent 422 | Document card presence on GET; active prompt on 422 |
| "Sesión s1/s2" known in advance | IDs are DB-assigned integers read from "Sesiones actuales" | Obtain actual integer IDs from rendered form |
| Direct SQL cleanup as default | Isolated disposable DB preferred; app-supported deletion available | Prefer `dropdb` of isolated DB; SQL only with owner confirmation |
| Invented usernames/passwords | Credentials come from `crear_profesor.py` prompts and professor panel ficha (single-shown provisional) | Record credentials from actual workflow |

**Sources verified:** `app/templates/atleta/parte.html` (binary restoration precedence lines 126-132, 169-175, 215-221; `dato()` macro lines 6-10; `edit_state_token` line 84; `discard_token` lines 85-87, 236-247; `csrf_input` line 83; `sessions`/`delete_session_ids` lines 140-148), `app/templates/_campos.html` (`escala_num` required lines 22-27; `binario` no required lines 60-69), `app/routers/parte.py` (`_session_payload`, `_render_form` 422/409 preservation, GET/POST), `app/services/parte_diaria.py` (`validate_and_normalize_wellness`, `validate_and_normalize_sessions`, `_apply_sessions`, `save_daily_record`, discard protocol), `app/services/parte_diaria_tokens.py` (HMAC edit-state/discard tokens, 15-min expiry), `app/routers/auth.py`, `app/auth.py`, `app/routers/cuenta.py`, `app/routers/atletas.py`, `scripts/crear_profesor.py`, `app/main.py`.

---

## 3. Corrected Manual Acceptance Runbook

### Preconditions

1. Repository at `C:\Archivos.Diego\atletismoWeb\atletismo`, branch `Baruc+Kilo`, clean working tree (verified). No files modified by Kilo.
2. Python 3.12 virtual environment `.venv/` present (verified) with `pytest`, `alembic`, `uvicorn`.
3. A modern browser installed by the owner (not available in Kilo environment; owner supplies).
4. Local PostgreSQL server available (owner provisioned); Kilo does not connect to any database.

### Database isolation and setup requirements

**Preferred (isolated disposable database):**
1. Create a dedicated database: `createdb atletismo_fase4` (or via `psql -U postgres -c "CREATE DATABASE atletismo_fase4;"`).
2. Create `.env` at repo root from `.env.example` (`.env` is gitignored; does not exist yet). Set `DATABASE_URL` to the isolated database, generate `SECRET_KEY` (`python -c "import secrets; print(secrets.token_hex(64))"`), set `HTTPS_ONLY=false` (local HTTP; Secure cookies are discarded by browsers over HTTP).
3. Run `alembic upgrade head` (adds `partes_diarios`, `sesiones_entrenamycin` additively; drops nothing).
4. Execute all tests against this isolated database.
5. **Disposal:** drop the database (`dropdb atletismo_fase4` or `DROP DATABASE atletismo_fase4;`). This disposes of all test data at once. Distinct from deleting individual records in a shared DB.

**If using a shared database:** use only a clearly identifiable test athlete (e.g. `atleta_test_fase4`) and delete only its records in FK-safe order (sessions → `partes_diarios` → `users`), after the owner confirms the database identity is local dev (not production/Supabase). Application-supported deletion preferred.

Kilo does not execute any setup, migration, or disposal.

### Professor and athlete account preparation (obtain credentials from the actual workflow)

Do not invent credentials.
1. **Professor:** Run `python scripts/crear_profesor.py`. At the interactive prompts, enter name, username, optional email, and a password (≥8 chars). Record the **username and password** you typed. The script creates `role="profesor"` and prints the login username.
2. **Athlete:** Log in as professor at `/auth/login`. Navigate to `/atletas/nuevo` (professor panel). Create the test athlete; the form shows a suggested provisional password. After creation, the ficha page displays the provisional password **once** (short-lived cookie). Record the **athlete username and provisional password**.
3. **First athlete login:** `/auth/login` with athlete username + provisional password → redirected to `/cuenta?cambiar=1` (`debe_cambiar_password=true`). Change password (≥8 chars, current = provisional). After change, `debe_cambiar_password=false`, then access `/parte`.

### Login procedure

1. Open `http://127.0.0.1:8002/auth/login` (app started by owner with `.venv\Scripts\python run.py` on port 8002).
2. Enter athlete username + password; click "Entrar".
3. Successful login → 302 redirect to `/inicio` (athlete dashboard).
4. Navigate to `/parte` (rail on desktop ≥1024px; bottom tabbar/floating menu on mobile, or direct URL).
5. `_athlete_required` enforces role `atleta`; professors get 403; unauthenticated → `/auth/login?next=/parte`.
6. Server date authority is `app.tiempo.hoy()` (America/La_Paz). One record per (atleta, fecha).

### Test execution steps (19 cases)

**A1 — Responsive interface: Mobile ~375px.** Set device toolbar ≈375×812. Load `/parte`. Scroll full form; tap radios, textareas, submit. Expected: single-column card, no horizontal overflow, touch targets usable, conditionals toggle via `main.js` `[data-abre]`. Layout-only; no persisted result. Evidence: 375px screenshot, viewport dims, console errors. **NOT RUN.**

**A2 — Responsive interface: Desktop ≥1024px.** Resize ≥1024px. Load `/parte`. Expected: left rail nav, bottom tabbar hidden, `.escala-10` expands, no overflow. Evidence: screenshot, dims. **NOT RUN.**

**B1 — Daily wellness: required fields and ranges.** Leave required wellness radios unselected / `horas_sueno` empty → **browser blocks submit** (HTML5 `required`, `min`/`max`/`step`; no server 422 reachable this way). Fill valid values (all five 1–10, `horas_sueno`=7.5) → submit → 302 redirect to `/parte?ok=1`. Expected persisted: `ParteDiaria` created, `entreno_hoy=false`, zero sessions. Evidence: screenshot of browser validation, screenshot of redirect. **NOT RUN.**

**B2 — Daily wellness: scale labels and persistence.** GET `/parte` → verify persisted radios selected, `horas_sueno` shown. Change one value (e.g. `animo` 8→3) → submit → 302 → reload → value persisted. Evidence: before/after screenshots. **NOT RUN.**

**C1 — Conditional fields: Discomfort (`hay_molestia`).** `hay_molestia=no` → `#bloque-molestia` hidden. Set `si` → block opens; `molestia_zona`, `molestia_dolor`, `afecta_entrenamiento` visible. Submit with `si` but no zone → **server 422** `"Seleccioná al menos una zona de molestia."` (reaches server; text input has no HTML5 `required`). Fill zone/dolor/afecta → 302 → reload → persisted. Set `hay_molestia=no` → submit → 302 → reload → discomfort fields cleared (NULL). Evidence: block open, 422, persisted state. **NOT RUN.**

**C2 — Conditional fields: Discomfort "otra" zone.** `hay_molestia=si`; `molestia_zona=otro`, `molestia_zona_otra=espalda baja` → 302 → reload → both persisted. Change `molestia_zona` to `rodillas` (drop "otro"), keep `zona_otra` → 302 → reload → `molestia_zona_otra` cleared (NULL). Evidence: both states. **NOT RUN.**

**C3 — Conditional fields: Illness (`sintomas_enfermedad`).** `no` → `#bloque-sintomas` hidden. Set `si` → `detalle_sintomas` visible; enter text → 302 → reload → persisted. Set `no` → 302 → reload → `detalle_sintomas` cleared (NULL). Evidence: screenshots. **NOT RUN.**

**D1 — Multiple sessions: add multiple.** `entreno_hoy=si`. In `sessions` textarea enter new sessions (leading pipe = blank id): `|1|resistencia|45|6|calentamiento` and `|2|fuerza|30|8|sentadillas`. Submit → 302. Reload → both sessions listed in "Sesiones actuales" with DB-assigned integer IDs; `carga_sesion` computed (270, 240). Evidence: session list with IDs. **NOT RUN.**

**D2 — Multiple sessions: edit individual sessions, stable IDs.** From a record with sessions, read actual integer IDs from "Sesiones actuales" (e.g. IDs 7 and 8). GET `/parte`; edit the line for ID 7 (`tipo` → `velocidad_sprint`, keep id=7); leave ID 8 line unchanged. Submit → 302 → reload → ID 7 updated, ID 8 unchanged; IDs stable. Evidence: before/after session list. **NOT RUN.**

**D3 — Multiple sessions: persistence after reload.** Reload `/parte` → `sessions_form` textarea shows current session lines; "Sesiones actuales" list matches. Evidence: screenshot. **NOT RUN.**

**E1 — Session deletion: explicit delete.** Record with sessions (IDs e.g. 7, 8). GET `/parte`; remove ID 7's line from `sessions` textarea; enter `7` in `delete_session_ids`. Submit → 302 → reload → only ID 8 remains; ID 7 gone. Evidence: session list. **NOT RUN.**

**E2 — Session omission: not silently deleted.** Record with one session (ID e.g. 7). GET `/parte`; in `sessions` textarea enter a NEW session (blank id) but do **not** include ID 7; do **not** add 7 to `delete_session_ids`; do **not** set `allow_full_session_replacement=1`. Submit → 302 → reload → **both ID 7 (preserved) and the new session exist**. Correction: omission alone does NOT delete; only explicit `delete_session_ids` or `allow_full_session_replacement=1` deletes. Evidence: session list showing both. **NOT RUN.**

**F1 — Signed discard: trigger and cancel.** Record with sessions, `entreno_hoy=true`. GET `/parte` (edit + discard tokens present). Set `entreno_hoy=no`, clear `sessions`. Submit → **422** with discard confirmation card; message `"Confirmá explícitamente el descarte de las sesiones existentes antes de guardar sin entrenamiento."`; `discard_token` hidden input present; `entreno_hoy=no` restored. Cancel: set `entreno_hoy` back to `si`/restore sessions, or navigate away → reload → sessions intact, `entreno_hoy=true`. Evidence: 422 screenshot (blur token values). **NOT RUN.**

**F2 — Signed discard: confirm discard.** On the F1 422 page: keep `entreno_hoy=no`; set `confirm_discard_sessions=si`; ensure `discard_token` + `edit_state_token` present. Submit → 302 → reload → `entreno_hoy=false`, zero sessions. Evidence: redirect, empty session list. Destructive to test data only (isolated athlete). **NOT RUN.**

**G1 — HTTP 422 binary restoration: `entreno_hoy`.** Record with `entreno_hoy=true` persisted. GET; set `entreno_hoy=no`; add server-only error: `hay_molestia=si` with no zone → **422**. Inspect form: `entreno_hoy` **No** checked (submitted-first, not persisted `true`); other submitted values present. Capture Network status 422. Database unchanged (422 = no write). Evidence: 422 screenshot, Network tab. **NOT RUN.**

**G2 — HTTP 422 binary restoration: `hay_molestia`.** Record with `hay_molestia=true`. GET; set `hay_molestia=no`; add server-only error: keep `entreno_hoy=si` with one malformed session line (e.g. `|abc|resistencia|45|6|x`) → **422** parse error. Verify `hay_molestia` **No** checked. Evidence: 422 screenshot. **NOT RUN.**

**G3 — HTTP 422 binary restoration: `sintomas_enfermedad`.** Record with `sintomas_enfermedad=true`. GET; set `sintomas_enfermedad=no`; add server-only error: `hay_molestia=si` with no zone → **422**. Verify `sintomas_enfermedad` **No** checked. Evidence: 422 screenshot. **NOT RUN.**

**H1 — HTTP 409 concurrent modification: two-tab.** Two tabs, same athlete, same record. Tab A: GET (edit token A). Tab B: GET (token B, initially equal). Tab A: change `animo` to 9 → 302 (saved; new fingerprint/token). Tab B: change `animo` to 5; submit with stale token B → **409**. Tab B shows conflict message `"Tu información está desactualizada..."`, submitted values retained, authoritative server card shows `animo=9`. Database: `animo=9` (Tab A only). Recovery: Tab B "Recargar datos actuales" (GET) → fresh form with `animo=9`, new tokens. Evidence: 409 screenshot, Network 409, DB state. **NOT RUN.**

**I1 — Keyboard accessibility.** Desktop viewport. Tab through form; verify visible focus ring on each element; logical focus order; arrow keys within radio groups; toggle `hay_molestia` to `si` via keyboard then Tab into discomfort block; conditional controls remain accessible; submit via keyboard; on 422/409 focus not trapped, error summary reachable. Evidence: focused-element screenshot, console errors. **NOT RUN.**

### Safe cleanup instructions

- On isolated disposable database: drop the database (`dropdb atletismo_fase4`) — disposes of all test data at once; no per-record SQL needed.
- On shared database (owner confirmation required for database identity): delete test records in FK order — `sesiones_entrenamiento` → `partes_diarios` → `users` — restricted to the identifiable test athlete username (`role='atleta'`). Never `DELETE FROM users` without WHERE; never `seed.py --borrar`; never target Supabase/production.
- Kilo does not execute any cleanup.

### Separately identified non-browser alternative

For G1–G3 (and any 422/409), if browser interaction cannot reliably reach the server, a direct HTTP/API test (e.g. `curl`/`httpx` POST `/parte` with a constructed body and cookies) may reproduce the status, but this requires session/CSRF cookies and is **outside browser-only scope**; Kilo does not execute it and the owner must decide whether to use it.

---

## 4. Verification Classification

- **VERIFIED:** binary restoration precedence (`parte.html` lines 126–132, 169–175, 215–221); `dato()` macro; `edit_state_token`/`discard_token`/`csrf_input` rendering; `escala_num` HTML5 `required` (`_campos.html` line 27); `binario` no `required`; router `_session_payload`/`_render_form` 422/409 preservation; service `validate_and_normalize_wellness`/`validate_and_normalize_sessions`/`_apply_sessions` (default no implicit delete by omission; explicit delete IDs only; `allow_full_session_replacement` deletes omitted); `save_daily_record` discard-confirmation 422 and no-write-on-422; token service HMAC/signing; login/JWT cookie; `debe_cambiar_password` → `/cuenta?cambiar=1`; professor creates athlete via `/atletas/nuevo` with single-shown provisional password; `crear_profesor.py` interactive prompts; 19 test IDs; git status clean.
- **INFERRED:** exact CSS rules (e.g. `overflow-x: hidden`, touch-target sizes) — not read from `main.css`; that two authenticated tabs can coexist without cookie-sharing issues; end-to-end rendering of conditional blocks via `main.js` (JS logic present but not executed).
- **BLOCKED:** all actual browser execution (no browser tooling, app not started); confirming active database identity and availability of `createdb`/`dropdb`; observing real HTTP statuses and persisted DB state; any cleanup execution.

No inferred or blocked behavior is presented as verified.

---

## 5. Test Results

All 19 test IDs retained, consistent across instructions/expected results/checklist/table. Every manual result is `NOT RUN` (no browser, integration, or runtime test executed).

| Test ID | Scenario | Result | Evidence | Notes |
|---|---|---|---|---|
| A1 | Responsive interface — Mobile ~375px | NOT RUN | | |
| A2 | Responsive interface — Desktop ≥1024px | NOT RUN | | |
| B1 | Daily wellness — Required fields and ranges | NOT RUN | | HTML5 blocks empty submit; no server 422 via browser |
| B2 | Daily wellness — Scale labels and persistence | NOT RUN | | |
| C1 | Conditional fields — Discomfort (`hay_molestia`) | NOT RUN | | Server 422 reachable via `hay_molestia=si` no zona |
| C2 | Conditional fields — Discomfort "otra" zone | NOT RUN | | |
| C3 | Conditional fields — Illness (`sintomas_enfermedad`) | NOT RUN | | |
| D1 | Multiple sessions — Add multiple sessions | NOT RUN | | New sessions use blank id (leading pipe) |
| D2 | Multiple sessions — Edit individual sessions, stable IDs | NOT RUN | | Use actual integer IDs from "Sesiones actuales" |
| D3 | Multiple sessions — Persistence after reload | NOT RUN | | |
| E1 | Session deletion — Explicit delete | NOT RUN | | ID in `delete_session_ids` + removed from textarea |
| E2 | Session omission — Not silently deleted | NOT RUN | | Omission preserves by default |
| F1 | Signed discard — Trigger and cancel | NOT RUN | | 422 discard-intent; sessions preserved on cancel |
| F2 | Signed discard — Confirm discard | NOT RUN | | Destructive to test data only |
| G1 | HTTP 422 binary restoration — `entreno_hoy` | NOT RUN | | Trigger via `hay_molestia=si` no zona (server-only) |
| G2 | HTTP 422 binary restoration — `hay_molestia` | NOT RUN | | Trigger via malformed session line (server-only) |
| G3 | HTTP 422 binary restoration — `sintomas_enfermedad` | NOT RUN | | Trigger via `hay_molestia=si` no zona (server-only) |
| H1 | HTTP 409 concurrent modification — Two-tab | NOT RUN | | Stable edit-state token fingerprint mismatch |
| I1 | Keyboard accessibility | NOT RUN | | |

Recording: owner replaces `NOT RUN` with `PASS`/`FAIL`/`BLOCKED` after executing each case; PASS requires all expected results and evidence; BLOCKED documents the blocker.

---

## 6. Final Safety Confirmation

Confirmed:
- No repository files were modified (read-only inspection only).
- No runtime data was modified.
- No database was accessed for modification (no connection made).
- No application or browser tests were executed (app not started; no browser tooling).
- No dependencies or tools were installed.
- No Git operations changed repository history or user changes (working tree clean; no commits/pushes/merges).
- Phase 5 was not begun.

**Limitation note:** Criteria requiring live execution (actual browser behavior, real HTTP statuses, persisted DB state, database-identity confirmation, cleanup execution) cannot be satisfied through read-only inspection and are classified BLOCKED; they require the repository owner to run the runbook against a live local instance.

---

