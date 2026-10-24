# Plan: Dependency Maintenance — Timezone and Starlette TestClient Warning

## Goal
Finalize a read-only dependency-maintenance plan for `atletismo` covering `tzdata` consistency and the Starlette `TestClient` deprecation warning.

## Repository state
- Root: `C:\Archivos.Diego\atletismoWeb\atletismo`
- Branch: `main`
- Working tree: clean
- HEAD: `534f0e79d1e367025089af34e89c27f387336b15` ("Mover el despliegue del VPS a Render + Supabase", 2026-09-22)
- Python venv: 3.12.10 (`.venv`, `include-system-site-packages = false`)
- Installed: FastAPI 0.136.3, Starlette 1.2.1, HTTPX 0.28.1, tzdata 2026.5
- Historical test result only: `328 passed, 1 StarletteDeprecationWarning in 64.29s` (NOT RUN in this audit)

## Executive recommendation
1. Align `tzdata` to `2026.5` in both manifests: add it to `requirements.txt`, and update `requirements-prod.txt` from `2026.4` to `2026.5`.
2. Resolve the warning by installing `httpx2>=2.0.0` in the development environment (and likely production if `TestClient` is used there), while keeping `httpx==0.28.1` for runtime/application compatibility.
3. Do not suppress the warning in `pytest.ini`.

## Exact proposed manifest changes
### `requirements.txt`
Current:
```
# Tests (solo desarrollo; no van en requirements-prod.txt)
pytest==9.1.1
httpx==0.28.1
```
Proposed addition:
```
# Zonas horarias (Windows no tiene base IANA del sistema)
tzdata==2026.5
```
Rationale: `app/tiempo.py` calls `ZoneInfo("America/La_Paz")`; on Windows Python's `zoneinfo` falls back to the `tzdata` package. Without it, import/runtime fails with `ZoneInfoNotFoundError`.

### `requirements-prod.txt`
Current:
```
tzdata==2026.4
```
Proposed:
```
tzdata==2026.5
```
Rationale: align production with the verified installed development version and keep reproducible pinning.

### Starlette / HTTPX
Current:
- `starlette==1.2.1`
- `httpx==0.28.1`
No change to these pins. Add `httpx2>=2.0.0` only if the warning remediation is approved, because Starlette 1.2.1 explicitly prefers `httpx2` and falls back to `httpx` with a deprecation warning.

## Compatibility evidence
- FastAPI 0.136.3 metadata: `Requires-Dist: starlette>=0.46.0`; Python `>=3.10`.
  Source: installed `fastapi-0.136.3.dist-info/METADATA`.
- Starlette 1.2.1 metadata: Python `>=3.10`; optional dependency `httpx2>=2.0.0` under `[full]`; `httpx<0.29.0,>=0.27.0` also listed for compatibility.
  Source: PyPI Starlette 1.2.1 project page and installed `starlette-1.2.1.dist-info/METADATA`.
- Starlette release notes 1.2.0: "Support httpx2 in the test client #3291"; 1.2.1: "Use httpx2 for type checking in the testclient module #3304".
  Source: https://starlette.dev/release-notes/
- Starlette docs: TestClient is built on `httpx2`; plain `httpx` still supported but deprecated.
  Source: https://starlette.dev/testclient/
- Starlette PR #3291: testclient prefers `httpx2`, falls back to `httpx` with `StarletteDeprecationWarning`.
  Source: https://github.com/encode/starlette/pull/3291
- `httpx2` is a fork of `httpx 0.28.1` with the same public API; both packages can coexist.
  Source: https://pydantic.dev/docs/httpx2/get-started/migration/
- Warning source in installed package: `starlette/testclient.py` lines 54-58, emitted when `httpx2` is not importable and `httpx` is used.
- `pytest.ini` ignores `DeprecationWarning:starlette.*` and httpx deprecations, but `StarletteDeprecationWarning` inherits from `UserWarning`, so it is not filtered.

## Validation plan
1. **Timezone resolution on Windows**
   - Command: `python -c "from app.tiempo import TZ, hoy; print(TZ, hoy())"`
   - Acceptance: resolves `America/La_Paz` and prints a valid date without `ZoneInfoNotFoundError`.
2. **Dependency consistency**
   - Command: `pip check`
   - Acceptance: no dependency conflicts.
   - Additional: compare declared versions in both manifests against installed distributions.
3. **Targeted TestClient tests**
   - Inspect `tests/` for `TestClient` usage and run relevant modules.
   - Acceptance: no new failures; warning status documented.
4. **Full test suite**
   - Command: `pytest -q`
   - Acceptance: compare against historical `328 passed, 1 StarletteDeprecationWarning`; any regression must be identified.
5. **Render-dependent checks** (NOT RUN locally)
   - Production dependency installation and build.
   - Timezone resolution in deployed container.
   - Application startup and health endpoint.

## Remaining uncertainties
- Whether `httpx2` is currently available in the project's package index and maintained beyond the documented fork.
- Whether Render's base image provides system timezone data; the manifest already declares `tzdata` defensively.
- Whether the historical `328 passed` result still applies; it must be rerun to confirm.

## Recommended next action
Verify availability and exact version of `httpx2` in the configured package index, then decide whether to add it as a development dependency to eliminate the Starlette `TestClient` deprecation warning.