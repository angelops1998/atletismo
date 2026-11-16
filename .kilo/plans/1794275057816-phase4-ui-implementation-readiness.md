# Phase 4 — Athlete-Facing Daily `/parte` Form Implementation Plan

**Status:** planning only — read-only investigation, no implementation  
**Session:** NEW (Plan mode)  
**Branch/HEAD:** `Baruc+Kilo` @ `ad45e94` (clean working tree)  
**Authoritative specs:** Phase 1–3 plans + S-0038/S-0039 evidence; Phase 3 router is **accepted** (local/SQLite evidence)

---

## 1. Repository State and Inspected Files

| File | Role | Status |
|------|------|--------|
| `app/routers/parte.py` | Phase 3 thin controller (GET/POST `/parte`) | **VERIFIED** — daily today-only, Policy A, signed discard, repeated-field restoration fixed (S-0038) |
| `app/services/parte_diaria.py` | Domain service (validation, locking, tokens, transactions) | **VERIFIED** — Policy A, `FOR UPDATE`, canonical fingerprints, edit-state/discard tokens |
| `app/services/parte_diaria_tokens.py` | HMAC-SHA256 tokens (edit-state + discard) | **VERIFIED** — deterministic canonical JSON, `compare_digest`, short expiry |
| `app/models/parte_diaria.py` | `ParteDiaria` + `MOLESTIA_ZONAS` whitelist | **VERIFIED** — 1–10 wellness, `ARRAY(String)` zones, conditional fields |
| `app/models/sesion_entrenamiento.py` | `SesionEntrenamiento` + `TIPOS_ENTRENAMIENTO` | **VERIFIED** — stable `id`, `orden`, `duracion_min`, `rpe`, `carga_sesion` |
| `app/templates/atleta/parte.html` | Current athlete form (weekly→daily transition) | **VERIFIED** — uses `_campos.html` macros, conditional `.condicional.abierto`, `sessions` textarea, `delete_session_ids` input |
| `app/templates/_campos.html` | Form macros (`escala_num`, `binario`, `escala_rpe`) | **VERIFIED** — radio-based 1–10 scales, binary yes/no with `data-abre` |
| `app/static/css/main.css` | Mobile-first styles (cards, scales, conditionals) | **VERIFIED** — `.escala-10`, `.binario`, `.condicional`, `.aviso`, touch targets ≥44px |
| `app/static/js/main.js` | Minimal progressive JS (conditionals, confirm) | **VERIFIED** — `[data-abre]` toggles `.abierto`, no framework |
| `tests/test_parte.py` | Route tests (auth, CRUD, validation, sessions, discard, 409, parsing) | **VERIFIED** — 48 tests pass; repeated-field restoration covered (S-0038) |
| `tests/conftest.py` | Fixtures (`client`, `db`, `crear_usuario`, `entrar`, `con_csrf`) | **VERIFIED** — SQLite `StaticPool`, cookie auth, CSRF extraction |

**Git state:** clean; only `.kilo/plans/` and `.kilo/kiloSesions/` modified by planning/debug sessions.

---

## 2. Current UI Findings (VERIFIED)

### 2.1 GET `/parte` — Form Initialization
- Router calls `pd.get_today_state(db, user.id, hoy())` → returns `(parte, edit_token, discard_token)` or `(None, None, None)`.
- `_render_form` builds context:
  - `parte`: authoritative persisted `ParteDiaria` (or `None`)
  - `form`: `None` on initial GET
  - `errors`: `[]`
  - `edit_state_token` / `discard_token`: fresh tokens for current state
  - `sessions_form`: serialized existing sessions (`id|orden|tipo|min|rpe|comentarios` joined by `\n`)
  - `delete_form`: comma-joined session IDs for explicit deletion input
  - `items`, `etiquetas`, `rpe_escala`, `rpe_franjas`: from `bienestar` service (weekly 1–5 items — **mismatch**: daily uses 1–10)

### 2.2 POST `/parte` — Submission Behavior
- Parses `await request.form()` via `_session_payload()`:
  - Wellness fields → direct pass-through to service payload
  - `sessions`: accepts **both** repeated `sessions` fields **and** newline-separated textarea; splits by `\n`, parses each line with `_parse_session_item` (strict: malformed lines → parse errors, no partial service call)
  - `delete_session_ids`: repeated fields or comma-separated; parses positive ints, rejects duplicates/malformed
  - `allow_full_session_replacement`: `"1"` enables full-replacement mode (default: explicit deletes only)
- Parse errors → HTTP 422 with `form=form`, `errors=parse_errors`, fresh tokens from `get_today_state`
- Service call `pd.save_daily_record(...)` with payload, tokens, `confirm_discard_sessions`, `explicit_delete_session_ids`, `allow_full_session_replacement`
- Service result mapping:
  - `ok` → 302 redirect to `/parte?ok=1`
  - `STATUS_VALIDATION` (422) → re-render with `result.parte`, `result.errors`, fresh tokens, **submitted `form` preserved**
  - `STATUS_CONFLICT` (409) → re-render with `conflict=True`, `stale=True`, `result.parte` (authoritative), **submitted `form` preserved**, fresh tokens
  - `STATUS_NOT_FOUND` (404) / 500 → controlled error responses

### 2.3 Persisted Daily-Record Loading
- `load_today` / `load_today_for_update` (with `FOR UPDATE` on PG) + `selectinload(sesiones)`
- `get_today_state` issues fresh `edit_state_token` (record fingerprint) and `discard_token` (session fingerprint)

### 2.4 Edit-State Handling (Policy A)
- Existing record: router passes `edit_state_token` from hidden input
- Service verifies **after lock + reload**: `verify_edit_state_token(token, atleta_id, fecha, registro_id, current_fingerprint)`
- Mismatch → 409 with fresh tokens + current authoritative `parte` + **submitted values preserved**

### 2.5 Signed Discard-Confirmation Protocol
- **Step 1 (intent):** `entreno_hoy=true→false` with existing sessions + no `confirm_discard_sessions`/`discard_token` → 422, fresh `discard_token` bound to **current session fingerprint**, message "Confirmá explícitamente el descarte...", sessions preserved
- **Step 2 (confirm):** resubmit with `confirm_discard_sessions="si"` + valid `discard_token` + `edit_state_token` → service verifies both tokens under lock; success deletes sessions, sets `entreno_hoy=false`, commits
- Stale/expired/invalid `discard_token` → 409, no deletion
- Template renders `discard_token` hidden input when present; `confirm_discard_sessions` via `binario` macro

### 2.6 Session Identity and Explicit Deletion
- Sessions have stable integer `id` (PK)
- Submitted sessions include `id` for updates; new sessions omit `id`
- Explicit deletion via `delete_session_ids` (comma-separated or repeated fields)
- **Default: no implicit delete by omission** — omitted session IDs are preserved unless `allow_full_session_replacement=1`
- Service validates ownership: every referenced `session_id` must belong to locked `ParteDiaria`

### 2.7 Validation and Conflict Responses
- Service `validate_and_normalize_wellness` → `DomainValidationError` → 422 with field-level messages
- Service `validate_and_normalize_sessions` → same
- 409 responses include: `conflict=True`, `stale=True`, authoritative `parte`, fresh tokens, **submitted `form` preserved separately**

### 2.8 Template Context Variables (Actual)
| Variable | Source | Notes |
|----------|--------|-------|
| `user` | router | current athlete |
| `fecha` | `hoy()` | server date |
| `parte` | `get_today_state` / `ServiceResult.parte` | ORM `ParteDiaria` or `None` |
| `form` | `request.form()` | only on 422/409/errors |
| `errores` | parse errors / `ServiceResult.errors` | list of strings |
| `message` | `ServiceResult.message` | user-facing |
| `conflict` / `stale` | `ServiceResult.conflict/stale` | booleans |
| `created` | `ServiceResult.created` | boolean |
| `edit_state_token` / `discard_token` | fresh tokens | strings or `None` |
| `molestia_zonas` | `pd.MOLESTIA_ZONAS` | tuple of allowed zone strings |
| `tipos_entrenamiento` | `pd.TIPOS_SET` | set of allowed training types |
| `items` / `etiquetas` | `bienestar.ITEMS/ETIQUETAS` | **weekly 1–5 items — mismatch for daily 1–10** |
| `rpe_escala` / `rpe_franjas` | `bienestar.RPE_ESCALA/FRANJAS` | 1–10 RPE with descriptors/colors |
| `sessions_form` | `_serialize_sessions(parte.sesiones)` or joined submitted values | string for textarea |
| `delete_form` | `_serialize_delete_ids(parte.sesiones)` or joined submitted values | string for text input |

### 2.9 Existing JavaScript Initialization
- `main.js` lines 11–22: `[data-abre]` toggles `.condicional.abierto` on radio `change`
- No session-management JS; sessions edited via textarea + delete input
- No validation JS; relies on server 422/409 + HTML5 `required` on radio groups

---

## 3. Router/Template Context Contract (ACTUAL → REQUIRED)

### 3.1 Missing / Mismatched Context for Daily UI
| Context Key | Current | Required for Daily UI | Impact |
|-------------|---------|----------------------|--------|
| `items` / `etiquetas` | Weekly 1–5 (4 items) | **Daily 1–10 wellness items (A–E sections)** | Template renders wrong questions/scale labels |
| `rpe_escala` / `rpe_franjas` | Session RPE only | Session RPE (ok) + **daily wellness 1–10 guidance** | Wellness scales need own descriptors |
| Wellness field names | `sueno_calidad`, `fatiga`, `dolor_muscular`, `estres`, `animo` | Same — **VERIFIED matches model** | OK |
| `horas_sueno` | Decimal 0–24 | Same | OK |
| `molestia_zona` | Comma-separated string in template `value` | Model expects `ARRAY(String)`; service normalizes from comma-string | Template must join array for display; parser splits |
| `molestia_zona_otra` | Text input | Required iff `otro` in `molestia_zona` | Conditional visibility + required |
| `sintomas_enfermedad` / `detalle_sintomas` | Binary + optional textarea | Same | OK |
| `entreno_hoy` | Binary `si/no` | Same | OK |
| Session serialization | `id|orden|tipo|min|rpe|comentarios` | Same — **stable ID critical** | OK |

**Critical gap:** The template receives `items`/`etiquetas` from `bienestar` (weekly 1–5), but daily wellness is 1–10 with different questions. The router must supply daily-specific items/labels or the template must define them inline.

---

## 4. Field-to-Backend Mapping (VERIFIED from Code)

| UI Field | HTML Name | Backend Payload Key | Type / Accepted Values | Required | Conditional Visibility | Server Validation | Restoration Behavior |
|----------|-----------|---------------------|------------------------|----------|------------------------|-------------------|----------------------|
| Sleep quality | `sueno_calidad` | `sueno_calidad` | Int 1–10 | Yes | Always | `validate_and_normalize_wellness` → 1–10 | `dato('sueno_calidad')` → `form.get` → `parte.sueno_calidad` |
| Sleep hours | `horas_sueno` | `horas_sueno` | Decimal 0–24 (1 decimal) | Yes | Always | `_to_decimal` min 0 max 24, finite, quantized 0.1 | Same |
| Fatigue | `fatiga` | `fatiga` | Int 1–10 | Yes | Always | 1–10 | Same |
| Muscle pain | `dolor_muscular` | `dolor_muscular` | Int 1–10 | Yes | Always | 1–10 | Same |
| Stress | `estres` | `estres` | Int 1–10 | Yes | Always | 1–10 | Same |
| Mood | `animo` | `animo` | Int 1–10 | Yes | Always | 1–10 | Same |
| Discomfort present | `hay_molestia` | `hay_molestia` | Bool (`si`/`no`) | Yes | Always | `_to_bool` default false | `binario` macro checks `valor=='si'` |
| Discomfort zones | `molestia_zona` | `molestia_zona` | Comma-separated string → normalized to `ARRAY(String)` whitelist | **If `hay_molestia=si`** | Shown when `hay_molestia=si` | `normalize_molestia_zona` → whitelist `MOLESTIA_ZONAS`, at least one | `dato('molestia_zona')` joins array with `, ` |
| Other zone | `molestia_zona_otra` | `molestia_zona_otra` | String ≤120 | **If `otro` in zones** | Shown when `otro` selected | Required non-empty trimmed if `otro`; else cleared | Same |
| Discomfort pain | `molestia_dolor` | `molestia_dolor` | Int 1–10 | **If `hay_molestia=si`** | Shown when `hay_molestia=si` | 1–10 required | Same |
| Affects training | `afecta_entrenamiento` | `afecta_entrenamiento` | Int 0–3 | **If `hay_molestia=si`** | Shown when `hay_molestia=si` | 0–3 required | Same |
| Illness symptoms | `sintomas_enfermedad` | `sintomas_enfermedad` | Bool (`si`/`no`) | Yes | Always | `_to_bool` default false | `binario` macro |
| Symptom details | `detalle_sintomas` | `detalle_sintomas` | Text (optional) | No | Shown when `sintomas_enfermedad=si` | Optional trimmed; cleared if `false` | Same |
| Comments | `comentarios` | `comentarios` | Text | No | Always | `_to_text` | Same |
| Trained today | `entreno_hoy` | `entreno_hoy` | Bool (`si`/`no`) | Yes | Always | `_to_bool` default false | `binario` macro |
| Sessions | `sessions` (textarea or repeated) | `sessions` list[dict] | Pipe lines: `id|orden|tipo|duracion_min|rpe|comentarios` | **If `entreno_hoy=si` ≥1** | Shown when `entreno_hoy=si` | `_parse_session_item` → `validate_and_normalize_sessions`; `entreno_hoy=true` requires ≥1 | `sessions_form` (joined `\n`) in textarea |
| Delete session IDs | `delete_session_ids` (text or repeated) | `explicit_delete_session_ids` set[int] | Comma-separated or repeated positive ints | No | Always (inside training block) | `_parse_positive_int` each; must belong to locked record | `delete_form` (joined `,`) in text input |

**Key invariants:**
- Omission ≠ deletion: sessions not in submitted `sessions` are preserved unless explicitly in `delete_session_ids` or `allow_full_session_replacement=1`
- `molestia_zona_otra` cleared server-side when `otro` not in zones
- `detalle_sintomas` cleared server-side when `sintomas_enfermedad=false`
- `entreno_hoy=false` forces `sessions=[]` in service (discard protocol handles existing sessions)

---

## 5. Proposed UI Structure (PROPOSED)

### 5.1 Section Organization (A–E)
| Section | Title | Fields | Visual Treatment |
|---------|-------|--------|------------------|
| **A** | Bienestar general (1–10) | `sueno_calidad`, `fatiga`, `dolor_muscular`, `estres`, `animo` | 5 × `.escala-10` radios with descriptors |
| **B** | Sueño | `horas_sueno` | Number input `step="0.5" min="0" max="24"` |
| **C** | Entrenamiento | `entreno_hoy` (binary) → conditional block: `sessions` textarea + `delete_session_ids` input + current sessions list | Binary toggle via `binario` + `.condicional.abierto`; sessions as editable textarea with helper text |
| **D** | Molestias | `hay_molestia` (binary) → conditional: `molestia_zona` (text + datalist?), `molestia_dolor` (1–10), `afecta_entrenamiento` (0–3), `molestia_zona_otra` (conditional on `otro`) | Binary toggle; zones as comma-separated text with placeholder listing whitelist; `otro` reveals extra field |
| **E** | Síntomas de enfermedad | `sintomas_enfermedad` (binary) → conditional: `detalle_sintomas` (textarea) | Binary toggle |
| **F** | Comentarios | `comentarios` (textarea) | Always visible |
| **G** | Descarte de sesiones | `confirm_discard_sessions` (binary) + `discard_token` hidden | Only relevant when `discard_token` present (existing sessions + `entreno_hoy=false` intent) |

### 5.2 Daily Wellness 1–10 Guidance (PROPOSED)
Replace weekly `ITEMS`/`ETIQUETAS` with daily-specific descriptors in template context or inline:

| Field | 1–3 | 4–6 | 7–8 | 9–10 |
|-------|-----|-----|-----|------|
| `sueno_calidad` | Deficiente | Regular | Bueno | Muy bueno |
| `fatiga` / `dolor_muscular` / `estres` | Bajo | Moderado | Elevado | Extremo |
| `animo` | Muy desanimado | Desanimado | Regular | Bueno / Excelente |

**Implementation:** Add `bienestar_diario.py` service module or extend router context with daily items/labels. **Do not modify `bienestar.py`** (weekly consumer).

### 5.3 Conditional Discomfort Fields
- `hay_molestia` binary (`binario` macro with `data-abre="bloque-molestia"`)
- When open: `molestia_zona` text input with `placeholder` listing `MOLESTIA_ZONAS`; **add `<datalist>` for whitelist suggestions** (progressive enhancement)
- `molestia_dolor` → `escala_num` 1–10
- `afecta_entrenamiento` → `escala_num` 0–3
- `molestia_zona_otra` → text input, **conditionally visible** via second `data-abre` on a hidden checkbox or JS watch for `otro` in zones text (simpler: always visible but labeled "Solo si elegiste 'otro'"; server clears if not `otro`)
- **Preservation:** When `hay_molestia` toggles to `no`, hidden fields retain values in DOM; server normalizes to `None` — **do not clear via JS** (user may toggle back)

### 5.4 Conditional Illness Details
- `sintomas_enfermedad` binary with `data-abre="bloque-sintomas"`
- When open: `detalle_sintomas` textarea (optional)
- Server clears when `false`; DOM retains — same pattern

### 5.5 Training Status & Dynamic Sessions
- `entreno_hoy` binary with `data-abre="bloque-entrenamiento"`
- When open:
  - **Sessions textarea:** each line = `id|orden|tipo|min|rpe|comentarios`; empty `id` = new session; helper text explains format
  - **Delete IDs input:** comma-separated session IDs to remove explicitly
  - **Current sessions list:** read-only `<ul>` showing `Sesión {id}: {tipo} · {min} min · RPE {rpe}` for reference
- **Add session:** user types new line in textarea (no JS required)
- **Edit session:** user modifies line in textarea (keeps same `id`)
- **Remove session:** user adds ID to `delete_session_ids` input **and** removes line from textarea (or leaves it; explicit delete wins)
- **Stable IDs:** never use array indexes; always `id` from persisted sessions

### 5.6 Discard Confirmation UX
- When `discard_token` present (returned on 422 from `entreno_hoy=true→false` intent):
  - Show "Confirmar descarte de sesiones" binary (`confirm_discard_sessions`) with `discard_token` hidden
  - Message: "Tenés sesiones guardadas. Si confirmás que no entrenaste, se descartarán. Esta acción no se puede deshacer."
  - Cancel: user changes `entreno_hoy` back to `si` or navigates away — sessions preserved
- On 409 (stale discard token): show conflict message, fresh tokens, current sessions — user must reload and re-confirm

### 5.7 HTTP 409 Recovery UX
- Render both:
  1. **Authoritative persisted record** (`parte`) — read-only summary or prefilled "current state" section
  2. **Submitted values** (`form`) — in the actual form inputs (already done via `form` preservation)
- Message: "Tu información está desactualizada. El registro cambió mientras lo editabas. Los datos que cargaste no se guardaron."
- Actions:
  - **"Recargar datos actuales"** button → GET `/parte` (loads fresh `parte` + tokens)
  - **"Reintentar con mis cambios"** → user reviews diff, edits form, resubmits with fresh `edit_state_token`
- **Never** auto-replace or silently overwrite

### 5.8 HTTP 422 Validation UX
- Error summary at top (`.aviso-error` with `<ul>`)
- Inline error association: add `.error` class to `.campo` + `aria-describedby` linking to error message (progressive; server renders errors in summary only for MVP)
- Preserve all submitted values (already done via `form` in context)
- Repeated session lines preserved in textarea (S-0038 verified)
- Delete IDs preserved in input (S-0038 verified)

### 5.9 Responsive & Accessible Interface (FOLLOW EXISTING PATTERNS)
- Mobile-first: single-column cards, 44px touch targets (`.btn`, `.escala label`, `.binario label`)
- 16px font on inputs (prevents iOS zoom)
- Radio-based scales (work without JS, screen-reader accessible)
- `required` on first radio of each mandatory scale group
- Visible focus states (`border-color: var(--tartan)`, `box-shadow: 0 0 0 3px var(--tartan-tint)`)
- `aria-label` on `.rpe-franjas` list
- Conditional blocks hidden via `display:none` (`.condicional`); shown via `.abierto` class toggled by `main.js` `[data-abre]`
- No new dependencies; reuse `main.css`/`main.js` patterns

---

## 6. Interaction & State-Transition Model (PROPOSED)

```
┌─────────────────────────────────────────────────────────────────┐
│                      INITIAL FORM STATE                         │
│  GET /parte → load_today_state → parte? edit_token discard_token│
│  • No parte: blank form, no tokens                              │
│  • Existing parte: prefilled, fresh tokens                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ CREATE MODE │ │  EDIT MODE  │ │ CONDITIONAL │
    │ (no parte)  │ │ (has parte) │ │  SECTIONS   │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           ▼               ▼               ▼
    POST /parte      POST /parte      Toggle hay_molestia,
    → save_daily     → save_daily     sintomas_enfermedad,
    → 302 or 422     → 302/422/409    entreno_hoy
           │               │               │
           └───────────────┼───────────────┘
                           ▼
              ┌─────────────────────────┐
              │   SESSION COLLECTION    │
              │  (inside bloque-entreno)│
              │  • Add: new line in     │
              │    textarea (id empty)  │
              │  • Edit: modify line    │
              │    (keep id)            │
              │  • Remove: add id to    │
              │    delete_session_ids   │
              │    + remove line        │
              │  • Stable IDs always    │
              └───────────┬─────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       ┌─────────────┐         ┌─────────────┐
       │ EXPLICIT    │         │ DISCARD     │
       │ DELETION    │         │ CONFIRMATION│
       │ (delete_    │         │ (entreno_   │
       │ session_ids)│         │ hoy=false   │
       └──────┬──────┘         │  + sessions)│
              │                └──────┬──────┘
              │                       │
              ▼                       ▼
       Service applies          Step 1: 422 + discard_token
       deletes only             Step 2: confirm + token → OK
       listed IDs               Stale → 409
              │                       │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │ VALIDATION / CONFLICT │
              │ 422: errors + form    │
              │ 409: conflict + form  │
              │     + parte (current) │
              └───────────┬───────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       ┌─────────────┐         ┌─────────────┐
       │ 422 RECOVERY│         │ 409 RECOVERY│
       │ Fix errors  │         │ • Recargar  │
       │ Resubmit    │         │ • Reintentar│
       └─────────────┘         └─────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   SUCCESS (302)       │
              │   Redirect /parte?ok=1│
              └───────────────────────┘
```

**Source of Truth per State:**
- **Initial GET:** `parte` (persisted) + fresh tokens
- **422:** `form` (submitted) + `parte` (persisted, may be `None`) + fresh tokens
- **409:** `form` (submitted) + `parte` (current authoritative) + fresh tokens
- **Success:** Redirect — no form state needed

**Transitions preserve user input:** Router `_render_form` passes `form=request.form()` on 422/409; template `dato(campo)` macro reads `form.get(campo)` first, falls back to `parte|attr(campo)`.

---

## 7. Exact Files to Modify (PROPOSED)

### 7.1 Required Changes

| File | Current Responsibility | Proposed Changes | Reason | Dependencies |
|------|------------------------|------------------|--------|--------------|
| `app/routers/parte.py` | Thin controller | **Add daily wellness items/labels to context** (replace `bienestar.ITEMS/ETIQUETAS` with daily 1–10 descriptors). Keep all Policy A/token/session logic. | Template needs correct questions + scale labels for daily 1–10. | None (self-contained) |
| `app/templates/atleta/parte.html` | Athlete daily form | **Full redesign**: Sections A–G per §5.1; use `escala_num` for 1–10 wellness; conditional blocks with `data-abre`; sessions textarea + delete input + current sessions list; discard confirmation UX; 409 recovery messaging; 422 error summary. | Implement Phase 4 functional/UX requirements. | `app/routers/parte.py` context; `_campos.html` macros; `main.css`/`.main.js` patterns |
| `app/templates/_campos.html` | Form macros | **Add `escala_num` descriptor support** (optional `descriptores` param for wellness 1–10 labels) OR define wellness descriptors inline in `parte.html`. Keep `escala_rpe` for session RPE. | Wellness 1–10 needs different labels than RPE. | `parte.html` usage |
| `app/static/css/main.css` | Styles | **Verify/extend**: `.escala-10` works for wellness; ensure conditional blocks, error states, touch targets adequate. Likely **no changes needed** — existing patterns cover requirements. | Confirm existing styles sufficient. | `parte.html` classes |
| `app/static/js/main.js` | Progressive JS | **Verify**: `[data-abre]` handles all conditionals (molestia, síntomas, entrenamiento, descarte). **No new JS needed** for MVP. | Confirm existing conditional toggle works for new blocks. | `parte.html` `data-abre` attrs |

### 7.2 Optional Improvements (Post-MVP)
- `<datalist>` for `molestia_zona` whitelist suggestions (progressive enhancement)
- Inline per-field error display (beyond summary) — requires router to pass field→error map
- Session add/remove buttons (JS) as alternative to textarea editing — only if UX testing shows textarea is problematic
- `detalle_sintomas` character counter (maxlength=1000 already in template)

### 7.3 Out of Scope (Phase 4)
- Phase 2 service changes
- Phase 3 router logic changes (accepted)
- Weekly consumer migration (Phase 5)
- Visualization/charts (Phase 5)
- ACWR/alert thresholds (PO decision)
- Schema/migrations (Phase 1 complete, Phase 7 separate)
- New dependencies (CSS framework, JS framework, date picker, etc.)

---

## 8. Automated Test Plan (PROPOSED)

**Reuse existing infrastructure:** `conftest.py` fixtures (`client`, `db`, `atleta`, `entrar`, `con_csrf`, `completo`, `_session_str`, `_get_edit_token`), `test_parte.py` patterns.

| # | Test | Description | Fixtures/Helpers |
|---|------|-------------|------------------|
| 1 | Create daily record via rendered form | POST valid payload → 302, `ParteDiaria` persisted with all wellness 1–10, `horas_sueno`, sessions | `completo()`, `_session_str()` |
| 2 | Edit existing daily record | GET → extract `edit_state_token` → POST with changes → 302, persisted updated | `_get_edit_token()` |
| 3 | Multiple training sessions | Submit 3 sessions (mix new + existing IDs) → all persisted with stable IDs, correct `carga_sesion` | `_session_str([...])` |
| 4 | Stable session IDs across render/submit | Create → GET → verify `sessions_form` contains IDs → POST edit → IDs unchanged | `_get_edit_token()`, `sessions_form` parsing |
| 5 | Explicit session deletion | Create 2 sessions → POST with `delete_session_ids` for one + keep other in `sessions` → only kept session persists | `_session_str()`, `delete_session_ids` |
| 6 | Omission without accidental deletion | Create 2 sessions → POST with only 1 in `sessions` (no `delete_session_ids`, no `allow_full_session_replacement`) → both persist | `_session_str()`, default mode |
| 7 | Conditional discomfort fields | `hay_molestia=si` + zones + `molestia_dolor` + `afecta_entrenamiento` → persisted; `hay_molestia=no` → zones/dolor/afecta cleared | `completo(hay_molestia="si", ...)` |
| 8 | `molestia_zona_otra` behavior | `molestia_zona="otro"` + `molestia_zona_otra="espalda baja"` → persisted; without `otro` → `otra` cleared | `completo(molestia_zona="otro", molestia_zona_otra="...")` |
| 9 | Conditional illness details | `sintomas_enfermedad=si` + `detalle_sintomas` → persisted; `false` → `detalle` cleared | `completo(sintomas_enfermedad="si", detalle_sintomas="...")` |
| 10 | Client/server validation consistency | Submit invalid wellness (0, 11, non-int) → 422, errors match service messages; submit invalid session (bad tipo, rpe 0) → 422 | Parametrized invalid values |
| 11 | Signed discard confirmation | `entreno_hoy=true→false` with sessions → 422 + `discard_token`; resubmit with `confirm_discard_sessions=si` + token → 302, sessions gone | `_get_edit_token()`, regex extract `discard_token` |
| 12 | Invalid/stale discard confirmation | Same as 11 but mutate sessions before confirm → 409, sessions preserved | Direct DB mutation between steps |
| 13 | HTTP 422 value repopulation | Submit invalid `animo="abc"` → 422, all other submitted values rendered in form (wellness, sessions, delete IDs) | `completo(animo="abc")`, assert rendered values |
| 14 | HTTP 422 error association | 422 response contains error summary + submitted values preserved (no DB write) | Assert `errores` in response, `db.query(ParteDiaria).count()==0` |
| 15 | HTTP 409 preservation of submitted values | Stale `edit_state_token` → 409, submitted `animo="9"` in form, authoritative `parte.animo=5` in DB | Mutate `parte.animo=5` in DB, POST with stale token |
| 16 | Distinction between submitted and persisted values on 409 | 409 response renders both: form shows submitted, separate "current record" shows authoritative | Check both value sets in response HTML |
| 17 | CSRF protection | POST without `csrf_token` → 403 | `del datos["csrf_token"]` |
| 18 | Existing route/template regression | All current `test_parte.py` tests pass (48 tests) | Run full `test_parte.py` |

**New test helpers needed (additive to `conftest.py` or `test_parte.py`):**
- `completo_diario()` — daily wellness payload with 1–10 fields (replace weekly `completo`)
- Daily-specific `_session_str()` already works (same format)
- `_get_edit_token()` already works

**Do not assume fixtures exist without locating them** — all above exist in `conftest.py` / `test_parte.py`.

---

## 9. Manual Browser Test Plan (PROPOSED)

| # | Check | Viewport | Steps | Expected |
|---|-------|----------|-------|----------|
| 1 | Mobile layout | 375px (iPhone SE) | Load `/parte` as athlete | Single-column cards, no horizontal scroll, touch targets ≥44px |
| 2 | Desktop layout | 1024px+ | Load `/parte` as athlete | Two-column rail + content, scales expand to 10 columns |
| 3 | Keyboard-only navigation | Desktop | Tab through entire form | All inputs reachable, visible focus rings, radio groups operable with arrows |
| 4 | Conditional discomfort visibility | Mobile | Toggle "¿Tenés molestia?" Sí/No | `bloque-molestia` shows/hides instantly (JS), values retained in DOM |
| 5 | `molestia_zona_otra` conditional | Mobile | Type "otro" in zones → `molestia_zona_otra` visible (or always visible with label) | Server requires `otra` iff `otro` in zones |
| 6 | Conditional illness visibility | Mobile | Toggle "¿Te sentiste enfermo?" Sí/No | `bloque-sintomas` shows/hides |
| 7 | Dynamic session add/edit/remove | Mobile | Add line to textarea → submit → session persists; edit line → updates; add ID to delete input + remove line → session deleted | Stable IDs, correct `carga_sesion` |
| 8 | Validation feedback | Mobile | Submit empty required field → 422 | Error summary at top, submitted values preserved, focus on first error |
| 9 | Discard confirmation flow | Mobile | Create with sessions → set `entreno_hoy=no` → submit → 422 with confirm prompt → confirm → 302, sessions gone | Two-step, token-bound, cancel preserves |
| 10 | Conflict recovery | Mobile | Open two tabs, edit in both → submit first → second gets 409 | Shows "desactualizada", submitted values + current record, reload/retry actions |
| 11 | Responsive session controls | Mobile/desktop | Textarea + delete input usable at both widths | No overflow, readable monospace in textarea |
| 12 | Accessibility | Both | Screen reader (NVDA/VoiceOver) | Labels announced, radio groups grouped, error regions live |

**Do not claim browser checks passed unless actually executed.**

---

## 10. Acceptance Criteria (VERIFIABLE)

| # | Criterion | Automated | Manual |
|---|-----------|-----------|--------|
| 1 | Daily wellness 1–10 renders with correct descriptors per §5.2 | ✓ (test HTML content) | ✓ |
| 2 | Create daily record persists all fields + sessions | ✓ | ✓ |
| 3 | Edit daily record updates only changed fields | ✓ | ✓ |
| 4 | Multiple sessions with stable IDs | ✓ | ✓ |
| 5 | Explicit session deletion works; omission preserves | ✓ | ✓ |
| 6 | Conditional discomfort: zones required when `hay_molestia=si`, `otra` required iff `otro` | ✓ | ✓ |
| 7 | `molestia_zona_otra` cleared server-side when `otro` not selected | ✓ | ✓ |
| 8 | Conditional illness: `detalle_sintomas` optional when `si`, cleared when `no` | ✓ | ✓ |
| 9 | `entreno_hoy` toggle shows/hides training block | ✓ (JS toggle) | ✓ |
| 10 | Session textarea format `id|orden|tipo|min|rpe|comentarios` works for create/edit | ✓ | ✓ |
| 11 | Discard confirmation: two-step, signed token, cancel preserves | ✓ | ✓ |
| 12 | Stale discard token → 409, no deletion | ✓ | ✓ |
| 13 | HTTP 422: errors displayed, all submitted values repopulated | ✓ | ✓ |
| 14 | HTTP 409: submitted vs authoritative distinguished, recovery actions | ✓ | ✓ |
| 15 | CSRF required, athlete-only, server date authority | ✓ | ✓ |
| 16 | Mobile-first responsive, touch targets, focus states | | ✓ |
| 17 | Keyboard operable, screen-reader accessible | | ✓ |
| 18 | All existing `test_parte.py` tests pass (regression) | ✓ | |

---

## 11. Risks and Unresolved Questions

| Risk / Question | Status | Mitigation / Decision Needed |
|-----------------|--------|------------------------------|
| **Daily wellness descriptors** — not in `bienestar.py` (weekly 1–5). Router must supply. | **UNVERIFIED** — need to define in router or template | Add `DAILY_ITEMS`/`DAILY_ETIQUETAS` in `parte.py` or inline in template. **Decision:** define in `parte.py` `_base_context` to keep template clean. |
| **`molestia_zona` input UX** — comma-separated text vs. multi-select vs. datalist. | **PROPOSED** — text + `<datalist>` for whitelist | Start with text + placeholder listing zones; add `<datalist id="zonas-list">` with `<option>` for each `MOLESTIA_ZONAS` (progressive). |
| **409 recovery "current record" display** — how to show authoritative `parte` alongside form? | **PROPOSED** — read-only summary card above form | Add a `.card` with `parte` serialized values (read-only) when `conflict=True`. |
| **Session textarea vs. structured UI** — textarea is simple but error-prone. | **PROPOSED** — keep textarea for MVP | Helper text + example line; validation errors show which line failed. Post-MVP: JS-enhanced row editor. |
| **`allow_full_session_replacement` exposure** — currently only via hidden input. | **PROPOSED** — do not expose in Phase 4 UI | Default explicit delete/add; full replacement is an advanced/admin feature. |
| **Redirect target on success** — currently `/parte?ok=1`; weekly used `/inicio?parte=1`. | **UNRESOLVED** — Phase 5 will migrate `parte_pendiente` | Keep `/parte?ok=1` for Phase 4; Phase 5 coordinates. |
| **PostgreSQL concurrency not revalidated** — S-0029 historical only. | **UNVERIFIED** — Phase 6 PG-disposable required | Document as known limitation; Phase 4 tests on SQLite only. |
| **Weekly `bienestar.ITEMS` still used by consumers** — Phase 4 must not break them. | **VERIFIED** — router context override isolates daily template | Router passes daily items; weekly consumers still import `bienestar.ITEMS`. |

---

## 12. Concrete Backend Blockers (if any)

| Blocker | Evidence | Impact | Resolution |
|---------|----------|--------|------------|
| **None blocking** — Phase 3 router + Phase 2 services provide complete contract for Phase 4 UI. | Router returns all required context (`parte`, `form`, `errores`, `conflict`, `stale`, `edit_state_token`, `discard_token`, `sessions_form`, `delete_form`, tokens, enums). Services handle validation, locking, tokens, discard, sessions. | **No blockers** for UI implementation. | Proceed with Phase 4. |

**Note:** The only mismatch is `bienestar.ITEMS/ETIQUETAS` (weekly 1–5) vs. daily 1–10 wellness. Router must supply daily descriptors. This is a **router context change**, not a backend blocker.

---

## 13. Phase 4 Readiness Assessment

| Dimension | Status | Notes |
|-----------|--------|-------|
| **Backend contract stability** | **READY** | Phase 3 router accepted (S-0038/S-0039); Phase 2 services verified; Policy A + signed discard preserved. |
| **Template context completeness** | **READY WITH CONDITIONS** | Router must add daily wellness items/labels; all other context present. |
| **UI component patterns** | **READY** | `_campos.html` macros, `main.css` scales/conditionals, `main.js` toggles cover all needs. |
| **Test infrastructure** | **READY** | `conftest.py` fixtures, `test_parte.py` patterns, 48 passing tests. |
| **Accessibility/responsive baseline** | **READY** | Mobile-first CSS, radio-based scales, focus states, 44px targets. |
| **Scope clarity** | **READY** | Bounded to `parte.html`, `_campos.html`, router context; no service/router logic changes. |

**Overall: READY WITH CONDITIONS**  
**Condition:** Router `_base_context` must supply daily 1–10 wellness items/labels (replacing `bienestar.ITEMS/ETIQUETAS` for this template only).

---

## 14. Primary Implementation Sequence

1. **Router context update** (`app/routers/parte.py`): Add `daily_items`/`daily_etiquetas` to `_base_context` (or extend context in `_render_form`) with 1–10 descriptors per §5.2.
2. **Template redesign** (`app/templates/atleta/parte.html`): Implement Sections A–G per §5.1 using `escala_num` for wellness, `binario` + `data-abre` for conditionals, sessions textarea + delete input + current list, discard/conflict UX.
3. **Macro extension** (`app/templates/_campos.html`): Add optional `descriptores` parameter to `escala_num` for wellness labels (or define inline in template).
4. **CSS/JS verification**: Confirm existing styles/scripts cover new blocks; add minimal styles only if gaps found.
5. **Automated tests**: Extend `test_parte.py` with daily-specific tests (§8 table); run full suite.
6. **Manual browser checks**: Execute §9 table on mobile/desktop.
7. **Regression**: Ensure all 48 existing `test_parte.py` tests still pass.

---

## 15. Dependencies and Prerequisites

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 3 router (`app/routers/parte.py`) | **ACCEPTED** | No changes to logic; only context addition. |
| Phase 2 services (`parte_diaria.py`, tokens) | **VERIFIED** | Stable contracts. |
| `main.css` / `main.js` patterns | **VERIFIED** | Sufficient for MVP. |
| Test fixtures (`conftest.py`) | **VERIFIED** | Reusable. |
| Weekly consumer migration (Phase 5) | **DEFERRED** | Phase 4 must not break weekly consumers — router isolates daily context. |

---

## 16. Decisions Requiring User Approval

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **Daily wellness descriptors** | (A) Define in `parte.py` context (B) Inline in `parte.html` | **A** — keeps template clean, single source of truth |
| **`molestia_zona` input** | (A) Text + `<datalist>` (B) Multi-select `<select multiple>` (C) Checkbox group | **A** — simplest, works without JS, progressive enhancement |
| **409 "current record" display** | (A) Read-only summary card (B) Prefill form with current + show submitted in sidebar (C) Modal diff | **A** — minimal, clear, no JS |
| **Session textarea vs. structured rows** | (A) Keep textarea MVP (B) Add JS row editor now | **A** — textarea works, no new JS; enhance post-MVP if needed |
| **Success redirect target** | (A) `/parte?ok=1` (current) (B) `/inicio` (C) Configurable | **A** — Phase 5 will coordinate; keep minimal |

---

## 17. Plan File Location

Saved to: `.kilo/plans/1794275057816-phase4-ui-implementation-readiness.md`

---

**Next step:** Upon approval of the above decisions, proceed to implementation phase (switch to implementation-capable agent).