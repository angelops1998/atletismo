# Daily Tracking Phase 2.2.1 — PostgreSQL Concurrency Validation

**Session:** `ses_e8fd`  
**Execution date:** 2026-11-08 (America/La_Paz)  
**Repository:** `C:\Archivos.Diego\atletismoWeb\atletismo`  
**Branch:** `Baruc+Kilo`  
**Initial and final HEAD:** `e81057803fccafcec390f7c21605be103951894e`  
**Overall assessment:** PASS

---

## 1. Objective and scope

Executed the Phase 2.2.1 concurrency hardening and regression validation for daily tracking. Scope was limited to the service create synchronization seam, PostgreSQL disposable-target verification and concurrency tests, plus this report. No migration, schema, router, UI, weekly consumer, or Phase 3 implementation was changed. No commit or push was made.

## 2. Initial Git state and safety

Before editing, confirmed repository root and branch `Baruc+Kilo`. `git status --short`, `git diff --stat`, the complete pre-existing diff, and untracked-file inspection were empty. Initial HEAD was `e81057803fccafcec390f7c21605be103951894e`. Recent history and required local context documents were inspected. The local tree was treated as authoritative; no remote synchronization was attempted.

**Classification: PASS — repository safety inspection.** Existing user changes were not present, and no reset, checkout, stash, clean, or overwrite operation was used.

## 3. Plans and previous reports inspected

Read and used these documents before implementation:

- `.kilo/plans/1792882624161-daily-tracking-replacement.md`
- `.kilo/plans/1792882624161-phase2-concurrency-policy.md`
- `.kilo/kiloSesions/S-0026_code_session-ses_e8fd.md`
- `.kilo/kiloSesions/S-0027_debug_session-ses_e8fd.md`
- `.kilo/kiloSesions/S-0028_debug_session-ses_e8fd.md`
- `.kilo/kiloSesions/S-0021_code_session-postgres-migration-validation.md`

The approved Policy A remains in force: signed edit-state tokens, canonical persisted-state fingerprints, lock then refresh then token verification, stale conflict responses, no retries or silent overwrite, create-race conflict after rollback/reload, and preserved signed discard behavior. The accepted Phase 1 PostgreSQL 16.15 migration validation was not repeated.

## 4. Initial defects identified

Code review confirmed three outstanding weaknesses described by prior work:

1. `_test_before_create_insert` ran after `db.flush()`, so it synchronized after PostgreSQL had already attempted the parent INSERT and could not prove a deterministic create race.
2. The PostgreSQL gate could accept marker hints or database-name patterns without requiring all task-specific labels, exact container-to-URL port correspondence, a dedicated DB/user, and live identity proof tied back to the inspected container.
3. `_wait_for_lock()` relied on relation lock evidence. PostgreSQL row-lock contention can appear as a transaction ID wait, so relation-name filtering did not establish the exact backend blocking relationship.

**Classification: PASS — defects verified by source inspection.**

## 5. Changes implemented

### `app/services/parte_diaria.py`

- Moved the optional create barrier to after the new parent and requested sessions are staged but before the `flush()` that issues INSERT.
- Added the narrow optional `_test_on_create_integrity_error` callback, invoked only from the real `IntegrityError` handler when this request entered the create path. This lets the test prove the production handler ran. Normal production calls leave both hooks unset.
- Kept the actual conflict behavior on `_conflict_result`: rollback and reload, returning a conflict without retry or reapplication.

### `tests/test_parte_diaria_concurrency_pg.py`

- Tightened independent target verification. Requires local Docker context; a full 64-character container ID; running state; exact `postgres:16` image configuration; mandatory task, purpose, and disposable labels plus dynamic identity labels; dedicated database, test login, and separate owner; exactly one published PostgreSQL port on `127.0.0.1`; and exact URL host, port, DB and test-user correspondence.
- Checks live database/user identity, PostgreSQL major version 16, server port 5432, nonprivileged test role, task-specific database comment and server start identity. Executes `psql` inside the inspected container and compares database, owner, version and postmaster start timestamp to the active SQLAlchemy connection. Marker/environment hints can only be checked for contradiction and never independently establish disposability.
- Added gate rejection tests for missing/wrong labels, non-loopback or mismatched port, mismatched live identity, URL mismatch, wrong image, and marker/allow hints without independent proof. Includes a positive matching synthetic gate test; actual target acceptance is separately tested against the live task container.
- Replaced relation-lock inference with `pg_stat_activity` and `pg_blocking_pids()` checks tied to the exact transaction PIDs and service query.
- Strengthened create-race assertions to prove both service calls saw no row, both reached the pre-insert barrier, one actual `IntegrityError` handler ran, the loser rolled back/reloaded the winner and returned conflict, and exactly one complete parent/session set persisted.
- Retained exact-ID cleanup and signed-token/discard tests. No table-wide DELETE statements were added.

**Classification: PASS — implementation and test changes.** No migration or schema change was made.

## 6. PostgreSQL disposable environment and independent verification

Docker Desktop was stopped at task start. It was started for validation; the Docker Engine became available using the local `desktop-linux` context. No containers existed before provisioning. Pulled the official `postgres:16` image (image ID `sha256:f9a7b9ebf6f56201f949db745e47bc423c0f0f8294bafe991cc10bf74b029657`).

Created a task-unique temporary container and task-unique named volume. Independently inspected the running container and active database connection before executing state-changing tests:

- **Container name:** `atle-pg-p2-2-1-3f9037f34956`
- **Container ID:** `bcdfa8c79984a6448b04f1b51d25d1e8ef50ac619b86bed121b0a87f3bee8de2`
- **Image:** `postgres:16` (official image; digest/image ID recorded above)
- **Mandatory labels:** `atletismo.task=phase2.2.1`, `atletismo.purpose=postgres-concurrency-validation`, `atletismo.disposable=true`; dynamic task instance, database, test user, owner, and volume labels were also present and matched container configuration.
- **Published binding:** `127.0.0.1:55440 -> 5432/tcp`; Docker `HostConfig.PortBindings` and `NetworkSettings.Ports` agreed, with no other published port.
- **Database:** `atle_test_p2_2_1_3f9037f34956`
- **Test connection user:** `atle_p2_2_1_3f9037f34956` (separate from owner; no superuser/create-database/create-role privileges)
- **Owner role:** task-specific `atle_owner_3f9037f34956`
- **Live server:** PostgreSQL 16.15 (Debian 16.15-1.pgdg13+2)
- **Identity correspondence:** live `current_database()`, `current_user()`, server port, DB comment, server version and postmaster-start timestamp matched the task labels/configuration; `docker exec`/`psql` against the full inspected container ID returned matching DB, owner, version and start timestamp.
- **Credential handling:** temporary credentials were not included in command output or this report. The scratch credential file was deleted after tests.

The gate rejected unverified targets in its isolated safety tests. With the independently verified task URL and marker set only for test discovery, every PostgreSQL concurrency test executed and none skipped.

**Classification: PASS — manual Docker/container inspection and live database identity verification.**

## 7. Exact validation commands and results

All commands used the repository virtual environment at `.venv\Scripts\python.exe`.

### PostgreSQL safety gate without a configured disposable target

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_parte_diaria_concurrency_pg.py -q
```

Result: **17 passed, 5 skipped, 1 warning in 0.09s.** The five skips were PostgreSQL-dependent tests because no verified target was configured; the isolated gate tests ran and confirmed marker/allow hints cannot bypass independent checks. This was a safety-gate run, not the PostgreSQL concurrency result.

### Schema tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_parte_diaria_schema.py -q
```

Result: **7 passed, 1 warning in 0.47s.**

### SQLite service tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_parte_diaria_service.py -q
```

Result: **22 passed, 1 warning in 3.18s.**

### PostgreSQL concurrency suite against the independently verified task container

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_parte_diaria_concurrency_pg.py -q -s
```

Result: **22 passed, 1 warning in 1.55s; zero skipped.** All gate, stale update, service create race, concurrent discard, and raw unique-constraint tests executed.

### Full repository regression suite

With the verified disposable PostgreSQL test URL and task marker set only in the test process:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **379 passed, 1 warning in 65.00s.** No tests were excluded. The warning was the existing `StarletteDeprecationWarning` concerning `httpx` and `starlette.testclient`.

**Classification: PASS — SQLite/schema, PostgreSQL suite, and full regression.**

## 8. PostgreSQL lock-wait proof

The deterministic stale-update test opened independent transactions and captured backend PIDs. Transaction 1 acquired and retained the `ParteDiaria` parent-row lock after its update. Transaction 2 entered the actual service update path with the stale signed edit token and attempted the same `FOR UPDATE` row lock.

Before releasing transaction 1, PostgreSQL backend inspection established:

- **tx1 PID (blocker):** `116`
- **tx2 PID (waiter):** `124`
- **waiting PID:** `124`
- **`pg_blocking_pids(124)`:** `[116]`
- **wait event:** `Lock` / `transactionid`
- **waiting query:** service query selecting the target `partes_diarios` row `FOR UPDATE OF partes_diarios`

After this exact PID relationship was observed, tx1 committed. Tx2 resumed, refreshed persisted parent/session state, rejected the stale fingerprint and returned **409 conflict**. Final persisted `animo` remained **7**, the value committed by tx1.

**Classification: PASS — exact backend blocking relationship, stale conflict and no-overwrite value verified in PostgreSQL.**

## 9. Service-level create-race proof

Two independent service calls targeted the same athlete/date. Instrumented observations showed both independently saw no daily record and both reached the pre-INSERT barrier before either parent INSERT was flushed. After release:

- Both missing-record observations: **2**
- Both pre-insert hook arrivals: **2**
- Winning request: **200**
- Losing request: **409 conflict**
- Actual service `IntegrityError` callback invocations: **1**, exception type `IntegrityError`
- Loser rollback/reload: reloaded the same winning parent ID `14` and session ID `5`
- Final state: exactly **1** daily record, complete with `animo=5`, `entreno_hoy=true`, and exactly one requested session with load calculated by `duracion_min * rpe`

There was no duplicate, partial record, blind retry, or silent overwrite. The raw SQL unique-constraint race remained supplementary evidence; the required service-level race exercised the actual service and exception path.

**Classification: PASS — deterministic service-level race and unique constraint authority.**

## 10. Concurrent discard proof

A stale signed discard attempt ran concurrently with a committed edit. It returned **409 conflict**, preserved `entreno_hoy=true`, and preserved the existing session (one session, RPE `9`). The stale request did not silently discard or replace session data.

**Classification: PASS — signed discard conflict and session preservation.**

## 11. Cleanup

Before cleanup, verified the exact full container ID, task name, image, mandatory labels, task instance, and its single task-labeled volume. Verified the volume was attached only to this task container. Removed only that exact container and exact task volume. The `postgres:16` image was absent before this task and no other container used it, so the exact image ID pulled for this task was also removed. Deleted the scratch credential JSON.

Post-cleanup inspection confirmed the task container, task volume, and `postgres:16` image were absent. Docker Desktop was stopped after use; `docker desktop status` then reported it was not running. No unrelated container, volume, database, or image was removed.

**Classification: PASS — task resources cleaned and absence verified.**

## 12. Final Git state and diff review

Final tracked changes are limited to:

- `app/services/parte_diaria.py`
- `tests/test_parte_diaria_concurrency_pg.py`

This report is the only new file. Final diff summary before adding the report: service `15 insertions / 16 deletions`; PostgreSQL test `436 insertions / 88 deletions`. `git diff --check` completed without whitespace errors. Git emitted only line-ending normalization warnings (LF may be converted to CRLF). No migration or schema file changed. Final HEAD remains `e81057803fccafcec390f7c21605be103951894e`; no commit was created.

**Classification: PASS — final scope and diff inspection.**

## 13. Risks and limitations

- One existing Starlette/httpx deprecation warning remains; it did not fail tests.
- PostgreSQL concurrency evidence is specific to the executed local Docker Engine and PostgreSQL 16.15 instance. The task container, volume and image were intentionally removed after validation.
- No production/staging database was accessed. No production behavior is claimed beyond the tested implementation and disposable PostgreSQL evidence.

## 14. Final assessment

**PASS.** The disposable target was independently verified, all five required PostgreSQL concurrency cases executed without skips, lock contention was proven through the exact PostgreSQL backend PID relationship, create-race conflict handling was exercised through the service's real `IntegrityError` path, SQLite/schema tests passed, and the full repository suite passed (379 tests). Task-created Docker resources and temporary credentials were cleaned up. Phase 2.2.1 validation is complete. No Phase 3 work was started; any further implementation requires its separate authorization.
