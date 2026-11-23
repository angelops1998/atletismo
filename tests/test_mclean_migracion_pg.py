"""Complete Alembic-chain test; only a separately verified disposable PG is used.

All DDL and data are in a uniquely named schema and an outer transaction that is
always rolled back. No URL, environment flag, or schema name alone proves safety.
"""
import importlib.util
import uuid
from datetime import date
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from test_parte_diaria_concurrency_pg import BLOCKED, _db_url, _independent_gate
from app.services import parte_diaria as svc

pytestmark = pytest.mark.pg
VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"
CHAIN = ("d61e48816ec5", "a3f1c9e27b04", "c4b8e2d91f07", "b67a104e9c32", "e8a4f670c11d", "f2a7c94b1d30")


def _upgrade(revision, conn, monkeypatch):
    paths = list(VERSIONS.glob(revision + "_*.py"))
    assert len(paths) == 1
    spec = importlib.util.spec_from_file_location("migration_" + revision, paths[0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(conn)))
    module.upgrade()
    return module


@pytest.fixture
def isolated_connection():
    url = _db_url()
    if not url:
        pytest.skip(BLOCKED + " No PARTE_DIARIA_TEST_DATABASE_URL.")
    try:
        parsed = make_url(url)
        if parsed.get_backend_name() != "postgresql" or parsed.host not in ("localhost", "127.0.0.1"):
            pytest.skip(BLOCKED + " URL is not local PostgreSQL.")
        engine = create_engine(url)
        conn = engine.connect()
        try:
            _independent_gate(url, conn)  # Read-only identity checks before any DDL.
        except Exception:
            conn.close()
            engine.dispose()
            raise
    except Exception as exc:
        pytest.skip(f"{BLOCKED} Cannot connect or independently verify: {type(exc).__name__}.")
    # The verification SELECT started a read-only transaction.
    conn.rollback()
    tx = conn.begin()
    try:
        schema = "mclean_test_" + uuid.uuid4().hex
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        yield conn
    finally:
        tx.rollback()
        conn.close()
        engine.dispose()


def _schema_snapshot(conn):
    inspector = inspect(conn)
    result = {}
    for table in ("users", "asistencias", "marcas", "pagos", "partes_semanales", "partes_diarios", "sesiones_entrenamiento", "entrenamientos_principales"):
        result[table] = {
            "indexes": sorted((i["name"], tuple(i["column_names"]), i["unique"]) for i in inspector.get_indexes(table)),
            "uniques": sorted((c["name"] or "", tuple(c["column_names"])) for c in inspector.get_unique_constraints(table)),
            "foreign_keys": sorted((tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]), f.get("options", {}).get("ondelete")) for f in inspector.get_foreign_keys(table)),
            "checks": sorted((c["name"], c["sqltext"]) for c in inspector.get_check_constraints(table)),
        }
    return result


def _assert_rejected(conn, sql, params=None):
    # PostgreSQL aborts the current transaction on error; isolate each rejection.
    with pytest.raises(IntegrityError):
        with conn.begin_nested():
            conn.execute(text(sql), params or {})


def test_full_chain_preserves_schema_history_and_existing_flow(isolated_connection, monkeypatch):
    conn = isolated_connection
    previous = None
    for revision in CHAIN[:-1]:
        module = _upgrade(revision, conn, monkeypatch)
        assert module.revision == revision and module.down_revision == previous
        previous = revision
    conn.execute(text("INSERT INTO users (id, username, hashed_password) VALUES (1, 'atleta_prueba', 'x')"))
    conn.execute(text("""INSERT INTO partes_semanales (id, atleta_id, semana, sueno_calidad, dolor_muscular, estres, animo, comentarios)
        VALUES (1, 1, '2026-11-16', 5, 4, 3, 2, 'semanal')"""))
    conn.execute(text("""INSERT INTO partes_diarios
        (id, atleta_id, fecha, sueno_calidad, fatiga, dolor_muscular, estres, animo, horas_sueno,
         hay_molestia, molestia_zona, molestia_zona_otra, molestia_dolor, afecta_entrenamiento,
         sintomas_enfermedad, detalle_sintomas, comentarios, entreno_hoy)
        VALUES (1, 1, '2026-11-23', 10, 9, 8, 7, 6, 7.5, true, ARRAY['rodillas','otro'],
                'tobillo', 8, 2, true, 'tos y fiebre', 'comentario privado', true)"""))
    conn.execute(text("""INSERT INTO sesiones_entrenamiento
        (id, parte_diaria_id, orden, tipo_entrenamiento, duracion_min, rpe, carga_sesion, comentarios_entrenamiento)
        VALUES (1, 1, 1, 'fuerza', 45, 6, 999, 'histórica'), (2, 1, 2, 'resistencia', 30, 5, 150, 'segunda')"""))
    conn.execute(text("""INSERT INTO entrenamientos_principales
        (id, parte_diaria_id, estructura_tipo, series, repeticiones_por_serie, distancia_m,
         descanso_micro_min_s, descanso_micro_max_s, descanso_macro_min_s, descanso_macro_max_s,
         tiempo_rep_min_s, tiempo_rep_max_s) VALUES (1, 1, 'aerobico', 3, 4, 400, 30, 60, 180, 300, 100, 120)"""))
    tables = ("users", "asistencias", "marcas", "pagos", "partes_semanales", "partes_diarios", "sesiones_entrenamiento", "entrenamientos_principales")
    rows_before = {table: [dict(row) for row in conn.execute(text(f'SELECT * FROM "{table}" ORDER BY id')).mappings()] for table in tables}
    schema_before = _schema_snapshot(conn)
    migration = _upgrade(CHAIN[-1], conn, monkeypatch)
    assert migration.revision == CHAIN[-1] and migration.down_revision == previous
    schema_after = _schema_snapshot(conn)
    for table in tables:
        for key in ("indexes", "uniques", "foreign_keys"):
            assert schema_before[table][key] == schema_after[table][key]
        assert set(schema_before[table]["checks"]) <= set(schema_after[table]["checks"])
        for old, new in zip(rows_before[table], conn.execute(text(f'SELECT * FROM "{table}" ORDER BY id')).mappings(), strict=True):
            assert all(new[key] == value for key, value in old.items())
    row = conn.execute(text("SELECT version_cuestionario, mclean_sueno FROM partes_diarios WHERE id=1")).one()
    assert tuple(row) == ("historico_1_10", None)
    assert conn.execute(text("SELECT array_agg(tipo_duracion ORDER BY id) FROM sesiones_entrenamiento")).scalar_one() == ["no_especificada", "no_especificada"]
    assert conn.execute(text("SELECT carga_sesion FROM sesiones_entrenamiento WHERE id=1")).scalar_one() == 999
    with pytest.raises(RuntimeError, match="Downgrade no disponible"):
        migration.downgrade()
    _assert_rejected(conn, "UPDATE partes_diarios SET fatiga=NULL WHERE id=1")
    _assert_rejected(conn, "UPDATE partes_diarios SET fatiga=11 WHERE id=1")
    _assert_rejected(conn, "UPDATE partes_diarios SET mclean_sueno=1 WHERE id=1")
    _assert_rejected(conn, "UPDATE sesiones_entrenamiento SET tipo_duracion='incorrecta' WHERE id=1")
    _assert_rejected(conn, "UPDATE sesiones_entrenamiento SET parte_diaria_id=999 WHERE id=1")
    _assert_rejected(conn, "INSERT INTO partes_diarios (atleta_id,fecha,sueno_calidad,fatiga,dolor_muscular,estres,animo,horas_sueno,entreno_hoy) VALUES (1,'2026-11-23',1,1,1,1,1,8,false)")
    conn.execute(text("""INSERT INTO partes_diarios (id,atleta_id,fecha,horas_sueno,entreno_hoy,version_cuestionario,
        mclean_sueno,mclean_fatiga,mclean_dolor_muscular,mclean_estres,mclean_animo)
        VALUES (2,1,'2026-11-24',8,false,'mclean_1_5',1,2,3,4,5)"""))
    for field in ("mclean_sueno", "mclean_fatiga", "mclean_dolor_muscular", "mclean_estres", "mclean_animo"):
        for value in (None, 0, 6):
            _assert_rejected(conn, f"UPDATE partes_diarios SET {field}=:value WHERE id=2", {"value": value})
    _assert_rejected(conn, "UPDATE partes_diarios SET sueno_calidad=1 WHERE id=2")
    _assert_rejected(conn, "UPDATE partes_diarios SET version_cuestionario='desconocida' WHERE id=2")
    # Existing service can update historical rows while preserving omitted sessions.
    with Session(bind=conn, join_transaction_mode="create_savepoint") as db:
        record, token, _ = svc.get_today_state(db, 1, date(2026, 11, 23))
        payload = {"sueno_calidad": 10, "fatiga": 9, "dolor_muscular": 8, "estres": 7, "animo": 6,
                   "horas_sueno": "7.5", "hay_molestia": True, "molestia_zona": ["rodillas", "otro"],
                   "molestia_zona_otra": "tobillo", "molestia_dolor": 8, "afecta_entrenamiento": 2,
                   "sintomas_enfermedad": True, "detalle_sintomas": "tos y fiebre", "comentarios": "actualizado",
                   "entreno_hoy": True, "sessions": [], "entrenamiento_principal": {
                       "estructura_tipo": "aerobico", "series": 3, "repeticiones_por_serie": 4, "distancia_m": 400,
                       "descanso_micro_min_s": 30, "descanso_micro_max_s": 60, "descanso_macro_min_s": 180,
                       "descanso_macro_max_s": 300, "tiempo_rep_min_s": 100, "tiempo_rep_max_s": 120}}
        result = svc.save_daily_record(db, atleta_id=1, fecha=record.fecha, payload=payload, edit_state_token=token)
        assert result.ok
        assert len(result.parte.sesiones) == 2
        assert sorted(s.carga_sesion for s in result.parte.sesiones) == [150, 999]
