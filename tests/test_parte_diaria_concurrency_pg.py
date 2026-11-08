"""PG-disposable concurrency tests for Phase 2 / 2.2 Policy A (daily tracking).

SAFETY GATE (mandatory): these tests run ONLY when a disposable, isolated
PostgreSQL target is independently verified with Docker+DB evidence.

Independent verification (env vars never independently authorize):
- Docker CLI must be available and able to inspect containers.
- A running container must be found (by cid/name from optional marker hint) and
  independently verified: container id exists, published port is localhost-only
  (127.0.0.1), and live DB identity (current_database/current_user/version)
  corresponds to the connection.
- ``PARTE_DIARIA_TEST_DATABASE_URL`` must target ``localhost``/``127.0.0.1`` only.
- ``PARTE_DIARIA_PG_DISPOSABLE_VERIFIED`` is NOT trusted as proof; it may only
  provide a hint (container/cid/db/user). All claims are re-verified.
- ``PARTE_DIARIA_PG_ALLOW`` is intentionally NOT honored.

If Docker/evidence is unavailable, tests safely skip with BLOCKED.

Test isolation: NO table-wide deletes. Each test creates uniquely identified
users/records, tracks exact IDs, and cleans up only those records (FK-safe),
including on failure.

PostgreSQL is authoritative for ``SELECT ... FOR UPDATE`` and real race
behavior. SQLite tests do NOT prove these properties.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import ParteDiaria, SesionEntrenamiento, User
from app.services import parte_diaria as svc


BLOCKED = "BLOCKED — PostgreSQL target not independently verified as disposable and isolated."
TASK_LABELS = {
    "atletismo.task": "phase2.2.1",
    "atletismo.purpose": "postgres-concurrency-validation",
    "atletismo.disposable": "true",
}
EXPECTED_POSTGRES_IMAGE = "postgres:16"
EXPECTED_CONTAINER_PORT = "5432/tcp"


def _db_url() -> str | None:
    return os.environ.get("PARTE_DIARIA_TEST_DATABASE_URL")


def _parse_verified_marker(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _docker_inspect(container_ref: str) -> dict[str, Any] | None:
    try:
        r = subprocess.run(
            ["docker", "inspect", container_ref],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        return data[0] if data else None
    except Exception:
        return None


def _docker_context_is_local() -> bool:
    """Reject a remote Docker daemon: localhost publish must be this host."""
    try:
        r = subprocess.run(
            ["docker", "context", "inspect"],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(r.stdout) if r.returncode == 0 else []
        host = data[0]["Endpoints"]["docker"]["Host"] if data else ""
        return host.startswith(("npipe://", "unix://"))
    except Exception:
        return False


def _container_labels(info: dict[str, Any]) -> dict[str, str]:
    return (info.get("Config") or {}).get("Labels") or {}


def _has_required_task_labels(info: dict[str, Any]) -> bool:
    labels = _container_labels(info)
    if any(labels.get(k) != v for k, v in TASK_LABELS.items()):
        return False
    if not labels.get("atletismo.instance-id"):
        return False
    if not labels.get("atletismo.database") or not labels.get("atletismo.database-user"):
        return False
    return True


def _find_disposable_container(hint: dict[str, str]) -> dict[str, Any] | None:
    """Use hints only to prioritize; every candidate must carry task labels."""
    for ref in [hint.get("cid"), hint.get("container")]:
        if not ref:
            continue
        info = _docker_inspect(ref)
        if (info and info.get("State", {}).get("Running")
                and _has_required_task_labels(info)):
            return info
    # Search by all fixed task labels. Dynamic identity labels are verified below.
    try:
        cmd = ["docker", "ps"]
        for key, value in TASK_LABELS.items():
            cmd.extend(["--filter", f"label={key}={value}"])
        cmd.extend(["--format", "{{.ID}}"])
        r = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            for cid in r.stdout.strip().splitlines():
                info = _docker_inspect(cid.strip())
                if (info and info.get("State", {}).get("Running")
                        and _has_required_task_labels(info)):
                    return info
    except Exception:
        pass
    return None


def _verify_localhost_only_ports(info: dict[str, Any]) -> dict[str, str]:
    """Require only PG/5432 published, explicitly on 127.0.0.1, consistently."""
    actual = (info.get("NetworkSettings") or {}).get("Ports") or {}
    configured = (info.get("HostConfig") or {}).get("PortBindings") or {}
    if set(actual) != {EXPECTED_CONTAINER_PORT} or set(configured) != {EXPECTED_CONTAINER_PORT}:
        return {}
    actual_entries = actual.get(EXPECTED_CONTAINER_PORT) or []
    configured_entries = configured.get(EXPECTED_CONTAINER_PORT) or []
    if len(actual_entries) != 1 or len(configured_entries) != 1:
        return {}
    a, c = actual_entries[0], configured_entries[0]
    if (a.get("HostIp") != "127.0.0.1" or c.get("HostIp") != "127.0.0.1"
            or not a.get("HostPort") or a.get("HostPort") != c.get("HostPort")):
        return {}
    if not str(a["HostPort"]).isdigit() or not (1 <= int(a["HostPort"]) <= 65535):
        return {}
    return {EXPECTED_CONTAINER_PORT: str(a["HostPort"])}


def _container_env(info: dict[str, Any]) -> dict[str, str]:
    values = (info.get("Config") or {}).get("Env") or []
    out = {}
    for item in values:
        if "=" in item:
            key, value = item.split("=", 1)
            out[key] = value
    return out


def _container_postgres_identity(
    info: dict[str, Any], database: str, owner: str
) -> tuple[str, str, str, int] | None:
    """Read identity via docker exec, without exposing container credentials."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", database) or not re.fullmatch(r"[A-Za-z0-9_]+", owner):
        return False
    cid = info.get("Id")
    if not cid:
        return False
    query = ("SELECT current_database() || '|' || current_user || '|' || "
             "version() || '|' || floor(extract(epoch from pg_postmaster_start_time())*1000000)::bigint")
    try:
        r = subprocess.run(
            ["docker", "exec", cid, "psql", "--no-psqlrc", "-X", "-A", "-t",
             "-U", owner, "-d", database, "-c", query],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return None
        parts = r.stdout.strip().split("|", 3)
        if len(parts) != 4:
            return None
        return parts[0], parts[1], parts[2], int(parts[3])
    except Exception:
        return False


def _independent_gate(url: str, conn) -> dict[str, str]:
    """Independent Docker+DB verification. Raises RuntimeError on failure."""
    if not _docker_available():
        raise RuntimeError(f"{BLOCKED} Docker CLI not available for independent verification.")
    if not _docker_context_is_local():
        raise RuntimeError(f"{BLOCKED} Docker context is not independently verified as local.")

    raw = os.environ.get("PARTE_DIARIA_PG_DISPOSABLE_VERIFIED", "")
    hint = _parse_verified_marker(raw)

    # Independently find and inspect container (do NOT trust marker as proof).
    info = _find_disposable_container(hint)
    if not info:
        raise RuntimeError(f"{BLOCKED} No independently verifiable disposable container found.")

    container_id = info.get("Id", "")
    container_name = (info.get("Name") or "").lstrip("/")
    if not info.get("State", {}).get("Running"):
        raise RuntimeError(f"{BLOCKED} Container not running.")
    if not re.fullmatch(r"[0-9a-f]{64}", container_id):
        raise RuntimeError(f"{BLOCKED} Docker did not return a full container ID.")
    if not _has_required_task_labels(info):
        raise RuntimeError(f"{BLOCKED} Mandatory task-specific Docker labels are missing or invalid.")
    config = info.get("Config") or {}
    labels = _container_labels(info)
    if config.get("Image") != EXPECTED_POSTGRES_IMAGE:
        raise RuntimeError(f"{BLOCKED} Container image is not the expected official {EXPECTED_POSTGRES_IMAGE} image.")
    env = _container_env(info)
    database = labels["atletismo.database"]
    db_user = labels["atletismo.database-user"]
    instance_id = labels["atletismo.instance-id"]
    owner = env.get("POSTGRES_USER", "")
    if (not re.fullmatch(r"atle_test_p2_2_1_[a-z0-9]+", database)
            or not re.fullmatch(r"atle_p2_2_1_[a-z0-9]+", db_user)
            or database != env.get("POSTGRES_DB")
            or not owner or owner == db_user or owner == "postgres"
            or not re.fullmatch(r"atle_owner_[a-z0-9]+", owner)
            or labels.get("atletismo.database-owner") != owner
            or not re.fullmatch(r"p2-2-1-[a-z0-9-]+", instance_id)):
        raise RuntimeError(f"{BLOCKED} Container configuration is not a dedicated task database/user.")

    bindings = _verify_localhost_only_ports(info)
    if not bindings:
        raise RuntimeError(f"{BLOCKED} PostgreSQL is not exclusively published on 127.0.0.1:5432.")

    try:
        parsed = make_url(url)
    except Exception:
        raise RuntimeError(f"{BLOCKED} Test URL could not be safely parsed.") from None
    if parsed.drivername.split("+")[0] not in ("postgres", "postgresql"):
        raise RuntimeError(f"{BLOCKED} Test URL is not PostgreSQL.")
    if parsed.host not in ("127.0.0.1", "localhost"):
        raise RuntimeError(f"{BLOCKED} URL must target localhost/127.0.0.1.")
    if (not parsed.port or parsed.port != int(bindings[EXPECTED_CONTAINER_PORT])
            or parsed.database != database or parsed.username != db_user):
        raise RuntimeError(f"{BLOCKED} URL host port/database/user do not exactly match the inspected task container.")
    if parsed.username == owner:
        raise RuntimeError(f"{BLOCKED} Test connection must use the dedicated non-owner task user.")

    # Live DB identity verification
    row = conn.execute(text("""
        SELECT current_database(), current_user, version(), inet_server_port(),
               (SELECT rolsuper FROM pg_roles WHERE rolname = current_user),
               (SELECT rolcreatedb FROM pg_roles WHERE rolname = current_user),
               (SELECT rolcreaterole FROM pg_roles WHERE rolname = current_user),
               (SELECT shobj_description(oid, 'pg_database')
                FROM pg_database WHERE datname = current_database()),
               floor(extract(epoch from pg_postmaster_start_time()) * 1000000)::bigint
    """)).first()
    if not row:
        raise RuntimeError(BLOCKED)
    (live_db, live_user, version, server_port, is_superuser,
     can_create_db, can_create_role, db_comment, start_usec) = row
    version = str(version or "")
    if (live_db != database or live_user != db_user or int(server_port or 0) != 5432
            or bool(is_superuser) or bool(can_create_db) or bool(can_create_role)
            or not re.search(r"PostgreSQL\s+16\.", version)
            or db_comment != f"atletismo-validation:{instance_id}"):
        raise RuntimeError(f"{BLOCKED} Live database/user/version/task identity does not match inspected container labels/configuration.")
    container_identity = _container_postgres_identity(info, database, owner)
    if (container_identity is None or container_identity[0] != live_db
            or container_identity[2] != version or container_identity[3] != int(start_usec or 0)):
        raise RuntimeError(f"{BLOCKED} Live connection could not be tied to the inspected PostgreSQL container instance.")
    # The docker-exec user is the unique database owner; the test connection uses
    # a separate non-superuser role scoped to the same task database.
    if container_identity[1] != owner:
        raise RuntimeError(f"{BLOCKED} Container-side PostgreSQL owner identity did not match its config.")
    if not start_usec:
        raise RuntimeError(f"{BLOCKED} PostgreSQL server identity query was incomplete.")

    for key, expected in (("cid", container_id), ("db", database),
                          ("user", db_user), ("instance", instance_id)):
        if hint.get(key) and hint[key] != expected:
            raise RuntimeError(f"{BLOCKED} Optional hint {key!r} contradicts independently inspected evidence.")

    return {
        "container": container_name,
        "cid": container_id,
        "image": config.get("Image", ""),
        "postgres_version": version,
        "bind": f"127.0.0.1:{bindings[EXPECTED_CONTAINER_PORT]}->{EXPECTED_CONTAINER_PORT}",
        "db": live_db,
        "user": live_user,
        "instance": instance_id,
        "localhost_only": "true",
        "verified_independently": "true",
    }


@dataclass
class CreatedRecords:
    session_ids: list[int] = field(default_factory=list)
    parte_ids: list[int] = field(default_factory=list)
    user_ids: list[int] = field(default_factory=list)

    def cleanup(self, engine) -> None:
        with Session(engine) as db:
            try:
                if self.session_ids:
                    db.execute(delete(SesionEntrenamiento).where(SesionEntrenamiento.id.in_(self.session_ids)))
                if self.parte_ids:
                    db.execute(delete(ParteDiaria).where(ParteDiaria.id.in_(self.parte_ids)))
                if self.user_ids:
                    db.execute(delete(User).where(User.id.in_(self.user_ids)))
                db.commit()
            except Exception:
                db.rollback()
                try:
                    with Session(engine) as db2:
                        if self.parte_ids:
                            db2.execute(delete(ParteDiaria).where(ParteDiaria.id.in_(self.parte_ids)))
                        if self.user_ids:
                            db2.execute(delete(User).where(User.id.in_(self.user_ids)))
                        db2.commit()
                except Exception:
                    pass

    def track_parte(self, parte: ParteDiaria | None) -> None:
        if parte and parte.id and parte.id not in self.parte_ids:
            self.parte_ids.append(parte.id)
            for s in (parte.sesiones or []):
                if s.id and s.id not in self.session_ids:
                    self.session_ids.append(s.id)

    def refresh_sessions(self, engine) -> None:
        if not self.parte_ids:
            return
        with Session(engine) as db:
            ids = db.execute(
                select(SesionEntrenamiento.id).where(SesionEntrenamiento.parte_diaria_id.in_(self.parte_ids))
            ).scalars().all()
            for i in ids:
                if i not in self.session_ids:
                    self.session_ids.append(i)


@pytest.fixture(scope="module")
def pg_engine():
    url = _db_url()
    if not url:
        pytest.skip(BLOCKED + " No PARTE_DIARIA_TEST_DATABASE_URL.")
    if not url.startswith("postgresql"):
        pytest.skip(BLOCKED + " URL is not PostgreSQL.")
    low = url.lower()
    if not ("@127.0.0.1" in low or "@localhost" in low):
        pytest.skip(BLOCKED + " URL not localhost.")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as c:
            marker = _independent_gate(url, c)
    except RuntimeError as e:
        pytest.skip(str(e))
    except Exception as e:
        pytest.skip(f"{BLOCKED} Cannot connect/verify: {type(e).__name__}.")
    Base.metadata.create_all(engine, tables=[User.__table__, ParteDiaria.__table__, SesionEntrenamiento.__table__])
    engine._atle_marker = marker  # type: ignore[attr-defined]
    yield engine
    engine.dispose()


@pytest.fixture
def pg_session_factory(pg_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)


@pytest.fixture
def tracked(pg_engine):
    rec = CreatedRecords()
    try:
        yield rec
    finally:
        rec.refresh_sessions(pg_engine)
        rec.cleanup(pg_engine)


def _unique_username(prefix: str) -> str:
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _create_user(SessionF, username_prefix: str, tracked: CreatedRecords) -> int:
    from app.auth import hash_password
    db = SessionF()
    try:
        u = User(username=_unique_username(username_prefix), role="atleta", hashed_password=hash_password("x"))
        db.add(u)
        db.commit()
        db.refresh(u)
        tracked.user_ids.append(u.id)
        return u.id
    finally:
        db.close()


def _payload(**overrides):
    base = {
        "sueno_calidad": 7, "horas_sueno": "7.5", "fatiga": 4, "dolor_muscular": 3,
        "estres": 4, "animo": 8, "hay_molestia": False, "sintomas_enfermedad": False,
        "entreno_hoy": False, "sessions": [],
    }
    base.update(overrides)
    return base


def _session(**overrides):
    base = {
        "orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45,
        "rpe": 6, "comentarios_entrenamiento": None,
    }
    base.update(overrides)
    return base


def _wait_for_lock(
    pg_engine,
    *,
    waiting_for_pid: int,
    blocking_pid: int,
    table_name: str = "partes_diarios",
    timeout_s: float = 15.0,
) -> dict[str, Any] | None:
    """Poll PostgreSQL until the named backend is blocked by the expected PID."""
    import time
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with pg_engine.connect() as c:
            row = c.execute(text("""
                SELECT blocked.pid AS waiting_pid,
                       pg_blocking_pids(blocked.pid) AS blocking_pids,
                       blocked.query AS blocked_query,
                       blocked.wait_event_type,
                       blocked.wait_event,
                       blocked.state
                FROM pg_stat_activity AS blocked
                WHERE blocked.pid = :waiting_pid
                  AND blocked.state = 'active'
                  AND blocked.wait_event_type = 'Lock'
                  AND blocked.query ILIKE '%' || :tname || '%'
                  AND blocked.query ILIKE '%FOR UPDATE%'
                  AND :blocking_pid = ANY(pg_blocking_pids(blocked.pid))
            """), {"waiting_pid": waiting_for_pid, "blocking_pid": blocking_pid,
                  "tname": table_name}).mappings().first()
            if row:
                return dict(row)
        time.sleep(0.05)
    return None


def _backend_pid(db: Session) -> int:
    return int(db.execute(text("select pg_backend_pid()")).scalar_one())


def _gate_fixture():
    instance = "p2-2-1-20261108-a1b2c3"
    database = "atle_test_p2_2_1_a1b2c3"
    test_user = "atle_p2_2_1_a1b2c3"
    owner = "atle_owner_a1b2c3"
    port = "55441"
    info = {
        "Id": "a" * 64,
        "Name": "/atletismo-pg-p2-2-1-a1b2c3",
        "State": {"Running": True},
        "Config": {
            "Image": EXPECTED_POSTGRES_IMAGE,
            "Labels": {
                **TASK_LABELS,
                "atletismo.instance-id": instance,
                "atletismo.database": database,
                "atletismo.database-user": test_user,
                "atletismo.database-owner": owner,
            },
            "Env": [f"POSTGRES_DB={database}", f"POSTGRES_USER={owner}"],
        },
        "HostConfig": {"PortBindings": {EXPECTED_CONTAINER_PORT: [
            {"HostIp": "127.0.0.1", "HostPort": port},
        ]}},
        "NetworkSettings": {"Ports": {EXPECTED_CONTAINER_PORT: [
            {"HostIp": "127.0.0.1", "HostPort": port},
        ]}},
    }
    row = (
        database, test_user, "PostgreSQL 16.15 (Debian)", 5432, False,
        False, False, f"atletismo-validation:{instance}", 1794000000000000,
    )
    return info, row, (database, owner, row[2], row[8]), test_user, port


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeConnection:
    def __init__(self, row):
        self.row = row

    def execute(self, *_args, **_kwargs):
        return _FakeResult(self.row)


def _patch_valid_gate(monkeypatch, info, row, owner_identity):
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_docker_available", lambda: True)
    monkeypatch.setattr(module, "_docker_context_is_local", lambda: True)
    monkeypatch.setattr(module, "_find_disposable_container", lambda _hint: info)
    monkeypatch.setattr(module, "_container_postgres_identity", lambda *_args: owner_identity)
    monkeypatch.delenv("PARTE_DIARIA_PG_DISPOSABLE_VERIFIED", raising=False)
    return _FakeConnection(row)


def test_gate_accepts_only_matching_labeled_local_task_database(monkeypatch):
    info, row, owner_identity, test_user, port = _gate_fixture()
    conn = _patch_valid_gate(monkeypatch, info, row, owner_identity)
    result = _independent_gate(
        f"postgresql://{test_user}:unused@127.0.0.1:{port}/atle_test_p2_2_1_a1b2c3", conn
    )
    assert result["verified_independently"] == "true"
    assert result["cid"] == "a" * 64
    assert result["bind"] == f"127.0.0.1:{port}->5432/tcp"


def test_gate_rejects_marker_or_allow_environment_as_standalone_proof(monkeypatch):
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_docker_available", lambda: True)
    monkeypatch.setattr(module, "_docker_context_is_local", lambda: True)
    monkeypatch.setattr(module, "_find_disposable_container", lambda _hint: None)
    monkeypatch.setenv("PARTE_DIARIA_PG_DISPOSABLE_VERIFIED", "cid=" + "a" * 64 + ";db=atle_test_p2_2_1_fake;user=atle_p2_2_1_fake")
    monkeypatch.setenv("PARTE_DIARIA_PG_ALLOW", "1")
    with pytest.raises(RuntimeError, match="No independently verifiable"):
        _independent_gate("postgresql://fake:fake@127.0.0.1:55441/atle_test_p2_2_1_fake", _FakeConnection(None))


@pytest.mark.parametrize("label,wrong", [
    ("atletismo.task", "phase2.2"),
    ("atletismo.purpose", "generic-postgres"),
    ("atletismo.disposable", "false"),
])
def test_gate_rejects_missing_or_wrong_task_labels(monkeypatch, label, wrong):
    info, row, owner_identity, test_user, port = _gate_fixture()
    info["Config"]["Labels"][label] = wrong
    conn = _patch_valid_gate(monkeypatch, info, row, owner_identity)
    with pytest.raises(RuntimeError, match="Mandatory task-specific Docker labels"):
        _independent_gate(f"postgresql://{test_user}:unused@127.0.0.1:{port}/{row[0]}", conn)


@pytest.mark.parametrize("host_ip,host_port", [("0.0.0.0", "55441"), ("::1", "55441"), ("127.0.0.1", "55442")])
def test_gate_rejects_non_loopback_or_wrong_published_port(monkeypatch, host_ip, host_port):
    info, row, owner_identity, test_user, _port = _gate_fixture()
    entry = {"HostIp": host_ip, "HostPort": host_port}
    info["HostConfig"]["PortBindings"][EXPECTED_CONTAINER_PORT] = [entry]
    info["NetworkSettings"]["Ports"][EXPECTED_CONTAINER_PORT] = [entry]
    conn = _patch_valid_gate(monkeypatch, info, row, owner_identity)
    url_port = "55441" if host_ip == "127.0.0.1" else host_port
    with pytest.raises(RuntimeError):
        _independent_gate(f"postgresql://{test_user}:unused@127.0.0.1:{url_port}/{row[0]}", conn)


@pytest.mark.parametrize("field,value", [(0, "other_db"), (1, "postgres"), (4, True), (5, "unmarked")])
def test_gate_rejects_shared_or_mismatched_live_database_identity(monkeypatch, field, value):
    info, row, owner_identity, test_user, port = _gate_fixture()
    changed = list(row)
    changed[field] = value
    conn = _patch_valid_gate(monkeypatch, info, tuple(changed), owner_identity)
    with pytest.raises(RuntimeError, match="Live database/user/version/task identity"):
        _independent_gate(f"postgresql://{test_user}:unused@127.0.0.1:{port}/{row[0]}", conn)


@pytest.mark.parametrize("host,port,database,user", [
    ("localhost", 55442, "atle_test_p2_2_1_a1b2c3", "atle_p2_2_1_a1b2c3"),
    ("192.168.0.10", 55441, "atle_test_p2_2_1_a1b2c3", "atle_p2_2_1_a1b2c3"),
    ("127.0.0.1", 55441, "atle_test_p2_2_1_other", "atle_p2_2_1_a1b2c3"),
    ("127.0.0.1", 55441, "atle_test_p2_2_1_a1b2c3", "postgres"),
])
def test_gate_requires_exact_url_host_port_database_and_user(monkeypatch, host, port, database, user):
    info, row, owner_identity, _test_user, _actual_port = _gate_fixture()
    conn = _patch_valid_gate(monkeypatch, info, row, owner_identity)
    url = f"postgresql://{user}:unused@{host}:{port}/{database}"
    with pytest.raises(RuntimeError):
        _independent_gate(url, conn)


def test_gate_rejects_wrong_postgres_image(monkeypatch):
    info, row, owner_identity, test_user, port = _gate_fixture()
    info["Config"]["Image"] = "postgres:latest"
    conn = _patch_valid_gate(monkeypatch, info, row, owner_identity)
    with pytest.raises(RuntimeError, match="expected official postgres:16"):
        _independent_gate(f"postgresql://{test_user}:unused@127.0.0.1:{port}/{row[0]}", conn)


@pytest.mark.pg
def test_pg_gate_reports_independently_verified_identity(pg_engine):
    marker = getattr(pg_engine, "_atle_marker", {})
    assert marker.get("verified_independently") == "true"
    assert marker.get("localhost_only") == "true"
    assert marker.get("db") and marker.get("user") and marker.get("cid")
    print("PG_GATE_VERIFIED " + json.dumps(marker, sort_keys=True))


@pytest.mark.pg
def test_pg_stale_update_deterministic_lock_wait_proof_no_overwrite(pg_session_factory, pg_engine, tracked):
    """Policy A with DB-level lock-wait proof: tx1 holds FOR UPDATE, tx2's service save
    blocks waiting on that lock (proven via pg_locks), tx1 commits, tx2 reloads fresh
    state, detects stale token, returns conflict, DB keeps tx1's value."""
    atleta_id = _create_user(pg_session_factory, "stlk", tracked)
    fecha = date(2026, 11, 8)

    setup = pg_session_factory()
    try:
        r0 = svc.save_daily_record(setup, atleta_id=atleta_id, payload=_payload(animo=5), fecha=fecha)
        assert r0.ok and r0.parte
        tracked.track_parte(r0.parte)
        stale_token = r0.edit_state_token
    finally:
        setup.close()

    ready = threading.Barrier(3)
    tx1_locked = threading.Event()
    tx1_pid_box: dict[str, int] = {}
    tx2_pid_box: dict[str, int] = {}
    release_tx1 = threading.Event()
    tx2_started = threading.Event()
    results: dict[str, Any] = {}
    exc: dict[str, Exception] = {}

    def tx1():
        db = pg_session_factory()
        try:
            ready.wait(timeout=15)
            tx1_pid_box["pid"] = _backend_pid(db)
            parte = svc.load_today_for_update(db, atleta_id, fecha)
            assert parte is not None
            tracked.track_parte(parte)
            tx1_locked.set()
            assert release_tx1.wait(timeout=20)
            parte.animo = 7
            db.commit()
            results["tx1"] = "committed"
        except Exception as e:
            exc["tx1"] = e
            try: db.rollback()
            except Exception: pass
        finally:
            db.close()

    def tx2():
        db = pg_session_factory()
        try:
            ready.wait(timeout=15)
            assert tx1_locked.wait(timeout=15)
            tx2_pid_box["pid"] = _backend_pid(db)
            tx2_started.set()
            # save_daily_record will do FOR UPDATE and block while tx1 holds the lock.
            r = svc.save_daily_record(
                db, atleta_id=atleta_id, payload=_payload(animo=9),
                edit_state_token=stale_token, fecha=fecha,
            )
            results["tx2"] = r
            tracked.track_parte(r.parte)
        except Exception as e:
            exc["tx2"] = e
        finally:
            db.close()

    th1 = threading.Thread(target=tx1, name="tx1-lock-holder")
    th2 = threading.Thread(target=tx2, name="tx2-stale-writer")
    th1.start(); th2.start()
    ready.wait(timeout=15)
    assert tx1_locked.wait(timeout=15)
    assert tx2_started.wait(timeout=15)

    tx1_pid = tx1_pid_box.get("pid")
    tx2_pid = tx2_pid_box.get("pid")
    try:
        assert tx1_pid and tx2_pid and tx1_pid != tx2_pid
        # Exact DB-level evidence: this test's tx2 backend is actively waiting on
        # a FOR UPDATE query of the target table and PostgreSQL names tx1 as blocker.
        lock_evidence = _wait_for_lock(
            pg_engine,
            waiting_for_pid=tx2_pid,
            blocking_pid=tx1_pid,
            table_name="partes_diarios",
            timeout_s=15,
        )
        assert lock_evidence is not None, (
            f"Expected tx2 PID {tx2_pid} to be blocked by tx1 PID {tx1_pid}; no exact pg_stat_activity/pg_blocking_pids evidence."
        )
        assert lock_evidence["waiting_pid"] == tx2_pid
        assert tx1_pid in lock_evidence["blocking_pids"]
        results["lock_evidence"] = lock_evidence
        print(
            "PG_LOCK_PROOF " + json.dumps({
                "tx1_pid": tx1_pid,
                "tx2_pid": tx2_pid,
                "waiting_pid": lock_evidence["waiting_pid"],
                "blocking_pids": lock_evidence["blocking_pids"],
                "wait_event_type": lock_evidence["wait_event_type"],
                "wait_event": lock_evidence["wait_event"],
                "query": lock_evidence["blocked_query"],
            }, sort_keys=True)
        )
    finally:
        # Always release tx1, even if the evidence assertion fails.
        release_tx1.set()

    th1.join(timeout=25); th2.join(timeout=25)
    assert not th1.is_alive() and not th2.is_alive(), "Lock test worker did not exit after release."
    assert not exc, f"Unexpected errors: {exc}"
    r2 = results["tx2"]
    assert not r2.ok and r2.status == svc.STATUS_CONFLICT and r2.stale, (
        f"Expected stale conflict after lock release+fresh reload, got: ok={r2.ok} status={r2.status} stale={r2.stale}"
    )

    check = pg_session_factory()
    try:
        row = check.execute(select(ParteDiaria).where(ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == fecha)).scalar_one()
        assert row.animo == 7, f"Stale write overwrote tx1: animo={row.animo}"
        print("PG_STALE_RESULT " + json.dumps({
            "tx1": results.get("tx1"),
            "tx2_status": r2.status,
            "tx2_conflict": r2.conflict,
            "tx2_stale": r2.stale,
            "persisted_animo": row.animo,
        }, sort_keys=True))
    finally:
        check.close()


@pytest.mark.pg
def test_pg_service_level_create_race_integrity_error_conflict_no_dup(pg_session_factory, tracked):
    """Deterministic service-level create race: both threads observe missing and enter
    the create path, synchronize before insert, actual unique constraint fires on
    commit in the losing service call, service catches IntegrityError -> rollback
    -> reload -> conflict. Exactly 1 complete row, no partial/dup/blind reapply."""
    atleta_id = _create_user(pg_session_factory, "svrace", tracked)
    fecha = date(2026, 11, 8)

    both_observed_missing = threading.Barrier(2, timeout=15)
    proceed_to_insert = threading.Barrier(2, timeout=15)
    outcomes: list[dict[str, Any]] = []
    ol = threading.Lock()
    hook_calls = {"observed": 0, "before_insert": 0, "integrity_error": 0}
    integrity_error_types: list[type[BaseException]] = []
    hl = threading.Lock()

    def after_observed(db, aid, f):
        with hl:
            hook_calls["observed"] += 1
        both_observed_missing.wait()

    def before_insert(db, instance):
        with hl:
            hook_calls["before_insert"] += 1
        # Service calls this before the flush that issues the parent INSERT.
        proceed_to_insert.wait()

    def on_create_integrity_error(db, aid, f, exc):
        assert aid == atleta_id and f == fecha
        assert isinstance(exc, IntegrityError)
        with hl:
            hook_calls["integrity_error"] += 1
            integrity_error_types.append(type(exc))

    def racer(animo: int):
        db = pg_session_factory()
        try:
            r = svc.save_daily_record(
                db, atleta_id=atleta_id,
                payload=_payload(animo=animo, entreno_hoy=True,
                                 sessions=[_session(duracion_min=30, rpe=animo)]),
                fecha=fecha,
                _test_after_create_observed_missing=after_observed,
                _test_before_create_insert=before_insert,
                _test_on_create_integrity_error=on_create_integrity_error,
            )
            tracked.track_parte(r.parte)
            with ol:
                outcomes.append({
                    "ok": r.ok, "status": r.status, "conflict": r.conflict,
                    "stale": r.stale, "parte_id": r.parte.id if r.parte else None,
                    "animo": r.parte.animo if r.parte else None,
                    "session_ids": [s.id for s in (r.parte.sesiones if r.parte else [])],
                })
        except Exception as e:
            with ol:
                outcomes.append({"ok": False, "status": "exception", "error": f"{type(e).__name__}: {e}"})
        finally:
            db.close()

    t1 = threading.Thread(target=racer, args=(5,))
    t2 = threading.Thread(target=racer, args=(8,))
    t1.start(); t2.start(); t1.join(timeout=25); t2.join(timeout=25)

    assert len(outcomes) == 2, outcomes
    assert not any(o["status"] == "exception" for o in outcomes), outcomes
    # Both must have gone through the service create path hooks.
    assert hook_calls["observed"] == 2, f"Expected both service calls to observe missing: {hook_calls}"
    assert hook_calls["before_insert"] == 2, f"Expected both service calls to reach create insert seam: {hook_calls}"
    assert hook_calls["integrity_error"] == 1, f"Expected the losing service call to reach the actual IntegrityError handler: {hook_calls}"
    assert integrity_error_types == [IntegrityError]

    ok = [o for o in outcomes if o["ok"]]
    conflicts = [o for o in outcomes if o["status"] == svc.STATUS_CONFLICT and o["conflict"]]
    assert len(ok) == 1, f"Expected exactly 1 service success, got: {outcomes}"
    assert len(conflicts) == 1, f"Expected exactly 1 service conflict (IntegrityError handled), got: {outcomes}"
    assert ok[0]["parte_id"] == conflicts[0]["parte_id"], "loser must reload and return the committed winner row"
    assert ok[0]["animo"] == conflicts[0]["animo"], "loser must not reapply or overwrite the winner's values"
    assert len(ok[0]["session_ids"]) == 1 and conflicts[0]["session_ids"] == ok[0]["session_ids"]
    print("PG_CREATE_RACE " + json.dumps({
        "observed_missing": hook_calls["observed"],
        "pre_insert_hook_calls": hook_calls["before_insert"],
        "integrity_error_handler_calls": hook_calls["integrity_error"],
        "integrity_error_type": integrity_error_types[0].__name__,
        "winner": ok[0],
        "loser": conflicts[0],
    }, sort_keys=True))

    check = pg_session_factory()
    try:
        rows = check.execute(select(ParteDiaria).where(ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == fecha)).scalars().all()
        assert len(rows) == 1, f"Expected exactly 1 row, got {len(rows)}"
        tracked.track_parte(rows[0])
        tracked.refresh_sessions(pg_session_factory.kw["bind"])
        check.refresh(rows[0])
        assert rows[0].atleta_id == atleta_id and rows[0].fecha == fecha
        assert rows[0].sueno_calidad == 7 and rows[0].horas_sueno is not None
        assert rows[0].fatiga is not None and rows[0].dolor_muscular is not None
        assert rows[0].estres is not None and rows[0].animo in (5, 8)
        assert rows[0].entreno_hoy is True
        assert len(rows[0].sesiones) == 1
        assert rows[0].sesiones[0].carga_sesion == rows[0].sesiones[0].duracion_min * rows[0].sesiones[0].rpe
    finally:
        check.close()


@pytest.mark.pg
def test_pg_raw_db_create_race_integrity_error_authority(pg_session_factory, tracked):
    """Supplementary: proves the DB unique constraint is the race authority at the
    raw insert level (IntegrityError), independent of service seam behavior."""
    atleta_id = _create_user(pg_session_factory, "dbrr", tracked)
    fecha = date(2026, 11, 8)
    b = threading.Barrier(2, timeout=15)
    raw: list[Any] = []
    rl = threading.Lock()

    def raw_insert(animo):
        db = pg_session_factory()
        try:
            _ = db.execute(select(ParteDiaria).where(ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == fecha)).first()
            b.wait()
            p = ParteDiaria(atleta_id=atleta_id, fecha=fecha, sueno_calidad=7, fatiga=4, dolor_muscular=3, estres=4, animo=animo,
                            horas_sueno=7.5, hay_molestia=False, sintomas_enfermedad=False, entreno_hoy=False)
            db.add(p)
            db.commit()
            with rl: raw.append(("ok", p.id))
        except IntegrityError:
            db.rollback()
            with rl: raw.append(("integrity", None))
        except Exception as e:
            try: db.rollback()
            except Exception: pass
            with rl: raw.append(("err", type(e).__name__))
        finally:
            db.close()

    t1 = threading.Thread(target=raw_insert, args=(3,))
    t2 = threading.Thread(target=raw_insert, args=(4,))
    t1.start(); t2.start(); t1.join(20); t2.join(20)
    assert len(raw) == 2
    kinds = [x[0] for x in raw]
    check = pg_session_factory()
    try:
        rows = check.execute(select(ParteDiaria).where(ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == fecha)).scalars().all()
        assert len(rows) == 1
        tracked.track_parte(rows[0])
    finally:
        check.close()
    assert kinds.count("ok") >= 1
    # True insert race => ok+integrity; serialized snapshot timing may yield one ok only,
    # but unique constraint remains authoritative (1 row). Documented.
    assert ("integrity" in kinds) or (kinds.count("ok") == 1)


@pytest.mark.pg
def test_pg_discard_under_concurrent_modification_conflict_sessions_preserved(pg_session_factory, tracked):
    """Stale discard must conflict and never silently delete sessions modified by another tx."""
    atleta_id = _create_user(pg_session_factory, "disc", tracked)
    fecha = date(2026, 11, 8)

    setup = pg_session_factory()
    try:
        r1 = svc.save_daily_record(
            setup, atleta_id=atleta_id,
            payload=_payload(entreno_hoy=True, sessions=[_session(rpe=5, duracion_min=45)]),
            fecha=fecha,
        )
        assert r1.ok and r1.parte and len(r1.parte.sesiones) == 1
        tracked.track_parte(r1.parte)
        tracked.refresh_sessions(pg_session_factory.kw["bind"])
        intent = svc.save_daily_record(
            setup, atleta_id=atleta_id, payload=_payload(entreno_hoy=False),
            edit_state_token=r1.edit_state_token, fecha=fecha,
        )
        assert not intent.ok and intent.discard_token
        discard_tok = intent.discard_token
    finally:
        setup.close()

    mod = pg_session_factory()
    try:
        parte, et, _ = svc.get_today_state(mod, atleta_id, fecha)
        assert parte and et
        tracked.track_parte(parte)
        rmut = svc.save_daily_record(
            mod, atleta_id=atleta_id,
            payload=_payload(entreno_hoy=True, sessions=[{"id": parte.sesiones[0].id, **_session(rpe=9, duracion_min=45, orden=1)}]),
            edit_state_token=et, fecha=fecha, allow_full_session_replacement=True,
        )
        assert rmut.ok and rmut.parte.sesiones[0].rpe == 9
        tracked.track_parte(rmut.parte)
        tracked.refresh_sessions(pg_session_factory.kw["bind"])
    finally:
        mod.close()

    disc = pg_session_factory()
    try:
        parte_cur, et_cur, _ = svc.get_today_state(disc, atleta_id, fecha)
        rdisc = svc.save_daily_record(
            disc, atleta_id=atleta_id, payload=_payload(entreno_hoy=False),
            edit_state_token=et_cur, discard_token=discard_tok, confirm_discard_sessions=True, fecha=fecha,
        )
        tracked.track_parte(rdisc.parte)
        assert not rdisc.ok and rdisc.status == svc.STATUS_CONFLICT and rdisc.stale
    finally:
        disc.close()

    verify = pg_session_factory()
    try:
        row = verify.execute(select(ParteDiaria).where(ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == fecha)).scalar_one()
        tracked.track_parte(row)
        tracked.refresh_sessions(pg_session_factory.kw["bind"])
        verify.refresh(row)
        assert row.entreno_hoy is True
        sess = verify.execute(select(SesionEntrenamiento).where(SesionEntrenamiento.parte_diaria_id == row.id)).scalars().all()
        assert len(sess) == 1 and sess[0].rpe == 9
        print("PG_DISCARD_STALE " + json.dumps({
            "status": rdisc.status,
            "conflict": rdisc.conflict,
            "stale": rdisc.stale,
            "entreno_hoy_preserved": row.entreno_hoy,
            "session_count_preserved": len(sess),
            "persisted_rpe": sess[0].rpe,
        }, sort_keys=True))
    finally:
        verify.close()
