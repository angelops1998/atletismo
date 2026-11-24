"""Duration contracts, final-state invariants and legacy preservation."""
from datetime import date

import pytest
from sqlalchemy import select
from app.models import ParteDiaria, SesionEntrenamiento
from app.services import parte_diaria as svc
from conftest import crear_usuario

DATE = date(2026, 11, 24)


def payload(*, sessions=None):
    return dict(sueno_calidad=7, fatiga=4, dolor_muscular=3, estres=4, animo=8,
                horas_sueno=8, hay_molestia=False, sintomas_enfermedad=False,
                comentarios="preservar", entreno_hoy=True, sessions=sessions or [])


def session(**changes):
    return {**dict(orden=1, tipo_entrenamiento="fuerza", duracion_min=30, rpe=6), **changes}


@pytest.mark.parametrize("contract,expected", [("historico", "no_especificada"), ("trabajo_principal", "trabajo_principal")])
@pytest.mark.parametrize("tipo", ["aerobico", "lactico", "velocidad", "fuerza", "resistencia", "velocidad_sprint"])
def test_contract_and_new_and_historical_types(db, contract, expected, tipo):
    athlete = crear_usuario(db, username="contrato_tipos")
    result = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session(tipo_entrenamiento=tipo)]), contrato_sesiones=contract)
    assert result.ok and result.parte.sesiones[0].tipo_duracion == expected
    assert result.parte.sesiones[0].carga_sesion == 180


def test_default_contract_never_trusts_client_semantics(db):
    athlete = crear_usuario(db, username="contrato_default")
    result = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session(tipo_duracion="trabajo_principal")]))
    assert result.ok and result.parte.sesiones[0].tipo_duracion == "no_especificada"


def test_unknown_contract_rejected_without_write(db):
    athlete = crear_usuario(db, username="contrato_invalido")
    result = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session()]), contrato_sesiones="invalido")
    assert result.status == svc.STATUS_VALIDATION and db.query(ParteDiaria).count() == 0


@pytest.mark.parametrize("mode", ["explicit", "replace"])
def test_deleting_last_session_without_plan_rolls_back(db, mode):
    athlete = crear_usuario(db, username="ultima_sesion")
    original = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session()]), contrato_sesiones="trabajo_principal")
    sid = original.parte.sesiones[0].id
    kwargs = {"explicit_delete_session_ids": [sid]} if mode == "explicit" else {"allow_full_session_replacement": True}
    result = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(), edit_state_token=original.edit_state_token, contrato_sesiones="trabajo_principal", **kwargs)
    assert result.status == svc.STATUS_VALIDATION
    db.expire_all()
    row = db.execute(select(ParteDiaria).where(ParteDiaria.atleta_id == athlete.id)).scalar_one()
    assert row.entreno_hoy and row.comentarios == "preservar"
    assert [(s.id, s.carga_sesion, s.tipo_duracion) for s in row.sesiones] == [(sid, 180, "trabajo_principal")]


def test_replacing_last_session_atomically_allowed_and_stale_token_rejected(db):
    athlete = crear_usuario(db, username="reemplazo_sesion")
    original = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session()]), contrato_sesiones="trabajo_principal")
    token = original.edit_state_token
    result = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session(tipo_entrenamiento="lactico", rpe=8)]), edit_state_token=token,
        contrato_sesiones="trabajo_principal", allow_full_session_replacement=True)
    assert result.ok and [(s.tipo_entrenamiento, s.carga_sesion) for s in result.parte.sesiones] == [("lactico", 240)]
    stale = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(), edit_state_token=token, contrato_sesiones="trabajo_principal", allow_full_session_replacement=True)
    assert stale.status == svc.STATUS_CONFLICT
    db.expire_all()
    assert db.query(SesionEntrenamiento).one().tipo_entrenamiento == "lactico"


def test_legacy_cannot_reinterpret_or_recompute_existing_session(db):
    athlete = crear_usuario(db, username="carga_legacy")
    first = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session()]))
    sid = first.parte.sesiones[0].id
    first.parte.sesiones[0].carga_sesion = 999
    db.commit()
    _, token, _ = svc.get_today_state(db, athlete.id, DATE)
    result = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session(id=sid, tipo_duracion="trabajo_principal")]), edit_state_token=token,
        contrato_sesiones="trabajo_principal")
    assert result.ok and result.parte.sesiones[0].carga_sesion == 999
    assert result.parte.sesiones[0].tipo_duracion == "no_especificada"
    invalid = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session(id=sid, duracion_min=31)]), edit_state_token=result.edit_state_token,
        contrato_sesiones="trabajo_principal")
    assert invalid.status == svc.STATUS_VALIDATION
    db.expire_all()
    assert db.query(SesionEntrenamiento).one().carga_sesion == 999


def test_foreign_session_rejected_without_modifying_owner(db):
    a = crear_usuario(db, username="dueno_a")
    b = crear_usuario(db, username="dueno_b")
    owned = svc.save_daily_record(db, atleta_id=a.id, fecha=DATE,
        payload=payload(sessions=[session()]), contrato_sesiones="trabajo_principal")
    foreign = svc.save_daily_record(db, atleta_id=b.id, fecha=DATE,
        payload=payload(sessions=[session(id=owned.parte.sesiones[0].id)]), contrato_sesiones="trabajo_principal")
    assert foreign.status == svc.STATUS_VALIDATION
    assert db.query(SesionEntrenamiento).count() == 1


def test_deleting_last_session_allowed_when_plan_is_preserved(db):
    from test_mclean_backend import PLAN
    athlete = crear_usuario(db, username="plan_y_sesion")
    data = payload(sessions=[session()])
    data["entrenamiento_principal"] = PLAN
    first = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE, payload=data,
                                   contrato_sesiones="trabajo_principal")
    sid = first.parte.sesiones[0].id
    result = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE, payload=payload(),
        edit_state_token=first.edit_state_token, explicit_delete_session_ids=[sid],
        contrato_sesiones="trabajo_principal")
    assert result.ok and result.parte.entreno_hoy and not result.parte.sesiones
    assert result.parte.entrenamiento_principal.distancia_m == 400


def test_legacy_cannot_edit_main_work_minutes_without_contract(db):
    athlete = crear_usuario(db, username="contrato_edit")
    first = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session()]), contrato_sesiones="trabajo_principal")
    sid = first.parte.sesiones[0].id
    bad = svc.save_daily_record(db, atleta_id=athlete.id, fecha=DATE,
        payload=payload(sessions=[session(id=sid, duracion_min=45)]), edit_state_token=first.edit_state_token)
    assert bad.status == svc.STATUS_VALIDATION
    db.expire_all()
    assert db.query(SesionEntrenamiento).one().carga_sesion == 180
