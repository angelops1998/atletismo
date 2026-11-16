# Plan: Replace Weekly Athlete Reports with a Daily Tracking System (Authoritative)

> **Status:** authoritative implementation plan — **documentation only, updated in place**. No code, migrations, tests, templates, frontend assets, DB writes, or destructive operations performed by this task. Implementation requires explicit authorization per phase constraints; **Phase 2 implementation NOT granted**. Phase 7 legacy removal remains **separately controlled and explicitly authorized**.

## 0. Verification Status (READ-ONLY, refreshed 2026-11-08, `ses_e8fd` Plan)
- **Repository**: `C:\Archivos.Diego\atletismoWeb\atletismo` (git repo) — VERIFIED.
- **Branch/HEAD**: `Baruc+Kilo` @ `b75b2a2` (`kilo markdown: S-0023_plan_session-ses_e8fd.md`), up to date with `origin/Baruc+Kilo` — VERIFIED (local git).
- **Working tree (initial)**: clean (`nothing to commit, working tree clean`); no existing user modifications/untracked files to preserve — VERIFIED.
- **Session**: `ses_e8fd` reused — VERIFIED. Inspected: `S-0006/S-0008/S-0012/S-0013/S-0018/S-0021/S-0022/S-0023`, `.kilo/plans/1792882624161-phase2-concurrency-policy.md` (PROPOSED, now superseded by approved Policy A in this plan), `.kilo/plans/1792882624161-daily-tracking-replacement.md`.
- **Phase 1 PostgreSQL validation evidence (S-0021, accepted):** disposable PG 16.15 (Docker/WSL2) ran `alembic upgrade a3f1c9e27b04` then `alembic upgrade c4b8e2d91f07` (**not `head`**); confirmed `partes_diarios`/`sesiones_entrenamiento`/`partes_semanales`, `molestia_zona` PG `ARRAY(VARCHAR)`, TZ timestamps/`now()` defaults, `uq_parte_diaria_atleta_fecha`, FKs + `ON DELETE CASCADE`, checks/indexes, duplicate `(atleta_id,fecha)` and invalid `sueno_calidad` rejected, ORM insert/read/update/delete/cascade/array roundtrip verified, `partes_semanales` intact. `tests/test_parte_diaria_schema.py` — 7 passed (SQLite). Disposable env cleaned up; **no app code/migrations/real DB changed**. (VERIFIED by S-0021 report; not re-executed now.)
- **Repo evidence inspected (this update):** `app/database.py`, `app/csrf.py`, `app/auth.py`, `app/tiempo.py`, `app/main.py`, `app/models/parte.py|parte_diaria.py|sesion_entrenamiento.py|__init__.py`, migration `c4b8e2d91f07_add_partes_diarios_sesiones.py` (+ historical `d61e48816ec5`,`a3f1c9e27b04` present/immutable), `app/services/bienestar.py|alertas.py|grafico.py|cobranza.py|pruebas.py`, `app/routers/parte.py|panel.py|atletas.py|estadisticas.py|cuenta.py|pagos.py`, templates `atleta/parte.html|inicio.html|mis_datos.html`, `panel/panel.html|atleta_ficha.html|atletas.html|estadisticas.html`, `_campos.html`, `templates_config.py`, tests/fixtures incl. `conftest.py`, `test_parte.py|test_bienestar.py|test_alertas.py|test_consultas.py|test_parte_diaria_schema.py|test_grafico.py`, `scripts/seed.py|seed_5_atletas.py`. Weekly refs grep: **no `app/schemas/` dir; no `ParteSemanal/partes_semanales` refs in `app/static/` JS/CSS** (templates carry refs). `render.yaml`/`DEPLOY.md`/`README.md` reference `alembic upgrade head` — deploy safeguard required (§7/§15).
- **Code/DB/migration/test changes made by this task**: **only this authoritative plan file updated** (authorized). — PASS.

## 1. Previous Audit Findings (ses_e8fd) — Reused / Superseded
### Reused (still valid)
- Weekly flow centered on `app/routers/parte.py` (`GET/POST /parte`), `app/models/parte.py` (`ParteSemanal`, `partes_semanales`, `uq_parte_atleta_semana (atleta_id, semana)`), `app/services/bienestar.py`, `app/services/alertas.py`.
- `semana` = Monday via `app/tiempo.lunes_de/lunes_actual`; TZ `America/La_Paz` in `app/tiempo.py` and DB session (`app/database.py` sets `timezone`).
- Upsert-by-week behavior and `SEMANAS_EDITABLES=1`.
- `grafico.py` is generic SVG scaling/geometry (line/bars/scatter/correlation) — reusable; it is **not** a weekly-data consumer, but its callers pass weekly-shaped series. (VERIFIED)
- Tests use SQLite in-memory `StaticPool` (`tests/conftest.py`) — **not** proof of PG `FOR UPDATE`/race/ARRAY semantics. (VERIFIED)

### Superseded
- ses_e8fd Option B (keep weekly active) superseded: objective requires **replacement and complete removal of functional dependencies** on the weekly *active* model/workflow; weekly summaries derived from daily records; **`partes_semanales` table/data removed only Phase 7** (separately controlled) after refs replaced; unrelated data preserved; never fabricate daily from historic weekly.
- Prior plan text stating “blind reapply” on create-race (§5.5 old) and missing stale-update prevention — **superseded by approved Policy A** (§5.5a/§5.5/§5.3).
- `1792882624161-phase2-concurrency-policy.md` — PROPOSED document **superseded as authority** by Policy A incorporated below (retained as read-only reference).

## 2. Current Weekly Architecture (verified)
| Layer | Files | Responsibility |
|---|---|---|
| Routes | `app/routers/parte.py` | `/parte` GET/POST; athlete-only; `_semana_pedida`; parse/validate; upsert `ParteSemanal` by `(atleta_id, semana)`. |
| Model | `app/models/parte.py` | `ParteSemanal` (`partes_semanales`): wellness 1-5, legacy `fatiga`, aggregate `sesiones/minutos_totales/rpe`, molestias 0-10, timestamps; unique `(atleta_id, semana)`. |
| Services | `app/services/bienestar.py` | `ITEMS/ETIQUETAS/RPE_ESCALA`; `bienestar_total/pct/semaforo/color_total`; `carga_ua=rpe*minutos_totales`; weekly series; `cruce_con_marcas` on `lunes_de`. |
| Services | `app/services/alertas.py` | `sin_parte`, bienestar/molestia/sueño/carga/peso/pago alerts; `acwr` (acute=last weekly carga / chronic=mean prior 4, needs >=2 prior weeks). |
| Services | `app/services/grafico.py` | **Generic** SVG helpers only (`linea,barras,dispersion,correlacion`, scaling/viewBox). No weekly queries/imports — callers supply series. (VERIFIED) |
| UI | `app/templates/atleta/parte.html`, `_campos.html` | Weekly form, CSRF, conditional molestia. |
| Consumers | `app/routers/panel.py,atletas.py,estadisticas.py,cuenta.py`; `app/templates/*`; `app/main.py` | `parte_pendiente`, weekly series/charts, alert cards, ficha/inicio/mis_datos. |
| DB/migrations | `alembic/versions/d61e48816ec5_*`, `a3f1c9e27b04_*`; `alembic/env.py` | Create `partes_semanales`; `fatiga` nullable. **Immutable.** |
| Tests/fixtures/scripts | `tests/conftest.py,test_parte.py,test_bienestar.py,test_alertas.py,test_consultas.py,test_grafico.py`; `scripts/seed*.py` | Weekly rules/helpers. |

## 3. Complete Dependency Inventory (evidence-based, weekly → daily replacement)
> Searched imports/queries/refs for `ParteSemanal|partes_semanales|bienestar\.(parte_de_semana|partes_de|serie_individual|series_de|serie_grupo|promedio_items_grupo|cruce_con_marcas|bienestar_total|semaforo|carga_ua)|sin_parte|SEMANAS_EDITABLES|/parte\?semana|parte_pendiente`. `app/schemas/` — none. `app/static/` JS/CSS — no weekly refs (VERIFIED). Historical alembic + `.kilo/` docs excluded from “active runtime” but tracked for Phase 7 grep gate.

| # | Module/path (exact) | Current weekly dependency (model/field/query/calc) | Actual purpose | Required transition (daily) | Phase | Dependencies / notes |
|---|---|---|---|---|---|---|
| 1 | `app/models/parte.py` (`ParteSemanal`, `partes_semanales`) | Weekly core, `uq_parte_atleta_semana`, 1-5/aggregate fields | Weekly persistence | Keep model/table intact through Phases 1–6 for safety; **remove only Phase 7** after zero active refs + gates. Do **not** fabricate daily from it. | 1 retain; **7 remove (separately authorized)** | HIGH. Immutable history preserved until gated drop. |
| 2 | `app/models/__init__.py` | Exports `ParteSemanal` (+ now `ParteDiaria`,`SesionEntrenamiento`) | Alembic/app model registry | Keep weekly export until Phase 7; ensure daily exports remain. | 1/7 | LOW. |
| 3 | `app/routers/parte.py` | `ParteSemanal`, `bienestar.parte_de_semana`, `SEMANAS_EDITABLES`, `lunes_actual/_semana_pedida`, weekly upsert | Athlete `/parte` GET/POST | Replace with daily today-only workflow (server `hoy()`), multi-session tx, explicit session ops, **signed discard** preserved, **Policy A** edit-state+409/create-race handling, CSRF/auth/ownership. | 3 (logic) + 4 (UI integration) | HIGH. Keep route `/parte`; remove weekly query params/semantics. |
| 4 | `app/services/bienestar.py` | Queries `ParteSemanal`/`User`; 1-5 `ITEMS/MAXIMO/MINIMO`; `carga_ua=rpe*minutos_totales`; `parte_de_semana/partes_de/_armar_serie/serie_individual/series_de/serie_grupo/promedio_items_grupo/cruce_con_marcas` (by `semana`/`lunes_de`) | Weekly calcs, series, group stats, marks cross | Add/adapt daily + **derived weekly** contracts: `carga_sesion/daily/weekly` (reported days), daily 1-10 series, weekly summaries = aggregates over **reported** Mon–Sun daily rows only (`dias_reportados`), missing≠0; redefine “parte pendiente” to today (coord. w/ consumers); adapt `cruce_con_marcas` to `fecha`/derived week (define rule explicitly). **No weekly→daily threshold transfer.** | 2 (contracts/services) + 5 (consumer migration) | HIGH. Preserve weekly helpers only if needed temporarily; remove weekly deps before Phase 7. |
| 5 | `app/services/alertas.py` | `sin_parte`, `_bienestar` (1-5/20, `UMBRAL_MAL`), `_molestia` (`molestias/molestia_dolor`), `_sueno/_carga/peso` weekly series; `acwr` weekly (acute=last, chronic=mean prior 4, >=2 prior, thresholds 1.5/0.8) | Coach alerts | **Preserve existing alert behavior unless separately, explicitly specified.** Phase 2: no fixed ACWR/new heuristics. Phase 5: migrate consumers to daily-derived semantics only for clearly-mapped rules (`sin_registro_hoy` replaces `sin_parte` behavior as approved subset) and keep ambiguous thresholds **deferred/PO-approved**; ACWR isolated/disabled or `None` until approved. No medical/injury claims. | 2 (isolate) + 5 (adapt) + 6 (verify) | HIGH. |
| 6 | `app/services/grafico.py` | Generic (`linea/barras/dispersion/correlacion`); comments mention weekly gaps — implementation data-agnostic | SVG chart primitives | **Reuse as-is** (VERIFIED sufficient for daily series/scatter/bars). No charting-architecture replacement. Update docstrings if touched. | 5 (callers) | LOW. |
| 7 | `app/routers/panel.py` | `ParteSemanal` query `filter(semana==lunes_actual)`; `bienestar.serie_grupo`; `alertas.del_club`; renders participation/bienestar/items/molestias by week | Professor dashboard | Use daily-derived week/today series; `sin_registro_hoy`/reported-day semantics; charts via `grafico` with daily-derived series; keep alert behavior preserved/approved subset. | 5 | MEDIUM-HIGH. |
| 8 | `app/routers/atletas.py` | `ParteSemanal` not directly queried but depends on `bienestar.series_de/bienestar_total/semaforo`, `alertas.del_atleta`, `cobranza` | Athlete roster + ficha (series, alerts, ACWR, charts) | Switch to daily-derived series/contracts; ficha training/wellness charts updated per §8.3/§8.4; keep ownership/auth/professor-only. | 5 | MEDIUM-HIGH. |
| 9 | `app/routers/estadisticas.py` | `bienestar.serie_grupo`, `bienestar.series_de`, `bienestar.cruce_con_marcas`, `alertas.acwr`, `grafico.*`; weekly ranges/trends | Club statistics | Daily-derived group/individual series; daily training + wellbeing visualizations; derived weekly summaries; ACWR display only if approved/non-misleading (else deferred/hidden). | 5 | MEDIUM-HIGH. |
| 10 | `app/routers/cuenta.py` | `bienestar.parte_de_semana(db,user.id,lunes_actual())` → `_parte_pendiente` | Account page, nav badge | Replace with “missing today’s `ParteDiaria`” (`tiempo.hoy()`), scoped to athlete. | 5 | LOW-MEDIUM. |
| 11 | `app/routers/pagos.py` | No weekly report dependency (billing) | Payments | **No functional change** (unrelated). Verify unaffected. | — | None (preserve). |
| 12 | `app/templates/atleta/parte.html`, `app/templates/_campos.html` | Weekly A/B/C/D sections, 1-5, single RPE/minutes/sesiones, `molestias` yes/no, `parte_pendiente` weekly, `semana` labels | Athlete form | Redesign to daily A–E (§6), 1-10, conditional illness/`otro`+`molestia_zona_otra`, `entreno_hoy`, dynamic sessions (stable IDs, explicit remove/add), discard confirm UX (server token/state), previews, 409 conflict recovery/reload, CSRF, repopulation. | 4 (primary) / 3 (server integration) | MEDIUM. |
| 13 | `app/templates/atleta/inicio.html` | `parte_pendiente`/`falta_anterior` weekly semantics, bienestar/carga/sueño series charts | Athlete home | Today-pending; daily/derived evolution charts; missing vs zero semantics in copy; keep cuota/marcas blocks. | 5 | MEDIUM. |
| 14 | `app/templates/atleta/mis_datos.html` | Weekly series table/charts (`bienestar/sueno/carga`, `parte`, `parte_pendiente`) | Athlete evolution | Daily evolution (selected period) + derived weekly summaries secondary; missing days distinct; no missing→0. | 5 | MEDIUM. |
| 15 | `app/templates/panel/panel.html` | “Partes de esta semana”, participation/molestias/bienestar by week | Professor dashboard UI | Today/derived-week labels; daily-derived data; reported-day coverage (`dias_reportados`) where shown. | 5 | MEDIUM. |
| 16 | `app/templates/panel/atletas.html` | “Sin parte” chip, `f.semaforo/bienestar` weekly-derived | Roster list | “Sin registro hoy”/approved semantics; preserve alert chips behavior per policy. | 5 | MEDIUM. |
| 17 | `app/templates/panel/atleta_ficha.html` | `serie` weekly rows, `acwr`, `grafico_bienestar/carga/sueno/peso`, “Partes semanales” table | Athlete ficha | Daily-derived series; training+wellbeing daily charts/categorical summaries; derived weekly table or daily table (min change preserving function); ACWR only if approved. | 5 | MEDIUM-HIGH. |
| 18 | `app/templates/panel/estadisticas.html` | Weekly trends/correlations/ACWR dispersion-adjacent metrics | Stats UI | Daily-derived charts, numeric/categorical wellbeing, derived weekly summaries, missing semantics, ACWR deferred if unapproved. | 5 | MEDIUM-HIGH. |
| 19 | `app/templates/_tabbar.html`, `_nav.html`, `_iconos.html`, `base.html`, `app/templates_config.py` | Nav/labels; `templates_config` has `color_bienestar` (bienestar scale helper) — may assume 1-5/20 semantics via service | Navigation/presentation infra | Update labels/badges to daily tracking; adapt `color_bienestar`/globals only if scale/meaning changes (PO/approved). Verify no weekly route assumptions. | 4/5 | LOW. |
| 20 | `app/main.py` | Includes `parte` router | App wiring | Keep router include; no weekly removal except route behavior changes inside router. | 3 | LOW. |
| 21 | `tests/conftest.py` | `crear_parte` → `ParteSemanal`; SQLite in-memory | Test fixtures | Add daily fixtures/builders (`ParteDiaria`/sessions, tokens helpers hooks) + PG-disposable fixture/marker (env-gated). Keep weekly helpers until weekly tests removed/rewritten. | 2/3/6 | MEDIUM. |
| 22 | `tests/test_parte.py` | Full weekly `/parte` behavior | Weekly form/validation tests | Replace/rewrite for daily `/parte`, sessions, discard, Policy A 409s, auth/CSRF/ownership. Remove weekly-only assumptions. | 3/4/6 | HIGH (rewrite). |
| 23 | `tests/test_bienestar.py` | `ParteSemanal`/1-5/20/`carga_ua`/weekly series | Weekly service tests | Split/rewrite: daily 1-10, load contracts, reported-day aggregation, missing≠0, derived weekly summaries; keep/retire weekly tests per migration. | 2/5/6 | HIGH. |
| 24 | `tests/test_alertas.py` | `sin_parte`/weekly thresholds/ACWR | Alert tests | Preserve behavior coverage where applicable; update to approved daily semantics; remove/adjust ACWR cases if deferred. | 5/6 | HIGH. |
| 25 | `tests/test_consultas.py` | `ParteSemanal` counts/series, weekly query budget patterns | Query/perf + contract tests | Adapt to daily-derived queries and equivalent/justified budgets. | 5/6 | MEDIUM. |
| 26 | `tests/test_grafico.py` | Generic SVG (if present behavior weekly-agnostic) | Graph helper tests | Keep; extend for daily-series shapes/missing gaps if needed. | 6 | LOW. |
| 27 | `tests/test_parte_diaria_schema.py` | Phase 1 schema sanity (SQLite) | New schema regression | Keep passing; may extend (non-breaking). | 1/6 | LOW. |
| 28 | Other unrelated tests (`test_pagos*`/`test_cobranza*`/`test_marcas*`/`test_asistencia*`/`test_seguridad*`/`test_validacion*`/`test_urls*`/`test_config*`/`test_pruebas*`/`test_landing*`/`test_busqueda*`) | No direct weekly report dependency (VERIFIED by grep focus) | Unrelated regressions | **No change** expected; run in Phase 6 regression. | 6 | LOW (monitor). |
| 29 | `scripts/seed.py`, `scripts/seed_5_atletas.py` | Create `ParteSemanal` rows/weekly data | Dev/demo data | Migrate to create `ParteDiaria` (+ sessions) or split legacy/demo clearly; no fabrication from old weekly. | 5/6 | LOW-MEDIUM. |
| 30 | `alembic/versions/d61e48816ec5_*`, `a3f1c9e27b04_*` | Create/alter `partes_semanales` | Historical migrations | **Immutable, never modified.** | — | — |
| 31 | `alembic/versions/c4b8e2d91f07_*` | Creates `partes_diarios`/`sesiones_entrenamiento` (Phase 1, validated) | Additive schema | **Immutable going forward** (validated/accepted). No schema change for Policy A. | 1 done | — |
| 32 | `alembic/env.py`, `alembic.ini` | `Base.metadata`/settings URL | Migration config | No change expected; supports controlled upgrades. | 1/7 | LOW. |
| 33 | `render.yaml`, `DEPLOY.md`, `README.md` | `alembic upgrade head` on deploy/manual | Ops | **Must not auto-execute drop revision.** Update in controlled change tied to Phase 7 strategy (targeted upgrade for non-drop deploys; separate authorized drop). Not executed now. | 7 (controlled) | MEDIUM (ops). |
| 34 | `.kilo/plans/*`, `.kilo/kiloSesions/*` | Historical/planning references to weekly terms | Docs/evidence | **Not runtime deps.** Excluded from grep-zero functional gate except awareness; this task updates authoritative plan only. | — | N/A. |

**Grep gate (before Phase 7 drop):** zero **functional/runtime** refs to `ParteSemanal|partes_semanales|parte_de_semana|partes_de|SEMANAS_EDITABLES|carga_ua` (weekly semantics)|`/parte?semana`|`sin_parte` in `app/`, `tests/`, `scripts/`, templates/static. **Exclude** historical `alembic/versions/d61e48816ec5*` and `a3f1c9e27b04*` and `.kilo/` documentation. Any intentional temporary compatibility must be listed and removed.

## 4. Proposed Daily Data Architecture (SQLAlchemy 2 + PostgreSQL) — **Phase 1 COMPLETE (validated, preserved)**

### 4.1 Daily record — `partes_diarios` (`ParteDiaria`) *(resolved — technical naming)*
> **Naming (resolved):** `partes_semanales`/`ParteSemanal` → `partes_diarios`/`ParteDiaria`.
- `id` PK; `atleta_id` FK→`users.id` `ondelete=CASCADE`, indexed, NOT NULL.
- `fecha` `Date` NOT NULL — **server-only** `tiempo.hoy()` (`America/La_Paz`); athlete ignores/rejects client date.
- **Unique** `('atleta_id','fecha')` `uq_parte_diaria_atleta_fecha` + indexes.
- Wellness (required): `sueno_calidad, fatiga, dolor_muscular, estres, animo` Int `CHECK 1-10`; `horas_sueno` `Numeric(4,1)` `CHECK 0-24`. **Fatigue ≠ session RPE**.

**Wellness 1–10 scale definitions (established):** Sleep 1–3 *Deficient*/4–6 *Regular*/7–10 *Good*. Fatigue/muscular pain/stress 1–3 *Low*/4–6 *Moderate*/7–8 *Elevated*/9–10 *Extreme*. Mood 1–2 *Very discouraged*/3–4 *Discouraged*/5–6 *Regular*/7–8 *Good*/9–10 *Excellent*. (UI labels must reflect; alert composites/cutoffs remain PO-pending §9.2/§13.)

- `hay_molestia` Bool NOT NULL default false. `molestia_zona` **PG `ARRAY(String)`** nullable (whitelist incl. `otro`), SQLite JSON variant. `molestia_zona_otra` `String(120)` nullable — **required iff `otro` selected; cleared otherwise** (backend). `molestia_dolor` Int `CHECK 1-10` nullable (required iff `hay_molestia`). `afecta_entrenamiento` Int `CHECK 0-3` nullable (required iff `hay_molestia`).
- `sintomas_enfermedad` Bool NOT NULL default false. `detalle_sintomas` Text nullable — **optional** when true; cleared when false; **not mandatory without explicit PO approval**.
- `comentarios` Text nullable. `entreno_hoy` Bool NOT NULL.
- `enviado/actualizado` `DateTime(timezone=True)` `server_default now()`, `onupdate`.
- **No schema change for Policy A** (no `version` column). Concurrency uses signed tokens + locks (§5.5a). Discard uses signed token + fingerprint (§5.3).

### 4.2 Training sessions — `sesiones_entrenamiento` (`SesionEntrenamiento`)
- `id` PK (**stable**). `parte_diaria_id` FK→`partes_diarios.id` `ondelete=CASCADE`, indexed, NOT NULL.
- `orden` Int NOT NULL. `tipo_entrenamiento` whitelist (`velocidad_sprint,resistencia,fuerza,tecnica_coordinacion,movilidad_recuperacion,competencia,entrenamiento_mixto,otro`).
- `duracion_min` Int NOT NULL `CHECK > 0`; `rpe` Int NOT NULL `CHECK 1-10`.
- `carga_sesion` Int NOT NULL — **backend recomputed** `duracion_min*rpe` (never trust client).
- `comentarios_entrenamiento` Text nullable.
- ORM: `ParteDiaria.sesiones` 1:N, `cascade='all, delete-orphan'`, `order_by=orden,id`, `passive_deletes=True`. DB `ON DELETE CASCADE` consistent.

### 4.3 Load & aggregation contracts (authoritative)
- `carga_sesion = duracion_min × rpe` (per session). `carga_diaria = Σ carga_sesion` (`0` only for a **submitted** `entreno_hoy=false` record with no sessions).
- `carga_semanal = Σ carga_diaria` over Mon–Sun (`lunes_de`) **counting only existing daily records**.
- **Missing daily reports ≠ 0 load** (unknown). Aggregates/trends/averages/ACWR exclude missing days from observed sums/denominators; expose `dias_reportados` and missing/context counts (`dias_con_entreno`, `dias_con_molestia`, `dias_con_sintomas` as applicable). `entreno_hoy=false` = observation; missing row = not observed.

### 4.4 Indexes/constraints
`uq_parte_diaria_atleta_fecha`; date/athlete-date/session-FK indexes; defense-in-depth checks. (S-0021 verified on disposable PG.)

## 5. Business Rules, Validation & Integrity (frontend + backend + DB)

### 5.1 Core record rules
1. **Unique** `(atleta_id, hoy())` via DB constraint + app logic. Concurrent create → **Policy A conflict** (§5.5), no blind reapply.
2. **Server date authority**: `tiempo.hoy()` only for athlete create/update.
3. **Today upsert/update**: GET loads today (+ fresh edit-state token for existing state). POST applies validated full state atomically to `(user.id,hoy())` **only if** edit-state/discard/create-race checks pass.
4. **Ownership**: athlete mutations/reads scoped to `user.id`; every `session_id` bound to locked owned `ParteDiaria`; 403/404/422 per conventions.
5. **Transactions**: all record+session mutations in one DB transaction; `IntegrityError` ⇒ `db.rollback()`. **CSRF required**.

### 5.2 `entreno_hoy` and sessions
6. **`entreno_hoy=true` ⇒ >= 1 valid session required** (frontend+backend; 422).
7. **`entreno_hoy=false` ⇒ zero sessions persisted/displayed**. No silent deletion — true→false with existing sessions uses **only** §5.3.
8. **Validation**: `duracion_min>0`, `rpe` 1-10, `tipo` whitelisted, `carga_sesion` recomputed server-side.

### 5.3 Yes→No discard — signed, locked, transactional (**preserved, no weakening**)
**Never** delete sessions silently; never rely on a free hidden boolean or JS-only confirmation. Cancel/invalid/stale ⇒ preserve all.

**`session_state_fingerprint` (canonical, deterministic):** persisted sessions in stable order (`orden,id`), including `id,orden,tipo_entrenamiento,duracion_min,rpe,carga_sesion,comentarios_entrenamiento` (stable serialization + hash/HMAC). Represents exact discardable set.
**`discard_token` (server-signed, HMAC/SHA-256, `settings.secret_key`, `compare_digest`, short expiry e.g. 15 min):** `purpose=discard_sessions`, `atleta_id`, `fecha_iso` (server `hoy()`), `registro_id`, `session_state_fingerprint`, `exp`.

**Two-step flow**
- **Step 1 (intent, no deletion):** lock `ParteDiaria (user.id,hoy())` (§5.4), load record+sessions, recompute fingerprint, **do not delete**, return 422/confirmation-required with count/summary, fresh `discard_token`, preserved form state. (May also return fresh edit-state token for current state.)
- **Step 2 (explicit confirm):** deliberate UI action + `discard_token` + explicit confirm flag. **One transaction:** lock → reload → recompute current session fingerprint → verify discard token (signature/expiry/purpose/athlete/fecha/registro/fingerprint == current) **and** verify edit-state consistency where applicable under Policy A (no weakening) → fail ⇒ **controlled conflict/422 (no delete)**, fresh token; success ⇒ set `entreno_hoy=false`, remove sessions, commit same tx.
- **Cancellation/missing token**: sessions preserved.

### 5.4 Locking & transaction conventions (PG authoritative)
`SessionLocal(autocommit=False, autoflush=False)`, `get_db()`; `IntegrityError` ⇒ `db.rollback()`. **Parent-row lock for every session-mutating/discard/critical update:** `SELECT ... FOR UPDATE` on `ParteDiaria` `(atleta_id,fecha==hoy())` (or equivalent SA 2 `with_for_update()`) **first**, then verify tokens/fingerprints against **reloaded current state**, then mutate, then `commit` — same tx. **Mandatory state recheck after lock.** **SQLite cannot prove row-lock/race behavior; PG-disposable tests authoritative.**

### 5.5a Policy A — Edit-state token / stale-update prevention (**APPROVED, fixed**)
- **Signed `edit_state_token`** (HMAC/SHA-256, `settings.secret_key`, `hmac.compare_digest`, short expiry) with distinct `purpose=edit_parte_diaria`. **No schema change.**
- **Canonical `record_state_fingerprint` (deterministic, all relevant persisted state):** `ParteDiaria` mutated/persisted fields — `atleta_id, fecha, sueno_calidad, horas_sueno, fatiga, dolor_muscular, estres, animo, hay_molestia, molestia_zona` (normalized/sorted), `molestia_zona_otra, molestia_dolor, afecta_entrenamiento, sintomas_enfermedad, detalle_sintomas, comentarios, entreno_hoy, registro_id` — **+** normalized session set in stable order (`orden,id`) with `id,orden,tipo_entrenamiento,duracion_min,rpe,carga_sesion,comentarios_entrenamiento`. Canonical serialization (e.g., stable JSON of normalized primitives) before hashing/signing. Exclude volatile timestamps unless required (fingerprint is source of truth).
- **Issuance:** GET `/parte` (today) returns token for current persisted state (or create marker/absent when no record). 422/conflict responses return **fresh token for current persisted state** + preserved submitted values for user recovery (server state authoritative).
- **Verification (mutations to an existing record):** single tx: `FOR UPDATE` lock → reload current record+sessions → recompute current fingerprint → verify signature/expiry/purpose/`atleta_id`/`fecha`/`registro_id` **and** `token.record_state_fingerprint == current`. **Mismatch/tamper/expiry/wrong binding ⇒ HTTP 409 Conflict, no writes, no overwrite, rollback**, respond with clear “submitted state is outdated” message + reload path/fresh token + current state (and user-submitted data preserved for manual recovery; **never silently discard/overwrite/blindly retry**).
- **Match:** apply validated changes (explicit session ops; recompute `carga_sesion`; discard sub-protocol only as §5.3) → commit.

### 5.5 Policy A — Concurrent daily-record creation / `IntegrityError` (**APPROVED, fixed; replaces blind reapply**)
Unique `(atleta_id, fecha)` may raise `IntegrityError` on concurrent inserts.
1. Create/update path resolves server `hoy()`, ownership, CSRF, validation. For existing row, prefer `FOR UPDATE` load+edit-state check. For create attempt, insert in tx.
2. On `IntegrityError` (likely unique violation): **`db.rollback()`** (required).
3. Reload (and lock) `ParteDiaria` for `(atleta_id, hoy())`.
4. **Do NOT reapply/retry submitted payload automatically.** Return **HTTP 409 Conflict** with clear outdated/created-elsewhere explanation, **fresh edit-state token for current persisted state**, and current state for reload/recovery. No duplicate records, no partial session persistence.
5. **Optional narrow safe case (only if implemented):** auto-apply **only** when request carries a **valid edit-state token proving update of the exact current reloaded state** (fingerprint+registro match) — default is conflict. No blind merge.
- Reload failure ⇒ controlled error (409/422/500 as appropriate), **no partial write**.

### 5.6 Explicit session deletion/update semantics
- **Stable IDs**: persisted sessions carry `id`; submitted existing rows include `session_id`; new rows omit id.
- **Ownership/binding**: each `session_id` must belong to locked `ParteDiaria` for `(user.id,hoy())`; unknown/foreign ⇒ 422/403.
- **No implicit delete by omission** (default). Individual deletes explicit (dedicated remove action/`delete_session_ids[]`) in tx. **Explicit validated complete-replacement mode** allowed only if unambiguously marked + locked + fully validated + discard implications handled — prefer explicit removes.
- `entreno_hoy` true→false uses §5.3 only.

### 5.7 Conditional fields (backend normalizes)
`hay_molestia=false` clears zones/otra/dolor/afecta. `true` requires whitelisted `molestia_zona`, `molestia_dolor` 1-10, `afecta_entrenamiento` 0-3; `otro` ⇒ required trimmed non-empty `molestia_zona_otra` (≤120) else cleared. `sintomas_enfermedad=false` clears `detalle_sintomas`; `true` accepts **optional** trimmed `detalle_sintomas`.

## 6. Frontend Plan (responsive, reuse conventions)
- Keep `/parte`; redesign `app/templates/atleta/parte.html`; extend `_campos.html` (1-10 + wellness ranges, multi-region select, conditional `otro`). Progressive JS only if patterned — no new deps.
- **A–E** categories; `entreno_hoy` toggle; dynamic sessions with **stable `session_id`**, explicit remove/add; per-session + daily load previews (server authoritative).
- **Discard UX:** explicit confirm bound to server `discard_token`/state; cancel preserves.
- **Policy A UX (Phase 3/4 integration):** show clear 409 message (“tu información está desactualizada / el registro cambió”), preserve user-submitted values for review, provide explicit **reload latest record** action and re-submit path with fresh tokens. **Never silent discard/overwrite/blind retry.** CSRF preserved; repopulate on errors.

## 7. Migration & Historical Data Strategy (safe, ops-aware)
**Established:** no fabrication from weekly; weekly *functional* deps fully replaced; `partes_semanales` table+data dropped **only Phase 7** after all functional refs replaced + hard gates; unrelated data intact. **Phase 1 done:** `c4b8e2d91f07` (additive) validated on disposable PG 16.15 (S-0021). Never execute prod migrations here.

### Alembic (forward-only; never modify `d61e48816ec5`, `a3f1c9e27b04`, or validated `c4b8e2d91f07`)
1. **Expand (complete):** `c4b8e2d91f07_add_partes_diarios_sesiones.py` — verified.
2. **Application replacement** until grep gate zero (§3).
3. **Contract (separate, controlled, Phase 7):** `<new>_drop_partes_semanales.py` — **only** under hard gates; **excluded from automatic deployment execution**.

### Critical deployment safety (`render.yaml`/`DEPLOY.md`/`README.md` run `alembic upgrade head`)
**Required controlled sequence:** keep drop revision out of auto-deployed path until authorized (deploy expand/no-drop target, or controlled `upgrade <rev>`, or separately authorized drop job). Verify grep gate + tests + PG-disposable validation + runtime smoke. Then **separately controlled, explicitly authorized** operation: **verified backup/snapshot**, approved maintenance window, execute drop. Rollback readiness. **No prod execution in this task.**

## 8. Statistics, Load, Wellness & Visualization Contracts

### 8.1 Load (training chart + services)
- `carga_sesion = duracion_min*rpe` (backend). `carga_diaria = Σ carga_sesion`. `carga_semanal = Σ carga_diaria` Mon–Sun over **reported days only**. Missing ≠ 0.
- **Daily training visualization (authoritative):** data sources **`ParteDiaria` + `SesionEntrenamiento` only**. Indicators: (1) **Total daily training duration** = Σ `duracion_min` of sessions for that day; (2) **Total daily training load** = Σ `duracion_min*rpe`. (3) **RPE = independent session-level indicator** — show per session (and/or session list/detail); **do not invent an aggregation rule for RPE or present an unqualified daily average RPE**. (If a clearly labeled session-level presentation is used, keep it explicit; no hidden mean.)
- **Semantics:** reported day with `entreno_hoy=false` may represent **zero duration and zero training load** (observed). Day **without** a daily report = **missing data, not zero training** (gap/null) — **never fabricate or plot as zero**. **Never use legacy weekly training values as a source.** **Do not mix wellbeing indicators into the training chart.**
- **Architecture:** reuse `app/services/grafico.py` (generic SVG, VERIFIED) where appropriate; do **not** replace charting architecture without concrete evidence. Current training/load chart callers (VERIFIED): `app/routers/atletas.py` + `templates/panel/atleta_ficha.html` (`grafico_carga` bars); `app/routers/estadisticas.py` + `templates/panel/estadisticas.html` (group carga); `app/routers/panel.py` (athlete/inicio paths use bienestar series — verify all carga visuals); `app/templates/atleta/inicio.html|mis_datos.html` consume series. Implementation must build daily-derived series in services and pass to `grafico` (Phase 5).

### 8.2 Daily wellbeing visualizations (authoritative)
Sources: **`ParteDiaria`** numeric/categorical fields. Transition existing athlete-status weekly visualizations to daily records.
- **Numeric (daily evolution, selected period):** `sueno_calidad, horas_sueno, fatiga, dolor_muscular, estres, animo`. Preserve each indicator’s meaning and **original scale** (1–10 for scales; `horas_sueno` 0–24). Distinguish **missing days** from reported values (`None`/gap) — **never convert missing to zero**. **Do not combine unrelated indicators into a misleading common scale.** (A clearly labeled composite/index is **not** approved by this plan; avoid unless explicitly specified/approved — UNRESOLVED/PO if desired.)
- **Categorical (appropriate representation):** `hay_molestia` + `molestia_zona` (multi), `afecta_entrenamiento`; `sintomas_enfermedad` (+ optional `detalle_sintomas` text). Use **counts/frequencies/presence summaries** over selected period/reported days. **Do not calculate arbitrary numeric averages for categorical information.**
- **Weekly summaries (secondary, derived only):** may be shown as secondary. Calculated **exclusively from reported daily records** (Mon–Sun), respect valid values/scales, **exclude missing values** (never treat as zero), report `dias_reportados`/coverage. **Never an independent source of truth.** Weekly view (§8.4) is a derived consultation/reporting interface.

### 8.3 ACWR — verified current state + deferred (do not block core)
VERIFIED: `app/services/alertas.py::acwr` weekly (acute last `carga` / chronic mean prior 4, >=2 prior, else `None`; 0 chronic `None`); thresholds `ACWR_ALTO=1.5`,`ACWR_BAJO=0.8`; weekly `carga` from `bienestar.carga_ua`. Candidates (not approved): weekly buckets from daily sums vs rolling 7/28. Missing reports reduce coverage → `None`; never missing as 0. **Isolate from Phases 2–4 core; no fixed new rule without PO approval + calibration.**

### 8.4 Weekly view compatibility (derived, preserved)
- Weekly view remains a **derived consultation/reporting interface**. Derive values **only** from daily records; **no dependency on removed weekly submission workflow**; **never reintroduce `ParteSemanal` as active source of truth**.
- Preserve `dias_reportados` (and missing counts where useful) to distinguish incomplete coverage. Missing days ≠ zero / ≠ no training.
- Weekly training load = Σ reported daily training loads Mon–Sun. Inspect existing weekly UI/queries and apply **minimum changes** to preserve functionality (`panel`, stats, ficha tables/labels as needed) — Phase 5.

## 9. Alerts — preserve behavior unless explicitly specified (no medical claims)

### 9.1 Migration approach (Policy A-era constraint)
- **Preserve existing alert behavior unless a separate, explicitly specified change is necessary.** No new medical interpretations, injury-risk formulas, or unapproved thresholds.
- Implementable mapping (Phase 5, with approved semantics): `sin_parte` → `sin_registro_hoy` (no `ParteDiaria` for `hoy()`), distinct from `entreno_hoy=false`/`no_entreno_hoy` informational. Molestia/síntomas map to new fields when reported; missing report ⇒ no alert. `pago_vencido` unchanged. **Copy/severity require PO approval where noted.**

| Key | Trigger (evidence-based) | Missing-data behavior | Notes |
|---|---|---|---|
| `sin_registro_hoy` (replaces `sin_parte`) | No `ParteDiaria` for `(atleta, hoy())` | absence is signal | severity/copy **PO approval** |
| `no_entreno_hoy` | Record exists, `entreno_hoy=false` | only if record exists | informational, not risk escalation |
| `molestia_reportada` | `hay_molestia=true` | missing ⇒ no alert | severity/copy **PO approval** |
| `sintomas_enfermedad` | `sintomas_enfermedad=true` | missing ⇒ no alert | `detalle_sintomas` optional |
| `pago_vencido` | existing billing logic | unchanged | unchanged |

### 9.2–9.3 Deferred / PO approval (fixed rules not shipped)
`sin_registro_reciente` (N), 1-10 composite `bienestar_bajo/item_minimo/caida_bienestar` (no 1-5/20 transfer), `sueno_insuficiente` daily window, `carga_alta_dia`/baselines, ACWR enablement/thresholds/windows/coverage, severities/copy, calibrated personal baselines. Monitoring indicators only.

## 10. Security & Data Integrity
Reuse `get_current_user`/role guards, CSRF (`app/csrf.py`/`CSRFMiddleware`), `get_db()`. Ownership on every query/mutation; `session_id` binding. Server `hoy()` + backend recompute/normalization. **Signed `discard_token`** + lock + fingerprint recheck (§5.3, preserved). **Signed `edit_state_token`** + lock + reload + fingerprint verify, **409** on stale/create-race per **Policy A** (§5.5a/§5.5). Unique constraint + `IntegrityError` rollback/reload/conflict. PG authoritative for locking/races.

## 11. Testing Strategy (plan; NOT RUN by this task)

| Type | Scope |
|---|---|
| **Unit (SQLite/logic)** | load math recompute; `entreno_hoy`/session invariants; conditional normalization/clearing; `otro`/`molestia_zona_otra`; optional `detalle_sintomas`; whitelists/ranges; Mon–Sun aggregation + `dias_reportados` + missing≠0; canonical fingerprint determinism; token sign/verify (edit-state + discard), tamper/expiry/purpose/bindings. |
| **Integration (SQLite app/DB path where meaningful)** | create/update today, uniqueness handling path, `hoy()` authority, 1/multi sessions, explicit session ops (no implicit omission), discard flow preservation/cancel, 422 validation, ownership/cross-athlete blocked, CSRF/auth flows, 409 conflict responses/recovery payloads (as implemented). |
| **Integration (real PostgreSQL, disposable only)** | `SELECT FOR UPDATE` serialization; stale wellness/session update ⇒ **409, DB unchanged, no overwrite**; discard vs concurrent change ⇒ reject/no delete; concurrent create `IntegrityError` ⇒ rollback+reload ⇒ **409, count==1, no blind reapply/no dup/no partial**; valid sequential update commits; migration/ARRAY/check/FK/cascade behavior (S-0021 baseline) + service paths. **Never on prod/staging/shared/real data.** |
| **Regression** | full `pytest` (SQLite path) + keep unrelated green; adapt/rewrite weekly-report tests/fixtures (`test_parte.py`, `test_bienestar.py`, `test_alertas.py`, `test_consultas.py`, `conftest.py`, seeds). |
| **Visualization semantics (Phase 5/6)** | training chart uses `ParteDiaria`+`SesionEntrenamiento` only; `entreno_hoy=false` reported ⇒ zero duration/load; missing day ⇒ gap/not zero; RPE not unqualified daily average; wellbeing numeric scales preserved, missing≠0, categoricals as counts/frequencies; weekly summaries derived from reported days with `dias_reportados`. |

**SQLite not proof of PG locks/races.** Destructive drop migration dry-run only in disposable env under Phase 7 controls (not executed).

## 12. Implementation Phases (7-phase strategy retained, refined)

### Phase 0 — Prep & guardrails (**complete/pending confirmation**) 
Grep baseline; PG-disposable + test strategy; confirm Policy A understood. **Acceptance:** baseline documented; no code changes.

### Phase 1 — Schema & migration (**COMPLETE, validated — preserve**)
- **Files (existing, immutable evidence):** `app/models/parte_diaria.py`, `app/models/sesion_entrenamiento.py`, `app/models/__init__.py`, `alembic/versions/c4b8e2d91f07_add_partes_diarios_sesiones.py`. Historical `d61e48816ec5`,`a3f1c9e27b04` immutable.
- **Evidence:** S-0021 disposable PG 16.15 validation; schema tests 7 passed (SQLite). **No schema change for Policy A.**
- **Acceptance (met):** imports OK; additive migration applied on disposable PG (not `head`); `partes_semanales` intact.

### Phase 2 — Core domain services (**Policy A fully specified here; implementation NOT authorized**)
- **Objective:** daily domain logic + concurrency safety (service-level), no router UI.
- **Scope:** daily create/update/session mgmt services; `carga_sesion` recompute + daily/weekly reported-day aggregation + `dias_reportados`; conditional normalization/validation; **signed edit-state token gen/verify** + **canonical `record_state_fingerprint`** (deterministic, all relevant persisted state); **DB locking + tx handling** (`FOR UPDATE`, rollback discipline); **stale-state detection ⇒ 409/conflict result**; **create-race `IntegrityError` ⇒ rollback+reload+conflict (no reapply)**; **preserve signed discard-confirmation** protocol/helpers; explicit session ops (stable IDs, no implicit omission). **No ACWR/new alert heuristics.**
- **Files (proposed):** `app/services/parte_diaria.py` (or equivalent, NEW), `app/services/parte_diaria_tokens.py` (NEW), minimal/adaptive touches to `app/services/bienestar.py` only if additive/non-breaking (prefer new module), additive `tests/conftest.py` helpers, `tests/test_parte_diaria_service*.py`, `tests/test_parte_diaria_concurrency_pg.py` (PG-only, disposable). **No changes:** migrations/schema/historical alembic, `csrf.py/database.py/auth.py` (reuse), routers/templates/weekly consumers (except not touched).
- **Dependencies:** Phase 1 models/migration; `tiempo.hoy/lunes_de`; `settings.secret_key`; Policy A approved.
- **Acceptance:** AC1–AC9 (relevant subset) pass: loads authoritative, missing≠0 aggregation, `entreno_hoy` invariants, conditional rules, ownership binding helpers, atomic tx/rollback safety, **PG stale/create-race/discard-race conflicts with no overwrite/dup/partial**, edit-state+discard tokens verified after lock/reload, no ACWR/new heuristics/weekly regression.

### Phase 3 — Router integration (**HTTP 409 + recovery; implementation NOT authorized**)
- **Objective:** wire Phase 2 services into `/parte` workflow.
- **Scope:** replace weekly `app/routers/parte.py` semantics (keep route) for athlete today-only GET/POST; server `hoy()`; CSRF (`CSRFMiddleware`/patterns), auth (`get_current_user`, athlete role), ownership; multi-session form parsing + explicit ops; **HTTP 409** for stale updates/create-races with clear outdated-state message and reload/fresh-token/current-state recovery payload; **preserve signed discard-confirmation integration** (two-step) and 422 UX for validation/discard-intent; repopulation. Conflict recovery UX coordination with Phase 4 templates/JS.
- **Files (proposed):** `app/routers/parte.py`; possibly small token/helper wiring; **no schema/migration changes**.
- **Dependencies:** Phase 2 complete/green (esp. PG concurrency); Phase 4 form fields aligned.
- **Acceptance:** correct 409/422/403/404 flows; no silent overwrite/discard/blind retry; CSRF/auth/ownership enforced; `entreno_hoy`/sessions/discard transactional; create-race safe.

### Phase 4 — Daily forms & interface (**implementation NOT authorized**)
- **Objective:** athlete-facing daily submission/editing UI.
- **Scope:** daily A–E wellness form, 1-10 guidance, conditional molestia/`otro`+`molestia_zona_otra`, optional conditional `detalle_sintomas`, `entreno_hoy`, dynamic sessions (stable IDs, explicit remove/add), previews, discard confirm UX, 409 reload/recovery UI, validation/error display/repopulation. Reuse `_campos.html`/project conventions; minimal patterned JS/CSS only.
- **Files (proposed):** `app/templates/atleta/parte.html`, `app/templates/_campos.html`, nav/tabbar/labels as needed (`_tabbar.html`/`_nav.html`/`templates_config.py` minimal), `app/static/*` only if already patterned.
- **Dependencies:** Phase 3 router contract; Phase 2/3 token flows.
- **Acceptance:** daily edit/create works against today; discard never silent; 409 clearly recoverable; no weekly submission workflow dependency; responsive/accessible per existing patterns.

### Phase 5 — Consumer migration & visualizations (**all identified consumers; implementation NOT authorized**)
- **Objective:** remove active weekly functional deps; migrate to daily/derived-weekly.
- **Scope (evidence-based):** `bienestar` daily+derived-weekly APIs; training chart migration (duration/load; RPE session-level, no unqualified avg) and daily wellbeing numeric/categorical visualizations + secondary derived weekly summaries; migrate `routers/panel.py,atletas.py,estadisticas.py,cuenta.py`; templates `atleta/inicio.html,mis_datos.html`, `panel/panel.html,atletas.html,atleta_ficha.html,estadisticas.html`; alert consumers adapted preserving behavior/approved mappings; `cruce_con_marcas` adapted; `scripts/seed.py,seed_5_atletas.py` to daily data; `grafico.py` reused. **ACWR/ambiguous thresholds not falsely enabled.**
- **Dependencies:** Phases 2–4; §3 inventory complete.
- **Acceptance:** grep gate near-zero for active app/templates/tests/scripts (excluding allowed historical alembic + `.kilo/`); visualizations follow §8.1/§8.2 semantics (missing≠0, no legacy weekly source, no mixed wellbeing in training chart, no RPE fabricated avg, categoricals as counts/freq); derived weekly preserves `dias_reportados`; `ParteSemanal` not active source.

### Phase 6 — Regression & integration validation (**implementation/validation NOT run now**)
- **Scope:** unit + integration (SQLite) + **real PG-disposable** concurrency/locking/409/discard-race/create-race; visualization data-semantics tests; missing-day/incomplete-week/derived-weekly tests; auth/authz/ownership/CSRF regressions; existing regression suite green; adapted weekly tests/fixtures/seeds.
- **Acceptance:** targeted+full `pytest` green per strategy; PG-disposable concurrency/Policy A cases pass; no unintended weekly active refs; ACWR/ambiguous alerts not enabled.

### Phase 7 — Legacy weekly data removal (**separately controlled, explicitly authorized; NEVER auto-executed**)
- **Scope:** remove `ParteSemanal` model/export/remaining refs; add separate forward `drop_partes_semanales` migration; update ops docs/mechanism so drop is **not** auto-executed (`render.yaml`/`DEPLOY.md`/`README.md`) — controlled only.
- **Hard gates:** Phase 6 green; grep gate zero (active `app/tests/scripts/templates/static`); PG-disposable validation incl. drop dry-run; **independent impact assessment** (historical weekly rows become unavailable; UI/history consequences communicated); **verified backup/snapshot + recovery/rollback plan**; **explicit user authorization**; approved maintenance window; separately controlled execution. **No prod execution in this task.**

## 13. Decisions

**Established:** daily unique per athlete+local date (server `America/La_Paz`); athlete today-only; multi-sessions; `duracion*RPE`/daily/weekly sums over reported days; fatigue independent of session RPE; `entreno_hoy` rules + secure explicit discard; conditional validation/cleanup; transactional+concurrent-safe; stats/charts from daily (+ derived weekly secondary); missing≠0; no fabrication from weekly; replace functional deps; drop old table/data only Phase 7 gated/controlled; preserve unrelated data; no prod migration execution.

**Approved/resolved (fixed):** **Policy A** — signed `edit_state_token` + canonical deterministic `record_state_fingerprint` (record + all relevant persisted session state), verified **after `FOR UPDATE` lock + reload**; stale ⇒ **HTTP 409, no silent overwrite**; create `IntegrityError` ⇒ `rollback`+reload+lock ⇒ **409 conflict, no blind reapply/retry**; conflict recovery = clear message + reload/fresh token/current state, **never silent discard/overwrite/blind retry**. **Preserve existing signed discard-confirmation protocol** (no weakening). `entreno_hoy=true`⇒>=1 session; stable session IDs + explicit deletes (no implicit omission except explicit validated full replacement). `molestia_zona_otra` conditional; `detalle_sintomas` optional. Phase 1 schema/migration preserved; **no schema change for concurrency**. ACWR isolated. Deploy drop excluded from auto `upgrade head`. Visualization semantics fixed per §8.1/§8.2.

**Technical (repo-safe):** reuse HMAC/signing pattern (`csrf.py`/`secret_key`), `get_db` commit/rollback/`IntegrityError` handling, FastAPI+Jinja+CSRF, `tiempo.hoy/lunes_de`, Alembic forward-only, `grafico.py` reuse, PG-disposable validation for PG-specific behavior.

**Requires product-owner approval (or explicit deferral acceptance):** ACWR windows/coverage/thresholds/enablement; 1-10 wellness composite/index/cutoffs and `item_minimo`/alert semantics; `sin_registro_reciente` N; alert severities/copy (incl. `sin_registro_hoy`, molestia, síntomas, conflict copy nuances beyond clarity); `carga_alta_dia`/`sueno_insuficiente`/baseline rules. **RPE daily aggregation for display:** plan fixes *no unqualified daily average*; any labeled presentation beyond per-session detail is **UNRESOLVED (PO/UX)**.

**Open technical decisions (documented, no invented answer):** token replay hardening beyond expiry+fingerprint+lock (nonce/single-use store would add complexity — impact: moderate; investigate if threat model requires). Exact 409 response payload shape (service result object vs HTTP body fields) — resolve in Phase 2/3 implementation design consistent with FastAPI/Jinja patterns. Canonical serialization details (Decimal/date/array normalization) — must be deterministic; verify with unit tests. `cruce_con_marcas` day-selection rule when multiple sessions/days in week — **UNRESOLVED** (evidence impact on `bienestar.cruce_con_marcas`); choose explicit rule (e.g., daily record of mark date, or derived-week aggregate) and document before Phase 5.

## 14. Dependency Map (text)
`tiempo.hoy/lunes_de` + `settings.secret_key` → `services/parte_diaria*` (validate/normalize, fingerprints, sign/verify edit+discard tokens, load contracts, reported-day aggregation) → `routers/parte` (auth/CSRF/ownership/server date, `FOR UPDATE` lock → reload → verify tokens → mutate/409, `IntegrityError`→rollback→409) → `app/templates/atleta/parte.html` (discard confirm + 409 recovery UI). `ParteDiaria`+`SesionEntrenamiento` → daily series → `services/grafico.py` (reuse) → `panel/atletas/estadisticas/cuenta` + templates (`inicio,mis_datos,panel,atletas,atleta_ficha,estadisticas`). `ParteSemanal` remains non-active until Phase 7 gated drop (excluded from auto-deploy). `alembic c4b8e2d91f07` (done) → app replacement → controlled drop revision last.

## 15. Migration & Deployment Safety Conditions (hard)
Never modify historical revisions (`d61e48816ec5`,`a3f1c9e27b04`,`c4b8e2d91f07`). Expand/drop separate; **drop never auto-executed** despite `upgrade head` — controlled targeting. Phase 7 only after grep gate zero, Phase 6 green, PG-disposable validation (incl. drop dry-run), impact assessment, verified backup+recovery, explicit authorization, maintenance window. Preserve unrelated modules/data. No prod execution in this task.

## 16. Readiness (scoped)
**Ready for explicit authorization:** **Phase 2 implementation** (core domain services, Policy A, PG-disposable concurrency tests) — *after user review of this updated plan*. Phase 3/4/5/6 follow in order with dependencies/gates. **Not ready/granted:** any implementation in this task; Phase 7 removal (separately authorized/controlled).

**Deferred:** ACWR rules, ambiguous/PO thresholds, unapproved composites/copy, destructive legacy removal.

## 17. Risks Remaining
- PG-vs-SQLite (locks, races, ARRAY) — PG-disposable authoritative tests mandatory.
- Fingerprint canonicalization bugs → false 409s or missed staleness — deterministic serialization + unit tests required.
- 409 UX/recovery confusion — clear copy + reload flow + preserved user input (no silent actions).
- Deploy misconfig runs drop — controlled ops + Phase 7 gates.
- Alert/visual semantics regressions (missing≠0, RPE not averaged misleadingly, no weekly source) — Phase 5/6 targeted tests.
- Cross-phase coupling (router expects service token/result shapes) — stabilize service API in Phase 2.
- Unresolved: replay hardening strength, `cruce_con_marcas` daily mapping, RPE display beyond per-session.

## 18. Applicable Verification Results
| Check | Result |
|---|---|
| Repo/branch/HEAD/clean tree (initial) | VERIFIED — `Baruc+Kilo` @ `b75b2a2`, up to date, clean |
| `ses_e8fd` reused | VERIFIED |
| S-0021 PG validation evidence read/acknowledged | VERIFIED (report); NOT RE-RUN |
| Phase 1 schema/migration files inspected; historical migrations present | VERIFIED |
| Weekly consumers inventoried from repo evidence (`app/routers,services,templates`, tests, scripts); `app/schemas`/`app/static` weekly refs absent | VERIFIED |
| `grafico.py` generic; callers weekly-shaped | VERIFIED |
| Only authorized plan file updated | VERIFIED (this task) |
| App code/tests/migrations/templates/DB modified; migrations/tests executed | **NO / NOT RUN** |

## 19. Recommendation
**Plan is implementation-ready for user review.** Recommended next task: **explicitly authorized Phase 2 implementation** (Policy A core domain services + signed tokens/fingerprints + PG-disposable concurrency tests), following this plan. Do **not** execute Phase 7 removal or auto-deploy drop; do **not** implement ACWR/ambiguous thresholds without PO approval. Stop after this documentation update.
