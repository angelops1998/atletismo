# Plan: Replace Weekly Athlete Reports with a Daily Tracking System

## 0. Verification Status (READ-ONLY, refreshed for this refinement)
- **Repository**: `C:\Archivos.Diego\atletismoWeb\atletismo` (git repo) — PASS.
- **Branch/HEAD**: `Baruc+Kilo` @ `74e4368` (`kilo markdown: S-0008_plan_session-ses_e8fd.md y plan: 1792882624161-daily-tracking-replacement.md`), up to date with `origin/Baruc+Kilo` — PASS.
- **Working tree**: clean (`nothing to commit, working tree clean`) — PASS. No existing user changes to preserve.
- **Previous session**: `ses_e8fd` available — `.kilo/kiloSesions/S-0006_ask_session-ses_e8fd.md` and `S-0008_plan_session-ses_e8fd.md` present; investigation reused and revalidated against current tree.
- **Repo evidence inspected (this refinement)**: `app/database.py` (`SessionLocal`/`get_db`, no `for_update`/`begin_nested` usage found), `app/csrf.py` (HMAC-SHA256 signing via `settings.secret_key`), `app/routers/atletas.py` & `app/routers/pagos.py` (`IntegrityError` → `db.rollback()` + user response), `alembic/env.py`, `render.yaml` (build runs `alembic upgrade head`), `DEPLOY.md`/`README.md` (manual `alembic upgrade head`), `app/services/alertas.py` (current `acwr`/thresholds), `app/routers/parte.py` (weekly form/upsert), `tests/conftest.py` (SQLite in-memory; `pool_static`).
- **Discrepancy from prior plan state**: HEAD/plan revision changed since last plan write (`01a676d`→`74e4368`, plus session file) — **no material product/architecture discrepancy**; plan updated accordingly.
- **Code changes made by this plan task**: **only this plan file updated** (authorized). No source/config/DB/migration/test/app-state changes — PASS.

## 1. Previous Audit Findings (ses_e8fd) — Reused / Superseded
### Reused (still valid)
- Weekly flow is centered on `app/routers/parte.py` (`GET/POST /parte`), `app/models/parte.py` (`ParteSemanal`, table `partes_semanales`, `uq_parte_atleta_semana (atleta_id, semana)`), `app/services/bienestar.py`, `app/services/alertas.py`.
- `semana` = Monday via `app/tiempo.lunes_de/lunes_actual`; TZ `America/La_Paz` in `app/tiempo.py` and DB session (`app/database.py` sets `timezone`).
- Upsert-by-week behavior and `SEMANAS_EDITABLES=1`.
- Consumers: `panel.py`, `atletas.py`, `estadisticas.py`, `cuenta.py`, templates, tests, `scripts/seed*.py`. Tests: `tests/test_parte.py`, `test_bienestar.py`, `test_alertas.py`, `test_consultas.py`, `conftest.py` (`crear_parte`).
### Superseded
- ses_e8fd Option B (keep weekly) superseded: objective requires **replacement and complete removal of functional dependencies** on the weekly model; weekly summaries derived from daily records; old table removed only after refs replaced; unrelated data preserved; never fabricate daily from historic weekly.

## 2. Current Weekly Architecture (verified)
| Layer | Files | Responsibility |
|---|---|---|
| Routes | `app/routers/parte.py` | `/parte` GET/POST; athlete-only; `_semana_pedida`; parse/validate; upsert `ParteSemanal` by `(atleta_id, semana)`. |
| Model | `app/models/parte.py` | `ParteSemanal` (`partes_semanales`): wellness 1-5, legacy `fatiga`, aggregate `sesiones/minutos_totales/rpe`, molestias 0-10, timestamps; unique `(atleta_id, semana)`. |
| Services | `app/services/bienestar.py` | `ITEMS/ETIQUETAS/RPE_ESCALA`; `bienestar_total/pct/semaforo/color_total`; `carga_ua=rpe*minutos_totales`; weekly series; `cruce_con_marcas` on `lunes_de`. |
| Services | `app/services/alertas.py` | `sin_parte`, bienestar/molestia/sueño/carga/peso/pago alerts; `acwr` (acute=last weekly carga / chronic=mean prior 4, needs >=2 prior weeks). |
| UI | `app/templates/atleta/parte.html`, `_campos.html` | Weekly form, CSRF, conditional molestia. |
| Consumers | `app/routers/panel.py,atletas.py,estadisticas.py,cuenta.py`; `app/templates/*`; `app/main.py` | `parte_pendiente`, weekly series/charts, alert cards. |
| DB/migrations | `alembic/versions/d61e48816ec5_*`, `a3f1c9e27b04_*`; `alembic/env.py` | Create `partes_semanales`; `fatiga` nullable. |
| Tests/fixtures/scripts | `tests/conftest.py,test_parte.py,test_bienestar.py,test_alertas.py,test_consultas.py`; `scripts/seed*.py` | Weekly rules/helpers. |

## 3. Complete Dependency Inventory (weekly → daily replacement)
> For each: current behavior / why weekly / required change / affected components / order & risk. (Paths verified.)

1. **`app/models/parte.py` (`ParteSemanal`, `partes_semanales`)** — weekly core, unique `(atleta_id,semana)`. *Change*: replace with daily+sessions; **remove model/table only after all refs replaced and hard gates pass**. *Order*: Phase 1 add; Phase 7 drop last. *Risk*: HIGH.
2. **`app/models/__init__.py`** — exports `ParteSemanal`. *Change*: export daily models; drop weekly at end. *Risk*: LOW.
3. **`app/routers/parte.py`** — week params, `_semana_pedida`, `SEMANAS_EDITABLES`, upsert by week. *Change*: server `hoy()` authority, athlete create/update **today only**, multi-session transactional save, locked+stale-proof discard confirmation, explicit session-ID operations, `IntegrityError` recovery. *Risk*: HIGH.
4. **`app/services/bienestar.py`** — 1-5 `ITEMS`/`MAXIMO`, `carga_ua`, weekly series, `cruce_con_marcas` on `lunes_de`. *Change*: daily 1-10 metrics, `carga_sesion/daily/weekly` contracts, derived weekly summaries over **reported days only** (missing ≠ 0), redefine pending as “registro de hoy”; adapt crosses. *Risk*: HIGH.
5. **`app/services/alertas.py`** — `sin_parte` weekly, thresholds 1-5/20, `acwr` weekly (verified). *Change*: split into implementable-now rules vs ACWR/ambiguous thresholds **deferred** (§9). *Risk*: HIGH.
6. **`app/services/grafico.py`** — generic; weekly comments. *Change*: minimal labels/caller alignment. *Risk*: LOW.
7. **`app/routers/panel.py,atletas.py,estadisticas.py,cuenta.py`** — `ParteSemanal`/weekly series/KPIs. *Change*: daily+derived summaries; keep coach workflows. *Risk*: MEDIUM-HIGH.
8. **Templates** (`atleta/parte.html,_campos.html,inicio.html,mis_datos.html`, `panel/*`, nav/tabbar) — weekly copy/1-5/RPE aggregate. *Change*: daily A–E form, 1-10 visuals, conditional illness/discomfort+`otro`, `entreno_hoy`, dynamic sessions w/ stable IDs & explicit remove, discard confirm UX backed by server, previews, error repopulation. *Risk*: MEDIUM.
9. **Tests/fixtures** (`tests/*`, `conftest.py` SQLite) — weekly helpers. *Change*: daily fixtures, rewrite/adapt; add PG-disposable migration/locking/concurrency validation path. *Risk*: MEDIUM.
10. **`scripts/seed.py`, `seed_5_atletas.py`** — `ParteSemanal`. *Change*: daily records+sessions. *Risk*: LOW.
11. **`alembic/versions/*` existing** — immutable history. *Change*: new forward revisions only; **drop revision kept separate and excluded from automatic deployment execution** (§7). *Risk*: HIGH.
12. **Deploy/docs refs** (`render.yaml` build `alembic upgrade head`; `DEPLOY.md`/`README.md`) — operational coupling to `upgrade head`. *Change*: update as part of safe deployment strategy (§7) in implementation PRs touching ops; **no changes now**. *Risk*: MEDIUM (ops) — documented.

**Grep gate (before any drop):** zero **functional** refs to `ParteSemanal|partes_semanales|parte_de_semana|partes_de|SEMANAS_EDITABLES|carga_ua` weekly helpers|`/parte?semana`|`sin_parte` in `app/`, `tests/`, `scripts/`. Exclude historical alembic migration filenames/content for `d61e48816ec5*` and `a3f1c9e27b04*` (they remain immutable history).

## 4. Proposed Daily Data Architecture (SQLAlchemy 2 + PostgreSQL)

### 4.1 Daily record — `partes_diarios` (`ParteDiaria`) *(resolved — technical naming)*
> **Naming (resolved, not a PO blocker):** uses existing repo convention — `partes_semanales` / `ParteSemanal` → `partes_diarios` / `ParteDiaria` (direct daily parallel; consistent table/model naming across the reporting domain).
- `id` PK; `atleta_id` FK→`users.id` `ondelete=CASCADE`, indexed, NOT NULL.
- `fecha` `Date` NOT NULL — **server-only** `tiempo.hoy()` (`America/La_Paz`); athlete ignores/rejects client date.
- **Unique** `('atleta_id','fecha')` `uq_parte_diaria_atleta_fecha` + indexes `(atleta_id, fecha desc)`, `fecha`.
- Wellness (required): `sueno_calidad, fatiga, dolor_muscular, estres, animo` Int `CHECK 1-10`; `horas_sueno` `Numeric(4,1)` `CHECK 0-24`. **Fatigue ≠ session RPE**.

**Wellness 1–10 scale definitions (established — not PO-pending):**
- **Sleep (`sueno_calidad`)**: 1–3 = *Deficient*; 4–6 = *Regular*; 7–10 = *Good*.
- **Fatigue (`fatiga`), muscular pain (`dolor_muscular`), stress (`estres`)**: 1–3 = *Low*; 4–6 = *Moderate*; 7–8 = *Elevated*; 9–10 = *Extreme*.
- **Mood (`animo`)**: 1–2 = *Very discouraged*; 3–4 = *Discouraged*; 5–6 = *Regular*; 7–8 = *Good*; 9–10 = *Excellent*.
UI labels/guidance must reflect these exact ranges and meanings (§6). Alert composite/cutoff rules built on these scales remain PO-pending where noted (§9.2, §13).
- `hay_molestia` Bool NOT NULL default false. `molestia_zona` **PG `ARRAY(String)`** nullable (whitelist: `cuello,hombros,espalda,cadera,gluteos,muslos,rodillas,pantorrillas,tobillos,pies,brazos,otro`). `molestia_zona_otra` `String(120)` nullable — **required iff `otro` selected; cleared otherwise** (backend). `molestia_dolor` Int `CHECK 1-10` nullable (required iff `hay_molestia`). `afecta_entrenamiento` Int `CHECK 0-3` nullable (required iff `hay_molestia`).
- `sintomas_enfermedad` Bool NOT NULL default false. `detalle_sintomas` Text nullable — **optional, displayed/accepted conditionally when `sintomas_enfermedad=true`; cleared when false; NOT mandatory without explicit PO approval** (preserves original requirement).
- `comentarios` Text nullable. `entreno_hoy` Bool NOT NULL.
- `enviado/actualizado` `DateTime(timezone=True)` `server_default now()`, `onupdate`.
- No mutable security-flag field for discard; confirmation uses signed token + DB-verified state (§5.3).

### 4.2 Training sessions — `sesiones_entrenamiento` (`SesionEntrenamiento`)
- `id` PK (**stable identifier, required**). `parte_diaria_id` FK→`partes_diarios.id` `ondelete=CASCADE`, indexed, NOT NULL.
- `orden` Int NOT NULL. `tipo_entrenamiento` String whitelist `velocidad_sprint,resistencia,fuerza,tecnica_coordinacion,movilidad_recuperacion,competencia,entrenamiento_mixto,otro`.
- `duracion_min` Int NOT NULL `CHECK > 0`; `rpe` Int NOT NULL `CHECK 1-10`.
- `carga_sesion` Int NOT NULL — **backend recomputed** `duracion_min*rpe` (never trust client); optional DB check.
- `comentarios_entrenamiento` Text nullable.
- ORM: `ParteDiaria.sesiones` 1:N, `cascade='all, delete-orphan'`, `order_by=orden,id`. DB cascade `ON DELETE CASCADE` is consistent; ORM orphan handling used only inside explicit transactional operations.

### 4.3 Load & aggregation contracts (authoritative)
- `carga_sesion = duracion_min × rpe`. `carga_diaria = Σ carga_sesion` for the record (`0` only for a **submitted** `entreno_hoy=false` record with no sessions).
- `carga_semanal = Σ carga_diaria` over Mon–Sun (`lunes_de`) **counting only existing daily records**.
- **Missing daily reports ≠ 0 load** (unknown). Aggregates/trends/averages/ACWR exclude missing days from observed sums/denominators; expose `dias_reportados` and missing counts. `entreno_hoy=false` is an observation; missing row is not.
- No physiological validity claimed.

### 4.4 Indexes/constraints
- `uq_parte_diaria_atleta_fecha`; date/athlete-date indexes; session FK index. Defense-in-depth checks as feasible.

## 5. Business Rules, Validation & Integrity (frontend + backend + DB)

### 5.1 Core record rules
1. **Unique** `(atleta_id, hoy())` via DB constraint + app logic. Concurrent create → `IntegrityError` recovery (§5.5).
2. **Server date authority**: `tiempo.hoy()` only for athlete create/update; no client date.
3. **Today upsert**: GET loads today; POST applies validated full state atomically to `(user.id,hoy())`.
4. **Ownership**: athlete mutations/reads scoped to `user.id`; 403/404 per conventions.
5. **Transactions**: all record+session mutations in a single DB transaction; rollback on error. **CSRF required** (reuse `app/csrf.py`/project patterns).

### 5.2 `entreno_hoy` and sessions (resolved)
6. **`entreno_hoy=true` ⇒ >= 1 valid session required** (frontend+backend; 422 if empty after validation).
7. **`entreno_hoy=false` ⇒ zero sessions persisted/displayed**. No silent deletion — changing true→false with existing sessions uses **only** §5.3 discard protocol.
8. **Validation**: `duracion_min>0`, `rpe` 1-10, `tipo` whitelisted, `carga_sesion` recomputed server-side.

### 5.3 Yes→No discard — stale-proof, locked, transactional (authoritative)
**Never** delete sessions silently; never rely on a freely-editable hidden boolean; never rely on JS-only confirmation. Cancel/invalid/stale ⇒ preserve all sessions.

**Stable session state + token binding**
- Compute `session_state_fingerprint` from **persisted** sessions in canonical order (`orden,id`): include `id,orden,tipo_entrenamiento,duracion_min,rpe,carga_sesion,comentarios_entrenamiento` (stable serialization + hash/HMAC). Fingerprint represents the exact discardable set.
- `discard_token` is **server-signed** (reuse HMAC pattern aligned with `app/csrf.py` / `settings.secret_key`; short expiry, e.g. 15 min) containing: `purpose=discard_sessions`, `atleta_id`, `fecha_iso`, `registro_id`, `session_state_fingerprint`, `exp`. Tampering fails signature; state change fails fingerprint match.

**Two-step flow**
- **Step 1 (intent, no deletion):** client requests `entreno_hoy=false` while persisted record has sessions. Server: acquire parent-record lock (§5.4), load record+sessions, recompute fingerprint, **do not delete**, render 422/confirmation-required response with count/summary, fresh `discard_token`, and form state preserved.
- **Step 2 (explicit confirm):** UI requires deliberate action (checkbox “Confirmo descartar N sesiones” + submit; optional modal). POST includes `discard_token` + explicit confirm flag. **Backend, in one transaction with lock held:**
  1. Lock `ParteDiaria` row for `(user.id,hoy())` (parent-record lock).
  2. Reload current sessions; recompute current fingerprint.
  3. Verify token signature/expiry/purpose/`atleta_id`/`fecha`/`registro_id` **and** `token.fingerprint == current_fingerprint`.
  4. If any check fails (stale/changed/wrong/missing) → **reject 422, delete nothing**, issue new token for current state.
  5. Only if valid → set `entreno_hoy=false`, remove sessions (delete-orphan/explicit) and commit **same transaction**.
- **Cancellation**: no confirmed valid POST → sessions preserved.

### 5.4 Concurrency, locking, and transaction conventions (evidence-based)
**Project evidence (verified):** `app/database.py` uses `SessionLocal(autocommit=False, autoflush=False)` + `get_db()` yield/finally close; **no `with_for_update`/`begin_nested` patterns found** in `app/`. Routers commit via `db.commit()` and handle `IntegrityError` with `db.rollback()` then user-facing response (`app/routers/atletas.py`, `pagos.py`).

**Required implementation details (PostgreSQL authoritative):**
- **Parent-record lock protocol (applies to every operation that modifies sessions or discards them):** lock the `ParteDiaria` row first, then validate token/fingerprint, then mutate sessions/record, then commit — all in the same request transaction. **PostgreSQL authoritative mechanism:** `SELECT ... FOR UPDATE` on the `ParteDiaria` row (`session.execute(select(ParteDiaria).where(...).with_for_update())` or equivalent). This serializes concurrent mutators for the same `(atleta,fecha)`.
- **SQLite/test caveat:** `SELECT FOR UPDATE` is **not** equivalent across databases and is effectively a no-op/unsupported semantics in SQLite (project tests use SQLite in-memory — `tests/conftest.py`). Therefore: **do not claim row-lock concurrency is validated under SQLite**. Specify **PostgreSQL disposable-DB tests** as authoritative for: discard race, concurrent session modification vs stale token, and concurrent create. Unit/functional logic tests may still run on SQLite; concurrency/locking acceptance is PG-only.
- **Session-state recheck after lock:** mandatory (prevents token validated against stale pre-lock snapshot).

### 5.5 Concurrent daily-record creation — correct SA recovery (required)
Unique `(atleta_id, fecha)` can raise `IntegrityError` on concurrent inserts. Plan must use a safe recovery compatible with project `IntegrityError` handling:
1. Perform find-or-create attempt in a transaction (optionally `SELECT FOR UPDATE` if row exists to stabilize update path).
2. On `IntegrityError` (likely unique violation): **`db.rollback()`** to clear failed transaction state (required with SQLAlchemy/Session after DB error).
3. Start/use a clean transaction scope and **reload** existing `ParteDiaria` for `(atleta_id, hoy())` (with lock if mutating sessions).
4. Reapply **already-validated** form data and session operations (respecting §5.3/§5.6) and `db.commit()`.
5. **No duplicate records, no partial session persistence**: never commit sessions against a rolled-back/ambiguous parent; all mutations only after valid parent state established.
- If reload fails unexpectedly, return controlled 409/422 error (not partial write). Log/handle per project norms.

### 5.6 Explicit session deletion/update semantics (required)
- **Stable IDs**: every persisted session has `id`. Forms/APIs that modify existing sessions submit `session_id` (hidden) per row; new rows have no id.
- **Ownership/record binding check**: backend verifies each submitted `session_id` belongs to the locked `ParteDiaria` for `(user.id,hoy())`. Reject unknown/foreign ids (422/403) — no cross-record mutation.
- **No implicit delete by omission (default safe rule):** omitting a session id from a generic payload **must not** delete it. **Individual session deletion is explicit and intentional** (e.g., a dedicated “remove session” action/flag with `session_id` processed transactionally, or an explicit `delete_session_ids[]` set). **Exception — explicit, validated complete replacement operation:** allowed **only** when the request is unambiguously marked as a full replacement (e.g., `session_update_mode=replace`), the server has locked the record, validated the full submitted set, and confirmed any discard implications; even then, deletions are the explicit result of that validated operation — not an accidental omission. Prefer explicit remove actions for UI simplicity/safety.
- **`entreno_hoy` true→false**: never uses implicit omission; uses §5.3 discard protocol only.
- Cancel/invalid confirmation preserves sessions. Avoid unnecessary new endpoints if form architecture supports (e.g., POST with action/mode + explicit ids).

### 5.7 Conditional fields (backend normalizes)
- `hay_molestia=false` ⇒ clear `molestia_zona`, `molestia_zona_otra`, `molestia_dolor`, `afecta_entrenamiento`.
- `hay_molestia=true` ⇒ require non-empty whitelisted `molestia_zona`, `molestia_dolor` 1-10, `afecta_entrenamiento` 0-3; if `otro` selected require trimmed non-empty `molestia_zona_otra` (max 120), else clear it.
- `sintomas_enfermedad=false` ⇒ clear `detalle_sintomas`. `true` ⇒ accept/display **optional** `detalle_sintomas` (trimmed) — **not mandatory without PO approval**.

## 6. Frontend Plan (responsive, reuse project conventions)
- Keep `/parte` route; redesign `app/templates/atleta/parte.html`; extend `_campos.html` (1-10 scale+guidance reflecting exact wellness definitions in §4.1: Sleep 1–3 Deficient/4–6 Regular/7–10 Good; Fatigue/Muscular pain/Stress 1–3 Low/4–6 Moderate/7–8 Elevated/9–10 Extreme; Mood 1–2 Very discouraged/3–4 Discouraged/5–6 Regular/7–8 Good/9–10 Excellent; multi-region select, conditional `otro` text). Progressive JS only if patterned in `app/static/` — no new deps.
- **5 categories A–E** per requirements (sleep/hours; fatigue/dolor muscular; estrés/ánimo; molestias conditional + `afecta_entrenamiento`; síntomas/`detalle_sintomas` optional conditional + comentarios).
- `entreno_hoy` toggle: hide training when No; when Yes dynamic session rows with **stable `session_id`**, explicit remove control, add/edit, per-session and daily load previews (server authoritative).
- Discard UX: explicit confirm step bound to server token/state; on 422 preserve values/sessions and show fresh confirmation state. CSRF preserved. Repopulate on errors.

## 7. Migration & Historical Data Strategy (safe, ops-aware)
**Established:** no fabrication from weekly; weekly model fully replaced; `partes_semanales` table+data dropped **only after all functional refs replaced**; unrelated data intact. Never execute prod migrations in this task.

### Alembic (forward-only; never modify `d61e48816ec5`, `a3f1c9e27b04`)
1. **Expand**: `<new>_add_partes_diarios_sesiones.py` — create new tables/constraints/indexes/checks only.
2. **Application replacement** (code/tests/scripts/templates/docs refs) until grep gate zero.
3. **Contract (separate, controlled)**: `<new>_drop_partes_semanales.py` — drops weekly table **only** under hard gates.

### Critical deployment safety (corrects auto-`upgrade head` risk)
**Evidence (verified):** `render.yaml` build command runs `alembic upgrade head`; `DEPLOY.md`/`README.md` instruct `alembic upgrade head`. **Separate Alembic revisions do NOT prevent execution if deploy tooling runs `upgrade head` to latest.**

**Required safe operational sequence:**
1. Create expand revision and **merge/deploy it such that automatic deployment runs only up to expand** — implementation must use a **controlled mechanism** (choose one, document in impl): e.g. keep drop revision out of deployed branch until authorized; or temporarily set Alembic target/branching so production upgrades stop at expand (e.g. deploy only expand commit; add drop in later authorized change); or change `render.yaml`/release process to `alembic upgrade <expand_revision>` for the deploy that must not drop, then a separately authorized job runs `alembic upgrade <drop_revision>`/`head`. **The plan requires the drop revision to be excluded from automatic deployment execution.**
2. Deploy app code that no longer depends on weekly model (can follow expand).
3. Verify: grep gate zero, full tests green, PG-disposable migration validation green, runtime smoke checks.
4. **Only then**, via **separately controlled, explicitly authorized operation** (not normal auto-deploy): take **verified backup/snapshot**, approved maintenance window, execute drop migration on production. Never in this task.
5. Rollback readiness: backup restore path; app rollback compatible with schema state.

**Historical impact:** `partes_semanales` rows become unavailable after drop (not migrated/fabricated). Unrelated modules/data unaffected.

## 8. Statistics, Load & Wellness Aggregation Contracts
- **Load**: `carga_sesion=duracion*rpe` (backend), `carga_diaria=Σ carga_sesion`, `carga_semanal=Σ carga_diaria` (Mon–Sun) over **reported days only**. Missing ≠ 0.
- **Wellness (1–10) + `horas_sueno`**: daily = stored observation. Weekly average = mean over **reported days only**; if `dias_reportados==0` → `None` (never 0). Report `dias_reportados` + context counts (`dias_con_entreno`, `dias_con_molestia`, `dias_con_sintomas`). Missing row ≠ low/zero value — always distinguish in data/UI.
- Charts/crosses: daily or derived-weekly from daily rows; `cruce_con_marcas` adapted to `fecha`/derived week. `grafico.py` generic.

### 8.3 ACWR — verified current state + deferred finalization (do not block core)
**Verified (repo evidence):** `app/services/alertas.py::acwr(serie)` uses `serie[-1]['carga']` as acute / mean of up to 4 prior weekly `carga` values as chronic; returns `None` if no last carga, <2 prior cargas, or zero chronic. Weekly `carga` from `bienestar.carga_ua = rpe * minutos_totales` (single aggregate per weekly report). Thresholds `ACWR_ALTO=1.5`, `ACWR_BAJO=0.8` (monitoring labels only).

**Viable technical candidates (to evaluate, not approve as final):** (A) keep weekly buckets derived from daily sums (acute=last complete week sum, chronic=mean prior 3–4 week sums) — closest continuity; (B) rolling 7-day acute / 28-day chronic ÷4 — common variant but **not validated here**. **Missing reports** must reduce observed coverage and can force `None`; never treat missing as 0.

**Minimum-data/coverage rules required (specify in impl design, validate on PG/data):** minimum observed days or minimum prior weekly buckets; explicit `None` when sparse. Exact windows, divisors, and coverage thresholds **require product-owner approval + calibration evidence**.

**Plan decision:** **isolate ACWR from the first implementation phase**. Phase 2/3 deliver core daily records, sessions, load/wellness contracts, and implementable alerts (§9.1) **without** reintroducing fixed ACWR business rules. ACWR adaptation ships only after approved formula/windows/coverage (deferred work item).

## 9. Alerts — separated by readiness (no mechanical transfer, no medical claims)

### 9.1 Implementable with established requirements (Phase 5, initial delivery)
| Key | Trigger (evidence-based on new data) | Missing-data behavior | Severity |
|---|---|---|---|
| `sin_registro_hoy` (replaces `sin_parte`) | No `ParteDiaria` for `(atleta, hoy())` | N/A (absence is the signal); distinct from “no training” | **PO approval** (suggest media) |
| `no_entreno_hoy` (informational) | Today record exists and `entreno_hoy=false` | Only if record exists | **informational, not a risk alert** (exclude from “problem” escalation) |
| `molestia_reportada` | `hay_molestia=true` | Missing report ⇒ no alert; report severity uses `molestia_dolor`/`afecta_entrenamiento` | **PO approval** |
| `sintomas_enfermedad` | `sintomas_enfermedad=true` | Missing ⇒ no alert; `detalle_sintomas` optional display | **PO approval** |
| `pago_vencido` | existing billing logic | unchanged | unchanged |

### 9.2 Requires explicit product-owner approval (defer fixed rules)
- `sin_registro_reciente` (enable? N days/window).
- `bienestar_bajo` / `item_minimo` / `caida_bienestar` on 1-10 — **no transfer** of 1-5/20 thresholds; composite formula, cutoffs, windows, and min observations need PO approval.
- `sueno_insuficiente` daily window/K over reported days.
- `carga_alta_dia` / unusual load absolute or personal-norm rule.
- Exact severities/copy for coach UX.
- ACWR thresholds/enablement post-adaptation.

### 9.3 Requires sufficient historical observations / calibration (defer)
- Personal-baseline alerts (drop/load norms), ACWR calibration, any relative percentile rules — implement only after data coverage policy + PO approval.

**Rule:** do not ship ambiguous thresholds as fixed business rules. Present monitoring indicators only, never medical diagnosis/injury prediction.

## 10. Security & Data Integrity
- Reuse `get_current_user`/role guards, CSRF (`app/csrf.py`), `get_db()`/SQLAlchemy session patterns. Ownership enforced on every query/mutation.
- Server date + server recompute + backend normalization. Signed discard token + lock + fingerprint recheck. Unique constraint + `IntegrityError` rollback/reload recovery. PG is authoritative for locking/concurrency validation.

## 11. Testing Strategy (plan; NOT RUN now)
**SQLite (existing fast path, `tests/conftest.py`) — logic/validation:** create/update today; unique handling path (where feasible); `hoy()` authority; `entreno_hoy=false` no sessions; 1/multi sessions + load math; invalid ranges/types; conditional `molestia`/`otro`/`molestia_zona_otra`; `sintomas_enfermedad` with optional `detalle_sintomas`; `entreno_hoy=true`+0 sessions → 422; cross-athlete blocked; aggregations missing≠0; non-ACWR alerts per approved subset.

**PostgreSQL disposable DB (authoritative) — migrations/concurrency/locking:** `alembic upgrade head` (expand path), `SELECT FOR UPDATE` discard/modify protocol, stale-token rejection under concurrent change, concurrent create `IntegrityError` recovery, drop-migration dry-run in disposable env, ARRAY/check behavior. **Do not treat SQLite as proof of PG row-lock behavior.**

Full `pytest` regression — NOT RUN. Modify/replace: `conftest.py`, `test_parte.py` (rewrite), `test_bienestar.py`, `test_alertas.py`, `test_consultas.py`; keep unrelated green.

## 12. Implementation Phases (refined, dependency-ordered)

### Phase 0 — Prep & guardrails
- Inventory grep baseline; confirm test/PG-disposable strategy. **Acceptance**: baseline documented.

### Phase 1 — New schema (expand, forward-only)
- **Files**: `app/models/parte_diaria.py`, `sesion_entrenamiento.py` (or project style), `app/models/__init__.py`, `alembic/versions/<new>_add_partes_diarios_sesiones.py`. No historical migration edits.
- **Acceptance**: imports OK; applies on disposable PG; unrelated tables intact.

### Phase 2 — Core domain services (no ACWR business rule)
- **Files**: `app/services/bienestar.py` (careful evolution) and/or focused service module, `alertas.py` (implementable subset only), `grafico.py` minimal.
- **Acceptance**: load/wellness/aggregation contracts + missing≠0; ACWR isolated/deferred (no fixed new threshold behavior shipped without approval).

### Phase 3 — Router/workflow (transactional, locked discard, explicit session ops, IntegrityError recovery)
- **Files**: `app/routers/parte.py`, discard-token helper aligned with `app/csrf.py`/secret patterns.
- **Acceptance**: server date/ownership/CSRF; `entreno_hoy` rules; explicit session IDs/remove; stale-proof discard w/ PG-authoritative lock protocol; correct `IntegrityError` rollback/reload/reapply.

### Phase 4 — UI/templates
- **Files**: `app/templates/atleta/parte.html`, `_campos.html`, athlete/panel/nav templates, minimal static JS/CSS if patterned.
- **Acceptance**: A–E form, 1-10 visuals, `otro`+`molestia_zona_otra`, optional conditional `detalle_sintomas`, dynamic sessions (stable IDs/explicit remove), discard confirm UX, previews, repopulation.

### Phase 5 — Consumers & de-weekly-fy (excluding deferred alerts)
- **Files**: `app/routers/panel.py,atletas.py,estadisticas.py,cuenta.py`, templates, `scripts/seed*.py`.
- **Acceptance**: zero functional weekly refs in `app/tests/scripts` (historical alembic excluded); dashboards coherent; deferred alerts/ACWR not falsely enabled.

### Phase 6 — Tests, seeds, regression, PG validation
- **Files**: `tests/*`, `conftest.py`, seeds.
- **Acceptance**: `pytest` green (SQLite path) + PG-disposable validations for migrations/locking/concurrency/`IntegrityError` recovery.

### Phase 7 — Remove weekly (last, controlled ops)
- **Files**: remove `ParteSemanal`/imports; `alembic/versions/<new>_drop_partes_semanales.py`; `README.md`,`DEPLOY.md`,`render.yaml` deployment mechanism adjusted so **drop is not auto-executed**.
- **Hard gates**: Phase 6 green; grep gate zero; **verified backup/snapshot + explicit approval + maintenance window**; separately controlled execution only. **Never run in prod here.**

## 13. Decisions — Established / Resolved / Technical (repo-safe) / Needs PO Approval

**Established (requirements):** daily unique per athlete+local date; server `America/La_Paz`; athlete today-only; multi-sessions; load formulas `duracion*RPE`, daily sum, weekly sum over reported days; fatigue independent of RPE; `entreno_hoy` rules + secure explicit discard (no silent/JS-only, cancel preserves); conditional validation/cleanup; transactional+concurrent-safe; stats from daily, weekly derived; missing ≠ 0; no fabrication from weekly; replace deps; drop old table+data after refs replaced (controlled); preserve unrelated data; no prod migration execution.

**Resolved (this plan):** stale-proof signed `discard_token` bound to locked state fingerprint; discard verified in-transaction after lock; all session-mutating ops use parent-record lock protocol (PG authoritative); `entreno_hoy=true` ⇒ >=1 session; stable session IDs + explicit delete (no implicit omission except explicit validated full-replacement mode); `IntegrityError` rollback→reload→reapply; `molestia_zona_otra` conditional; `detalle_sintomas` **optional** when symptoms true (not mandatory w/o PO); ACWR isolated from Phase 1 core; safe deployment sequence excluding drop from auto `upgrade head`.

**Technical choices resolvable from repo conventions (no PO approval needed):** reuse HMAC signing pattern (`app/csrf.py`/secret), `get_db`/`db.commit()`/`db.rollback()` flow, FastAPI+Jinja+CSRF patterns, indexed form fields, keep `/parte` route, Alembic forward-only workflow, PG-disposable validation for PG-specific behavior.

**Requires product-owner approval (behavior/rules/copy):**
1. ACWR windows, coverage/min-data rules, and thresholds (or confirm deferral).
2. 1-10 wellness composite formula/cutoffs and `item_minimo` semantics.
3. `sin_registro_reciente` enablement/N.
4. Alert severities and coach-facing copy (including `sin_registro_hoy`, molestia, síntomas).
5. `carga_alta_dia` / `sueno_insuficiente` / drop-baseline rules.

## 14. Dependency Map (text)
`tiempo.hoy` → `routers/parte` (auth+CSRF+ownership+server date) → validate/normalize → **lock parent record `ParteDiaria` (PG)** → (discard: verify signed token+fingerprint) → **single transaction** → upsert `ParteDiaria` `(atleta,fecha)` + explicit `SesionEntrenamiento` mutations → `services` (loads, reported-day aggregations, implementable alerts; ACWR deferred) → `routers/panel,atletas,estadisticas,cuenta` → templates. `alembic expand` → code/tests/scripts → controlled `alembic drop` last (excluded from auto-deploy).

## 15. Migration & Deployment Safety Conditions (hard)
- Never modify historical Alembic revisions. Expand and drop in **separate** forward revisions.
- **Drop migration never auto-executed** despite `upgrade head` tooling — enforce via controlled deployment/revision targeting.
- Drop only after: zero functional weekly refs, Phase 6 green, disposable-PG validation, **verified backup/snapshot**, explicit authorization, maintenance window.
- Preserve unrelated modules/data. No prod execution in this task.

## 16. Components Ready for First Implementation Phase (scoped)
**Ready (after this plan approval):** Phase 1 schema; Phase 2 load/wellness/missing-aggregation contracts and **non-ambiguous** plumbing; Phase 3 core daily create/update, `entreno_hoy` rules, explicit session IDs/remove, locked discard protocol, `IntegrityError` recovery; Phase 4 form/UI structure (with placeholder-approved copy if PO defers text); Phase 5 consumer migration for core tracking; Phase 6 tests/PG validation for core.

**Explicitly deferred:** ACWR final formula/windows/thresholds; `bienestar_bajo/item_minimo/caida_bienestar` composites/cutoffs; `sin_registro_reciente`; `carga_alta_dia`/`sueno_insuficiente` fixed rules; any calibrated personal-baseline alerts; final PO copy/severities beyond safe informational defaults.

## 17. Risks Remaining
- PG-vs-SQLite behavior (locking, ARRAY, checks) — mitigated by PG-disposable validation.
- Deployment misconfiguration could run drop if `upgrade head` not controlled — mitigated by §7/§15 hard gates.
- Alert/UX behavior change; missing≠0 interpretation requires clear UI.
- Discard-token/fingerprint complexity — needs careful tests.
- Unapproved thresholds remain deferred (prevents unsafe business rules).

## 18. Applicable Verification Results
| Check | Result |
|---|---|
| Repo/branch/HEAD/clean tree (refreshed) | PASS |
| ses_e8fd context available | PASS |
| Evidence inspected (`database.py,csrf.py,routers,alembic,render.yaml,DEPLOY,alertas,parte,conftest`) | PASS |
| Only authorized plan file updated | PASS |
| Source/DB/migrations/tests modified; migrations/tests executed | NO / NOT RUN (PASS) |

## 19. Recommendation
**Ready for scoped Code mode** for **Phases 1–6 core tracking** (daily records, multi-sessions with stable IDs/explicit deletes, secure locked discard, `IntegrityError` recovery, load/aggregation with missing≠0, UI, consumer migration, non-ambiguous alerts), **with ACWR and ambiguous alert thresholds explicitly deferred** until §13 PO approvals are provided. Do **not** execute or auto-deploy the drop migration; follow §7/§15.
