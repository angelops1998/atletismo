# Plan: Dependency Maintenance — Timezone and Starlette TestClient Warning

## Goal
Prepare minimal dependency-management plan for `atletismo` without implementing changes.

## Repository state
- Root: `C:\Archivos.Diego\atletismoWeb\atletismo`
- Branch: `main` (tree clean)
- Last commit: `534f0e79d1e367025089af34e89c27f387336b15`
- Historical test result: `328 passed, 1 StarletteDeprecationWarning in 64.29s` (NOT RUN in this audit)

## Findings
- Python venv: 3.12.10
- FastAPI: 0.136.3; Starlette: 1.2.1; HTTPX: 0.28.1; tzdata: 2026.5
- FastAPI metadata requires `starlette>=0.46.0`
- `app/tiempo.py` uses `ZoneInfo("America/La_Paz")`
- `tests/conftest.py:23` imports `fastapi.testclient.TestClient`
- Warning source: `starlette/testclient.py` lines 54-58, emitted because Starlette 1.2.1 prefers `httpx2` and project installs `httpx`
- `pytest.ini` ignores `DeprecationWarning:starlette.*` and httpx deprecations, but not `StarletteDeprecationWarning` (UserWarning subclass)

## Proposed manifest changes
### requirements.txt
- Add `tzdata==2026.5` under a timezone section.
- Rationale: Windows has no IANA system timezone database; `ZoneInfo("America/La_Paz")` fails without tzdata.

### requirements-prod.txt
- Change `tzdata==2026.4` to `tzdata==2026.5`.
- Rationale: align installed dev version with production pin.

### Starlette/HTTPX
- No dependency change recommended yet.
- UNVERIFIED whether `httpx2` is available and maintained.
- Do not suppress warning solely for clean output.

## Compatibility evidence
- FastAPI 0.136.3 supports Starlette >=0.46.0; installed 1.2.1 is compatible.
- Warning is upstream compatibility notice, not application defect.

## Validation plan
1. Manifest consistency and dependency resolution after changes.
2. Timezone behavior on Windows via importing `app.tiempo`.
3. TestClient warning reproduction/elimination on relevant tests.
4. Full suite comparison against historical baseline.
- Render-environment verification remains UNVERIFIED locally.

## Uncertainties
- Availability and maintenance status of `httpx2`.
- Actual Render package resolution and OS timezone data.

## Decision
Proceed with tzdata version alignment only; investigate httpx2 compatibility before any Starlette/HTTPX change.

## Recommended next action
Verify whether `httpx2` is an available, maintained package compatible with Starlette 1.2.1 and FastAPI 0.136.3 before deciding on the warning remediation.