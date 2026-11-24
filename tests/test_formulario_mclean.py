"""New form is opt-in; HTTP tests use the in-memory DB fixture."""
import re
from datetime import date

import pytest

from app.config import get_settings
from app.models import ParteDiaria, SesionEntrenamiento
from app.services import parte_diaria as svc
from app.tiempo import hoy
from conftest import con_csrf, crear_usuario, entrar


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(get_settings(), "formulario_mclean_habilitado", True)


def token(client):
    page = client.get("/parte")
    match = re.search(r'name="edit_state_token" value="([^"]*)"', page.text)
    return match.group(1) if match else ""


def data(client, **kwargs):
    body = {"csrf_token": con_csrf(client, "/parte"), "mclean_fatiga": "5", "mclean_sueno": "4",
            "mclean_dolor_muscular": "3", "mclean_estres": "2", "mclean_animo": "1",
            "horas_sueno": "7.5", "hay_molestia": "si", "molestia_zona": "rodillas",
            "molestia_dolor": "4", "afecta_entrenamiento": "1", "sintomas_enfermedad": "si",
            "detalle_sintomas": "tos", "comentarios": "algo", "entreno_hoy": "si",
            "sesion_id": ["", ""], "sesion_tipo": ["aerobico", "lactico"],
            "sesion_minutos": ["30", "40"], "sesion_rpe": ["5", "7"]}
    body.update(kwargs)
    return body


def test_disabled_by_default_and_enabled_form_texts(client, db, monkeypatch):
    athlete = crear_usuario(db, username="ui_flag")
    entrar(client, athlete)
    assert "Escala 1 a 10" in client.get("/parte").text
    monkeypatch.setattr(get_settings(), "formulario_mclean_habilitado", True)
    page = client.get("/parte")
    assert page.status_code == 200
    for value in ("Escala 1 a 5", "Muy recuperado", "Muy cansado", "Insomnio",
                  "Dificultad para conciliar el sueño", "Dolor y rigidez muscular",
                  "Altamente estresado", "Menos interés en otros y/o en otras actividades de lo normal",
                  "Aeróbico", "Láctico", "Velocidad", "Fuerza", "viewport", "csrf_token"):
        assert value in page.text
    assert 'name="series"' not in page.text and 'name="distancia_m"' not in page.text
    assert page.text.count('name="sesion_tipo"') >= 3


def test_multiple_sessions_and_additional_health(client, db, enabled):
    athlete = crear_usuario(db, username="ui_create")
    entrar(client, athlete)
    response = client.post("/parte", data=data(client), follow_redirects=False)
    assert response.status_code == 302
    p = db.query(ParteDiaria).one()
    assert p.version_cuestionario == "mclean_1_5" and p.mclean_fatiga == 5 and p.sueno_calidad is None
    assert [(s.tipo_entrenamiento, s.tipo_duracion, s.carga_sesion) for s in p.sesiones] == [
        ("aerobico", "trabajo_principal", 150), ("lactico", "trabajo_principal", 280)]
    assert p.molestia_zona == ["rodillas"] and p.detalle_sintomas == "tos" and p.comentarios == "algo"


def test_422_preserves_input_and_rejects_bad_session(client, db, enabled):
    athlete = crear_usuario(db, username="ui_invalid")
    entrar(client, athlete)
    body = data(client, sesion_minutos=["0", "40"], comentarios="texto guardado en pantalla")
    response = client.post("/parte", data=body, follow_redirects=False)
    assert response.status_code == 422 and "texto guardado en pantalla" in response.text
    assert db.query(ParteDiaria).count() == 0


def test_stale_edit_conflict_preserves_committed_data(client, db, enabled):
    athlete = crear_usuario(db, username="ui_conflict")
    entrar(client, athlete)
    body = data(client)
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    old = token(client)
    record = db.query(ParteDiaria).one()
    record.mclean_animo = 4
    db.commit()
    body["edit_state_token"] = old
    response = client.post("/parte", data=body, follow_redirects=False)
    assert response.status_code == 409
    db.refresh(record)
    assert record.mclean_animo == 4 and len(record.sesiones) == 2


def test_historical_record_keeps_original_form(client, db, enabled):
    athlete = crear_usuario(db, username="ui_historical")
    record = ParteDiaria(atleta_id=athlete.id, fecha=hoy(), sueno_calidad=8, fatiga=5,
        dolor_muscular=4, estres=3, animo=9, horas_sueno=8, entreno_hoy=False)
    db.add(record); db.commit()
    entrar(client, athlete)
    page = client.get("/parte")
    assert page.status_code == 200 and "Escala 1 a 10" in page.text
    assert 'name="mclean_fatiga"' not in page.text
    db.refresh(record)
    assert record.version_cuestionario == "historico_1_10" and record.sueno_calidad == 8


def test_csrf_and_role_still_enforced(client, db, enabled):
    athlete = crear_usuario(db, username="ui_csrf")
    entrar(client, athlete)
    assert client.post("/parte", data={}).status_code == 403
    professor = crear_usuario(db, username="ui_profesor", role="profesor")
    entrar(client, professor)
    assert client.get("/parte").status_code == 403


def test_edit_work_and_preserve_historical_load(client, db, enabled):
    athlete = crear_usuario(db, username="ui_edit")
    entrar(client, athlete)
    assert client.post("/parte", data=data(client), follow_redirects=False).status_code == 302
    record = db.query(ParteDiaria).one()
    old = SesionEntrenamiento(parte_diaria_id=record.id, orden=3, tipo_entrenamiento="resistencia",
                              duracion_min=50, rpe=6, carga_sesion=999, tipo_duracion="no_especificada")
    db.add(old); db.commit(); db.refresh(record)
    assert "duración no está identificada" in client.get("/parte").text
    first, second = record.sesiones[:2]
    body = data(client, edit_state_token=token(client), sesion_id=[str(first.id), str(second.id)],
                sesion_tipo=["fuerza", "lactico"], sesion_minutos=["35", "40"], sesion_rpe=["6", "7"])
    response = client.post("/parte", data=body, follow_redirects=False)
    assert response.status_code == 302
    db.expire_all()
    record = db.query(ParteDiaria).one()
    assert [(s.tipo_duracion, s.carga_sesion) for s in record.sesiones] == [
        ("trabajo_principal", 210), ("trabajo_principal", 280), ("no_especificada", 999)]


def test_explicit_single_delete_and_discard_confirmation(client, db, enabled):
    athlete = crear_usuario(db, username="ui_delete")
    entrar(client, athlete)
    assert client.post("/parte", data=data(client), follow_redirects=False).status_code == 302
    record = db.query(ParteDiaria).one()
    first, second = record.sesiones
    body = data(client, edit_state_token=token(client), sesion_id=[str(first.id), str(second.id)],
                delete_session_ids=[str(first.id)])
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    db.expire_all(); record = db.query(ParteDiaria).one()
    assert len(record.sesiones) == 1 and record.sesiones[0].id == second.id
    body = data(client, edit_state_token=token(client), entreno_hoy="no",
                sesion_id=[], sesion_tipo=[], sesion_minutos=[], sesion_rpe=[])
    intent = client.post("/parte", data=body, follow_redirects=False)
    assert intent.status_code == 422 and "Confirmar descarte de sesiones" in intent.text
    assert len(db.query(ParteDiaria).one().sesiones) == 1
    body["edit_state_token"] = re.search(r'name="edit_state_token" value="([^"]+)"', intent.text).group(1)
    body["discard_token"] = re.search(r'name="discard_token" value="([^"]+)"', intent.text).group(1)
    body["confirm_discard_sessions"] = "si"
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    db.expire_all(); assert not db.query(ParteDiaria).one().sesiones


def test_foreign_session_cannot_be_deleted(client, db, enabled):
    athlete = crear_usuario(db, username="ui_owner")
    other = crear_usuario(db, username="ui_other")
    entrar(client, other)
    assert client.post("/parte", data=data(client), follow_redirects=False).status_code == 302
    foreign_id = db.query(ParteDiaria).filter_by(atleta_id=other.id).one().sesiones[0].id
    entrar(client, athlete)
    assert client.post("/parte", data=data(client), follow_redirects=False).status_code == 302
    body = data(client, edit_state_token=token(client), delete_session_ids=[str(foreign_id)])
    response = client.post("/parte", data=body, follow_redirects=False)
    assert response.status_code == 422
    db.expire_all(); assert len(db.query(ParteDiaria).filter_by(atleta_id=other.id).one().sesiones) == 2


def test_validation_error_does_not_refresh_stale_token(client, db, enabled):
    athlete = crear_usuario(db, username="ui_stale_invalid")
    entrar(client, athlete)
    body = data(client)
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    old = token(client)
    record = db.query(ParteDiaria).one()
    ids = [str(s.id) for s in record.sesiones]
    record.mclean_animo = 4
    db.commit()
    body.update(edit_state_token=old, sesion_id=ids, sesion_minutos=["0", "40"])
    invalid = client.post("/parte", data=body, follow_redirects=False)
    assert invalid.status_code == 422
    assert re.search(r'name="edit_state_token" value="([^"]+)"', invalid.text).group(1) == old
    body["sesion_minutos"] = ["30", "40"]
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 409
    db.refresh(record)
    assert record.mclean_animo == 4


def test_existing_mclean_record_blocked_when_flag_disabled(client, db, monkeypatch):
    athlete = crear_usuario(db, username="ui_disabled_existing")
    record = ParteDiaria(atleta_id=athlete.id, fecha=hoy(), version_cuestionario="mclean_1_5",
        mclean_sueno=4, mclean_fatiga=4, mclean_dolor_muscular=4, mclean_estres=4, mclean_animo=4,
        horas_sueno=8, entreno_hoy=False)
    db.add(record); db.commit()
    entrar(client, athlete)
    monkeypatch.setattr(get_settings(), "formulario_mclean_habilitado", False)
    assert client.get("/parte").status_code == 503
    db.refresh(record)
    assert record.version_cuestionario == "mclean_1_5" and record.mclean_animo == 4


def test_historical_record_can_be_edited_without_conversion(client, db, enabled):
    from test_parte import completo
    athlete = crear_usuario(db, username="ui_historical_edit")
    record = ParteDiaria(atleta_id=athlete.id, fecha=hoy(), sueno_calidad=8, fatiga=5,
        dolor_muscular=4, estres=3, animo=9, horas_sueno=8, entreno_hoy=False)
    db.add(record); db.commit()
    entrar(client, athlete)
    body = completo(client, entreno_hoy="no", sessions="", edit_state_token=token(client), animo="7")
    response = client.post("/parte", data=body, follow_redirects=False)
    assert response.status_code == 302
    db.refresh(record)
    assert record.version_cuestionario == "historico_1_10" and record.animo == 7
    assert record.mclean_animo is None


def test_disabled_flag_does_not_accept_forged_mclean_submission(client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "formulario_mclean_habilitado", False)
    athlete = crear_usuario(db, username="ui_disabled_forged")
    entrar(client, athlete)
    response = client.post("/parte", data=data(client), follow_redirects=False)
    assert response.status_code == 422
    assert db.query(ParteDiaria).count() == 0
