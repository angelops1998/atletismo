# S-0038 — Debug: Phase 3 repeated-field restoration fix (`/parte`)

- **Session:** NEW (debug)
- **Date:** 2026-11-09 (America/La_Paz context)
- **Objective:** Correct and validate incomplete repeated-field restoration in Phase 3. Preserve every submitted value without redesigning architecture.
- **Authorized scope:** `app/routers/parte.py`, `tests/test_parte.py`. `app/templates/atleta/parte.html` conditional — inspected; **no template change required** (template already renders `sessions_form`/`delete_form` into the existing inputs; router path traced).

## 1. Initial repository state (verified)

| Item | Value |
|---|---|
| Repository root | `C:/Archivos.Diego/atletismoWeb/atletismo` |
| Branch | `Baruc+Kilo` |
| HEAD (initial/final unchanged) | `ad45e940224967332f6d3f7fb3b9db549dae7756` (`kilo markdown: S-0037_debug_session-ses_e418.md y S-0036_debug_session-ses_e8fd.md`) |
| Working tree (initial) | clean (`git status`: up to date with `origin/Baruc+Kilo`, nothing to commit) |
| Staged/unstaged/untracked (initial) | none (`git status --porcelain=v1` empty) |
| Session export convention check | `.kilo/kiloSesions/S-0001`…`S-0037` present; next unique = `S-0038`; destination verified absent before creation (`Test-Path .kilo\kiloSesions\S-0038_debug_session-repeated-field-restoration.md` = `False`) |

S-0034–S-0037 **preserved** (not modified/overwritten); this export is a new file.

## 2. Historical evidence inspected (evidence, not proof of current implementation)

- `.kilo/kiloSesions/S-0036_debug_session-ses_e8fd.md` — reported prior Phase 3 debug acceptance and noted router already had `getlist`/newline splitting in `_session_payload` and preserved submitted `sessions`/`delete_form` on 422/409 in `_render_form`; also reported repeated-form preservation tests.
- `.kilo/kiloSesions/S-0037_debug_session-ses_e418.md` — exported prior session log; contains overlapping S-0036 narrative (historical evidence only).
- `.kilo/plans/1792882624161-phase3-router-integration-readiness.md` — Policy A/signed discard/409 preservation context; Phase 3 thin controller constraints.

## 3. Actual local implementation traced (request → render)

1. **POST `/parte`** (`guardar`): `get_current_user` + athlete role check; `target_date=hoy()` (server authority). Parses `await request.form()` via `_session_payload(form)`.
2. **`_session_payload(form)`** (lines ~105–187): already used `form.getlist("sessions")` when available, split each item by newlines, parsed each line with `_parse_session_item` (strict on malformed submitted values per S-0036). Used `form.getlist("delete_session_ids")` and split by commas; parsed positive ints, rejected malformed/non-positive/duplicate delete IDs; collected parse errors and **did not pass partial parse results to service** when errors returned to caller. Returns `(payload, delete_ids, allow_replace, errors)`. Single-value fallback exists when `getlist` absent.
3. **POST parse-error path:** on `parse_errors`, fetched current state via `pd.get_today_state(...)` and returned 422 via `_render_form(..., form=form, errors=parse_errors, ..., status_code=422)` — **no `pd.save_daily_record` call**.
4. **Service paths:** `pd.save_daily_record(...)` called only when parse errors absent. Validation failure (`STATUS_VALIDATION`) → 422 `_render_form` with `form=form`, `result.parte/tokens/errors`. Conflict (`STATUS_CONFLICT`) → 409 `_render_form` with `form=form`, `result.parte/tokens`, `conflict/stale`. 404/500 mapped similarly. **Service owns transactions/locking/Policy A/signed discard.**
5. **`_render_form` (pre-fix root cause):** on 422/409/errors with submitted form present, it used `form.get("sessions", "")` and `form.get("delete_session_ids", "")` (single-value). For Starlette/FastAPI form data, `get()` returns one value; repeated submitted fields under the same name can be discarded for restoration. `_session_payload` already preserved repeated values, so the parser/service path was not the same defect as rendering.
6. **Template:** `sessions_form` rendered into `<textarea id="sessions" name="sessions">...</textarea>`; `delete_form` rendered into `<input ... name="delete_session_ids" value="...">`. `data` macro reads submitted `form` for single wellness fields on 422/409. No template change needed for repeated restoration once router supplies joined preserved values.

## 4. Root cause

- **`_render_form` used single-value `form.get()` for `sessions` and `delete_session_ids` on 422/409/error restoration paths**, while `_session_payload` correctly used `form.getlist()` and newline/comma splitting. This mismatch could discard submitted repeated values when rendering validation/conflict responses, even though parsing preserved them.

## 5. Exact implementation changes

### `app/routers/parte.py` (only source file modified)
- Updated `_render_form` (422/409/errors branch with submitted `form`): when `form` supports `getlist`, collect non-empty `str(item)` values from `form.getlist("sessions")` and `form.getlist("delete_session_ids")`, then join with `"\n"` and `","` respectively for `sessions_form`/`delete_form`. Fallback preserves prior single-value behavior (`form.get(...) or ""`) when `getlist` unavailable. Non-error/non-422/409 path unchanged (uses persisted `parte` serialization). Existing 422/409 behavior, template context shape, and single-value behavior preserved.

### `tests/test_parte.py` (only test file modified)
- Strengthened existing `test_repeated_sessions_fields_se_preservan` to assert both complete submitted session lines appear in the rendered `sessions` textarea area (not only type substrings).
- Added precise regression tests in `TestInputParsing` using existing fixtures/helpers (`client, db, atleta, entrar, con_csrf, completo, _session_str, _get_edit_token`), httpx-valid repeated-field encoding (`list` values), and DB assertions:
  1. `test_repeated_sessions_fields_surviven_409` — two repeated `sessions` fields survive 409; both complete lines preserved in textarea; persisted `animo` unchanged (stale write not applied).
  2. `test_newline_sessions_textarea_survives_422` — newline-separated textarea `sessions` preserves both lines on 422; no persisted record created.
  3. `test_repeated_delete_ids_survive_422` — two repeated `delete_session_ids` survive 422; both IDs present in `delete_session_ids` input; persisted session IDs unchanged.
  4. `test_repeated_delete_ids_survive_409` — two repeated `delete_session_ids` survive 409; both IDs preserved; persisted wellness/sessions unchanged.
- No fixtures/helpers/DB APIs invented. No existing tests weakened.

### `app/templates/atleta/parte.html`
- **Not modified** (tracing showed router supplied joined values to existing template inputs; no demonstrated rendering defect required template change).

## 6. Tests and exact results

| # | Exact command | Exit | Actual result | Notes |
|---:|---|---:|---|---|
| 1 | `python -m py_compile app/routers/parte.py tests/test_parte.py` | 0 | PASS | no output |
| 2 | `pytest --collect-only -q tests/test_parte.py` (baseline) | 0 | PASS | 44 tests collected, 1 pre-existing deprecation warning (`starlette.testclient`/`httpx`) |
| 3 | `pytest tests/test_parte.py -q -k "repeated_sessions_fields_se_preservan" --tb=short` | 0 | PASS | 1 passed, 43 deselected, 1 warning |
| 4 | `pytest --collect-only -q tests/test_parte.py` (after additions) | 0 | PASS | 48 tests collected |
| 5 | `pytest tests/test_parte.py -v --tb=short -k "repeated_sessions_fields_surviven_409 or newline_sessions_textarea_survives_422 or repeated_delete_ids_survive_422 or repeated_delete_ids_survive_409 or repeated_sessions_fields_se_preservan or 409_preserva_lo_submitido or valores_preservados_en_422"` | 0 | PASS | 7 passed, 41 deselected, 1 warning in 1.94s |
| 6 | `pytest tests/test_parte.py -v --tb=short` | 0 | PASS | **48 passed, 1 warning in 13.52s** |
| 7 | `pytest -q --tb=no` | 0 | PASS | **395 passed, 5 skipped, 1 warning in 73.89s (0:01:13)** |
| 8 | `git --no-pager diff -- app/services/parte_diaria.py app/services/parte_diaria_tokens.py app/models/parte_diaria.py app/models/sesion_entrenamiento.py app/models/parte.py app/templates/atleta/parte.html` | 0 | PASS | empty diff |
| 9 | `git --no-pager diff --stat` | 0 | PASS | `app/routers/parte.py | 14 ++++--`, `tests/test_parte.py | 123 ++++++++++++++++++++++++++++++++++++++++++++++++++-` (2 files, 132 insertions, 5 deletions); warnings about LF→CRLF on touch (environment) |

## 7. Acceptance criteria assessment

| Criterion | Status | Evidence |
|---|---|---|
| Repeated `sessions` values survive HTTP 422 restoration | VERIFIED | `test_repeated_sessions_fields_se_preservan` (strengthened), `test_newline_sessions_textarea_survives_422`; complete lines in textarea area |
| Repeated `sessions` values survive HTTP 409 restoration | VERIFIED | `test_repeated_sessions_fields_surviven_409`; textarea lines preserved; stale persisted state unchanged |
| Repeated `delete_session_ids` values survive 422 restoration | VERIFIED | `test_repeated_delete_ids_survive_422`; both IDs in input; persisted sessions unchanged |
| Repeated `delete_session_ids` values survive 409 restoration | VERIFIED | `test_repeated_delete_ids_survive_409`; both IDs preserved; persisted wellness/sessions unchanged |
| Newline-separated textarea behavior remains compatible | VERIFIED | existing payload parsing preserved; `test_newline_sessions_textarea_survives_422`; full `test_parte.py` green |
| Failed requests do not modify persisted sessions | VERIFIED | DB assertions in new tests; existing parsing-failure/conflict/discard tests still pass |
| Existing Phase 3 behavior and acceptance criteria remain intact | VERIFIED (local/SQLite evidence) | full `tests/test_parte.py` 48 passed; full suite 395 passed, 5 skipped |
| All relevant tests pass | VERIFIED | commands 5–7 |
| No unrelated modifications introduced | VERIFIED | git diff stat shows only `app/routers/parte.py`, `tests/test_parte.py`; Phase 2/services/models/templates unchanged |

## 8. Final Git state

- Branch: `Baruc+Kilo...origin/Baruc+Kilo`
- HEAD: `ad45e940224967332f6d3f7fb3b9db549dae7756` (unchanged)
- Modified tracked: `app/routers/parte.py`, `tests/test_parte.py`
- Untracked non-ignored (after export): `.kilo/kiloSesions/S-0038_debug_session-repeated-field-restoration.md` (authorized session export)
- No commits, pushes, merges, PRs, or deployments.

## 9. Remaining limitations

- **PostgreSQL concurrency NOT revalidated.** S-0029 remains historical reported evidence only. SQLite/full-suite results do not prove `FOR UPDATE`/race serialization.
- Starlette/TestClient `httpx` deprecation warning is pre-existing test-environment noise (not introduced by this change).
- The router now joins repeated submitted `delete_session_ids` values with commas for the text input; repeated `sessions` values are joined with newlines for the textarea. This preserves distinct submitted values and remains compatible with the existing parser (which already splits commas/newlines). It does not change persisted state representation.

## 10. Final assessment

**ACCEPTED (bounded, SQLite/local evidence).** Repeated-field restoration criteria for `sessions` and `delete_session_ids` on 422/409 are verified by targeted regression tests and rendered-value assertions; newline textarea compatibility preserved; failed requests do not modify persisted sessions; previous Phase 3 local acceptance criteria remain satisfied by full `test_parte.py` and full suite. PostgreSQL concurrency remains **UNVERIFIED in this session** (S-0029 historical only).
