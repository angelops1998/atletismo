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
            "detalle_sintomas": "tos", "comentarios": "algo", "entreno_hoy": "si", "tipo_entrenamiento_diario": "aerobico",
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
    assert 'name="tipo_entrenamiento_diario"' in page.text


def test_tipo_diario_and_additional_health(client, db, enabled):
    athlete = crear_usuario(db, username="ui_create")
    entrar(client, athlete)
    assert client.post("/parte", data=data(client), follow_redirects=False).status_code == 302
    p = db.query(ParteDiaria).one()
    assert p.tipo_entrenamiento_diario == "aerobico" and not p.sesiones
    assert p.molestia_zona == ["rodillas"] and p.detalle_sintomas == "tos" and p.comentarios == "algo"



def test_422_preserves_input_and_rejects_bad_type(client, db, enabled):
    athlete = crear_usuario(db, username="ui_invalid")
    entrar(client, athlete)
    response = client.post("/parte", data=data(client, tipo_entrenamiento_diario="invalid", comentarios="borrador"), follow_redirects=False)
    assert response.status_code == 422 and "borrador" in response.text
    assert db.query(ParteDiaria).count() == 0



def test_stale_edit_conflict_preserves_committed_data(client, db, enabled):
    athlete = crear_usuario(db, username="ui_conflict")
    entrar(client, athlete)
    body = data(client)
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    stale = token(client)
    record = db.query(ParteDiaria).one()
    record.mclean_animo = 4; db.commit()
    body["edit_state_token"] = stale
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 409
    db.refresh(record); assert record.mclean_animo == 4



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











def test_validation_error_does_not_refresh_stale_token(client, db, enabled):
    athlete = crear_usuario(db, username="ui_stale_422")
    entrar(client, athlete)
    assert client.post("/parte", data=data(client), follow_redirects=False).status_code == 302
    stale = token(client)
    record = db.query(ParteDiaria).one(); record.mclean_animo = 4; db.commit()
    response = client.post("/parte", data=data(client, edit_state_token=stale, tipo_entrenamiento_diario="incorrecto"), follow_redirects=False)
    assert response.status_code == 422 and _hidden(response, "edit_state_token") == stale



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


def test_desactivar_y_restaurar_mclean_conserva_datos_y_acceso_docente(client, db, monkeypatch, enabled):
    athlete = crear_usuario(db, username="ui_cambio_flag")
    teacher = crear_usuario(db, username="ui_cambio_flag_profesor", role="profesor")
    entrar(client, athlete)
    body = data(client)
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    record = db.query(ParteDiaria).one()
    original = (record.mclean_sueno, record.mclean_fatiga, record.mclean_dolor_muscular,
                record.mclean_estres, record.mclean_animo, record.comentarios,
                [(s.tipo_duracion, s.carga_sesion) for s in record.sesiones])
    edit_token = token(client)
    body.update(edit_state_token=edit_token, sesion_id=[str(s.id) for s in record.sesiones])
    monkeypatch.setattr(get_settings(), "formulario_mclean_habilitado", False)
    assert client.get("/parte").status_code == 503
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 503
    entrar(client, teacher)
    ficha = client.get(f"/atletas/{athlete.id}")
    assert ficha.status_code == 200 and "Sueño 4/5" in ficha.text and "Suma 15/25" in ficha.text
    entrar(client, athlete)
    monkeypatch.setattr(get_settings(), "formulario_mclean_habilitado", True)
    assert client.get("/parte").status_code == 200
    db.expire_all()
    assert (record.mclean_sueno, record.mclean_fatiga, record.mclean_dolor_muscular,
            record.mclean_estres, record.mclean_animo, record.comentarios,
            [(s.tipo_duracion, s.carga_sesion) for s in record.sesiones]) == original
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302


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


def _hidden(response, name):
    return re.search(r'name="' + name + r'" value="([^"]*)"', response.text).group(1)


def test_conflict_requires_explicit_review_before_draft_can_overwrite(client, db, enabled):
    athlete = crear_usuario(db, username="ui_review")
    entrar(client, athlete); body = data(client)
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    record = db.query(ParteDiaria).one(); stale = token(client)
    record.comentarios = "servidor"; db.commit()
    body.update(edit_state_token=stale, comentarios="borrador")
    response = client.post("/parte", data=body, follow_redirects=False)
    assert response.status_code == 409 and "borrador" in response.text and "servidor" in response.text
    review = _hidden(response, "review_token"); body["review_token"] = review
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 409
    db.refresh(record); assert record.comentarios == "servidor"
    body["confirmar_revision"] = "si"
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    db.refresh(record); assert record.comentarios == "borrador"



def test_review_token_invalidated_by_further_change_and_422_keeps_tokens(client, db, enabled):
    athlete = crear_usuario(db, username="ui_review_stale")
    entrar(client, athlete); body = data(client)
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    record = db.query(ParteDiaria).one(); stale = token(client)
    record.mclean_animo = 4; db.commit(); body["edit_state_token"] = stale
    first = client.post("/parte", data=body, follow_redirects=False)
    review = _hidden(first, "review_token")
    body.update(review_token=review, confirmar_revision="si", tipo_entrenamiento_diario="invalido")
    invalid = client.post("/parte", data=body, follow_redirects=False)
    assert invalid.status_code == 422 and _hidden(invalid, "edit_state_token") == stale and _hidden(invalid, "review_token") == review
    record.mclean_animo = 3; db.commit(); body["tipo_entrenamiento_diario"] = "fuerza"
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 409
    db.refresh(record); assert record.mclean_animo == 3






def test_no_script_fallback_includes_all_conditional_blocks(client, db, enabled):
    athlete = crear_usuario(db, username="ui_no_script")
    entrar(client, athlete)
    response = client.get("/parte")
    fallback = re.search(r'<noscript>(.*?)</noscript>', response.text, re.DOTALL).group(1)
    for name in ("bloque-entrenamiento", "bloque-molestia", "bloque-sintomas"):
        assert f"#{name}" in fallback
    assert "display: block" in fallback
    # Server accepts all conditional fields without depending on JavaScript.
    assert client.post("/parte", data=data(client), follow_redirects=False).status_code == 302


def test_422_keeps_original_edit_and_discard_tokens(client, db, enabled):
    athlete = crear_usuario(db, username="ui_422_tokens"); entrar(client, athlete)
    assert client.post("/parte", data=data(client), follow_redirects=False).status_code == 302
    page = client.get("/parte"); old_edit = _hidden(page, "edit_state_token"); old_discard = _hidden(page, "discard_token")
    result = client.post("/parte", data=data(client, edit_state_token=old_edit, discard_token=old_discard, tipo_entrenamiento_diario="invalido"), follow_redirects=False)
    assert result.status_code == 422 and _hidden(result, "edit_state_token") == old_edit and _hidden(result, "discard_token") == old_discard



def test_review_token_cannot_be_forged_or_reused_by_another_athlete(client, db, enabled):
    a = crear_usuario(db, username="ui_review_owner")
    b = crear_usuario(db, username="ui_review_other")
    entrar(client, a)
    body_a = data(client)
    assert client.post("/parte", data=body_a, follow_redirects=False).status_code == 302
    rec_a = db.query(ParteDiaria).filter_by(atleta_id=a.id).one()
    old_a = token(client)
    ids_a = [str(s.id) for s in rec_a.sesiones]
    rec_a.mclean_animo = 4; db.commit()
    body_a.update(edit_state_token=old_a, sesion_id=ids_a)
    conflict_a = client.post("/parte", data=body_a, follow_redirects=False)
    assert conflict_a.status_code == 409
    review_a = _hidden(conflict_a, "review_token")
    forged = review_a[:-1] + ("A" if review_a[-1] != "A" else "B")
    body_a.update(review_token=forged, confirmar_revision="si")
    assert client.post("/parte", data=body_a, follow_redirects=False).status_code == 409
    db.refresh(rec_a); assert rec_a.mclean_animo == 4
    entrar(client, b)
    body_b = data(client)
    assert client.post("/parte", data=body_b, follow_redirects=False).status_code == 302
    rec_b = db.query(ParteDiaria).filter_by(atleta_id=b.id).one()
    body_b.update(edit_state_token=token(client), review_token=review_a, confirmar_revision="si",
                  sesion_id=[str(s.id) for s in rec_b.sesiones])
    assert client.post("/parte", data=body_b, follow_redirects=False).status_code == 409
    db.refresh(rec_b); assert rec_b.mclean_animo == 1
