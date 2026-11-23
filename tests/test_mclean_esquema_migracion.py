"""Versioned daily wellness and session semantics, using isolated SQLite only."""
import importlib.util
from pathlib import Path
from datetime import date

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.models import ParteDiaria, SesionEntrenamiento
from app.services.parte_diaria import current_fingerprint, current_session_fingerprint
from conftest import crear_usuario

MIGRATION = Path(__file__).resolve().parents[1] / "alembic/versions/f2a7c94b1d30_mclean_version_y_duracion.py"


def test_upgrade_preserves_historical_records_and_load(monkeypatch):
    # A deliberately minimal old schema, entirely in memory: no application DB.
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE partes_diarios (
            id INTEGER PRIMARY KEY, sueno_calidad INTEGER NOT NULL,
            fatiga INTEGER NOT NULL, dolor_muscular INTEGER NOT NULL,
            estres INTEGER NOT NULL, animo INTEGER NOT NULL,
            comentarios TEXT)"""))
        conn.execute(text("""CREATE TABLE sesiones_entrenamiento (
            id INTEGER PRIMARY KEY, parte_diaria_id INTEGER NOT NULL,
            duracion_min INTEGER NOT NULL, rpe INTEGER NOT NULL, carga_sesion INTEGER NOT NULL,
            FOREIGN KEY(parte_diaria_id) REFERENCES partes_diarios(id))"""))
        conn.execute(text("INSERT INTO partes_diarios VALUES (1, 10, 9, 8, 7, 6, 'conservar')"))
        conn.execute(text("INSERT INTO sesiones_entrenamiento VALUES (1, 1, 45, 6, 999)"))
        spec = importlib.util.spec_from_file_location("mclean_migration", MIGRATION)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
        migration.upgrade()
        row = conn.execute(text("SELECT sueno_calidad, fatiga, dolor_muscular, estres, animo, comentarios, version_cuestionario, mclean_sueno FROM partes_diarios")).one()
        assert tuple(row) == (10, 9, 8, 7, 6, "conservar", "historico_1_10", None)
        assert tuple(conn.execute(text("SELECT duracion_min, rpe, carga_sesion, tipo_duracion FROM sesiones_entrenamiento")).one()) == (45, 6, 999, "no_especificada")
        with pytest.raises(IntegrityError):
            conn.execute(text("UPDATE partes_diarios SET mclean_sueno = 5 WHERE id = 1"))
        with pytest.raises(RuntimeError, match="Downgrade no disponible"):
            migration.downgrade()
    engine.dispose()


def base_record(db, **overrides):
    athlete = crear_usuario(db, username="mclean_test")
    fields = dict(atleta_id=athlete.id, fecha=date(2026, 11, 23), horas_sueno=7.5,
                  hay_molestia=False, sintomas_enfermedad=False, entreno_hoy=False,
                  version_cuestionario="mclean_1_5", mclean_sueno=1, mclean_fatiga=2,
                  mclean_dolor_muscular=3, mclean_estres=4, mclean_animo=5)
    fields.update(overrides)
    return ParteDiaria(**fields)


def test_mclean_roundtrip_and_new_duration_semantics(db):
    record = base_record(db)
    record.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
        duracion_min=30, tipo_duracion="trabajo_principal", rpe=6, carga_sesion=180))
    db.add(record)
    db.commit()
    db.refresh(record)
    assert (record.mclean_sueno, record.mclean_animo, record.sueno_calidad) == (1, 5, None)
    assert record.sesiones[0].tipo_duracion == "trabajo_principal"


@pytest.mark.parametrize("changes", [
    {"version_cuestionario": "desconocida"},
    {"version_cuestionario": "historico_1_10"},
    {"mclean_sueno": None}, {"mclean_fatiga": 0}, {"mclean_animo": 6},
    {"sueno_calidad": 5},
])
def test_version_constraints_reject_incomplete_mixed_or_invalid_answers(db, changes):
    db.add(base_record(db, **changes))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_invalid_duration_semantics_rejected(db):
    record = base_record(db)
    record.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
        duracion_min=30, tipo_duracion="invalida", rpe=6, carga_sesion=180))
    db.add(record)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_fingerprints_include_new_data(db):
    record = base_record(db)
    record.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
        duracion_min=30, rpe=6, carga_sesion=180))
    db.add(record)
    db.commit()
    before = current_fingerprint(record)
    record.mclean_sueno = 2
    assert current_fingerprint(record) != before
    session_before = current_session_fingerprint(record)
    record.sesiones[0].tipo_duracion = "trabajo_principal"
    assert current_session_fingerprint(record) != session_before
