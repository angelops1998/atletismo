# S-0036 — Debug: Phase 3 final validation and defect correction (`/parte`)

- **Session:** NEW (debug)
- **Date:** 2026-11-09 (America/La_Paz context)
- **Scope:** Bounded Phase 3 correction/validation only. No Phase 4. No redesign.
- **Authorized files:** `app/routers/parte.py`, `tests/test_parte.py`; `app/templates/atleta/parte.html` only if a demonstrated restoration/validation-display defect required it (none required).

## 1. Baseline / Git

### Initial (verified before edits)
| Item | Value |
|---|---|
| Repository root | `C:/Archivos.Diego/atletismoWeb/atletismo` |
| Branch | `Baruc+Kilo` |
| HEAD | `d1c3750468841250c87389fc176c712d23ce5cc3` (`kilo markdown: S-0035_debug_session-ses_e424.md y S-0034_debug_session-ses_e8fd.md`) |
| Working tree status | clean (no staged/unstaged/untracked non-ignored changes) |

### Final
| Item | Value |
|---|---|
| Branch | `Baruc+Kilo...origin/Baruc+Kilo` |
| HEAD | unchanged (`d1c3750468841250c87389fc176c712d23ce5cc3`) — no commits made |
| Modified tracked files | `app/routers/parte.py`, `tests/test_parte.py` |
| Untracked non-ignored | none (this export created in working tree as authorized session export) |
| Unauthorized diffs | none in Phase 2 services/models/migrations/templates/consumers (`git diff -- app/services/parte_diaria.py app/services/parte_diaria_tokens.py app/models/parte_diaria.py app/models/sesion_entrenamiento.py app/models/parte.py app/templates/atleta/parte.html` = empty) |

## 2. Session export preservation (S-0034 / S-0035)

| File | Size | Last write (local listing) | Preserved? | Overwritten/modified by this session? |
|---|---:|---|---|---|
| `.kilo/kiloSesions/S-0034_debug_session-ses_e8fd.md` | 9808 bytes | 2026-11-08 20:39:22 | YES | **No.** Different file; exists unchanged on disk; no diff; not overwritten. |
| `.kilo/kiloSesions/S-0035_debug_session-ses_e424.md` | 16277 bytes | 2026-11-08 20:40:09 | YES | **No.** S-0035 did **not** overwrite/replace S-0034 (both exist, different names/sizes/content; committed together in HEAD `d1c3750`). |

This export: `S-0036_debug_session-ses_e8fd.md` — destination verified absent before creation (`Test-Path` = `False`).

## 3. Files inspected (actual local implementation authoritative)

- `.kilo/kiloSesions/S-0034_debug_session-ses_e8fd.md`, `.kilo/kiloSesions/S-0035_debug_session-ses_e424.md`
- `.kilo/plans/1792882624161-daily-tracking-replacement.md`, `.kilo/plans/1792882624161-phase2-concurrency-policy.md`, `.kilo/plans/1792882624161-phase3-router-integration-readiness.md`
- `app/routers/parte.py`, `app/templates/atleta/parte.html`, `tests/test_parte.py`, `tests/conftest.py`
- `app/services/parte_diaria.py`, `app/services/parte_diaria_tokens.py` (Phase 2 contract/boundary; not modified)
- Git metadata/history for session-export context

## 4. Material discrepancies (actual implementation vs S-0034/S-0035 reports/Phase 3 readiness)

Verified in HEAD `d1c3750` (`git show HEAD:app/routers/parte.py`):

1. **Malformed deletion IDs silently discarded** (`_session_payload`): `delete_ids.append(int(item))` inside `try/except ValueError: pass`. Mixed valid+malformed requests could be partially interpreted; invalid/non-positive/duplicate IDs not explicitly rejected by contract.
2. **Malformed session ID became `None`** (`_parse_session_item`): `except ValueError: item["id"] = None` — an invalid submitted existing-session ID could be treated as a new session payload shape (dangerous semantic coercion).
3. **Malformed session numeric fields silently defaulted** (`orden/duracion_min/rpe`): `except ValueError: pass` kept defaults instead of rejecting malformed submitted values.
4. **Repeated form fields / restoration**: router already supported `form.getlist()` + newline splitting and preserved submitted `sessions`/`delete_session_ids` on 422/409 in `_render_form`; template already used submitted values on error paths. No demonstrated template defect required change. New tests prove repeated `sessions` fields are preserved on 422 and accepted when valid.
5. **S-0034 acceptance claims** marked “Malformed IDs rejected explicitly” / form restoration as PASS, but implementation/tests at HEAD did not enforce explicit rejection for these malformed cases. This session corrects the implementation and adds regression coverage; it does not alter historical exports.

## 5. Defects reproduced (evidence)

From HEAD behavior inspection + targeted new tests (before fix these cases would not be explicitly rejected by router parsing as required):
- Malformed delete ID (`abc`) — previously swallowed.
- Mixed valid+malformed delete IDs — previously partial parse risk.
- Non-positive delete ID (`0`) — not rejected by router parser.
- Duplicate delete IDs — not rejected.
- Malformed existing-session ID (`abc|...`) — previously coerced to `id=None`.
- Malformed `orden`/`duracion_min`/`rpe` — previously defaulted.
- Parsing failures needed proof they cannot trigger unintended create/delete/partial service mutation.

All reproduced/captured by `TestInputParsing` failures during red→green cycle (2 initial test-shape issues fixed: TestClient repeated-field encoding and accidentally removed `TestConflictos` restored) and final green suite.

## 6. Corrections implemented (`app/routers/parte.py` only)

- Added `FormParseError` and `_parse_positive_int(raw, name=...)`: rejects empty/non-integer/non-positive values with controlled messages.
- `_parse_session_item(text, index=...)`: missing optional values still keep defaults; **malformed submitted** `id/orden/duración/RPE` now raise `FormParseError` (no `id=None` coercion, no silent defaults).
- `_session_payload(form)` now returns `(payload, delete_ids, allow_replace, errors)`:
  - Preserves existing repeated-form-field handling (`getlist`) and newline splitting for `sessions`.
  - Preserves comma splitting for `delete_session_ids`.
  - Rejects malformed, non-positive, and **duplicate** delete IDs explicitly (duplicates rejected as inconsistent/ambiguous; no partial request forwarded).
  - Collects parse errors; **never passes partially parsed delete/session mutations to the Phase 2 service**.
- `POST /parte`: parses form, obtains current `parte/edit_token/discard_token` via `pd.get_today_state` for stable 422 context, and if `parse_errors` returns 422 with preserved submitted form/errors/tokens — **no `pd.save_daily_record` call**. Phase 2 service contracts/validation unchanged.
- `_render_form` preservation behavior for 422/409 left intact (submitted `sessions`/`delete_session_ids` preserved; authoritative persisted state remains in `parte`/tokens from service/current state).
- No router-level commits/rollbacks. No template changes.

## 7. Tests added (`tests/test_parte.py`, `TestInputParsing`)

Using existing fixtures/helpers (`client`, `db`, `atleta`, `entrar`, `con_csrf`, `completo`, `_session_str`, `_get_edit_token`):

1. `test_malformed_delete_id_es_422`
2. `test_mixed_valid_and_malformed_delete_ids_no_borra_nada` (DB proves no partial delete)
3. `test_non_positive_delete_id_es_422`
4. `test_duplicate_delete_ids_es_422`
5. `test_malformed_existing_session_id_no_crea_nueva` (existing ID/values unchanged)
6. `test_malformed_session_order_es_422`
7. `test_malformed_duration_es_422`
8. `test_malformed_rpe_es_422`
9. `test_repeated_sessions_fields_se_preservan` (422, both lines preserved; no record created)
10. `test_repeated_sessions_fields_crean_multiples` (valid repeated fields create 2 sessions)
11. `test_parsing_failure_no_llama_service_ni_modifica` (malformed session + malformed delete + would-change `animo`; DB snapshot unchanged)

Also preserved/restored existing coverage: `test_valores_preservados_en_422`, both `TestConflictos` tests (409 stale + submitted preservation), all prior 33 tests still pass. No existing tests weakened.

## 8. Commands executed (exact) and results

| # | Command | Exit | Result | Relevant output |
|---:|---|---:|---|---|
| 1 | `git rev-parse --show-toplevel` | 0 | PASS | `C:/Archivos.Diego/atletismoWeb/atletismo` |
| 2 | `git branch --show-current` | 0 | PASS | `Baruc+Kilo` |
| 3 | `git rev-parse HEAD` | 0 | PASS | `d1c3750468841250c87389fc176c712d23ce5cc3` |
| 4 | `git status --porcelain=v1` | 0 | PASS | (empty) |
| 5 | `git --no-pager diff --name-only` | 0 | PASS | (empty before edits) |
| 6 | `python -m py_compile app/routers/parte.py tests/test_parte.py` | 0 | PASS | (no output) |
| 7 | `pytest --collect-only -q tests/test_parte.py` | 0 | PASS | 44 tests collected |
| 8 | `pytest tests/test_parte.py -q --tb=no` (baseline) | 0 | PASS | `33 passed, 1 warning in 8.23s` |
| 9 | `pytest tests/test_parte.py -v -k "InputParsing or 409_preserva or valores_preservados" --tb=short` | 0 | PASS | `13 passed, 31 deselected, 1 warning in 3.90s` (after red→green fix) |
| 10 | `pytest tests/test_parte.py -q --tb=no` | 0 | PASS | `44 passed, 1 warning in 14.06s` |
| 11 | `pytest -q --tb=no` (full suite) | 0 | PASS | `391 passed, 5 skipped, 1 warning in 80.81s (0:01:20)` |
| 12 | `git --no-pager diff --name-only` | 0 | PASS | `app/routers/parte.py`, `tests/test_parte.py` |
| 13 | `git ls-files --others --exclude-standard` | 0 | PASS | (empty) |
| 14 | `git --no-pager diff -- app/services/parte_diaria.py app/services/parte_diaria_tokens.py app/models/parte_diaria.py app/models/sesion_entrenamiento.py app/models/parte.py app/templates/atleta/parte.html` | 0 | PASS | (empty) |
| 15 | `git status --short --branch` | 0 | PASS | `M app/routers/parte.py`, `M tests/test_parte.py` |

Notes: Starlette/TestClient `httpx` deprecation warning observed (pre-existing test environment noise); not a failure.

## 9. Phase 2 / architecture boundary confirmation

- **No Phase 2 service changes:** `app/services/parte_diaria.py`, `app/services/parte_diaria_tokens.py` unchanged.
- **No model/migration changes.** No weekly consumers/dashboard/alerts/statistics/charts changes. No Phase 4 functionality added.
- **Router does not commit/rollback DB transactions.** Parse errors short-circuit before service call; service remains authoritative for validation/transactions/locking/concurrency/signed discard semantics.
- **Policy A / signed discard preserved:** existing `TestDescarte`/`TestConflictos` pass unchanged in behavior.
- **`app/templates/atleta/parte.html` unchanged** (no demonstrated restoration/validation-display defect required it).

## 10. Limitations / risks

- **PostgreSQL concurrency NOT revalidated** in this session. S-0029 remains **previously reported evidence only** (PG 16.15 disposable container: lock-wait/create-race/discard proofs, suite 379 passed as reported). SQLite-based tests here do not prove `FOR UPDATE`/race serialization.
- A successful local/SQLite test suite does **not** independently establish correctness of untested PG concurrency behavior.
- Router parse errors for session fields are intentionally strict on malformed submitted values; missing optional values remain accepted/defaulted by design. Domain validation (types/ranges/ownership/entreno_hoy rules) remains in Phase 2 service.
- Duplicate delete IDs are rejected at router boundary (explicit, non-partial). Service contract inspected: it accepts `explicit_delete_session_ids` but does not explicitly reject duplicates; router rejection avoids ambiguous intent. No Phase 2 change made.

## 11. Phase 3 acceptance decision

| Criterion | Status | Evidence |
|---|---|---|
| Invalid deletion identifiers explicitly rejected | PASS | `test_malformed_delete_id_es_422`, non-positive, duplicate |
| Mixed valid+malformed deletion IDs rejected, no partial delete | PASS | `test_mixed_valid_and_malformed_delete_ids_no_borra_nada` |
| Invalid existing-session identifiers explicitly rejected | PASS | `test_malformed_existing_session_id_no_crea_nueva` |
| Invalid numeric session fields explicitly rejected | PASS | order/duration/RPE tests |
| Invalid input cannot silently create/replace/delete sessions; parsing failures cannot execute partially parsed deletion requests | PASS | DB assertions + `test_parsing_failure_no_llama_service_ni_modifica` |
| Submitted values preserved on validation/conflict responses | PASS | `test_valores_preservados_en_422`, `test_409_preserva_lo_submitido`, repeated-fields preservation |
| Repeated form fields handled correctly | PASS | `test_repeated_sessions_fields_*` |
| Existing signed discard and Policy A behavior intact | PASS | `TestDescarte`, `TestConflictos`, full `test_parte.py` |
| Targeted route tests pass | PASS | 44 passed |
| Full-suite results reported accurately | PASS | 391 passed, 5 skipped, 1 warning (exit 0) |
| No unauthorized Phase 2 or unrelated changes | PASS | git diff/name checks |

**Phase 3 status: ACCEPTED** (bounded to corrected router input-validation defects + verified local test evidence; PG concurrency remains S-0029 reported evidence only).
