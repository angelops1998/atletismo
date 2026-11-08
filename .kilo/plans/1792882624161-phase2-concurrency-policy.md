# Phase 2 Concurrency Policy Resolution — Daily Tracking (`ses_e8fd`)

**Status:** PROPOSED decision report for explicit review/approval **before Phase 2 Code mode**. Read-only investigation/planning only; no code/docs/migrations executed or modified (except this plan file). Preserves approved architecture (PG `SELECT FOR UPDATE` for session mutations, signed discard-confirmation protocol, `uq_parte_diaria_atleta_fecha`, request-scoped SA sessions, atomicity, stable session IDs, explicit session ops, missing≠0, CSRF/auth ownership) unless noted.

## 1. Evidence (approved plan & current implementation)
| Source | VERIFIED evidence |
|---|---|
| `.kilo/plans/1792882624161-daily-tracking-replacement.md` §5.1/§5.4/§5.5/§5.6/§10/§11/§12 Phase 3 | Today upsert intent; single-transaction mutations; `get_db`/commit/rollback; **PG-authoritative parent-row lock** `SELECT ... FOR UPDATE` on `ParteDiaria (atleta_id,hoy)` for session-mutating/discard ops; lock→validate→mutate→commit; §5.5: on `IntegrityError` do `rollback`→reload (lock if mutating)→**reapply already-validated form data**→commit. Discard protocol (§5.3) is signed, fingerprint-bound, verified after lock, stale⇒422/no delete. No `for_update`/`begin_nested` in `app/` today. |
| `.kilo/plans/...` §4.1/§4.2, `app/models/parte_diaria.py`, `sesion_entrenamiento.py` | `ParteDiaria` unique `(atleta_id,fecha)`; `entreno_hoy` required; wellness fields; `sesiones` 1:N `delete-orphan`, `passive_deletes`, `order_by=(orden,id)`. `SesionEntrenamiento` stable `id`, FK CASCADE, `carga_sesion` stored (backend recompute authoritative later). |
| `app/database.py` | `SessionLocal(autocommit=False, autoflush=False)` + `get_db()` yield/finally close; PG `pool_pre_ping/recycle`; session TZ set on connect. |
| `app/csrf.py` | HMAC-SHA256 signing via `settings.secret_key`, `hmac.compare_digest`; cookie+form token; CSRF required for mutations. Reusable signing pattern for server-signed state tokens. |
| `app/routers/atletas.py:270-276`, `pagos.py:110-117` | `IntegrityError` → `db.rollback()` + user response (422/redirect). |
| `app/routers/parte.py` (current weekly) | Upsert-by-key load/edit; 422 preserves form; CSRF enforced by app patterns. (To be replaced in Phase 3/4; conventions informative.) |
| `.kilo/kiloSesions/S-0021_code_session-postgres-migration-validation.md` | **Phase 1 PG migration validation accepted** (VERIFIED): `c4b8e2d91f07` applied on disposable PG 16.15 up from `a3f1c9e27b04`; `uq_parte_diaria_atleta_fecha`, FKs/CASCADE, checks/indexes, `molestia_zona` PG `ARRAY(VARCHAR)`, TZ timestamps/defaults verified; duplicate `(atleta_id,fecha)` and invalid `sueno_calidad` rejected by PG; ORM insert/read/update/delete/cascade verified. No `alembic upgrade head`; `partes_semanales` intact. |
| Readiness context | `.kilo/kiloSesions/S-0021_plan_session-ses_e8fd.md` and a saved “latest Phase 2 readiness report” file: **not found** in repo (VERIFIED by listing/search). This report addresses the two issues stated by the user. `S-0021_code_session-postgres-migration-validation.md` does not describe stale-update/create-race policy gaps (VERIFIED). |

## 2. Issue 1 — Stale daily-record updates (not prevented by parent-row locking alone)

**VERIFIED problem:** PG `SELECT ... FOR UPDATE` serializes writers on the *same existing row*, but cross-request staleness remains: client A loads state `S1`, client B commits `S2`, client A submits based on `S1` → after lock A sees `S2` and can overwrite with `S1`-derived data, silently losing `S2`. Parent-row locking alone is necessary for atomicity/session safety but **insufficient** for lost-update detection.

| Approach | Fit | Pros | Cons/limits |
|---|---|---|---|
| **Parent-row locking alone** | Insufficient for this issue | Simple; serializes same-row writers | **Loses updates across requests** (stale form overwrites newer commit). |
| **Optimistic version checking** (integer `version`/compare-and-set) | Viable but adds schema | Clear monotonic check | **Schema change** (new column/migration), backfill/default semantics; not required by current model. **PROPOSED (rejected for minimality)**. |
| **Signed snapshot/fingerprint of initial persisted state** (edit token) — **RECOMMENDED** | Best fit | **No schema change**; tamper-resistant (HMAC, aligns with `csrf.py`/discard); reuses discard fingerprint concept; detects staleness before applying; works for wellness-only and session mutations; compatible with lock-then-verify | Requires canonical fingerprint definition; token carried in form/hidden field (signed, not a free boolean); expiry/rotation; must cover all mutated persisted state. |
| **`actualizado` timestamp compare** | Partial | No schema change | ORM `onupdate`/DB precision/timezone/`now()` semantics can be brittle; `server_default now()`/`onupdate` not guaranteed to change in every desired case depending on dialect; easier to misuse than signed canonical state. **UNVERIFIED** reliability across PG/SA 2 edge cases in this codebase. **PROPOSED (fallback only, not preferred)**. |

**Recommendation (Issue 1, PROPOSED — amend plan):** adopt a **signed edit-state token** (server-issued, HMAC, `compare_digest`, short expiry) carrying `purpose=edit_parte_diaria`, `atleta_id`, `fecha` (`hoy()` ISO), `registro_id` (nullable for create intent only if ever used; see Issue 2), and **`record_state_fingerprint` = canonical hash/HMAC of the persisted state the client is editing**. 
- **Fingerprint scope (canonical, stable order):** wellness/health fields persisted on `ParteDiaria` that the mutation can affect (`sueno_calidad, horas_sueno, fatiga, dolor_muscular, estres, animo, hay_molestia, molestia_zona` normalized/sorted, `molestia_zona_otra, molestia_dolor, afecta_entrenamiento, sintomas_enfermedad, detalle_sintomas, comentarios, entreno_hoy`) **+** normalized session set in `order_by (orden,id)` including `id,orden,tipo_entrenamiento,duracion_min,rpe,carga_sesion,comentarios_entrenamiento` (same rigor as §5.3). Exclude volatile server timestamps unless explicitly needed; **UNVERIFIED** whether `actualizado` alone is sufficient — fingerprint avoids that risk.
- **Issuance:** GET `/parte` (today) returns token for current state (or `null`/create marker when no record exists — create handled by Issue 2). 422 re-render returns **fresh token for current persisted state** plus preserved user input (current state wins for conflict detection).
- **Verification (transaction):** for any mutation of an **existing** record, `BEGIN` → lock `ParteDiaria FOR UPDATE` for `(user.id,hoy())` → reload current record+sessions → recompute `current_fingerprint` → verify token signature/expiry/purpose/ids **and** `token.record_state_fingerprint == current_fingerprint` (and `registro_id` matches when present) → **if mismatch: 409 Conflict (controlled)**, **no writes**, rollback, re-render/load with fresh token and current state + user’s submitted values shown as “your changes (not applied)” if UX feasible, or clear conflict message. → if match: apply validated changes atomically (incl. explicit session ops / discard sub-protocol where applicable), commit.
- **Discard interaction (preserved):** true→false discard remains the **only** path to remove sessions silently? No — never silent; discard still requires explicit confirm + `discard_token` bound to `session_state_fingerprint`. The edit-state token guards against stale *record* submissions; discard token guards the destructive transition. **PROPOSED rule:** a confirmed discard POST must satisfy **both** (a) valid edit-state token for the current record state at submission context as applicable **or** be evaluated under the same locked-current-state check, and (b) valid discard token/fingerprint per §5.3. Implementation may unify checks but **must not weaken** either guarantee. (Detail PROPOSED; preserve §5.3.)
- **Limitations:** fingerprint canonicalization must be deterministic (normalize arrays/order/None/whitespace as stored); does not coordinate multi-field merges (conflict returned instead — safe). Expiry requires re-submit flow. PG authoritative for lock; SQLite cannot prove race behavior (existing caveat).

## 3. Issue 2 — Concurrent daily-record creation (approved §5.5 can overwrite)

**VERIFIED risk in current plan:** §5.5 step 4 “Reapply **already-validated** form data…” after `IntegrityError`+rollback+reload means the losing create-race request can overwrite the winner’s committed record. That violates “never silently overwrite concurrently submitted information” (and conflicts with new Issue 1 staleness principle).

| Option | Preserves unique/no-dup? | Silent overwrite? | Notes |
|---|---|---|---|
| **(1) Keep approved retry/reapply with safeguards** | Yes | **Risk remains** unless safeguards become “conflict on existing” | Hard to define safe merge for full upsert payload; minimal change but semantically unsafe. **Not recommended**. |
| **(2) Conflict when another transaction creates first** — **RECOMMENDED** | Yes | **No** | On unique violation, rollback+reload; if record now exists, **409 Conflict**, return current state + fresh edit-state token; **do not reapply**. Client reloads/resubmits as explicit update against current state (Issue 1 applies). Fits “athlete updates today”. No schema/infra change. |
| **(3) Other minimal (e.g. `INSERT ... ON CONFLICT DO NOTHING` + conflict)** | Yes | No | DB-specific path; SA 2/PG supports `insert().on_conflict_do_nothing()`; still must detect “not inserted” and return conflict (and avoid blind update). Equivalent safety to (2); implementation detail. **PROPOSED acceptable** if consistent with repo/SA style. |

**Recommendation (Issue 2, PROPOSED — amend §5.5):** **replace blind reapply with conflict-on-race-create**.
1. Resolve `hoy()`/ownership/validate/CSRF as today. Determine intent from **server-verified state**: `SELECT ... FOR UPDATE` for `(user.id,hoy())` **if row exists** (load+edit path). If **no row exists**, attempt create path (insert) in transaction.
2. **If insert raises `IntegrityError` (likely `uq_parte_diaria_atleta_fecha`):** `db.rollback()` (required). Reload `(user.id,hoy())` **FOR UPDATE**. **Do NOT reapply submitted payload.** Return **409 Conflict** (controlled): “today’s record was created/updated in another request; review current data and resubmit.” Include fresh **edit-state token** for the *current* persisted state and render current values. (No duplicates, no partial sessions — nothing committed from failed tx.)
3. **Only reapply/merge automatically in a narrow, safe case (PROPOSED, optional/minimal):** if request carried a **valid edit-state token proving it edited the *current* reloaded state** (token matches current fingerprint/registro_id) — treat as legitimate update and apply atomically under lock. In a pure create race the client lacked such a token for the new row, so conflict remains the default. **UNVERIFIED** whether UI will carry edit tokens on first-create; default to conflict is safe.
4. Keep unique constraint as authoritative guard; never catch-and-ignore IntegrityError as success.

**Explicit plan amendment required:** Yes — **§5.5 must be rewritten** to remove “Reapply already-validated form data…” on create-race and replace with **conflict + reload + fresh token (no silent overwrite)**, coordinated with Issue 1 edit-state tokens.

## 4. Recommended policies (summary)
| Issue | Policy (PROPOSED, preserves approved architecture) | Conflict handling |
|---|---|---|
| Stale daily-record update (existing row) | Signed **edit-state token** bound to canonical `record_state_fingerprint` of persisted record+sessions; lock `FOR UPDATE` → reload → recompute → verify token==current before mutation. No schema change. Discard protocol preserved/compatible. | **409 Conflict** (or 422 with explicit conflict semantics; pick one consistently) — **no overwrite**, fresh token + current state. |
| Concurrent daily-record creation | Unique constraint + `IntegrityError`→rollback→reload; **no blind reapply**. Conflict when row appears; only apply if request proves valid edit of *current* state via matching edit-state token. | **409 Conflict** — **no overwrite/dup/partial**. |

## 5. Exact transaction & conflict-handling behavior (PROPOSED)
- **Scope:** request-scoped `Session` (`get_db`). All mutations in **one** DB transaction; `IntegrityError` ⇒ `rollback()` before reuse.
- **Existing record (edit/session/discard):** `lock = SELECT ParteDiaria FOR UPDATE WHERE atleta_id=:a AND fecha=:hoy` → `record = reload` → `verify_edit_token(record,current_fp)`; if discard also `verify_discard_token(session_fp)` per §5.3 → validate ownership/stable session IDs/whitelists/load recompute → apply explicit ops → `commit`. Failures: validation 422; staleness/tamper **409**; ownership/cross-record 403/404/422 as applicable.
- **No existing row (create attempt):** `INSERT` ParteDiaria (+ validated sessions under `entreno_hoy` rules) → `commit`. On `IntegrityError`: `rollback` → reload+lock → **409 conflict**, no reapply.
- **PG authoritative** for `FOR UPDATE`/constraint races; SQLite tests not proof (per plan §5.4/§11). **UNVERIFIED:** exact HTTP status (409 vs 422) vs existing frontend conventions — **recommend 409 Conflict** for concurrency/state staleness, 422 for validation; confirm during implementation.

## 6. Required changes to the approved implementation plan (`.kilo/plans/1792882624161-daily-tracking-replacement.md`)
**Amendment required (PROPOSED; explicit approval needed before Phase 2 Code):**
1. **§5.3 (discard):** add note that discard confirm is evaluated against **locked current state** and remains compatible with record-level staleness protection; **preserve** signed discard token/fingerprint/explicit confirm/no-JS-only — no weakening.
2. **New §5.5a (or extend §5.1/§5.4) — stale-update prevention:** introduce **signed edit-state token** (HMAC, CSRF-aligned) bound to `record_state_fingerprint` of persisted `ParteDiaria`+sessions; issued on GET/422; **verified after `FOR UPDATE` lock + reload** for mutations to existing records; mismatch ⇒ **409, no overwrite**. No schema change.
3. **§5.5 (rewrite):** concurrent create: `IntegrityError`→`rollback`→reload+lock→**409 conflict with fresh token/current state; NEVER blind reapply** (optional narrow reapply only when valid edit token proves update of *current* state). Remove current step 4 reapply text.
4. **§10/§12 Phase 3 acceptance:** add “stale existing-record submit ⇒ conflict, no lost update; create race ⇒ conflict, no overwrite/dup”.
5. **§11 testing:** add PG concurrency cases (below). Keep SQLite caveat.
6. **§13/§16:** mark these as resolved technical policies **pending your explicit approval** (product/security-significant behavior: user sees conflict instead of silent merge).

**No change required (preserve):** `SELECT FOR UPDATE` protocol, discard fingerprint/token, request-scoped sessions, atomicity, stable session IDs, explicit session ops, missing≠0, CSRF/ownership, unique constraint, Phase 1 schema accepted.

## 7. Additional PostgreSQL concurrency tests (authoritative, disposable PG)
1. **Stale wellness update:** T1 loads record `S1` (token fp1), T2 commits `S2`, T1 submits with fp1 → **409/conflict, DB remains `S2`**.
2. **Stale session mutation:** T1 edits/deletes based on old session fingerprint/token, T2 mutates sessions, T1 submits → **409, no partial/missing mutation applied**.
3. **Concurrent create race:** two tx insert `(atleta,hoy)`; one commits, other gets `IntegrityError` → handler returns **conflict, final state is winner only, no overwrite, no dup** (`count==1`).
4. **Discard under concurrent change (existing §11 intent, make explicit):** valid discard token vs mutated sessions/record after issue → **422/409 stale, no delete**.
5. **Valid sequential update:** submit with current token after lock/fp match → commits; next stale token rejected.
6. **IntegrityError recovery safety:** after induced unique violation, session usable only after `rollback`; reload shows consistent state. (Partly covered; assert no partial sessions.)
7. **Lock serialization sanity (PG):** concurrent session-mutating ops on same `(atleta,hoy)` serialize; no cross-athlete blocking (separate rows). **UNVERIFIED** timing in CI; use deterministic barriers or focused integration harness.

## 8. Updated Phase 2 acceptance criteria (PROPOSED additions to Phase 2/3/6)
- Core domain/services/router logic (as scoped) **never silently overwrites** a newer `ParteDiaria` or concurrently created record.
- Existing-record mutation requires valid **edit-state token/fingerprint** verified **after `SELECT ... FOR UPDATE` + reload**; stale/tampered ⇒ controlled conflict, no writes.
- Concurrent create `IntegrityError` ⇒ `rollback` + reload + **conflict (no reapply/no dup/no partial)**.
- Signed discard protocol (§5.3) preserved and compatible; explicit session ops/stable IDs unchanged.
- Request-scoped SA session/CSRF/ownership/server `hoy()`/load recompute authoritative.
- **PG-disposable tests PASS** for cases in §7; SQLite not accepted as lock/race proof. ACWR/ambiguous thresholds still deferred.

## 9. Open decision for explicit approval
Both issues are resolvable from existing safety requirements (no silent overwrite, no dup, atomicity, existing signed-token/lock patterns) with **minimal amendments** above. I recommend: **signed edit-state fingerprint token (no schema change) + conflict-on-stale-update (409) + amend §5.5 to conflict-on-create-race (no blind reapply)**, preserving discard/lock/CSRF/atomicity/stable IDs/missing≠0.

**One targeted question (recommended answer first):** Do you approve these two policy amendments for Phase 2 — **(A, recommended)** stale updates and create-races return a **409 conflict with fresh current state/token (no silent overwrite, no blind reapply)** using a **signed edit-state fingerprint token (no DB schema change)**, preserving the existing discard token protocol; or **(B)** require a different conflict status/UX or a schema `version` column approach?

**Final restriction honored:** no implementation performed; awaiting explicit approval before Phase 2 Code mode.
