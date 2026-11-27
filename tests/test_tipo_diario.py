import pytest
from app.models import ParteDiaria, SesionEntrenamiento
from app.tiempo import hoy
from conftest import crear_usuario, entrar
from test_formulario_mclean import data, enabled, token


@pytest.mark.parametrize("tipo", ["aerobico", "lactico", "velocidad", "fuerza"])
def test_cuatro_tipos_sin_sesiones(client, db, enabled, tipo):
    athlete = crear_usuario(db, username="tipo_nuevo")
    entrar(client, athlete)
    assert client.post("/parte", data=data(client, tipo_entrenamiento_diario=tipo), follow_redirects=False).status_code == 302
    record = db.query(ParteDiaria).one()
    assert record.tipo_entrenamiento_diario == tipo and not record.sesiones


def test_creacion_edicion_y_descanso_con_servicio_docente(client, db, enabled):
    athlete = crear_usuario(db, username="tipo_atleta")
    teacher = crear_usuario(db, username="tipo_docente", role="profesor")
    entrar(client, athlete)
    body = data(client, tipo_entrenamiento_diario="lactico")
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    record = db.query(ParteDiaria).one()
    assert record.tipo_entrenamiento_diario == "lactico" and not record.sesiones
    page = client.get("/parte")
    assert "Tipo de entrenamiento" in page.text and "Sesiones realizadas" not in page.text
    body.update(tipo_entrenamiento_diario="fuerza", edit_state_token=token(client))
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    db.refresh(record)
    assert record.tipo_entrenamiento_diario == "fuerza"
    entrar(client, teacher)
    stats = client.get("/estadisticas", params={"desde": hoy().isoformat(), "hasta": hoy().isoformat()})
    assert stats.status_code == 200 and "Tipos de entrenamiento diarios" in stats.text and "Fuerza · 1" in stats.text
    entrar(client, athlete)
    body.update(entreno_hoy="no", tipo_entrenamiento_diario="", edit_state_token=token(client))
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    db.refresh(record)
    assert not record.entreno_hoy and record.tipo_entrenamiento_diario is None


@pytest.mark.parametrize("tipo", ["", "invalido"])
def test_tipo_es_obligatorio_si_entrena(client, db, enabled, tipo):
    athlete = crear_usuario(db, username="tipo_invalido")
    entrar(client, athlete)
    response = client.post("/parte", data=data(client, tipo_entrenamiento_diario=tipo), follow_redirects=False)
    assert response.status_code == 422 and db.query(ParteDiaria).count() == 0


def test_preserva_sesiones_al_editar_y_marcar_descanso(client, db, enabled):
    athlete = crear_usuario(db, username="tipo_preservar")
    record = ParteDiaria(atleta_id=athlete.id, fecha=hoy(), version_cuestionario="mclean_1_5",
        mclean_sueno=1, mclean_fatiga=2, mclean_dolor_muscular=3, mclean_estres=4, mclean_animo=5,
        horas_sueno=8, entreno_hoy=True)
    for i, kind in enumerate(("no_especificada", "trabajo_principal"), 1):
        record.sesiones.append(SesionEntrenamiento(orden=i, tipo_entrenamiento="fuerza", tipo_duracion=kind,
            duracion_min=30, rpe=5, carga_sesion=999+i))
    db.add(record); db.commit()
    before = [(s.id, s.tipo_duracion, s.carga_sesion) for s in record.sesiones]
    entrar(client, athlete)
    body = data(client, tipo_entrenamiento_diario="velocidad", edit_state_token=token(client))
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    db.expire_all()
    assert [(s.id, s.tipo_duracion, s.carga_sesion) for s in record.sesiones] == before
    body.update(entreno_hoy="no", edit_state_token=token(client), delete_session_ids=[str(before[0][0])])
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    db.expire_all()
    assert [(s.id, s.tipo_duracion, s.carga_sesion) for s in record.sesiones] == before
    assert record.tipo_entrenamiento_diario is None


def test_conflicto_por_cambio_de_tipo(client, db, enabled):
    athlete = crear_usuario(db, username="tipo_conflicto")
    entrar(client, athlete)
    body = data(client, tipo_entrenamiento_diario="aerobico")
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    body["edit_state_token"] = token(client)
    record = db.query(ParteDiaria).one()
    record.tipo_entrenamiento_diario = "fuerza"
    db.commit()
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 409
    db.refresh(record)
    assert record.tipo_entrenamiento_diario == "fuerza"


def test_ids_ajenos_no_modifican_sesiones(client, db, enabled):
    owner = crear_usuario(db, username="tipo_dueno")
    other = crear_usuario(db, username="tipo_otro")
    record = ParteDiaria(atleta_id=owner.id, fecha=hoy(), sueno_calidad=8, fatiga=7,
        dolor_muscular=6, estres=5, animo=4, horas_sueno=8, entreno_hoy=True)
    record.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
        tipo_duracion="no_especificada", duracion_min=30, rpe=5, carga_sesion=999))
    db.add(record); db.commit()
    sid = record.sesiones[0].id
    entrar(client, other)
    body = data(client, tipo_entrenamiento_diario="fuerza", delete_session_ids=[str(sid)])
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    db.expire_all()
    assert db.get(SesionEntrenamiento, sid).carga_sesion == 999
