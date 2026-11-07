"""Validación focalizada Fase 1: esquema de partes diarias y sesiones.

Pruebas de metadata/modelos sobre SQLite (infra existente). La validación
autoritaria de migración/ARRAY/constraints PostgreSQL requiere una BD PostgreSQL
desechable verificada (ver informe de Fase 1).
"""
from datetime import date

import pytest
from sqlalchemy import inspect

from app.models import ParteDiaria, SesionEntrenamiento, ParteSemanal
from app.models.parte_diaria import MOLESTIA_ZONAS
from app.models.sesion_entrenamiento import TIPOS_ENTRENAMIENTO


def test_modelos_registrados_en_metadata():
    tablas = set(ParteDiaria.metadata.tables)
    assert "partes_diarios" in tablas
    assert "sesiones_entrenamiento" in tablas
    # Tabla semanal histórica intacta en metadata
    assert "partes_semanales" in tablas


def test_parte_diaria_tabla_y_constraints():
    t = ParteDiaria.__table__
    assert t.name == "partes_diarios"
    uqs = {c.name for c in t.constraints if getattr(c, "name", None)}
    cks = {c.name for c in t.constraints if getattr(c, "name", None)}
    assert "uq_parte_diaria_atleta_fecha" in uqs
    for name in [
        "ck_partes_diarios_sueno_calidad",
        "ck_partes_diarios_fatiga",
        "ck_partes_diarios_dolor_muscular",
        "ck_partes_diarios_estres",
        "ck_partes_diarios_animo",
        "ck_partes_diarios_horas_sueno",
        "ck_partes_diarios_molestia_dolor",
        "ck_partes_diarios_afecta_entrenamiento",
    ]:
        assert name in cks
    idx = {i.name for i in t.indexes}
    assert "ix_partes_diarios_atleta_fecha" in idx
    assert "ix_partes_diarios_fecha" in idx


def test_sesion_entrenamiento_tabla_y_constraints():
    t = SesionEntrenamiento.__table__
    assert t.name == "sesiones_entrenamiento"
    cks = {c.name for c in t.constraints if getattr(c, "name", None)}
    assert "ck_sesiones_entrenamiento_duracion_min" in cks
    assert "ck_sesiones_entrenamiento_rpe" in cks
    assert "ck_sesiones_entrenamiento_carga_sesion" in cks
    assert "ck_sesiones_entrenamiento_tipo" in cks
    idx = {i.name for i in t.indexes}
    assert "ix_sesiones_entrenamiento_parte_diaria" in idx
    fks = list(t.foreign_keys)
    assert any(fk.column.table.name == "partes_diarios" and fk.ondelete == "CASCADE" for fk in fks)


def test_relaciones_y_cascade_orm():
    insp = inspect(ParteDiaria)
    rel = insp.relationships["sesiones"]
    assert rel.mapper.class_ is SesionEntrenamiento
    assert "delete" in rel.cascade
    assert "delete-orphan" in rel.cascade
    back = inspect(SesionEntrenamiento).relationships["parte_diaria"]
    assert back.mapper.class_ is ParteDiaria


def test_whitelists_dominio():
    assert "otro" in MOLESTIA_ZONAS
    assert "cuello" in MOLESTIA_ZONAS and "brazos" in MOLESTIA_ZONAS
    assert "entrenamiento_mixto" in TIPOS_ENTRENAMIENTO
    assert "otro" in TIPOS_ENTRENAMIENTO


def test_create_schema_sqlite_y_roundtrip_basico(db, crear_usuario):
    """create_all sobre SQLite (variante JSON para molestia_zona) — sanity check."""
    atleta = crear_usuario(db, username="a1")
    parte = ParteDiaria(
        atleta_id=atleta.id,
        fecha=date(2026, 11, 7),
        sueno_calidad=7,
        fatiga=4,
        dolor_muscular=3,
        estres=4,
        animo=8,
        horas_sueno=7.5,
        hay_molestia=False,
        molestia_zona=None,
        sintomas_enfermedad=False,
        entreno_hoy=True,
    )
    db.add(parte)
    db.flush()
    ses = SesionEntrenamiento(
        parte_diaria_id=parte.id,
        orden=1,
        tipo_entrenamiento="resistencia",
        duracion_min=45,
        rpe=6,
        carga_sesion=270,
    )
    db.add(ses)
    db.commit()
    db.refresh(parte)
    assert parte.sesiones[0].carga_sesion == 270
    assert parte.sesiones[0].parte_diaria_id == parte.id


def test_parte_semanal_historica_sigue_intacta(db, crear_usuario):
    """Fase 1 no altera modelo/tabla semanal histórica."""
    from app.models.parte import ParteSemanal
    from app.tiempo import lunes_actual

    atleta = crear_usuario(db, username="a2")
    p = ParteSemanal(
        atleta_id=atleta.id,
        semana=lunes_actual(),
        sueno_calidad=4,
        dolor_muscular=4,
        estres=4,
        animo=4,
    )
    db.add(p)
    db.commit()
    assert db.query(ParteSemanal).count() == 1
