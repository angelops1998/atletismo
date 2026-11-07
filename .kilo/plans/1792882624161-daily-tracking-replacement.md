# Plan: Replace Weekly Athlete Reports with a Daily Tracking System

## 0. Verification Status (READ-ONLY, refreshed for this plan revision)
- **Repository**: `C:\Archivos.Diego\atletismoWeb\atletismo` (git repo) — PASS.
- **Branch/HEAD**: `Baruc+Kilo` @ `01a676d` (`kilo markdown: S-0007_plan_session-ses_e8fd.md y plan: 1792882624161-daily-tracking-replacement.md`), up to date with `origin/Baruc+Kilo` — PASS.
- **Working tree**: clean (`nothing to commit, working tree clean`) — PASS. No existing user changes to preserve.
- **Previous session**: `.kilo/kiloSesions/S-0006_ask_session-ses_e8fd.md` (`ses_e8fd`) — FOUND; investigation reused and revalidated against current tree. Session artifacts `S-0007_*` present on branch.
- **Code changes made by this plan task**: **only this plan file updated** (authorized planning document). No source/config/DB/migration/test/app-state changes — PASS.

## 1. Previous Audit Findings (ses_e8fd) — Reused / Superseded
### Reused (still valid)
- Weekly flow is centered on `app/routers/parte.py` (`GET/POST /parte`), `app/models/parte.py` (`ParteSemanal`, table `partes_semanales`, `uq_parte_atleta_semana (atleta_id, semana)`), `app/services/bienestar.py`, `app/services/alertas.py`.
- `semana` = Monday via `app/tiempo.lunes_de/lunes_actual`; TZ `America/La_Paz` in `app/tiempo.py` and DB session (`app/database.py` sets `timezone`).
- Upsert-by-week behavior (edit existing row, not duplicate) and `SEMANAS_EDITABLES=1`.
- Calculations mostly derived at runtime in `bienestar.py`; consumers: `panel.py`, `atletas.py`, `estadisticas.py`, `cuenta.py`, templates, tests, `scripts/seed*.py`.
- Tests: `tests/test_parte.py`, `tests/test_bienestar.py`, `tests/test_alertas.py`, `tests/test_consultas.py`, `tests/conftest.py` helpers (`crear_parte`, `ParteSemanal`).

### Superseded by this objective
- ses_e8fd recommended **Option B (complementary daily entity, keep weekly)** as least disruptive for “independent daily reports while preserving historical weekly records”.
- **This task’s objective explicitly requires replacement and complete removal of functional dependencies on the old weekly model**, with weekly summaries derived from daily records and old table removed only after references replaced. The plan follows the **current objective** (replacement) while preserving **unrelated data** and never fabricating daily records from historical weekly data.

## 2. Current Weekly Architecture (verified)
| Layer | Files | Responsibility |
|---|---|---|
| Routes | `app/routers/parte.py` | `/parte` GET/POST; role athlete-only; week selection `_semana_pedida`; form parse/validate; upsert `ParteSemanal` by `(atleta_id, semana)`; redirect `/inicio?parte=1`. |
| Model | `app/models/parte.py` | `ParteSemanal` (`partes_semanales`): wellness 1-5 (`sueno_calidad,dolor_muscular,estres,animo`), `fatiga` legacy nullable, sleep/nutrition/body optional, `sesiones/minutos_totales/rpe` (RPE 1-10), `molestias/muestra_zona/dolor 0-10`, `comentarios`, timestamps. |
| Services | `app/services/bienestar.py` | `ITEMS/ETIQUETAS/RPE_ESCALA`; `bienestar_total/pct/semaforo/color_total`; `carga_ua` (`rpe*minutos_totales`); `parte_de_semana/partes_de/series_*`; `serie_grupo`; `promedio_items_grupo`; `cruce_con_marcas` (joins on `lunes_de(marca.fecha)`). |
| Services | `app/services/alertas.py` | `sin_parte`, `bienestar_bajo/item_minimo/caida_bienestar`, `molestia`, `sueno_insuficiente`, `carga` (ACWR via `serie.carga`), `peso`, `pago_vencido`; `del_atleta/del_club`. |
| UI | `app/templates/atleta/parte.html`, `_campos.html` macros | Weekly form, CSRF, conditional molestia block. |
| Consumers | `app/routers/panel.py`, `atletas.py`, `estadisticas.py`, `cuenta.py`; `app/templates/atleta/inicio.html`, `mis_datos.html`, `panel/*`; `app/main.py` nav wiring (`parte_pendiente` flags) | “Parte pendiente”, weekly series/charts, alert cards, athlete evolution. |
| DB | `alembic/versions/d61e48816ec5_*`, `a3f1c9e27b04_*` | Create `partes_semanales`; make `fatiga` nullable. |
| Tests/fixtures | `tests/test_parte.py`, `test_bienestar.py`, `test_alertas.py`, `test_consultas.py`, `conftest.py` | Weekly rules, RPE, ACWR/alerts, query patterns, helpers. |
| Scripts | `scripts/seed.py`, `seed_5_atletas.py` | Generate `ParteSemanal` data. |

## 3. Complete Dependency Inventory (weekly → daily replacement)
> For each: current behavior / why weekly / required change / affected components / order & risk.

1. **`app/models/parte.py` (`ParteSemanal`, `partes_semanales`)** — Core weekly entity, unique `(atleta_id, semana)`. *Change*: replace with daily model + sessions (see §4); remove weekly model/table only after all refs replaced. *Affects*: every consumer below. *Order*: Phase 1-2 (model/migration) but deletion is **last**. *Risk*: HIGH.
2. **`app/models/__init__.py`** — exports `ParteSemanal`. *Change*: export new daily models; drop `ParteSemanal` at end. *Risk*: LOW.
3. **`app/routers/parte.py`** — `/parte` GET/POST, week params, athlete edits current/previous week logic, `SEMANAS_EDITABLES`, upsert by week. *Change*: daily UX/API (server date = `tiempo.hoy()` in `America/La_Paz`), athlete may create/update **today only** (no date picker), upsert by `(atleta_id, fecha=hoy)`, multi-session payload, transactional save, explicit discard-sessions confirmation. *Affects*: templates, tests, nav pending flag. *Order*: Phase 3. *Risk*: HIGH.
4. **`app/services/bienestar.py`** — weekly `ITEMS` (4x1-5) + `fatiga` legacy; `carga_ua=rpe*minutos_totales`; all series keyed by `semana`; `cruce_con_marcas` joins on `lunes_de`. *Change*: **major refactor/rename of domain logic** to daily tracking: new scales 1-10, fatigue independent, daily load = `sum(session.duracion_min*session.rpe)`, derive weekly summaries from daily rows for charts/stats where needed, redefine `parte_pendiente` as “has today’s record?”, adapt `cruce_con_marcas` to join daily records by `fecha`. Keep API shape stable where possible for templates or update callers coherently. *Affects*: alerts, panel, atletas, estadisticas, cuenta, charts. *Order*: Phase 2 (core services) before/with routers. *Risk*: HIGH.
5. **`app/services/alertas.py`** — “sin_parte esta semana”, uses `serie[-1]` weekly, thresholds `BIENESTAR_BAJO` over 20 (`MAXIMO=len(ITEMS)*5`), sleep/carga/ACWR on weekly series. *Change*: redefine to daily semantics (e.g., missing today / recent days — **decision point, see §11**), recalc thresholds for 1-10 scales and daily/derived-weekly load; `afecta_entrenamiento` can inform severity (use carefully, not diagnosis). *Risk*: HIGH (behavioral).
6. **`app/services/grafico.py`** — doc/comments reference weekly gaps; functions generic. *Change*: minimal; update labels/comments and any weekly assumptions in callers. *Risk*: LOW.
7. **`app/routers/panel.py`, `atletas.py`, `estadisticas.py`, `cuenta.py`** — import `ParteSemanal`/`bienestar.parte_de_semana` weekly series, “partes cargados esta semana”, `maximo/bienestar_total` display. *Change*: switch to daily queries/derived summaries, update KPIs (“registros hoy / esta semana derivados”), keep coach workflows intact. *Risk*: MEDIUM-HIGH.
8. **`app/templates/atleta/parte.html`, `_campos.html`, `atleta/inicio.html`, `mis_datos.html`, `panel/*`, `base.html/_nav/_tabbar`** — weekly copy, 1-5 scales, RPE/sessions as aggregate fields, “parte pendiente”. *Change*: full daily form (5 categories A-E, 1-10 scales + labels, conditional illness/discomfort, `entreno_hoy`, dynamic sessions CRUD UI, load previews, preserve values on error); update dashboard copy/metrics. *Risk*: MEDIUM (UX) but must preserve CSRF/project conventions.
9. **`tests/conftest.py`, `test_parte.py`, `test_bienestar.py`, `test_alertas.py`, `test_consultas.py`** — fixtures/helpers create `ParteSemanal`. *Change*: new fixtures for daily+sessions; replace/adapt tests per §8; remove weekly-only tests after coverage parity. *Risk*: MEDIUM.
10. **`scripts/seed.py`, `scripts/seed_5_atletas.py`** — create `ParteSemanal`. *Change*: generate daily records + sessions; never backfill from historic weekly. *Risk*: LOW.
11. **`alembic/versions/*` (existing)** — historical; **do not edit**. *Change*: add new forward migration(s); final migration drops `partes_semanales` only after app deps removed. *Risk*: HIGH.
12. **Docs/config text** (`README.md`, `DEPLOY.md`, any in-app text) — mention `partes_semanales`/weekly. *Change*: update in implementation (documentation edits allowed in implementation phase; **not done now**). *Risk*: LOW.

**Indirect deps to grep during implementation** (must be zero before drop-table migration): `ParteSemanal`, `partes_semanales`, `parte_de_semana`, `partes_de`, `semana=` in tracking context, `bienestar.ITEMS/MAXIMO/UMBRAL_*` weekly semantics, `/parte?semana`, `SEMANAS_EDITABLES`, `carga_ua` weekly fields, `serie_grupo` weekly, `sin_parte`.

## 4. Proposed Daily Data Architecture (SQLAlchemy 2 + PostgreSQL)

### 4.1 Daily record table — `registros_diarios` (`RegistroDiario`) **(recommended naming; keep `/parte` route/UX naming independent if desired)**
- `id` PK.
- `atleta_id` FK → `users.id` `ondelete=CASCADE`, indexed, NOT NULL.
- `fecha` `Date` NOT NULL — **server-only authority**: set from `tiempo.hoy()` (`America/La_Paz`). Athlete GET/POST **must ignore/reject any client-supplied date** for create/update; coaches may query by date.
- **Uniqueness (DB-level, required):** `UniqueConstraint('atleta_id','fecha', name='uq_registro_diario_atleta_fecha')` + supporting index `(atleta_id, fecha desc)` / `fecha`.
- Wellness (required unless noted): `sueno_calidad` Int `CHECK 1-10`; `horas_sueno` `Numeric(4,1)` `CHECK 0-24`; `fatiga, dolor_muscular, estres, animo` Int `CHECK 1-10`. **Fatigue and session RPE remain independent variables** (different entities/meanings).
- `hay_molestia` Boolean NOT NULL default false.
- `molestia_zona` **PG `ARRAY(String)`** nullable/empty when no molestia. **Backend whitelist (canonical keys):** `cuello,hombros,espalda,cadera,gluteos,muslos,rodillas,pantorrillas,tobillos,pies,brazos,otro`. (Alt: normalized join table — higher complexity; ARRAY + whitelist recommended for PG target/fixed set.)
- `molestia_zona_otra` `String(120)`/`Text` nullable — **required iff `otro` selected**; ignored/cleared otherwise (backend authoritative). *(Resolves `otro`.)*
- `molestia_dolor` Int `CHECK 1-10`, nullable — required iff `hay_molestia`.
- `afecta_entrenamiento` Int `CHECK 0-3`, nullable — required iff `hay_molestia`.
- `sintomas_enfermedad` Boolean NOT NULL default false.
- `detalle_sintomas` Text nullable — required iff `sintomas_enfermedad`; cleared otherwise.
- `comentarios` Text nullable.
- `entreno_hoy` Boolean NOT NULL.
- `sesiones_descartadas_en`/token mechanism **not stored as a mutable security flag alone** — see §5 (stale-proof confirmation). No freely-editable hidden boolean is sufficient as sole authority.
- `enviado/actualizado` `DateTime(timezone=True)`, `server_default now()`, `onupdate=now()`.

### 4.2 Training sessions — `sesiones_entrenamiento` (`SesionEntrenamiento`)
- `id` PK.
- `registro_diario_id` FK → `registros_diarios.id` `ondelete=CASCADE`, indexed, NOT NULL.
- `orden` Int/SmallInt NOT NULL (stable UI/order).
- `tipo_entrenamiento` String NOT NULL, whitelist: `velocidad_sprint,resistencia,fuerza,tecnica_coordinacion,movilidad_recuperacion,competencia,entrenamiento_mixto,otro`.
- `duracion_min` Int NOT NULL `CHECK (duracion_min > 0)`.
- `rpe` Int NOT NULL `CHECK 1-10`.
- `carga_sesion` Int NOT NULL — **computed authoritatively by backend** as `duracion_min * rpe` on every write (never trust client). Optional DB `CHECK (carga_sesion = duracion_min * rpe)` for defense in depth.
- `comentarios_entrenamiento` Text nullable.
- **Relationship**: `RegistroDiario.sesiones` 1:N, `cascade='all, delete-orphan'`, `passive_deletes` aligned with DB cascade, `order_by=orden,id`. **Replacement/deletion happens only via transactional service logic** (never silent).

### 4.3 Load & aggregation contracts (authoritative)
- **Individual session load** = `duracion_min × rpe` (integer AU).
- **Daily load** = `sum(carga_sesion)` over sessions of that `RegistroDiario` for `fecha`; if no sessions (valid only when `entreno_hoy=false`), daily load is `0` **for that submitted record**. **Persist `carga_sesion` per row; derive daily load by sum in service/query** (recommended — avoids drift).
- **Weekly load** = `sum(daily_load)` for days in the week (Mon–Sun via `lunes_de`) **where a daily record exists**.
- **Missing daily reports MUST NOT be interpreted as zero training load** in aggregates, trends, ACWR, or averages: exclude missing days from denominators/sums that represent “observed load”; represent absence explicitly (`None`/missing count). (A submitted `entreno_hoy=false` record is an observation with `0` load; a missing record is unknown.)
- No physiological validity claimed for thresholds; monitoring indicators only.

### 4.4 Indexes/constraints & cascade consistency
- `uq_registro_diario_atleta_fecha` (critical, concurrency safety).
- Indexes `(atleta_id, fecha desc)`, `fecha`; `sesiones_entrenamiento(registro_diario_id)`.
- DB FK `ondelete=CASCADE` from sessions → registro; ORM `delete-orphan` for in-app replacement. **Consistency rule**: session add/edit/remove/replace occurs only inside the same transaction as record update and only after authorization + confirmation checks.

## 5. Business Rules, Validation & Integrity (frontend + backend + DB)

### 5.1 Core record rules
1. **One record/athlete/local date**: DB unique + find-or-create on `(atleta_id, hoy())`; concurrent submits → handle `IntegrityError` and retry update once in-request/transaction-safe pattern; never duplicate.
2. **Date authority**: `tiempo.hoy()` (`America/La_Paz`) is the sole date for athlete create/update. No athlete date picker; ignore/reject client date overrides.
3. **Create/update today**: GET loads today if exists; POST upserts `(user.id, hoy())` and applies full validated state atomically.
4. **Athlete ownership**: scope all reads/writes to `user.id`; 403/404 as per project conventions. Coaches/profs read-only per existing auth.
5. **Transactions**: **all record + session mutations in a single DB transaction**; rollback on any validation/integrity error.

### 5.2 Training / `entreno_hoy` (resolved)
6. **`entreno_hoy=true` ⇒ require >= 1 valid session** (recommended & specified). Frontend and backend must agree: backend returns 422 with clear error if true and session list empty after parsing/validation.
7. **`entreno_hoy=false` ⇒ zero sessions persisted/displayed**. Backend rejects submitted session rows when false (or discards them only via the explicit confirmed discard flow below when replacing existing sessions).
8. **Session validity**: `duracion_min > 0` integer, `rpe` 1-10, `tipo` in whitelist, `carga_sesion` recomputed server-side.

### 5.3 Secure two-step discard confirmation for Yes→No (resolves A) — **authoritative, stale-proof, transactional**
**Required behavior**: existing persisted sessions never deleted silently; changing Yes→No requires explicit confirmation; cancel preserves all; backend authoritative; **not** a freely-editable boolean hidden field alone.

**Design (two-step, bound to exact state):**
- **Step 1 (intent / GET-or-POST preview state, server-rendered):** When the current persisted record has `entreno_hoy=true` and `count(sesiones)>0`, and user submits/changes `entreno_hoy=false`, backend **does not delete**. It returns the form (422/200 validation-response pattern consistent with project — prefer 422 “confirmation required”) with: `discard_confirmation_required=true`, `sesiones_a_descartar` count/summary, and a server-generated **`discard_token`**.
- **`discard_token`** = HMAC-signed payload (reuse project secret/CSRF-signing approach, e.g. `itsdangerous`/HMAC like CSRF if available, or equivalent) containing: `atleta_id`, `fecha` (`hoy()`), `registro_id` (if exists), **`session_state_hash`** (hash of ordered persisted session ids + `(orden,tipo,duracion_min,rpe,carga_sesion,comentarios)` or stable fingerprint), and short expiry (e.g. 15 min). Token is **opaque to trust except signature+payload checks**; it is not “freely editable” authority because tampering breaks signature and mismatched state breaks verification.
- **UI step 2**: shows explicit message, requires deliberate user action (checkbox “Confirmo descartar N sesiones” + submit button, and/or modal confirm). JS improves UX but is not relied upon. On submit, includes `confirmar_descartar_sesiones=on` (or explicit value) **and** the hidden `discard_token` echoed back.
- **Backend verification (must pass before any deletion)** inside the **same transaction**:
  1. Load current `RegistroDiario` for `(user.id, hoy())` with sessions (lock row as appropriate for update if project uses `SELECT FOR UPDATE` patterns; otherwise rely on transaction + recheck).
  2. Recompute current `session_state_hash` from persisted sessions.
  3. Validate `discard_token` signature, expiry, `atleta_id==user.id`, `fecha==hoy()`, `registro_id` matches (or consistent), and **`session_state_hash` matches current**. 
  4. If **any check fails** (stale token, sessions changed/added/removed after confirmation initiated, wrong user/date) → **reject (422), do not delete**, re-render requiring fresh confirmation with a new token.
  5. Only if valid: set `entreno_hoy=false`, **delete sessions** (delete-orphan/explicit), clear session-related aggregates as derived, commit atomically.
- **Cancel**: no valid confirmed POST occurs → sessions preserved. Submitting without valid token+confirm when discard needed → 422, preserved.
- **Idempotent**: if no persisted sessions exist, no confirmation required.

### 5.4 Conditional fields (backend normalizes; frontend mirrors)
9. `hay_molestia=false` ⇒ clear/ignore `molestia_zona`, `molestia_zona_otra`, `molestia_dolor`, `afecta_entrenamiento`.
10. `hay_molestia=true` ⇒ require `molestia_zona` non-empty subset of whitelist, `molestia_dolor` 1-10, `afecta_entrenamiento` 0-3. If `otro` in `molestia_zona` ⇒ require non-empty `molestia_zona_otra` (trimmed, max length); if `otro` absent ⇒ clear `molestia_zona_otra`.
11. `sintomas_enfermedad=false` ⇒ clear/ignore `detalle_sintomas`. `true` ⇒ require `detalle_sintomas` (trimmed, non-empty) unless PO relaxes — **recommend required for clinical usefulness**.

### 5.5 Validation, concurrency, security
12. Backend authoritative for all ranges/whitelists/conditionals/load math. CSRF required (project `csrf_input`/validation). 
13. Concurrency: unique `(atleta_id,fecha)` + transaction; stale discard token prevents cross-state deletion.

## 6. Frontend Plan (responsive, reuse project conventions)
**Files**: keep `/parte` route; redesign `app/templates/atleta/parte.html`; extend `app/templates/_campos.html` (1-10 scale macro w/ labels+guidance, multi-select regions + conditional `otro` text). Minimal progressive JS in existing static pattern if present (verify `app/static/`) for dynamic session rows & discard modal/step — **no new deps**.

- **5 categories**: (A) Descanso/sueño `sueno_calidad` 1-10, `horas_sueno`. (B) Fatiga/recuperación `fatiga` 1-10, `dolor_muscular` 1-10. (C) Psicológico `estres` 1-10, `animo` 1-10. (D) Condición/molestias `hay_molestia` → multi `molestia_zona` + `molestia_zona_otra` (shown/required iff `otro`), `molestia_dolor`, `afecta_entrenamiento`. (E) Salud/observaciones `sintomas_enfermedad` → `detalle_sintomas`, `comentarios`.
- `entreno_hoy` after wellness: hide training when No; when Yes show dynamic session list (add/edit/remove), per-session load preview and daily total (JS) — server recomputes.
- Yes→No with existing sessions: UI requires explicit step; posts `discard_token` + confirm flag; if backend returns confirmation-required, preserve visible state and show warning/count.
- Repopulate all submitted values/sessions on 422; update today without duplication.

## 7. Migration & Historical Data Strategy
**Established (not a product decision):** weekly records **will not** be converted to daily; weekly model completely replaced; `partes_semanales` table+data removed **only after all functional references replaced**; unrelated data intact (`users, atletas, marcas, pagos, asistencias`, etc.). **Never fabricate daily records from historical weekly data. Never execute production migrations.**

### Alembic (forward-only; never modify historical revisions `d61e48816ec5`, `a3f1c9e27b04`)
1. **`add_registros_diarios_sesiones`** (expand): create new tables/constraints/indexes/FKs/checks. No data copy.
2. **Application replacement** (code/tests/scripts/templates) until grep gate is zero.
3. **`drop_partes_semanales`** (contract, separate migration): drop table/indexes **only when** repo-wide functional refs are zero and full tests pass.

### Safety & validation
- **Destructive migration explicitly controlled**: Phase 7 gated; production execution requires **verified backup/snapshot + explicit approval + maintenance window** (not performed here).
- Validate on **disposable PostgreSQL**: `alembic upgrade head` on empty and seeded-like disposable DB; run test suite against disposable PG config. Existing `tests/conftest.py` uses SQLite in-memory for speed — **add/plan PG migration validation path** (separate job/script) because ARRAY/check behavior differs.
- **Historical impact**: all `partes_semanales` rows become unavailable after drop (historic weekly trends/alerts/cruces on that data lost unless exported externally). Unrelated modules unaffected.

## 8. Statistics, Load & Wellness Aggregation Contracts

### 8.1 Load (specified)
- `carga_sesion = duracion_min × rpe` (per session, backend-computed).
- `carga_diaria = Σ carga_sesion` for the daily record (0 when `entreno_hoy=false` and no sessions).
- `carga_semanal = Σ carga_diaria` over calendar/training week (Mon–Sun, `lunes_de`) **counting only days with an existing daily record**. Missing reports contribute **no value** (not 0) to load evidence; weekly aggregates must also expose `dias_reportados`/missing counts.

### 8.2 Wellness aggregation (1–10), missing vs low (specified)
For each 1–10 metric (`sueno_calidad,fatiga,dolor_muscular,estres,animo`) and `horas_sueno`:
- **Daily value**: the stored observation for that date (or null only if field truly optional — target model requires core wellness fields).
- **Weekly average**: arithmetic mean over **reported days only** in the week; if `dias_reportados==0` → `None` (never 0). Report `dias_reportados` and `dias_esperados/posibles` context where useful.
- **Missing observations**: absence of a `RegistroDiario` row — **never imputed as 0 and never treated as “low wellness”**.
- **Counts**: `dias_reportados`, `dias_con_entreno`, `dias_con_molestia`, `dias_con_sintomas`, etc., derived from existing daily rows.
- Distinguish explicitly in services/templates: `sin dato`/missing vs `valor bajo`.

### 8.3 ACWR — adaptation required (evidence-based, no invented validity)
**Current (verified):** `app/services/alertas.py::acwr` computes acute = `serie[-1]["carga"]` (last week) / chronic = mean of up to previous 4 weekly `carga` values; needs >=2 prior weeks. Weekly `carga` comes from `bienestar.carga_ua` (`rpe*minutos_totales`) — one aggregate per weekly report.

**Required change (specify, finalize numbers with care):**
- Build **daily load series** from daily records (missing day = unknown, not 0). Derive **weekly load sums** over reported days for comparability, **or** (recommended for daily system) use rolling windows: e.g. **acute = sum(load) over last 7 days** (or last N reported/eligible days — define explicitly), **chronic = average weekly load over prior 3–4 weeks = (sum(load) over prior 21–28 days) / (3 or 4)**, computed only when sufficient observed coverage. **Exact window and minimum-data rules are a technical recommendation requiring implementation-time validation/tests; do not claim injury-prediction validity.**
- Exclude missing days from sums; if coverage is too sparse (e.g. < X reported days in chronic window — define threshold), return `None`.
- Keep `ACWR_ALTO/BAJO` as **reassessed initial monitoring thresholds** (see §9) — do not assume weekly semantics unchanged.

### 8.4 Charts & crosses
- Daily or derived-weekly series from daily rows; `cruce_con_marcas` joins on `fecha`/derived week. `grafico.py` remains generic.

## 9. Alerts — Concrete Daily Semantics & Reassessed Thresholds

**Principles:** monitoring tools, not medical diagnoses/injury predictions. Compare athlete to self where meaningful (preserve current philosophy). Missing ≠ low/zero.

### 9.1 Alert types (proposed concrete semantics)
| Tipo (proposed key) | Meaning | Trigger (initial rule, reassess) | Severity (initial) |
|---|---|---|---|
| `sin_registro_hoy` (replaces `sin_parte`) | Missing **wellness/report** for today | No `RegistroDiario` for `(atleta, hoy())` after local cutoff/context used by UI — **define**: show as “pendiente hoy” in dashboards; alert severity `media`/`baja` configurable. **Distinguish from “no training today”.** | media (recommended) |
| `sin_registro_reciente` (optional) | Repeated missing reports | No record for last `N` days (recommend N=2–3) — **requires PO approval**. | baja/media |
| `sin_entreno_registrado_hoy` (if needed) | Has today record but `entreno_hoy=false` | Informational only, **not** a risk alert; may appear in summary, not “problem” list. | info/none |
| `carga_alta_dia` | High/unusual **daily** load | `carga_diaria >= UMBRAL_CARGA_DIA` (absolute, initial placeholder) **or** > `P%` of athlete’s recent personal daily/weekly-derived norm — requires calibration. | media/alta |
| `salto_de_carga` (ACWR/adapted) | Acute/chronic spike | Recomputed ACWR >= `ACWR_ALTO` with sufficient coverage. | alta (keep concept) |
| `caida_de_carga` | Underload | ACWR <= `ACWR_BAJO` with sufficient coverage. | baja |
| `bienestar_bajo` | Low wellness (daily or derived) | Composite/index on 1-10 (e.g. mean of 5 scales <= threshold, or >=K scales <=2) — **must be rebaselined from 1-5/20**. | alta/media |
| `item_minimo` / `bienestar_item_critico` | Any critical item | Any core wellness item == 1 (on 1-10) — stronger signal; confirm. | alta |
| `caida_bienestar` | Drop vs self baseline | % drop vs prior `M` reported days/weeks average, min observations required. | alta/media |
| `molestia_reportada` | Discomfort | `hay_molestia` true; severity by `molestia_dolor` and/or `afecta_entrenamiento`. | media/alta |
| `sintomas_enfermedad` | Illness symptoms | `sintomas_enfermedad` true (inform coach; not diagnosis). | media/alta (configurable) |
| `sueno_insuficiente` | Sleep low | `horas_sueno < SUENO_MINIMO` over `K` **reported** days (ignore missing). | media |
| `pago_vencido` | Billing | Unchanged. | as today |

### 9.2 Thresholds — reassessment (no mechanical transfer)
- **Do not copy** `BIENESTAR_BAJO=UMBRAL_MAL` (20-scale weekly), 1-5 item logic, or weekly-only sleep windows without redefining for daily 1-10 + missing data.
- **Recommended initial starting points (product-owner approval required; calibrate after data):** `SUENO_MINIMO` keep 7.0h concept but apply to reported days; `DOLOR_ALTO` keep 5/10 concept if retained (now `molestia_dolor` 1-10 daily — aligns); `ACWR_ALTO/BLO` 1.5/0.8 as monitoring defaults pending recalibration; define new `BIENESTAR_*` on 1-10 composite with explicit formula.
- All alert copy must avoid definitive medical/injury claims.

## 10. Security & Data Integrity
- Reuse `get_current_user`/role guards, CSRF (`app/csrf.py`/`csrf_input`), SQLAlchemy sessions. 
- Ownership: athlete routes scope to `user.id` only. 
- Server date = `tiempo.hoy()`; loads recomputed server-side; conditional normalization server-side.
- Discard protection: signed+state-bound `discard_token`, verified in-transaction; rejects stale mutations.
- Concurrency: unique `(atleta_id,fecha)` + integrity handling; transactional session replacement.

## 11. Testing Strategy (plan; NOT RUN now)
1. Create daily record (athlete, server date). 2. Update today no duplicate. 3. Unique `(atleta,fecha)` incl. concurrent/integrity path. 4. `America/La_Paz` `hoy()` authority; client date ignored/rejected. 5. `entreno_hoy=false` saves no sessions. 6. One session: `carga_sesion` + daily total correct. 7. Multiple sessions add/edit/remove; totals. 8. Reject invalid `duracion_min<=0`, `rpe` out of 1-10, wellness 1-10 out of range. 9. Conditionals: molestia/síntomas/`otro`+`molestia_zona_otra`. 10. **Yes→No discard**: no token/confirm → 422, sessions preserved; stale token (sessions changed) → 422, preserved; valid token+confirm → sessions deleted in transaction. 11. `entreno_hoy=true` + 0 sessions → 422. 12. Cross-athlete blocked. 13. Aggregations treat missing as missing (not zero). 14. Alerts/derived weekly stats. 15. Alembic on **disposable PostgreSQL** (`upgrade head`, new migrations). 16. Full `pytest` regression — NOT RUN.

**Modify/replace**: `tests/conftest.py` helpers (`crear_registro_diario`+sessions), `test_parte.py` rewrite, `test_bienestar.py`, `test_alertas.py`, `test_consultas.py`; keep unrelated modules green.

## 12. Implementation Phases (refined, dependency-ordered)

### Phase 0 — Prep & guardrails
- **Files**: refs only + inventory checklist. **Acceptance**: grep baseline for `ParteSemanal|partes_semanales|parte_de_semana|/parte\\?semana|SEMANAS_EDITABLES|carga_ua|sin_parte` documented.

### Phase 1 — New schema (expand, forward-only)
- **Files**: `app/models/registro_diario.py`, `app/models/sesion_entrenamiento.py` (or per style), `app/models/__init__.py` (add exports), `alembic/versions/<new>_add_registros_diarios_sesiones.py`. **No edits to historical migrations.**
- **Acceptance**: models import; migration applies on disposable PG; unrelated tables untouched.

### Phase 2 — Core domain services
- **Files**: `app/services/bienestar.py` (evolve carefully) or new `seguimiento_diario.py` + migrate callers; `app/services/alertas.py`; `app/services/grafico.py` (minimal).
- **Acceptance**: unit-testable pure calcs for load/aggregation/missing handling/ACWR adaptation; thresholds isolated/constants documented.

### Phase 3 — Router/workflow (transactional, secure discard)
- **Files**: `app/routers/parte.py`, shared validation/helpers (and signed discard-token helper aligned with `app/csrf.py`/`config` secret).
- **Acceptance**: tests 1–12 pass for router rules; server date/ownership/CSRF enforced.

### Phase 4 — UI/templates
- **Files**: `app/templates/atleta/parte.html`, `_campos.html`, nav/pending in `atleta/inicio.html`, `mis_datos.html`, `panel/*`, `_nav/_tabbar`, minimal static JS/CSS if patterned.
- **Acceptance**: responsive A–E form, conditional fields, dynamic sessions, discard confirmation UX backed by server flow, error repopulation.

### Phase 5 — Consumers & de-weekly-fy
- **Files**: `app/routers/panel.py,atletas.py,estadisticas.py,cuenta.py`, templates, any remaining refs (including `scripts/` except final removal handled carefully).
- **Acceptance**: **zero functional runtime refs** to weekly model in app/tests (allow only migration history? historical alembic files retain table names by definition — exclude `alembic/versions/d61e48816ec5*`, `a3f1c9e27b04*` from “functional ref” gate; app code/tests/scripts must be zero). Dashboards coherent.

### Phase 6 — Tests, seeds, full regression
- **Files**: `tests/*` per §11, `scripts/seed.py`, `seed_5_atletas.py`, `conftest.py`.
- **Acceptance**: full `pytest` green on project test setup; PG migration validation completed on disposable DB.

### Phase 7 — Contract migration: remove weekly (last)
- **Files**: remove `ParteSemanal` from `app/models/parte.py`/`__init__` and all imports/usages; `alembic/versions/<new>_drop_partes_semanales.py`; `README.md`, `DEPLOY.md` text.
- **Preconditions (hard gates)**: Phase 6 green; grep gate = zero functional refs; **verified backup/snapshot before any production run**; explicit approval. **Never run in prod here.**
- **Acceptance**: disposable PG `upgrade head` drops table; tests still green.

## 13. Decisions — Established / Recommended / Resolved / Needs Approval

**Established (requirements):** daily per athlete+local date unique; server `America/La_Paz` date; athlete create/update today only; no duplicates; multi-sessions; session/daily/weekly load formulas as §8.1; fatigue independent of session RPE; `entreno_hoy` + secure explicit discard (never silent, never JS-only, backend authoritative, cancel preserves); conditional validation/cleanup; transactional + concurrent-safe; stats from daily, weekly derived from daily; no fabrication of daily from historic weekly; replace/remove weekly deps; drop old table+data after refs replaced; preserve unrelated data; no prod migration execution.

**Resolved in this plan (technical decisions):**
- **A**. Stale-proof signed `discard_token` bound to `(atleta,fecha,registro,session_state_hash,expiry)`; verified in-transaction; not a freely-editable boolean.
- **B**. `entreno_hoy=true` ⇒ **>=1 valid session** required (frontend+backend).
- **C**. Load contracts + missing ≠ 0 + ACWR adaptation direction (rolling/derived windows, coverage guards) — exact window constants finalized in impl with tests.
- **D**. Wellness aggregation over reported days only; counts; missing ≠ low.
- **E**. Concrete daily alert catalog + reassessment rule (no mechanical transfer); initial severity proposals.
- **F**. `molestia_zona_otra` required iff `otro`; cleared otherwise; backend-validated.
- **G**. Historic weekly data: **no longer unresolved** — will not convert, table+data dropped post-ref replacement; destructive migration controlled w/ verified backup pre-prod; not executed.

**Recommended (confirm or override):** `registros_diarios`/`sesiones_entrenamiento` naming; `molestia_zona` PG `ARRAY(String)` + whitelist; persist `carga_sesion`, derive daily total; replace-session-set per transaction; keep `/parte` route; indexed session form fields.

**Still requires user/product-owner approval:**
1. **Exact ACWR windows & minimum coverage** (e.g. 7d acute / 28d chronic ÷4, min reported days) and final numeric thresholds after rebaseline.
2. **Final 1-10 wellness composite formula** and numeric cutoffs (`bienestar_bajo`, `item_minimo` on 1-10).
3. **`sin_registro_reciente`** (N days) — enable? N?
4. **`sintomas_enfermedad=true` requires `detalle_sintomas`** — confirm (recommended yes).
5. **1-10 UI labels/guidance copy** per scale (product text) — I can draft defaults on request.
6. **Severity levels** for illness/molestia/sin_registro_hoy in coach UX.
7. Naming confirmation if you prefer `partes_diarias` over `registros_diarios`.

## 14. Dependency Map (text)
`tiempo.hoy(America/La_Paz)` → `routers/parte.py` (auth+CSRF+server date+ownership) → validate/normalize (conditionals, loads recompute, `entreno_hoy` rules, discard token verify) → **single transaction** → `RegistroDiario` upsert `(atleta,fecha)` + replace `SesionEntrenamiento` set → `services/*` (daily series, derived weekly sums/means over reported days, ACWR, alerts) → `routers/panel,atletas,estadisticas,cuenta` → templates. `alembic` expand → code replace → `alembic` drop `partes_semanales` **last**.

## 15. Safest Migration & Deployment Sequence (do not execute)
1. Resolve §13 approvals. 2. Implement Phases 1–6; validate migrations + tests on disposable PG. 3. Deploy expand migration + new code (no weekly read/write). 4. Verify prod (today record, sessions, discard flow, dashboards, alerts). 5. Confirm zero functional weekly refs. 6. **Verified backup/snapshot + explicit approval** → run drop migration in controlled window (ack weekly data loss). 7. Monitor; rollback plan ready.

## 16. Risks, Assumptions, Unresolved
- **Risks**: alert/ACWR behavior change; ARRAY/PG-specific features require PG validation (SQLite tests may not cover all); discard-token UX complexity; coach confusion over missing≠0.
- **Assumptions**: Postgres production; FastAPI `Form` (no dominant Pydantic form layer found); reuse `tiempo.lunes_de` for week grouping.
- **Resolved**: A–G from task (discard stale-proof, `entreno_hoy>=1`, load/agg contracts, alerts catalog, `otro` field, historic weekly drop established).
- **Remaining (needs approval)**: §13 items 1–7 (ACWR windows/thresholds, wellness composite/cutoffs, recent-missing alert, `detalle_sintomas` required, 1-10 copy, severities, naming).

## 17. Applicable Verification Results
| Check | Result |
|---|---|
| Repo/branch/HEAD/clean tree verified (refreshed) | PASS |
| ses_e8fd located and reused | PASS |
| Only authorized planning doc updated | PASS |
| Source/config/DB/migrations/tests modified | **NO** (PASS) |
| Migrations/tests/prod ops executed | NOT RUN (prohibited) |

## 18. Recommendation
**Ready for implementation approval in Code mode**, contingent on resolving the **remaining §13 approval items (1–7)** — especially ACWR window/min-coverage, wellness composite cutoffs, and UI label/copy decisions. Core contradictions (discard confirmation, `entreno_hoy` zero sessions, load/wellness/missing semantics, `otro`, and historic weekly data handling) are now specified and consistent with project constraints (SQLAlchemy 2, PostgreSQL, Alembic forward-only, transactional integrity). Execute Phases 1→7 in order; do **not** drop `partes_semanales` before the zero-functional-ref gate and verified backup.

