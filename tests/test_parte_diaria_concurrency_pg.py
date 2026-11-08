"""PG-disposable concurrency tests for Phase 2 Policy A (daily tracking).

These tests require a VERIFIED disposable PostgreSQL database, isolated from
production/staging/shared environments. They are skipped unless
``PARTE_DIARIA_TEST_DATABASE_URL`` is set to an explicitly disposable target.

Safety: the fixture refuses URLs that do not look disposable (must include a
local/localhost host and a database name containing ``test`` or ``disposable``;
override with ``PARTE_DIARIA_PG_ALLOW=I_UNDERSTAND_DISPOSABLE_ONLY`` at your own
risk — not recommended).

PostgreSQL is authoritative for ``SELECT ... FOR UPDATE`` and real race
behavior. SQLite tests do NOT prove these properties.
"""
from __future__ import annotations

import os
import threading
from datetime import date

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ParteDiaria, User
from app.services import parte_diaria as svc


def _db_url() -> str | None:
    return os.environ.get("PARTE_DIARIA_TEST_DATABASE_URL") or os.environ.get(
        "TEST_DATABASE_URL"
    )


def _assert_disposable(url: str) -> None:
    if os.environ.get("PARTE_DIARIA_PG_ALLOW") == "I_UNDERSTAND_DISPOSABLE_ONLY":
        return
    low = url.lower()
    if "supabase" in low or "render.com" in low or "amazonaws" in low or "neon.tech" in low:
        raise RuntimeError("Refusing PG URL that looks non-disposable/shared.")
    # Must target localhost/127.0.0.1 and a test/disposable database name.
    if not ("localhost" in low or "127.0.0.1" in low):
        raise RuntimeError("PG concurrency tests require localhost/127.0.0.1 disposable DB.")
    if "test" not in low and "disposable" not in low and "migval" not in low:
        raise RuntimeError(
            "PG DB name must indicate disposable/test (e.g. contains 'test', 'disposable', or 'migval')."
        )


@pytest.fixture(scope="module")
def pg_engine():
    url = _db_url()
    if not url:
        pytest.skip(
            "BLOCKED: no disposable PG URL (set PARTE_DIARIA_TEST_DATABASE_URL to a verified localhost test DB)."
        )
    if not url.startswith("postgresql"):
        pytest.skip("BLOCKED: PARTE_DIARIA_TEST_DATABASE_URL must be PostgreSQL.")
    _assert_disposable(url)
    engine = create_engine(url)
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"BLOCKED: cannot connect to disposable PG: {e}")
    # Ensure only relevant tables exist cleanly (Phase 1 schema must be present).
    Base.metadata.create_all(engine, tables=[User.__table__, ParteDiaria.__table__])
    # SesionEntrenamiento table
    from app.models import SesionEntrenamiento

    Base.metadata.create_all(engine, tables=[SesionEntrenamiento.__table__])
    yield engine
    engine.dispose()


@pytest.fixture
def pg_session_factory(pg_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)


@pytest.fixture
def clean_day(pg_engine):
    # Clean tables for deterministic tests
    with pg_engine.begin() as c:
        c.execute(text("DELETE FROM sesiones_entrenamiento"))
        c.execute(text("DELETE FROM partes_diarios"))
        c.execute(text("DELETE FROM users"))
    yield


def _create_user(Session, username="ath"):
    from app.auth import hash_password

    db = Session()
    try:
        u = User(username=username, role="atleta", hashed_password=hash_password("x"))
        db.add(u)
        db.commit()
        db.refresh(u)
        return u.id
    finally:
        db.close()


def _payload(**overrides):
    base = {
        "sueno_calidad": 7,
        "horas_sueno": "7.5",
        "fatiga": 4,
        "dolor_muscular": 3,
        "estres": 4,
        "animo": 8,
        "hay_molestia": False,
        "sintomas_enfermedad": False,
        "entreno_hoy": False,
        "sessions": [],
    }
    base.update(overrides)
    return base


def _session(**overrides):
    base = {
        "orden": 1,
        "tipo_entrenamiento": "resistencia",
        "duracion_min": 45,
        "rpe": 6,
    }
    base.update(overrides)
    return base


@pytest.mark.pg
def test_pg_stale_update_conflict_no_overwrite(pg_session_factory, clean_day):
    atleta_id = _create_user(pg_session_factory, "pgstale")
    fecha = date(2026, 11, 8)
    db = pg_session_factory()
    try:
        r1 = svc.save_daily_record(db, atleta_id=atleta_id, payload=_payload(animo=5), fecha=fecha)
        assert r1.ok
        tok1 = r1.edit_state_token
        r2 = svc.save_daily_record(db, atleta_id=atleta_id, payload=_payload(animo=7), edit_state_token=tok1, fecha=fecha)
        assert r2.ok
        # stale
        r3 = svc.save_daily_record(db, atleta_id=atleta_id, payload=_payload(animo=9), edit_state_token=tok1, fecha=fecha)
        assert not r3.ok and r3.status == svc.STATUS_CONFLICT and r3.stale
        db.expire_all()
        row = db.execute(select(ParteDiaria).where(ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == fecha)).scalar_one()
        assert row.animo == 7
    finally:
        db.close()


@pytest.mark.pg
def test_pg_create_race_conflict_no_dup(pg_session_factory, clean_day):
    atleta_id = _create_user(pg_session_factory, "pgrace")
    fecha = date(2026, 11, 8)
    barrier = threading.Barrier(2)
    results = [None, None]
    errors = []

    def worker(i, animo):
        db = pg_session_factory()
        try:
            # best-effort race: barrier + immediate save
            barrier.wait(timeout=10)
            results[i] = svc.save_daily_record(db, atleta_id=atleta_id, payload=_payload(animo=animo), fecha=fecha)
        except Exception as e:
            errors.append(e)
        finally:
            db.close()

    t1 = threading.Thread(target=worker, args=(0, 5))
    t2 = threading.Thread(target=worker, args=(1, 8))
    t1.start(); t2.start(); t1.join(); t2.join()
    assert not errors
    ok = [r for r in results if r and r.ok]
    conflicts = [r for r in results if r and r.status == svc.STATUS_CONFLICT]
    # At least one succeeds; the other must be conflict or (if serialized) also succeed only if different design - but unique+conflict policy means exactly 1 row.
    db = pg_session_factory()
    try:
        count = db.execute(select(ParteDiaria).where(ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == fecha)).scalars().all()
        assert len(count) == 1
    finally:
        db.close()
    assert len(ok) >= 1
    assert len(ok) + len(conflicts) == 2
