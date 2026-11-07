# Plan: Replace Weekly Athlete Reports with a Daily Tracking System

## 0. Verification Status (READ-ONLY)
- **Repository**: `C:\Archivos.Diego\atletismoWeb\atletismo` (git repo) — PASS.
- **Branch/HEAD**: `Baruc+Kilo` @ `956b634`, up to date with `origin/Baruc+Kilo` — PASS.
- **Working tree**: clean (`nothing to commit, working tree clean`) — PASS. No local changes to preserve.
- **Previous session**: `.kilo/kiloSesions/S-0006_ask_session-ses_e8fd.md` (`ses_e8fd`) — FOUND; findings reused and revalidated against current tree.
- **Code changes made by this plan task**: NONE — PASS (read-only).

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

### 4.1 Daily record table — **recommended**: `registros_diarios` (new name avoids semantic collision) or `partes_diarias`
**Decision (recommended, needs confirmation if you prefer keeping `/parte` naming internally only):** introduce `RegistroDiario` / `registros_diarios` with clear daily semantics.
- `id` PK.
- `atleta_id` FK → `users.id` `ondelete=CASCADE`, indexed, NOT NULL.
- `fecha` `Date` NOT NULL — **set by server from `tiempo.hoy()` (`America/La_Paz`)** on create; for athlete POST, ignore client-supplied date for authorization path (or reject mismatch). For coach read-only views, date may be queried.
- **Uniqueness (DB-level, required):** `UniqueConstraint('atleta_id','fecha', name='uq_registro_diario_atleta_fecha')` + supporting index.
- Wellness (all required unless specified): `sueno_calidad` SmallInt/Int `CHECK 1-10`; `horas_sueno` `Numeric(4,1)` or `(3,1)` `CHECK 0-24`; `fatiga, dolor_muscular, estres, animo` Int `CHECK 1-10`.
- `hay_molestia` Boolean NOT NULL default false.
- `molestia_zona` **recommended** `postgresql.ARRAY(String)` (or `ARRAY(Text)`) nullable/empty when no molestia; **alternative** normalized join table — *compare*: ARRAY is simpler for fixed selectable set and Postgres-only target; join table better for querying/analytics but more schema/ORM overhead. **Recommend ARRAY + backend whitelist validation** of allowed values (`cuello,hombros,espalda,cadera,gluteos,muslos,rodillas,pantorrillas,tobillos,pies,brazos,otro`). Store canonical keys; render labels in UI.
- `molestia_dolor` Int `CHECK 1-10`, nullable (required iff `hay_molestia`).
- `afecta_entrenamiento` Int `CHECK 0-3`, nullable (required iff `hay_molestia`).
- `sintomas_enfermedad` Boolean NOT NULL default false.
- `detalle_sintomas` Text nullable (required/allowed iff `sintomas_enfermedad`).
- `comentarios` Text nullable.
- `entreno_hoy` Boolean NOT NULL.
- `enviado/actualizado` timestamps (consistent with project: `DateTime(timezone=True)`, `server_default now()`, `onupdate`).

### 4.2 Training sessions — `sesiones_entrenamiento`
- `id` PK.
- `registro_diario_id` FK → `registros_diarios.id` `ondelete=CASCADE`, indexed, NOT NULL.
- `orden` SmallInt/Int NOT NULL (stable display/edit order) — optional but recommended.
- `tipo_entrenamiento` String/Enum-like constrained text; allowed: `velocidad_sprint, resistencia, fuerza, tecnica_coordinacion, movilidad_recuperacion, competencia, entrenamiento_mixto, otro` (canonical keys) + whitelist validation.
- `duracion_min` Int NOT NULL `CHECK (duracion_min > 0)`.
- `rpe` Int NOT NULL `CHECK 1-10`.
- `carga_sesion` Int NOT NULL `CHECK (carga_sesion = duracion_min * rpe)` **if persisted**; **authoritative calculation in backend** on every write (never trust client value).
- `comentarios_entrenamiento` Text nullable.
- **Relationship**: `RegistroDiario.sesiones` one-to-many, `cascade='all, delete-orphan'`, `order_by=orden/id`. No sessions allowed/persisted when `entreno_hoy=false`.

### 4.3 Load storage — recommendation
- **Persist `carga_sesion` on session AND persist/derive `carga_diaria`?** Options: (A) persist both (session computed, daily stored as sum) with consistency enforced in service transaction; (B) persist session load, derive daily sum in queries/services — simpler integrity. **Recommend (B)**: persist `carga_sesion` (authoritative per row) and compute daily total as `sum(carga_sesion)` in service/property/query; avoids dual-write drift. If perf needed later, add materialized/cache column — not required now. *This is a technical recommendation; confirm if you prefer stored daily total.*

### 4.4 Indexes/constraints
- `uq_registro_diario_atleta_fecha` (critical).
- Indexes on `registros_diarios.fecha`, `(atleta_id, fecha desc)`.
- FK indexes default/explicit as per project style.
- Optional `CHECK` constraints aligning with backend ranges (defense in depth).

## 5. Business Rules, Validation & Integrity (frontend + backend + DB)
1. **One record/athlete/local date**: DB unique + service upsert on `(atleta_id, hoy())`; handle concurrent submits by catching integrity error and retrying update in same request/transaction pattern (SQLAlchemy session-safe) — never create duplicate.
2. **Date authority**: server uses `tiempo.hoy()` (`America/La_Paz`). Athlete cannot select/create/modify other dates — GET/POST ignore or reject any client date param for athlete flow; show “hoy” only.
3. **Create/update today**: GET loads today’s record if exists; POST finds-or-creates for `(user.id, hoy())` and updates fields/sessions atomically.
4. **`entreno_hoy=false`**: backend must **clear sessions** (delete-orphan / explicit delete) and reject any submitted sessions; UI hides section.
5. **`entreno_hoy=true`**: allow 0? **Clarify** (recommend require >=1 session when true, else validation error) — list dynamic add/edit/remove.
6. **Yes→No with existing sessions — explicit confirmation (secure, not JS-only)**:
   - UI: changing to No when sessions exist shows warning and requires a deliberate confirm action (checkbox “Confirmo descartar X sesiones” **and/or** modal with explicit button) — JS allowed for UX.
   - **Backend enforcement (authoritative)**: POST must include `confirmar_descartar_sesiones=true` (signed/form flag) **only honored when** transition discards existing persisted sessions; if discarding and flag absent/false → return 422/validation error with message, **do not delete**. If flag present → delete sessions in same transaction. Also accept idempotent case (no existing sessions).
   - Never rely solely on hiding fields or `window.confirm`.
7. **Cancel discard**: if user cancels in UI, keep state/sessions; on re-render/submit without discard confirmation path, preserve existing sessions.
8. **Conditional fields**: if `hay_molestia=false` null/ignore `molestia_zona/dolor/afecta_entrenamiento`; if `sintomas_enfermedad=false` null/ignore `detalle_sintomas`. Backend normalizes before save.
9. **Authoritative backend validation**: ranges, enums/whitelists (body regions, session types), required conditionals, session invariants, `carga_sesion` recomputed server-side. Frontend mirrors for UX only.
10. **Transactional**: single DB transaction per save (record + session replacements/edits) via `Session`/commit boundary; on error rollback. Prefer “replace session set for record” strategy (delete existing + insert submitted ordered set) inside transaction to simplify edit/remove/add — simple and correct given cascade/orphan.
11. **Concurrency**: unique constraint + `IntegrityError` handling / upsert retry; Postgres-safe.
12. **AuthZ**: reuse `get_current_user`; athlete-only for create/update own record; coaches/professors read per existing permissions — **athletes must never access/modify others’ records** (all queries scoped by `atleta_id=user.id` for athlete routes).

## 6. Frontend Plan (responsive, reuse project conventions)
**File focus**: `app/templates/atleta/parte.html` (replace weekly form) or new `parte_diario.html` wired to same `/parte` — **recommend keep `/parte` route, replace template/content** to preserve nav/links; `_campos.html` add 1-10 visual scale macro with descriptive labels/guidance and multi-select for body regions.
- **5 categories**: (A) Descanso y sueño: `sueno_calidad` 1-10, `horas_sueno`. (B) Fatiga y recuperación: `fatiga` 1-10, `dolor_muscular` 1-10. (C) Bienestar psicológico: `estres` 1-10, `animo` 1-10. (D) Condición física/molestias: `hay_molestia` → multi body regions, `molestia_dolor` 1-10, `afecta_entrenamiento` 0-3. (E) Salud general/observaciones: `sintomas_enfermedad` → `detalle_sintomas`, `comentarios`.
- Visual 1-10 scales: extend radio-pattern macros (no-JS baseline) with per-value descriptors; guidance text.
- `entreno_hoy` after wellness: hide training section when No (`.condicional` pattern exists) **and** server-side removal.
- Dynamic sessions: JS-enhanced add/edit/remove rows (progressive enhancement) posting indexed fields (`sesiones-0-tipo`, etc.) or JSON-in-hidden-field fallback — **recommend simple indexed form fields compatible with FastAPI `Form` parsing patterns already used**; include row template; show per-session `carga_sesion` preview and total (JS) + recompute server-side.
- Validation errors: re-render with submitted values and parsed sessions (like current `form` repopulation).
- Update existing today record without duplication.
- No unnecessary frontend deps.

## 7. Migration & Historical Data Strategy
**Requirements honored**: create new structures; replace deps; drop old weekly table only after all functional refs replaced; **never fabricate daily records from historical weekly data**; preserve unrelated data (users, athletes, marcas, pagos, asistencias, etc.); never execute production migrations/destructive ops; validate on disposable test DB.

### Recommended Alembic sequence (forward migrations)
1. **`add_registros_diarios_sesiones`** (expand): create `registros_diarios`, `sesiones_entrenamiento`, constraints/indexes/FKs. No data copy from `partes_semanales`. App can deploy dual-read readiness not required (objective is replacement) — but safest to deploy code that uses new tables in same release after migration 1.
2. **(code) Replace all weekly deps** across models/services/routes/templates/tests/scripts.
3. **`drop_partes_semanales`** (contract): `op.drop_table('partes_semanales')` (and indexes/constraints) **only when grep shows zero functional refs** and tests pass. Existing migrations `d61e48816ec5`, `a3f1c9e27b04` remain untouched history.

### Historical impact (explicit)
- **Data that becomes unavailable after drop**: all rows in `partes_semanales` (historic weekly wellness, weekly RPE/minutes/sessions aggregate fields, weekly molestia/comments as stored). **Consequences**: historic weekly trends/alerts/cruces based on old records will no longer be queryable unless separately exported before migration — acceptable/accepted by “replace/remove” objective? **Flag for approval**. Unrelated modules unaffected.

### Validation on disposable PostgreSQL
- Use a throwaway Postgres DB/URL (e.g., local Docker or temp DB); run `alembic upgrade head` on empty + on snapshot-with-seed-like data if available; run app test suite against disposable DB config; verify downgrade path only if project practices require (optional) — never production.

## 8. Statistics & Alerts Adaptation
- **Daily source of truth**: all new computations read `registros_diarios` (+ sessions).
- **Weekly summaries derived** from daily records (group by `lunes_de(fecha)` / ISO week in local TZ) — no second weekly reporting model. Define aggregation: e.g., mean of daily 1-10 metrics, presence count, total load = sum of daily loads, molestia any-day flags — **technical recommendation; confirm exact formulas**.
- **Thresholds**: **do not auto-transfer** weekly 1-5/`MAXIMO=20` cutoffs to daily 1-10. Rebase (e.g., proportional) and review ACWR window meaning (daily load summed weekly vs 7-day acute/chronic) — treat as monitoring indicators, not medical diagnoses/injury predictions.
- **Charts**: update `panel/estadisticas/mis_datos` to daily or derived-weekly series; `cruce_con_marcas` join on `fecha` (or week containing `fecha`).
- **Pending indicators**: “parte pendiente” → “registro de hoy pendiente”.

## 9. Security & Data Integrity
- Reuse auth/role guards (`get_current_user`, role checks), CSRF (`csrf_input`, template/project middleware), SQLAlchemy session patterns.
- **Ownership**: all athlete mutations/reads scoped to `user.id`; return 403/404 appropriately on cross-access attempts.
- Server-side date = `tiempo.hoy()`; conditional validation/cleanup server-side; recompute loads server-side.
- Transactional record+session writes; uniqueness + concurrent handling.
- Secure discard: backend `confirmar_descartar_sesiones` gate.

## 10. Testing Strategy (plan; NOT RUN now)
1. Create daily record (happy path, athlete).
2. Update today without duplication (second submit edits same row).
3. DB/app enforce one record per athlete+date (including concurrent case simulation/integrity handling).
4. Correct `America/La_Paz` date determination (`tiempo.hoy()` used; no client date override).
5. Save wellness without training (`entreno_hoy=false`, no sessions persisted).
6. Save one session; verify `carga_sesion` and daily total.
7. Save multiple sessions; add/edit/remove; totals correct.
8. Reject invalid `duracion_min` (<=0, non-int) and `rpe` (out of 1-10), invalid 1-10 wellness.
9. Conditional fields: molestia/síntomas required/cleared appropriately.
10. Yes→No with existing sessions: without confirmation → rejected, sessions preserved; with explicit confirmation → sessions deleted.
11. Prevent cross-athlete access/modification.
12. Daily statistics/alerts behave per redefined rules (derived weekly where applicable).
13. Migrations validated on disposable PostgreSQL (`alembic upgrade head`).
14. Full regression suite (`pytest`) — NOT RUN (read-only task).

**Existing tests to modify/replace**: `test_parte.py` (rewrite to daily), `test_bienestar.py`/`test_alertas.py` (new scales/semantics), `test_consultas.py`, `conftest.py` helpers; remove weekly-only assumptions. Keep unrelated module tests green.

## 11. Implementation Phases (dependency-ordered)

### Phase 0 — Prep & guardrails
- **Objective**: freeze weekly contract understanding, add test scaffolding patterns.
- **Files**: (investigation refs) `app/models/parte.py`, `services/bienestar.py|alertas.py`, `routers/parte.py`, tests above.
- **Mod**: none now; during impl add new fixtures alongside old until swap.
- **Deps**: none. **Regression risk**: low. **Validation**: inventory grep baseline saved mentally.

### Phase 1 — New data model (expand)
- **Objective**: introduce daily+session tables without breaking unrelated data.
- **Files**: `app/models/registro_diario.py` (or chosen names), `app/models/sesion_entrenamiento.py` (or combined module per project style), `app/models/__init__.py`, new Alembic revision under `alembic/versions/`.
- **Current responsibility**: n/a (new). **Expected mod**: SA2 models, relationships/cascades, constraints, indexes.
- **Deps**: `app.database.Base`, `app.tiempo`. **Risks**: ARRAY portability (PG-only OK), constraint naming. **Validation**: model import, migration on disposable PG.

### Phase 2 — Core services (daily calculations & derived summaries)
- **Objective**: daily metrics, load, weekly derivations, alert primitives.
- **Files**: `app/services/bienestar.py` (or split `seguimiento_diario.py` — **recommend evolve `bienestar.py` carefully to limit churn, or add new service and migrate callers**; flag naming choice), `app/services/alertas.py`, `app/services/grafico.py` (comments/callers only).
- **Expected mod**: new scale constants 1-10, `carga_diaria/sesion` helpers, daily CRUD/query helpers, derived weekly aggregators, revised thresholds/rules.
- **Deps**: Phase 1. **Risk**: HIGH (formulas/threshold meaning). **Validation**: unit tests for calcs/aggregations.

### Phase 3 — Router & backend workflow
- **Objective**: `/parte` daily create/update-today, multi-session transactional save, secure discard confirmation.
- **Files**: `app/routers/parte.py`, possibly schemas/helpers if project uses them; `app/tiempo.py` reuse.
- **Expected mod**: remove week selection for athlete mutation; `hoy()` authority; parse indexed sessions; recompute loads; conditional cleanup; confirm flag enforcement.
- **Deps**: Phases 1-2. **Risk**: HIGH. **Validation**: tests 1-11.

### Phase 4 — Templates/UI
- **Objective**: responsive daily form (A-E), 1-10 visuals, conditional sections, dynamic sessions + previews, preserved errors.
- **Files**: `app/templates/atleta/parte.html`, `app/templates/_campos.html`, minimal `app/static/js|css` only if already patterned (verify; avoid new deps), nav labels/pending in `atleta/inicio.html`, `mis_datos.html`, `panel/*`, `_nav/_tabbar` as needed.
- **Deps**: Phase 3 payload contract. **Risk**: MEDIUM. **Validation**: manual review + integration tests rendering key states.

### Phase 5 — Consumers (panel/athletes/stats/cuenta) & cross-module
- **Objective**: remove all functional weekly deps; stats/alerts on daily + derived weekly.
- **Files**: `app/routers/panel.py`, `atletas.py`, `estadisticas.py`, `cuenta.py`, related templates, any other `ParteSemanal` refs from inventory grep.
- **Deps**: Phase 2. **Risk**: MEDIUM-HIGH. **Validation**: dashboards load, KPIs coherent, no weekly imports.

### Phase 6 — Tests, seeds, fixtures
- **Objective**: full coverage of new rules; green regression.
- **Files**: `tests/conftest.py`, `test_parte.py` (rewrite), `test_bienestar.py`, `test_alertas.py`, `test_consultas.py`, new `test_registro_diario.py` if clearer; `scripts/seed.py`, `seed_5_atletas.py`.
- **Deps**: Phases 1-5. **Risk**: MEDIUM. **Validation**: `pytest` pass.

### Phase 7 — Remove weekly model & drop table (contract)
- **Objective**: complete removal of old weekly reporting model.
- **Files**: delete/replace `app/models/parte.py` content (remove class) and all imports; Alembic migration to drop `partes_semanales`; update `README.md/DEPLOY.md` text.
- **Precondition**: repo-wide grep for `ParteSemanal|partes_semanales` (and runtime weekly helpers) returns **zero functional references**.
- **Deps**: Phase 6 green. **Risk**: HIGH (irreversible for historic weekly rows). **Validation**: tests + disposable PG migration.

## 12. Decisions — Established / Recommended / Needs Approval

**Established by requirements (must implement as specified)**
- One daily record per athlete + local date (`America/La_Paz`), DB unique; multiple sessions per daily record; session fields/types; `carga_sesion = duracion_min*RPE` backend-authoritative; daily load = sum sessions; fatigue and session RPE independent; server date authority; athlete create/update current day only; no duplicates on update; `entreno_hoy` semantics; explicit confirmation before discarding existing sessions on Yes→No (never silent, never JS-only reliance); conditional validation/cleanup; transactional; concurrent-safe; stats on daily, weekly summaries derived from daily; remove weekly deps and drop old table after replacement; never fabricate daily from historic weekly; preserve unrelated data.

**Technical recommendations (investigation-based)**
- New tables `registros_diarios` + `sesiones_entrenamiento` (clear naming); `molestia_zona` as PG `ARRAY(String)` with backend whitelist (vs join table).
- Persist `carga_sesion`, derive `carga_diaria` by sum (avoid drift).
- Replace-session-set strategy in one transaction for simplicity.
- Keep `/parte` route, redesign form/template in place.
- Rebaseline alert thresholds for 1-10/daily; define ACWR over derived weekly/daily windows explicitly in impl.
- Indexed form fields for dynamic sessions (FastAPI-friendly, no new deps).

**Needs explicit approval before implementation**
1. **Historic weekly rows**: confirm acceptance that `partes_semanales` data will be dropped (unavailable) after replacement and will **not** be migrated/fabricated into daily records.
2. **`entreno_hoy=true` with zero sessions**: allow or require >=1?
3. **Alert semantics**: replace “sin parte esta semana” with “sin registro hoy” and/or “N días sin registro” — choose rule/thresholds.
4. **Exact 1-10 descriptive labels/guidance text** per scale (product copy) — I can propose defaults only if you want.
5. **Body region value when `otro` selected**: free text field needed?
6. **Table/model naming** (`registros_diarios` vs `partes_diarias`) and service naming (keep `bienestar.py` vs split) — functional either way.

## 13. Dependency Map (text)
`tiempo.hoy(America/La_Paz)` → `routers/parte.py` (auth athlete, server date) → `models/RegistroDiario + SesionEntrenamiento` (DB unique/FKs/checks) → transaction commit → `services/bienestar(or seguimiento)` (loads, totals, derived weekly series) → `services/alertas.py` / `services/grafico.py` → `routers/panel,atletas,estadisticas,cuenta` → `templates (athlete/coach)`. `scripts/seed*` → models. `tests/*` → all layers. `alembic` → schema; drop `partes_semanales` **after** all arrows to old model removed.

## 14. Safest Migration & Deployment Sequence (do not execute)
1. Finalize approvals (§12). 2. Implement Phases 1-6 on feature branch with disposable-PG migration+test validation. 3. Deploy expand migration (new tables) + new code that no longer reads/writes weekly. 4. Verify prod behavior (auth, create/update today, sessions, dashboards, alerts). 5. Confirm zero `partes_semanales` functional refs. 6. Run drop-table migration in a controlled window (ack historic weekly data loss). 7. Monitor regressions; rollback = restore app version + (if needed) re-create old table structure **without data** unless backup exists — **ensure DB backup/snapshot before step 6** (ops action).

## 15. Risks, Assumptions, Unresolved
- **Risk**: threshold/behavior changes in alerts/stats (weekly→daily) may surprise users; mitigate with explicit review. **Assumption**: Postgres is production target (ARRAY/checks ok). **Assumption**: no Pydantic schema layer found dominating forms (FastAPI `Form` used) — verify during impl. **Unresolved**: historic weekly data fate approved?; `entreno_hoy` zero-session rule; alert window definitions; final copy for 1-10 labels; `otro` detail.

## 16. Applicable Verification Results
| Check | Result |
|---|---|
| Repo/branch/HEAD/clean tree verified | PASS |
| ses_e8fd located and reused | PASS |
| Read-only (no source/config/DB/migrations/tests modified) | PASS |
| Migrations executed | NOT RUN (prohibited) |
| Tests executed | NOT RUN (read-only planning) |
| Production/destructive ops | NOT RUN (prohibited) |

## 17. Recommendation
**Conditionally ready for approval to implement** — the architecture, dependency order, secure discard mechanism, and migration strategy are grounded in the verified codebase, **provided** the §12 approval items are resolved (especially historic `partes_semanales` data drop acceptance, `entreno_hoy` zero-session rule, and alert/label semantics). Once approved, proceed in **Code mode** following Phases 1→7 without skipping the zero-ref gate before dropping the weekly table.
