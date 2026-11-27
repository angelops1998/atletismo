"""Backend-only McLean and session behavior; SQLite fixtures are in-memory."""
from datetime import date

import pytest

from app.models import ParteDiaria, SesionEntrenamiento
from app.services import parte_diaria as svc
from conftest import crear_usuario

def save_work(*args, **kwargs):
    return svc.save_daily_record(*args, contrato_sesiones="trabajo_principal", **kwargs)


DAY = date(2026, 11, 23)
MCLEAN = dict(version_cuestionario="mclean_1_5", mclean_sueno=1, mclean_fatiga=2,
              mclean_dolor_muscular=3, mclean_estres=4, mclean_animo=5)
HIST = dict(sueno_calidad=10, fatiga=9, dolor_muscular=8, estres=7, animo=6)
PLAN = dict(estructura_tipo="aerobico", series=3, repeticiones_por_serie=4, distancia_m=400,
            descanso_micro_min_s=30, descanso_micro_max_s=60, descanso_macro_min_s=180,
            descanso_macro_max_s=300, tiempo_rep_min_s=100, tiempo_rep_max_s=120)


def payload(answers=None, **values):
    data = dict(answers or MCLEAN)
    data.update(horas_sueno="7.5", hay_molestia=False, sintomas_enfermedad=False,
                comentarios="conservar", entreno_hoy=False, sessions=[])
    data.update(values)
    return data


def session(**values):
    data = dict(orden=1, tipo_entrenamiento="fuerza", duracion_min=30, rpe=6)
    data.update(values)
    return data


def test_create_update_mclean_and_derived_totals(db):
    athlete = crear_usuario(db, username="backend_mclean")
    result = save_work(db, atleta_id=athlete.id, fecha=DAY, payload=payload())
    assert result.ok and result.parte.sueno_calidad is None
    assert svc.resumen_mclean(result.parte) == {"suma": 15, "promedio": 3.0}
    new_values = {**MCLEAN, "mclean_sueno": 5}
    result = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(new_values), edit_state_token=result.edit_state_token)
    assert result.ok and svc.resumen_mclean(result.parte) == {"suma": 19, "promedio": 3.8}
    assert "suma" not in result.parte.__table__.columns and "promedio" not in result.parte.__table__.columns


@pytest.mark.parametrize("field", list(MCLEAN)[1:])
@pytest.mark.parametrize("value", [None, 0, 6, 1.5, True])
def test_rejects_invalid_mclean_field(db, field, value):
    athlete = crear_usuario(db, username="invalid_mclean")
    result = save_work(db, atleta_id=athlete.id, fecha=DAY, payload=payload({**MCLEAN, field: value}))
    assert result.status == svc.STATUS_VALIDATION and db.query(ParteDiaria).count() == 0


def test_versions_never_mix_or_convert_on_edit(db):
    athlete = crear_usuario(db, username="legacy_version")
    initial = save_work(db, atleta_id=athlete.id, fecha=DAY, payload=payload(HIST))
    assert initial.ok and svc.resumen_mclean(initial.parte) is None
    reject = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(), edit_state_token=initial.edit_state_token)
    assert reject.status == svc.STATUS_VALIDATION
    db.refresh(initial.parte)
    assert initial.parte.version_cuestionario == "historico_1_10" and initial.parte.sueno_calidad == 10
    reject = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload({**MCLEAN, "sueno_calidad": 10}), edit_state_token=initial.edit_state_token)
    assert reject.status == svc.STATUS_VALIDATION


def test_mclean_to_legacy_and_stale_edits_do_not_overwrite(db):
    athlete = crear_usuario(db, username="version_conflict")
    first = save_work(db, atleta_id=athlete.id, fecha=DAY, payload=payload())
    changed = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload({**MCLEAN, "mclean_animo": 1}), edit_state_token=first.edit_state_token)
    stale = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(), edit_state_token=first.edit_state_token)
    assert changed.ok and stale.status == svc.STATUS_CONFLICT
    reject = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(HIST), edit_state_token=changed.edit_state_token)
    assert reject.status == svc.STATUS_VALIDATION
    assert db.query(ParteDiaria).one().mclean_animo == 1


def test_new_sessions_main_minutes_without_planning(db):
    athlete = crear_usuario(db, username="sessions_mclean")
    result = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(entreno_hoy=True, sessions=[session(), session(orden=2, duracion_min=20, rpe=8)]))
    assert result.ok and result.parte.entrenamiento_principal is None
    assert [(s.tipo_duracion, s.carga_sesion) for s in result.parte.sesiones] == [("trabajo_principal", 180), ("trabajo_principal", 160)]
    assert svc.carga_diaria(result.parte) == 340


def test_historical_session_load_and_planning_preserved(db):
    athlete = crear_usuario(db, username="history_preserved")
    initial = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(HIST, entreno_hoy=True, entrenamiento_principal=PLAN))
    assert initial.ok
    old = SesionEntrenamiento(parte_diaria_id=initial.parte.id, orden=1,
        tipo_entrenamiento="fuerza", duracion_min=45, rpe=6, carga_sesion=999,
        tipo_duracion="no_especificada", comentarios_entrenamiento="antes")
    db.add(old); db.commit(); db.refresh(initial.parte)
    _, token, _ = svc.get_today_state(db, athlete.id, DAY)
    edited = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(HIST, entreno_hoy=True, sessions=[session(id=old.id, duracion_min=45, rpe=6, comentarios_entrenamiento="nuevo")]), edit_state_token=token)
    assert edited.ok and edited.parte.entrenamiento_principal.distancia_m == 400
    assert (edited.parte.sesiones[0].tipo_duracion, edited.parte.sesiones[0].carga_sesion) == ("no_especificada", 999)
    rejected = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(HIST, entreno_hoy=True, sessions=[session(id=old.id, duracion_min=46, rpe=6)]), edit_state_token=edited.edit_state_token)
    assert rejected.status == svc.STATUS_VALIDATION
    db.refresh(old)
    assert (old.duracion_min, old.carga_sesion) == (45, 999)


def test_session_ownership_and_discard_confirmation(db):
    a = crear_usuario(db, username="owner_a")
    b = crear_usuario(db, username="owner_b")
    first = save_work(db, atleta_id=a.id, fecha=DAY,
        payload=payload(entreno_hoy=True, sessions=[session()]))
    other = save_work(db, atleta_id=b.id, fecha=DAY,
        payload=payload(entreno_hoy=True, sessions=[session(id=first.parte.sesiones[0].id)]))
    assert first.ok and other.status == svc.STATUS_VALIDATION
    intent = save_work(db, atleta_id=a.id, fecha=DAY, payload=payload(), edit_state_token=first.edit_state_token)
    assert intent.status == svc.STATUS_VALIDATION and len(intent.parte.sesiones) == 1
    confirm = save_work(db, atleta_id=a.id, fecha=DAY, payload=payload(),
        edit_state_token=intent.edit_state_token, discard_token=intent.discard_token, confirm_discard_sessions=True)
    assert confirm.ok and not confirm.parte.sesiones


def test_existing_planning_survives_confirmed_session_discard(db):
    athlete = crear_usuario(db, username="plan_retained")
    created = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(HIST, entreno_hoy=True, entrenamiento_principal=PLAN, sessions=[session()]))
    intent = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(HIST), edit_state_token=created.edit_state_token)
    confirmed = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(HIST), edit_state_token=intent.edit_state_token,
        discard_token=intent.discard_token, confirm_discard_sessions=True)
    assert confirmed.ok and not confirmed.parte.sesiones
    assert confirmed.parte.entrenamiento_principal.distancia_m == 400


def test_update_new_session_recalculates_main_work_load(db):
    athlete = crear_usuario(db, username="new_session_update")
    initial = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(entreno_hoy=True, sessions=[session()]))
    sid = initial.parte.sesiones[0].id
    updated = save_work(db, atleta_id=athlete.id, fecha=DAY,
        payload=payload(entreno_hoy=True, sessions=[session(id=sid, duracion_min=40, rpe=7)]),
        edit_state_token=initial.edit_state_token)
    assert updated.ok
    assert (updated.parte.sesiones[0].tipo_duracion, updated.parte.sesiones[0].carga_sesion) == ("trabajo_principal", 280)
