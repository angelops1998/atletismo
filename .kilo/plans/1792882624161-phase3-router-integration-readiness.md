# Phase 3 — `/parte` Router Integration Readiness Plan (Daily Tracking)

**Status:** planning only — **no source, test, template, migration, or repository-state changes made** by this investigation. Implementation requires explicit authorization.  
**Session:** `ses_e8fd` (existing, available/inspected). **Mode:** Plan.  
**Date (inspected):** 2026-11-08 (America/La_Paz context from workspace).  
**Authoritative specs:** `.kilo/plans/1792882624161-daily-tracking-replacement.md` (authoritative; Policy A fixed), `.kilo/plans/1792882624161-phase2-concurrency-policy.md` (Policy A approved/resolved supporting doc).  
**Evidence basis (VERIFIED unless labeled):** `app/services/parte_diaria.py`, `app/services/parte_diaria_tokens.py`, `app/routers/parte.py`, `app/auth.py`, `app/csrf.py`, `app/database.py`, `app/tiempo.py`, `app/main.py`, `app/templates/atleta/parte.html`, `app/templates/_campos.html`, `app/templates_config.py`, `app/models/parte_diaria.py|sesion_entrenamiento.py`, `tests/test_parte.py|test_parte_diaria_service.py|test_parte_diaria_concurrency_pg.py|test_parte_diaria_schema.py|test_asistencia.py|test_seguridad.py|conftest.py`, session docs S-0026–S-0029. **PostgreSQL execution evidence is REPORTED from S-0029** (not re-run in this investigation).

---

## 1. Executive Summary

- **VERIFIED (current behavior):** `app/routers/parte.py` still implements the **weekly** athlete report (`GET/POST /parte`, `?semana=`), using `ParteSemanal`/`bienestar.parte_de_semana`, `SEMANAS_EDITABLES=1`, Monday-week upsert, and renders `templates/atleta/parte.html` (weekly 1–5/RPE/molestias). It is mounted in `app/main.py`. **Phase 3 router integration has not been implemented.**
- **VERIFIED (domain readiness):** Phase 2 daily domain services exist: `app/services/parte_diaria.py` (validation/normalization, conditional clearing, stable explicit session ops, authoritative `carga_sesion` recompute, `hoy()` server date authority, `SELECT ... FOR UPDATE(of=ParteDiaria)` on PostgreSQL + `selectinload` + `populate_existing` reload, Policy A edit-state verification after lock+reload, create-race `IntegrityError` → rollback→reload→409 conflict result, preserved signed discard protocol; controlled internal errors; test-only coordination seams prefixed `_test_*`). `app/services/parte_diaria_tokens.py` issues/verifies HMAC-SHA256 edit-state (`edit_parte_diaria`) and discard (`discard_sessions`) tokens bound to canonical fingerprints, using `settings.secret_key` and `hmac.compare_digest`.
- **REPORTED (S-0029):** Phase 2.2.1 passed on an independently verified disposable PostgreSQL 16.15 container (lock-wait proof, service-level create race, concurrent discard, full suite 379 passed). **Not re-executed here.**
- **PROPOSED (Phase 3 objective):** replace `/parte` **functional** behavior with the daily today-only workflow by adapting the existing router as a thin HTTP/controller layer over the verified domain services, preserving Policy A and signed discard exactly. Keep route path `/parte`; remove weekly `semana`/Monday semantics from this router in Phase 3 only as required for daily flow (no weekly consumer/viz/schema/legacy removal). **Phase 4** implements the full daily template UX; Phase 3 must define a stable template/response contract.
- **Main implementation risk:** `save_daily_record` commits/rollbacks internally (service-owned transactions). The router must **not** wrap service calls in competing commits/rollbacks or hold a conflicting transaction. CSRF is enforced globally by `CSRFMiddleware` for `/parte` (not exempt); the template already includes `csrf_input(request)`. `app/schemas/` does not exist (VERIFIED) — form parsing remains router/template-form based, consistent with repo conventions.

---

## 2. Verified Current Repository and Git State

| Item | Evidence | Status |
|---|---|---|
| Repository root | `git rev-parse --show-toplevel` → `C:/Archivos.Diego/atletismoWeb/atletismo` | VERIFIED |
| Branch | `git branch --show-current` → `Baruc+Kilo` | VERIFIED |
| HEAD | `git rev-parse HEAD` → `12d6f3f5aecbc59a5c0dcffab53d8e2c0aa3143d` | VERIFIED |
| Commit | `12d6f3f codex markdown: S-0029_codex_validation_session-ses_e8fd.md` (recent log also shows `e810578`, `1aa8120`, `ad1661b`, `f5e94f0`) | VERIFIED |
| Reported HEAD to compare | `e810578` (user context) and previously observed remote `12d6f3f5aecbc59a5c0dcffab53d8e2c0aa3143d` | VERIFIED (compared) |
| Working tree / tracked / staged / untracked (non-ignored) | `git status --short --branch` → `## Baruc+Kilo...origin/Baruc+Kilo`; `git diff --name-status` empty; `git diff --cached --name-status` empty; `git ls-files --others --exclude-standard` empty | VERIFIED |
| Remote | `origin https://github.com/angelops1998/atletismo.git` (fetch/push) | VERIFIED |
| Upstream divergence | `git rev-list --left-right --count origin/Baruc+Kilo...Baruc+Kilo` → `0	0` | VERIFIED |
| Reconciliation vs reported state | Local HEAD **is** `12d6f3f5...` and equals the previously observed remote commit; it is **ahead of** `e810578` in local history (`e810578` is an ancestor in recent log). Branch is **not behind/diverged** from recorded upstream state (`0 0`). No fetch performed. | VERIFIED (interpretation from local git only) |
| Repository modified by this investigation | Only the plan file created at `.kilo/plans/1792882624161-phase3-router-integration-readiness.md` (and this report references it). No source/tests/templates/docs/migrations modified. | VERIFIED (planning-file write only; no implementation files) |

**Safety note:** no reset/clean/stash/checkout/overwrite/commit/fetch performed.

---

## 3. Verified Service API and Token Contracts

### 3.1 `app/services/parte_diaria.py`

| Contract area | Evidence | Status |
|---|---|---|
| Transport abstraction | `ServiceResult` dataclass: `ok,status,message,errors,parte,edit_state_token,discard_token,current_fingerprint,conflict,stale,created`; `data` property. Status constants: `STATUS_OK=200, STATUS_VALIDATION=422, STATUS_CONFLICT=409, STATUS_FORBIDDEN=403, STATUS_NOT_FOUND=404, STATUS_INTERNAL=500`. | VERIFIED |
| Public load/state APIs | `load_today(db, atleta_id, fecha=None)->ParteDiaria|None` (no lock); `load_today_for_update(db, atleta_id, fecha=None)` → `fecha or hoy()`, lock query when PG + `execution_options(populate_existing=True)`, `selectinload(sesiones)`; `get_today_state(db, atleta_id, fecha=None)->(parte, edit_token, discard_token)` issues fresh tokens from **current persisted state** (no lock; read path). `serialize_parte/serialize_session`, `current_fingerprint/current_session_fingerprint`. | VERIFIED |
| Save API | `save_daily_record(db, *, atleta_id, payload:dict, edit_state_token=None, discard_token=None, confirm_discard_sessions=False, explicit_delete_session_ids=None, allow_full_session_replacement=False, fecha=None, _test_* hooks=None)->ServiceResult`. `fecha` defaults to `hoy()` (server authority). Router must not pass client date for athlete today-only flow (or must enforce same policy explicitly). | VERIFIED |
| Discard API | `discard_sessions(db, *, atleta_id, edit_state_token, discard_token, confirm, fecha=None)->ServiceResult`. Missing confirm/token → `STATUS_VALIDATION` with fresh tokens/state (no deletion). Missing record → `STATUS_NOT_FOUND` after rollback. Stale edit/discard under lock → 409 conflict. Success deletes sessions, sets `entreno_hoy=False`, commits, returns fresh tokens. | VERIFIED |
| Validation | `validate_and_normalize_wellness(payload)` raises `DomainValidationError(errors)`. Required 1–10: `sueno_calidad,fatiga,dolor_muscular,estres,animo`; `horas_sueno` `Decimal` 0–24 (non-finite rejected, normalized 1 decimal) required; `hay_molestia` bool default false with conditional required `molestia_zona` whitelist (`MOLESTIA_ZONAS`), required `molestia_zona_otra` iff `otro`, required `molestia_dolor` 1–10 and `afecta_entrenamiento` 0–3 when true; clears conditional fields when false; `sintomas_enfermedad` bool clears `detalle_sintomas` when false, accepts optional trimmed text when true; `comentarios` text; `entreno_hoy` bool default false. `validate_and_normalize_sessions(raw, *, entreno_hoy)` requires list; validates stable `id` ownership later, `tipo` whitelist (`TIPOS_ENTRENAMIENTO`), `duracion_min>=1`, `rpe` 1–10, recomputes `carga_sesion=duracion_min*rpe`; `entreno_hoy=true` requires >=1 valid session; `entreno_hoy=false` returns `[]`. | VERIFIED |
| Session ops / ownership | `_apply_sessions`: default **no implicit delete by omission** (`allow_delete_omitted=False`); explicit deletes only via `explicit_delete_ids` unless `allow_full_session_replacement=True`. Any referenced `session_id` (desired or explicit delete) must belong to locked current record else `DomainValidationError` “no pertenece al registro actual”. New sessions have `id=None`. | VERIFIED |
| DB/session ownership & tx | Service uses passed `db: Session`; performs `db.add/flush/delete/commit/rollback/refresh`. **Service owns mutation transactions/rollback for these operations** (commits on success paths; rollbacks on conflict/validation/internal/error paths as coded). Router must supply request-scoped `get_db()` session and must **not** add competing `commit()`/`rollback()` around these calls. | VERIFIED |
| Locking/reload (Policy A) | PG: `_supports_for_update` true for `postgresql`; lock query uses `with_for_update(of=ParteDiaria)` + `selectinload(sesiones)` + `populate_existing`. SQLite: no `FOR UPDATE` (service still executes logic; **not proof of PG race/lock behavior**). Stale edit-state verified **after** lock+reload on existing-record path. | VERIFIED |
| Stale-state / create race | Existing record: invalid `edit_state_token` against locked current fingerprint → `_conflict_result` (`STATUS_CONFLICT`, `conflict/stale=True`, rollback, reload current state, fresh tokens). Create path: test seams before/around flush/commit; on `IntegrityError` after create attempt → `_conflict_result` with same conflict semantics, **no blind reapply/retry**. Generic `Exception` → rollback best-effort, `STATUS_INTERNAL` (500), no raw leakage. | VERIFIED |
| Discard protocol (preserved) | Turning `entreno_hoy` true→false with existing sessions: if not `confirm_discard_sessions` or no `discard_token`, rollback and return `STATUS_VALIDATION` + message/errors requiring explicit confirmation + `discard_token` for current session state (no deletion). If confirmed but `discard_token` invalid/stale under lock+current session fingerprint → 409 conflict, no delete. Valid → delete sessions + set `entreno_hoy=false` in same locked tx, commit. `discard_sessions` additionally verifies edit-state token against locked current record fingerprint before discard-token verification (no weakening). | VERIFIED |
| Other | Aggregation helpers exist (`carga_sesion/carga_diaria/aggregate_week_reported`, missing≠0) — not required for Phase 3 router minimal GET/POST save, but available. `_test_*` seams are test-only; production callers leave `None`. | VERIFIED |

### 3.2 `app/services/parte_diaria_tokens.py`

| Contract area | Evidence | Status |
|---|---|---|
| Crypto/trust root | HMAC-SHA256 via `settings.secret_key`; `hmac.compare_digest` for signatures/fingerprint comparisons; base64url payload+signature token format `<payload>.<sig>`; canonical JSON `sort_keys,separators(',',':'),ensure_ascii=True`. Aligns with `app/csrf.py` trust pattern. | VERIFIED |
| Edit-state token | Purpose `edit_parte_diaria`, default 900s. Claims: `purpose,atleta_id,fecha(iso),registro_id|null,fingerprint,exp`. `issue_edit_state_token(atleta_id,fecha,registro_id,fingerprint,exp_seconds)` / `verify_edit_state_token(token,*,atleta_id,fecha,registro_id,current_fingerprint)`. Rejects missing/malformed, bad signature, wrong purpose, expired, athlete/date/registro/fingerprint mismatch. | VERIFIED |
| Discard token | Purpose `discard_sessions`, default 900s. Claims: `purpose,atleta_id,fecha,registro_id,session_fingerprint,exp`. `issue_discard_token` requires `registro_id`; `verify_discard_token` checks current session fingerprint. | VERIFIED |
| Fingerprints | `record_state_fingerprint(parte,sessions)`: canonicalizes relevant persisted fields (includes `horas_sueno` normalized decimal string, normalized/sorted `molestia_zona`, normalized booleans/text/ints, `sessions` sorted normalized). `session_state_fingerprint(sessions)`: normalized session set by `(orden,id)` fields. Deterministic/stable ordering. | VERIFIED |
| Invalid/expired/mismatch behavior | `TokenVerification(ok,payload,reason)`. Reasons include `missing_or_malformed,bad_signature,bad_payload,wrong_purpose,expired,athlete_mismatch,date_mismatch,registro_mismatch,fingerprint_mismatch`. Service maps stale/invalid edit/discard verification to 409 conflict (or validation for missing discard confirmation step). | VERIFIED |

### 3.3 Discrepancies vs prior reports (evidence-based)

| Topic | Status | Evidence |
|---|---|---|
| Phase 2.2.1 PostgreSQL validation passed | REPORTED | `S-0029_codex_validation_session-ses_e8fd.md`; not re-run. |
| Service implementation vs S-0028/27 concerns | VERIFIED as implemented now | `parte_diaria.py` includes `populate_existing` reload, `selectinload`, controlled internal errors, non-finite decimal rejection, test seams, explicit discard/edit-state checks. |
| Router still weekly | VERIFIED | `app/routers/parte.py` unchanged in semantics (weekly). |
| Phase 1 migration present/immutable | VERIFIED/REPORTED per S-0021 | `alembic/versions/c4b8e2d91f07_*` exists; historical migrations present. |

---

## 4. Existing Router, Auth, Authorization, and CSRF Conventions

| Convention | Evidence | Status |
|---|---|---|
| Authentication | `get_current_user(request, db=Depends(get_db))` decodes cookie token (`access_token`), verifies user/active, enforces `pv` (password hash fingerprint) and `debe_cambiar_password` → raises `NotAuthenticatedException(next_url)` / `DebeCambiarPassword` (handlers in `main.py` redirect to login/account). Templates/HTML routers typically call `get_current_user`; unauthenticated → 302 login (not JSON 401) for HTML routes. | VERIFIED |
| Authorization | Weekly `/parte`: athlete-only (`if user.role != "atleta": raise HTTPException(403, ...)`). Service layer scopes mutations by `atleta_id` arg and session binding/ownership checks for `session_id`. Router must resolve current athlete as `user.id` and never accept athlete id from client for self-report. | VERIFIED |
| CSRF | `CSRFMiddleware` in `app/main.py`: protects `_METODOS_INSEGUROS` (`POST/PUT/PATCH/DELETE`), exempts only `/auth/login`. Parses `csrf_token` from form-urlencoded/multipart; missing/invalid → renders `403.html` (403). **`/parte` POST is protected by default.** Templates use `{{ csrf_input(request) }}` (signed token). | VERIFIED |
| DB session lifecycle | `get_db()` yields request-scoped `SessionLocal` and closes in `finally`. Routers depend on `db: Session = Depends(get_db)`. No app-level global transaction wrapper in router examples reviewed. | VERIFIED |
| Dependency injection | FastAPI `Depends(get_db)`, `Request`, form fields via `Form(...)` or `await request.form()` for dynamic fields. | VERIFIED |
| Form parsing/validation | Routers parse/normalize form values, collect errors, render template with `status_code=422` and `form=request.form()`/values on validation error (see `parte.py`, `atletas._leer_form`, `asistencia.guardar` for dynamic multi-items). `app/schemas/` absent. | VERIFIED |
| Exception handling | `HTTPException` used for 403/404 etc.; global handlers render `403/404/500.html`; `NotAuthenticatedException`/`DebeCambiarPassword` redirect. Router may raise `HTTPException` or render responses; JSON API patterns not used in reviewed HTML routers. | VERIFIED |
| Redirect/response conventions | Successful form submits often `RedirectResponse(..., status_code=302)` (e.g. weekly parte → `/inicio?parte=1`, asistencia → `...?ok=1`). GET/validation render `TemplateResponse(request, template, context)` with optional `status_code`. | VERIFIED |
| Date authority | `app/tiempo.hoy()` / `lunes_actual()` use `America/La_Paz` (`NOMBRE_TZ`, `ZoneInfo`). Weekly router normalizes requested week; daily service defaults `fecha` to `hoy()`. | VERIFIED |
| Weekly behaviors to preserve intact (not Phase 3 router removal scope beyond `/parte` replacement) | `ParteSemanal` model/table, `bienestar`/`alertas` weekly consumers, panel/estadisticas/ficha templates/routers, weekly tests/scripts, migrations — **preserve** per plan; Phase 3 only changes `/parte` router behavior/integration and its related tests/contract. Phase 4 handles full template redesign. | PROPOSED/POLICY (authoritative plan) |

**Phase 3 implication:** new `/parte` GET/POST must use `get_current_user` (or equivalent), enforce athlete role, use request-scoped DB, rely on CSRFMiddleware (template keeps CSRF), obtain `target_date = hoy()` server-side, and delegate validation/concurrency/discard/state to domain services.

---

## 5. Proposed Route Lifecycle (Phase 3, PROPOSED)

### 5.1 GET `/parte` (athlete today)

1. **Auth:** resolve `user = get_current_user(request, db)` (handles unauthenticated/provisional password via existing handlers).
2. **Authorization:** require `user.role == "atleta"` else 403 (existing convention).
3. **Date authority:** `target_date = hoy()` (server). Ignore any `?semana=`/date query for athlete write flow (PROPOSED; aligns with today-only). May accept no params.
4. **Load state:** `parte, edit_token, discard_token = get_today_state(db, user.id, target_date)` (read state + fresh tokens). Alternatively `load_today` + token issuance is equivalent as implemented.
5. **Response:** render `templates/atleta/parte.html` (Phase 4 redesign) with stable contract (§8): `user`, `hoy/fecha`, `parte` (or serialized), `form=None`/defaults, `errors=[]`, `conflict=False`, `message`, `edit_state_token`, `discard_token` (if record exists; discard token is for session-discard context per service), `csrf_input` via templates, plus any enums/ranges for UI.
6. **No mutation.** Router does not create records on GET.

### 5.2 POST `/parte` (save today)

1. **Auth/authorization:** same as GET; athlete-only, scoped to `user.id`.
2. **CSRF:** validated by middleware before handler (VERIFIED). Router does not need manual CSRF unless repo pattern requires — **do not duplicate** if middleware already enforces.
3. **Date authority:** `target_date = hoy()` server-side. Do **not** trust client `fecha/semana`.
4. **Parse form:** extract wellness/training/discard/token fields into service payload shape (`sueno_calidad, horas_sueno, fatiga, dolor_muscular, estres, animo, hay_molestia, molestia_zona/zonas, molestia_zona_otra, molestia_dolor, afecta_entrenamiento, sintomas_enfermedad, detalle_sintomas, comentarios, entreno_hoy, sessions[...]`). Extract `edit_state_token`, `discard_token`, `confirm_discard_sessions` (explicit), explicit delete ids/full-replacement flags only if Phase 4/form design uses them (all must be explicit; no implicit delete).
5. **Invoke domain service:** `result = save_daily_record(db, atleta_id=user.id, payload=payload, edit_state_token=..., discard_token=..., confirm_discard_sessions=..., explicit_delete_session_ids=..., allow_full_session_replacement=..., fecha=target_date)`.
6. **Map result to HTTP/UX (§7):** success → redirect/response contract; validation (`422`) → render 422 preserving submitted values + fresh tokens/state from result; conflict/stale/create race (`409`) → render 409 preserving submitted values + showing current authoritative `result.parte`/fresh tokens/message, **no overwrite/no blind retry**; internal (`500`) → controlled error response per app convention.
7. **Ownership/date/session binding:** enforced by service; router never supplies another athlete id.

### 5.3 Optional discard endpoint/action (PROPOSED, only if needed)

The authoritative plan mentions signed discard protocol integration in router Phase 3. `save_daily_record` already handles turn-off-training discard intent/confirm and `discard_sessions` exists as explicit operation. **PROPOSED:** Phase 3 implementation should choose the minimal clear flow:
- **Option A (minimal):** single POST `/parte` handles save + discard-intent + discard-confirm via fields (`entreno_hoy`, `discard_token`, `confirm_discard_sessions`) — matches current service behavior.
- **Option B:** separate POST (e.g. `/parte/descartar-sesiones`) calling `discard_sessions`. Only add if it simplifies UX/contract; keep CSRF/auth/ownership.

**UNRESOLVED (design choice, low risk):** single endpoint vs separate discard endpoint. Recommendation: **Option A** first to minimize route surface, unless Phase 4 UX requires separation.

---

## 6. Transaction and Concurrency Boundaries

| Concern | Boundary | Status |
|---|---|---|
| DB session | Request-scoped `Depends(get_db)`. | VERIFIED |
| Mutation transactions | **Service-owned:** `save_daily_record`/`discard_sessions` lock/load, mutate, `commit()` on success, `rollback()` on conflict/validation/errors as coded. `get_today_state` is read/issue-tokens path. | VERIFIED |
| Router responsibility | Parse/authorize/call service/map `ServiceResult`. **Do not** `db.commit()` after service mutation calls; **do not** wrap in an outer transaction that conflicts with service commit/rollback behavior. | PROPOSED (required) |
| Policy A | Preserved entirely in service: lock existing row (`FOR UPDATE` PG) → reload fresh state → verify edit-state (and discard as applicable) → mutate/commit; stale/tamper/mismatch/wrong binding → conflict 409, no write. Create race `IntegrityError` → rollback→reload→conflict 409, no blind reapply. | VERIFIED |
| PG authority | `FOR UPDATE` and race serialization authoritative on PostgreSQL; SQLite tests do not prove them. PG-disposable evidence REPORTED passed. | VERIFIED/REPORTED |

---

## 7. HTTP Response Contract (PROPOSED for Phase 3/4, constrained by service + app conventions)

> HTML router conventions dominate (TemplateResponse/RedirectResponse). Status codes align with service `STATUS_*` and Policy A.

| Scenario | Service result/behavior | Router handling | HTTP | Response | Template context / notes | Preserve submitted values? |
|---|---|---|---|---|---|---|
| Successful creation | `ok=True,status=200,created=True`, fresh `parte/edit_state_token/discard_token` | Redirect after POST (PRG) or render success — follow existing pattern | 302 recommended (PRG) | `RedirectResponse('/inicio?parte=1'` or daily equivalent) | Flash via query/session not currently evidenced; if using redirect, destination should reflect daily success (coordinate with existing nav/inicio expectations, Phase 5-aware) | n/a after redirect |
| Successful update | `ok=True,status=200,created=False` | Same PRG | 302 | redirect | same | n/a |
| Invalid submitted values | `ok=False,status=422,errors`, message | Re-render daily form | 422 | `TemplateResponse(..., status_code=422)` | `errors`, field mapping (Phase 4), `form/submitted` values, current/loaded tokens/parte as appropriate; use service’s returned state if provided | **Yes** |
| Discard intent, missing confirmation | `ok=False,status=422`, `discard_token` issued, `errors` ask explicit confirmation, `parte`/fresh tokens | Re-render | 422 | Template 422 | show confirmation UI bound to `discard_token` + explicit confirm flag; keep submitted state | **Yes** (service preserves/returns state) |
| Stale edit-state token (existing record) | `ok=False,status=409,stale/conflict`, fresh `parte`+tokens, message | Re-render conflict state | 409 | `TemplateResponse(..., status_code=409)` | `conflict=True, stale=True`, clear outdated message, **submitted values preserved separately**, current authoritative `parte` + fresh `edit_state_token/discard_token`, reload action | **Yes — critical** |
| Create race / `IntegrityError` | `ok=False,status=409,conflict/stale` via `_conflict_result` | Re-render conflict | 409 | 409 | same as stale; message indicates created/updated elsewhere/conflict | **Yes** |
| Stale/invalid discard token on confirm | `ok=False,status=409,stale` | Re-render conflict | 409 | 409 | no deletion performed; fresh state/tokens | **Yes** |
| Missing daily record (explicit discard op) | `ok=False,status=404` from `discard_sessions` | 404 or render with message (follow convention) | 404 | `TemplateResponse`/`HTTPException` per convention | UNRESOLVED exact UX; recommend controlled 404 or redirect to GET `/parte` | n/a |
| Unauthorized athlete ownership | athlete-only enforced in router; service assumes caller supplies authorized `atleta_id`; cross-record session binding errors become validation/ownership errors in service paths where applicable | 403 if role wrong; 404/403 if attempting unauthorized access pattern (should not occur when using `user.id`) | 403/404 | `HTTPException`/existing handler | do not leak other athlete existence | n/a |
| Unauthenticated request | `NotAuthenticatedException` / optional auth none | existing handler | 302 | redirect to `/auth/login?next=...` | VERIFIED | n/a |
| Provisional password | `DebeCambiarPassword` | existing handler | 302 | redirect to `/cuenta?cambiar=1` | VERIFIED | n/a |
| Missing/invalid CSRF token | middleware `validate_csrf` failure | middleware renders | 403 | `403.html` | VERIFIED | n/a |
| Invalid discard intent (no confirm/token on explicit discard op) | `discard_sessions` returns 422 | 422 | 422 | Template 422 | explicit confirmation required | **Yes** |
| Internal error | `ok=False,status=500` | controlled 500 | 500 | `500.html` or equivalent safe response | no raw internals | avoid echoing unsafe data |

**UNRESOLVED (must resolve in implementation, consistent with app):** exact PRG redirect target/query param for daily success (weekly used `/inicio?parte=1`; `parte_pendiente` semantics change in Phase 5 — avoid breaking unrelated consumers in Phase 3 beyond what plan allows). Recommendation: use a dedicated daily success indicator or keep minimal compatible redirect, decided explicitly in Phase 3 task.

---

## 8. Discard-Confirmation Flow (VERIFIED in service; PROPOSED router wiring)

| Step | Evidence / proposed behavior | Status |
|---|---|---|
| Intent issuance | When `entreno_hoy` becomes false but current locked/persisted state has sessions, `save_daily_record` rolls back and returns 422 with `discard_token` bound to **current session fingerprint**, fresh edit token/parte, explicit message. No deletion. | VERIFIED |
| Signed data | `discard_sessions` token: `purpose=discard_sessions, atleta_id, fecha, registro_id, session_fingerprint, exp` (HMAC, secret_key, compare_digest). | VERIFIED |
| Router validation | Router forwards `edit_state_token`, `discard_token`, `confirm_discard_sessions` from explicit form fields; service verifies signature/expiry/purpose/bindings/fingerprints under lock+reload. Router must not accept unsigned free booleans as authorization to delete sessions. | VERIFIED/PROPOSED |
| Explicit confirmation representation | Boolean/flag from form (e.g. `confirm_discard_sessions=true`) **plus** valid signed `discard_token`. Service requires both for destructive path. | VERIFIED |
| Expiration/replay | Expired/wrong-purpose/signature/fingerprint mismatch → verification fails; stale session set after concurrent modification → fingerprint mismatch → 409 conflict, no delete. Short expiry (900s). | VERIFIED |
| Ownership/record identity | Token and verification bind `atleta_id`, `fecha`, `registro_id`; service uses locked owned record and verifies edit-state/discard against current state. | VERIFIED |
| Stale-state protection | Discard confirmation verified after lock+reload; edit-state consistency also checked in `discard_sessions` and in save discard-confirm path (no weakening). | VERIFIED |

**Do not replace** signed intent with unsigned hidden field/ordinary boolean (authoritative constraint).

---

## 9. Phase 4 Template Integration Contract (PROPOSED, minimum stable contract)

Phase 3 must not redesign templates, but should make its handler/context shape compatible with Phase 4.

| Context key (PROPOSED names) | When present | Purpose |
|---|---|---|
| `user` | GET/POST render | current athlete |
| `fecha` / `hoy` | all | server-authoritative local date (`hoy()`) |
| `parte` | GET/POST render | authoritative current `ParteDiaria` ORM/serialized state (from `get_today_state` or `ServiceResult.parte`) |
| `edit_state_token` | existing record / recovery | fresh token for current persisted state |
| `discard_token` | when discard flow relevant | signed discard token for current session state |
| `form` / `submitted` | 422/409 | user-submitted values (raw/normalized for repopulation), **kept separate from `parte`** |
| `errors` | 422 | list + optional field map (Phase 4) |
| `conflict` / `stale` | 409 | booleans and message/reason |
| `message` | all as needed | safe user-facing message |
| `mode` or `has_record` | all | empty-record vs existing-record rendering |
| enums | GET/422/409 | `MOLESTIA_ZONAS`, `TIPOS_ENTRENAMIENTO` (from models/services), wellness ranges/labels as needed |

**409 recovery (critical):** render both (1) **submitted values** and (2) **current authoritative `parte` + fresh tokens**. UI must explain “submitted state outdated/not applied” and offer explicit reload/re-apply path. **Never silently replace submitted values with DB values as if saved.**

**Phase 4 scope (deferred):** full A–E daily form, 1–10 controls, dynamic session JS, discard modal/confirmation UX details, per-session/daily load previews, responsive layout, `_campos.html` extensions.

---

## 10. Minimal File-by-File Change Map

### 10.1 Required Phase 3 source changes (PROPOSED)

| Path | Current responsibility | Proposed Phase 3 change | Reason | Phase |
|---|---|---|---|---|
| `app/routers/parte.py` | Weekly `/parte` GET/POST (`ParteSemanal`, `semana`, weekly validation/upsert) | Replace handler logic with daily today-only GET/POST using `get_current_user`, `hoy()`, `get_today_state`/`save_daily_record` (and/or `discard_sessions`), form parsing for daily payload/sessions/tokens/explicit flags, ServiceResult→HTTP mapping (302/422/409/403/404/500 as applicable), no competing tx. Keep router prefix/path mounted. | Implement authorized daily workflow + Policy A HTTP mapping | 3 |
| `app/main.py` | Mounts `parte.router` | **No change expected** (keep include). | Route remains `/parte` | 3 (verify) |
| `app/services/parte_diaria.py` | Phase 2 domain service | **No change by default.** Only if a concrete defect is discovered; document separately and request authorization. | Preserve verified Policy A implementation | — |
| `app/services/parte_diaria_tokens.py` | Token/fingerprint service | **No change by default.** | Preserve verified contract | — |
| `app/auth.py`, `app/csrf.py`, `app/database.py`, `app/tiempo.py` | auth/CSRF/db/time infra | **No functional change expected.** | Reuse existing conventions | — |

### 10.2 Required Phase 3 route tests (PROPOSED)

| Path | Current responsibility | Proposed change | Reason | Phase |
|---|---|---|---|---|
| `tests/test_parte.py` | Weekly `/parte` behavior (one-per-week, week window, 1–5 weekly fields, RPE weekly rules, permissions) | **Rewrite/replace** for daily `/parte` contract: auth/role/CSRF, today authority, create/update, validation 422, 409 stale/create-race mapping (service/result-driven; reuse PG evidence rather than duplicating deep race proofs unless needed), discard intent/confirm flow, ownership/session binding exposed via 422/409, repopulation/conflict context. Keep test style consistent with `conftest`/`TestClient`. | Old weekly assumptions incompatible with daily router | 3 |
| `tests/conftest.py` | weekly `crear_parte`, auth/CSRF helpers, SQLite fixtures | Add minimal daily fixtures/helpers if useful (e.g., create `ParteDiaria`, set valid edit/discard tokens via service or token helpers, form payload builders). Keep weekly helpers if still used elsewhere; avoid breaking unrelated tests. | Support daily route tests | 3 |
| `tests/test_parte_diaria_service.py`, `tests/test_parte_diaria_schema.py`, `tests/test_parte_diaria_concurrency_pg.py` | domain/PG evidence | **No changes required** unless a verified defect is authorized. May be referenced by route tests only indirectly. | Preserve Phase 2/2.2.1 evidence | — |

### 10.3 Phase 4 template work (deferred)

| Path | Proposed later work | Phase |
|---|---|---|
| `app/templates/atleta/parte.html` | Full daily form redesign (A–E, 1–10, sessions, discard/409 UX) | 4 |
| `app/templates/_campos.html` | 1–10/range/multi-select/conditional helpers as needed | 4 |
| `app/templates/_tabbar.html`, `_nav.html`, `app/templates_config.py` | labels/badges/minimal globals if needed | 4/5 (minimal) |
| `app/static/*` | patterned progressive JS/CSS only if needed | 4 |

### 10.4 Existing files that must remain untouched in Phase 3 (PROPOSED)

Weekly model/migrations/consumers/visualizations not directly required: `app/models/parte.py`, historical alembic versions, `c4b8e2d91f07` (immutable), `app/services/bienestar.py|alertas.py|grafico.py` (unless a separately authorized minimal non-breaking need is proven — default **no**), `app/routers/panel.py|atletas.py|estadisticas.py|cuenta.py|pagos.py|asistencia.py|marcas.py|publico.py|auth.py`, `app/templates/atleta/inicio.html|mis_datos.html`, `app/templates/panel/*`, billing/marks/attendance/payment tests, `render.yaml/DEPLOY.md/README.md`, `scripts/seed*.py`.

---

## 11. Route-Level Acceptance Criteria and Regression Tests

| Group | Acceptance criteria | Minimum tests (PROPOSED) | PG required? |
|---|---|---|---|
| Authentication/authorization | Unauthenticated → login redirect; provisional password flow preserved; authenticated athlete can GET/POST own `/parte`; professor/other role rejected (403 or existing convention; weekly used 403 for profesor GET/POST); no cross-athlete targeting (uses `user.id`). | GET unauthenticated redirects; GET/POST as professor rejected; GET/POST as athlete succeeds to expected status/flow. | No |
| CSRF | Missing/invalid CSRF blocked by middleware (403/403.html path as app behaves); valid CSRF allows POST to reach handler. | POST without valid token blocked (align with `test_seguridad`/`test_asistencia` patterns); valid token + valid payload not blocked by CSRF. | No |
| Date authority | Server uses `hoy()`; client cannot select/override date for athlete save. Ignore/reject `fecha`/`semana` fields from client. | POST with manipulated date still affects today or is rejected/ignored; created/updated record has `fecha==hoy()` in controlled test context. | No |
| Persistence | Create daily record; update existing today record; explicit session ops work through service contract; changes persist across independent sessions/requests; no duplicate `(atleta_id,fecha)`. | GET empty → POST create → DB row exists; POST update with valid edit token → persisted changes; reload in new request shows update; uniqueness preserved. | No for basic; PG for race authority |
| Concurrency / Policy A mapping | Stale update → 409; create race → 409; conflict response carries fresh state/tokens/message; no silent overwrite; no blind retry. Router correctly maps `ServiceResult.status/conflict/stale`. | Unit-like route tests can simulate by: create record, capture stale token, mutate via service in separate step, POST with stale token → 409 and DB unchanged. Service-level PG tests remain authoritative for real races/locks; do **not** duplicate full PG proofs unnecessarily. | **PG authoritative** for real lock/race proofs (already REPORTED); route-level stale mapping can be tested on SQLite by service state changes. |
| Discard | Missing confirmation/invalid/expired/mismatched discard intent rejected safely; valid confirmation applies approved discard; ownership/record binding enforced; stale discard → 409/conflict, sessions preserved. | POST `entreno_hoy=false` with existing sessions and no confirm → 422 + discard token; valid confirm after token issuance → sessions removed/`entreno_hoy=false`; stale confirm after concurrent modification → 409 and sessions preserved. | PG not required for basic mapping; PG evidence exists for concurrent discard |
| Validation/repopulation | 422 on invalid payload; submitted values preserved in context; conditional rules/whitelists enforced by service. | Missing required fields/ranges/`otro` without text/`entreno_hoy=true` without sessions → 422. | No |

**Test files/fixtures (PROPOSED):** primary `tests/test_parte.py`; helpers in `tests/conftest.py`; reuse `con_csrf`, `entrar`, `crear_usuario` patterns. Inspect `test_asistencia.py`/`test_seguridad.py` for dynamic form + CSRF patterns.

---

## 12. Dependencies and Unresolved Decisions

| Dependency | Status |
|---|---|
| Phase 2/2.2.1 domain services + token contracts treated as stable | VERIFIED code / REPORTED PG validation |
| Policy A and signed discard protocol fixed | VERIFIED in authoritative plan + code |
| Phase 4 template redesign for full daily UX | UNRESOLVED (deferred) — Phase 3 provides stable contract |
| Phase 5 consumer migration (`parte_pendiente`, inicio/mis_datos/panel/stats cues) | UNRESOLVED — coordinate minimal non-breaking PRG targets/messages in Phase 3 |
| PO: alert semantics/copy, RPE display beyond per-session, `cruce_con_marcas` rule, wellness composite/thresholds, ACWR enablement | UNRESOLVED (out of Phase 3) |
| Exact 409 payload/context field names for Jinja/JS | UNRESOLVED — finalize in Phase 3 implementation consistent with app conventions |
| Single POST vs separate discard endpoint | UNRESOLVED — recommend single POST (Option A) |
| PRG redirect target for daily success (`/inicio?...` compatibility) | UNRESOLVED — decide explicitly in Phase 3 to avoid breaking existing cues |
| Full-replacement session mode exposure in UI | PROPOSED avoid in Phase 3/4 unless explicitly required; service supports only when flag set — default explicit deletes/adds/no omission |

---

## 13. Risks and Evidence Limitations

- **REPORTED, not re-run:** S-0029 PostgreSQL 16.15 disposable-container results (lock wait, service create race, discard, 379 passed). Local Docker daemon was unavailable in later context noted previously; this investigation did not execute DB tests.
- **SQLite cannot prove** `FOR UPDATE`/race serialization — route tests on SQLite can cover mapping/state but not PG authority (same caveat as Phase 2).
- **Service commits internally:** incorrect router transaction handling could cause closed-session/commit-order bugs. Must follow service-owned tx boundary.
- **Dynamic session form parsing:** Phase 3 must define stable field naming/indexing for `sessions[...]` and explicit delete ids consistent with `validate_and_normalize_sessions` / service API; Phase 4 will depend on it. **UNRESOLVED detail.**
- **Weekly test replacement impact:** `tests/test_parte.py` currently covers weekly behavior relied upon historically; rewriting it changes regression coverage. Ensure new tests cover required daily acceptance and do not silently drop security checks (CSRF/auth/ownership/422).
- **Phase 3 vs Phase 5 boundary:** changing `/parte` away from weekly semantics is required, but downstream `parte_pendiente`/dashboard/chart consumers remain weekly-oriented until Phase 5. Minimize unrelated breakage and document any temporary UI inconsistencies.
- **Git state interpretation:** ahead/behind relative to `origin` is **VERIFIED as `0 0` now**; history contains `12d6f3f` beyond `e810578`. No fetch was performed; remote may have moved since last local sync — **UNVERIFIED live remote state beyond local refs shown**.

---

## 14. Recommended Implementation Sequence (PROPOSED, after explicit authorization)

1. **Confirm contract details** (Phase 3 pre-impl): PRG target, 409 template context keys, form field names for sessions/explicit deletes/tokens/discard confirm, single-endpoint discard decision.
2. **Add/adjust daily test helpers** in `tests/conftest.py` (additive, minimal).
3. **Implement router thin controller** in `app/routers/parte.py`: auth/role/date authority, form parsing, `get_today_state` for GET, `save_daily_record` for POST, ServiceResult→HTTP mapping (302/422/409), preserve submitted values on 409/422, no competing tx.
4. **Rewrite `tests/test_parte.py`** for daily route acceptance (auth/CSRF/date/persistence/basic discard/409 mapping). Keep security assertions strong.
5. **Run targeted tests** (SQLite): `tests/test_parte.py`, related service/schema tests; optionally broader affected subset. **Do not claim PG race proofs beyond S-0029 unless revalidated on disposable PG.**
6. **Phase 4 handoff:** finalize template against stable context contract (§9). Do not start Phase 4 in Phase 3.

---

## Final Stop Condition

This plan is complete. **No implementation performed. No source, test, template, migration, or documentation files modified except this plan file.** No Phase 4 started. No commit/push/merge/deploy. Await explicit authorization before Phase 3 implementation.

**Repository modification statement:** The repository state was modified only by creating the planning document `C:\Archivos.Diego\atletismoWeb\atletismo\.kilo\plans\1792882624161-phase3-router-integration-readiness.md`. No application code, tests, templates, migrations, configuration, or Git history were changed by this investigation. This is **VERIFIED** by the commands executed/read operations and by the absence of tracked/staged/non-ignored untracked changes observed at inspection time (aside from the plan file write performed as an allowed plan artifact). If the plan file is considered an investigation artifact inside `.kilo/plans`, it is the sole change.