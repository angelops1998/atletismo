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


@pytest.mark.parametrize("field", ["mclean_sueno", "mclean_fatiga", "mclean_dolor_muscular", "mclean_estres", "mclean_animo"])
@pytest.mark.parametrize("value", [None, 0, 6])
def test_each_mclean_answer_required_and_in_range(db, field, value):
    db.add(base_record(db, **{field: value}))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize("field", ["sueno_calidad", "fatiga", "dolor_muscular", "estres", "animo"])
@pytest.mark.parametrize("value", [None, 0, 11])
def test_each_historical_answer_required_and_in_range(db, field, value):
    athlete = crear_usuario(db, username="historico_test")
    answers = dict(sueno_calidad=10, fatiga=9, dolor_muscular=8, estres=7, animo=6)
    answers[field] = value
    db.add(ParteDiaria(atleta_id=athlete.id, fecha=date(2026, 11, 23), horas_sueno=8,
                       entreno_hoy=False, **answers))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize("field", ["version_cuestionario", "mclean_sueno", "mclean_fatiga", "mclean_dolor_muscular", "mclean_estres", "mclean_animo"])
def test_edit_token_rejects_changed_questionnaire_state(db, field):
    from app.services.parte_diaria_tokens import issue_edit_state_token, verify_edit_state_token
    record = base_record(db)
    db.add(record)
    db.commit()
    binding = dict(atleta_id=record.atleta_id, fecha=record.fecha, registro_id=record.id)
    original = current_fingerprint(record)
    token = issue_edit_state_token(**binding, fingerprint=original)
    assert verify_edit_state_token(token, **binding, current_fingerprint=original).ok
    setattr(record, field, "historico_1_10" if field == "version_cuestionario" else 5 if getattr(record, field) != 5 else 1)
    result = verify_edit_state_token(token, **binding, current_fingerprint=current_fingerprint(record))
    assert not result.ok and result.reason == "fingerprint_mismatch"


def test_both_tokens_reject_changed_duration_semantics(db):
    from app.services.parte_diaria_tokens import (issue_edit_state_token, verify_edit_state_token,
                                                    issue_discard_token, verify_discard_token)
    record = base_record(db)
    record.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza", duracion_min=30,
                                               rpe=6, carga_sesion=180))
    db.add(record)
    db.commit()
    binding = dict(atleta_id=record.atleta_id, fecha=record.fecha, registro_id=record.id)
    edit = issue_edit_state_token(**binding, fingerprint=current_fingerprint(record))
    discard = issue_discard_token(**binding, session_fingerprint=current_session_fingerprint(record))
    record.sesiones[0].tipo_duracion = "trabajo_principal"
    assert not verify_edit_state_token(edit, **binding, current_fingerprint=current_fingerprint(record)).ok
    assert not verify_discard_token(discard, **binding, current_session_fingerprint=current_session_fingerprint(record)).ok


def test_upgrade_reconstructed_full_schema_preserves_related_data(monkeypatch):
    """SQLite model reconstruction is supplementary; it is not PostgreSQL evidence."""
    from sqlalchemy import MetaData, inspect
    from app.database import Base

    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(metadata)
    daily = metadata.tables["partes_diarios"]
    sessions = metadata.tables["sesiones_entrenamiento"]
    for table, constraint_name in ((daily, "ck_partes_diarios_version_bienestar"),
                                   (sessions, "ck_sesiones_tipo_duracion")):
        table.constraints.remove(next(c for c in table.constraints if c.name == constraint_name))
    for field in ("version_cuestionario", "mclean_sueno", "mclean_fatiga", "mclean_dolor_muscular", "mclean_estres", "mclean_animo"):
        daily._columns.remove(daily.c[field])
    sessions._columns.remove(sessions.c.tipo_duracion)
    for field in ("sueno_calidad", "fatiga", "dolor_muscular", "estres", "animo"):
        daily.c[field].nullable = False
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(text("INSERT INTO users (id,username,hashed_password) VALUES (1,'reconstruccion','x')"))
        conn.execute(text("""INSERT INTO partes_diarios (id,atleta_id,fecha,sueno_calidad,fatiga,dolor_muscular,estres,animo,horas_sueno,
            hay_molestia,molestia_zona,molestia_zona_otra,molestia_dolor,afecta_entrenamiento,sintomas_enfermedad,detalle_sintomas,comentarios,entreno_hoy)
            VALUES (1,1,'2026-11-23',10,9,8,7,6,7.5,1,'["rodillas", "otro"]','tobillo',8,2,1,'tos','comentario',1)"""))
        conn.execute(text("""INSERT INTO sesiones_entrenamiento (id,parte_diaria_id,orden,tipo_entrenamiento,duracion_min,rpe,carga_sesion,comentarios_entrenamiento)
            VALUES (1,1,1,'fuerza',45,6,999,'sesion'),(2,1,2,'resistencia',30,5,150,'segunda')"""))
        conn.execute(text("""INSERT INTO entrenamientos_principales (id,parte_diaria_id,estructura_tipo,series,repeticiones_por_serie,distancia_m,
            descanso_micro_min_s,descanso_micro_max_s,descanso_macro_min_s,descanso_macro_max_s,tiempo_rep_min_s,tiempo_rep_max_s)
            VALUES (1,1,'aerobico',3,4,400,30,60,180,300,100,120)"""))
        tables = ("users", "partes_diarios", "sesiones_entrenamiento", "entrenamientos_principales", "partes_semanales", "pagos", "marcas", "asistencias")
        data = {t: [dict(row) for row in conn.execute(text(f'SELECT * FROM "{t}" ORDER BY id')).mappings()] for t in tables}
        def structure():
            inspector = inspect(conn)
            return {t: {
                "indexes": sorted((i["name"], tuple(i["column_names"]), i["unique"]) for i in inspector.get_indexes(t)),
                "uniques": sorted((c["name"] or "", tuple(c["column_names"])) for c in inspector.get_unique_constraints(t)),
                "fks": sorted((tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]), f.get("options", {}).get("ondelete")) for f in inspector.get_foreign_keys(t)),
                "checks": {c["name"] for c in inspector.get_check_constraints(t)},
            } for t in tables}
        before = structure()
        spec = importlib.util.spec_from_file_location("mclean_full_schema_migration", MIGRATION)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
        migration.upgrade()
        after = structure()
        for table in tables:
            for kind in ("indexes", "uniques", "fks"):
                assert before[table][kind] == after[table][kind]
            assert before[table]["checks"] <= after[table]["checks"]
            rows = [dict(row) for row in conn.execute(text(f'SELECT * FROM "{table}" ORDER BY id')).mappings()]
            assert len(rows) == len(data[table])
            for old, new in zip(data[table], rows):
                assert all(new[k] == v for k, v in old.items())
        assert conn.execute(text("PRAGMA foreign_key_check")).all() == []
        assert conn.execute(text("SELECT tipo_duracion FROM sesiones_entrenamiento ORDER BY id")).scalars().all() == ["no_especificada"] * 2
        assert conn.execute(text("SELECT carga_sesion FROM sesiones_entrenamiento WHERE id=1")).scalar_one() == 999
    engine.dispose()
