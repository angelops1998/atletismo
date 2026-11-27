import pytest
from datetime import date, timedelta
from app.models import ParteDiaria, SesionEntrenamiento
from app.services import parte_diaria as pd, seguimiento_diario as sd
from app.tiempo import hoy
from conftest import crear_usuario, entrar
from test_formulario_mclean import data, enabled, token


def test_semana_entrenamiento_sin_medicion_no_es_cero(db):
    athlete = crear_usuario(db, username="semana_sin_carga")
    monday = date(2026, 11, 23)
    def record(day, trained):
        return ParteDiaria(atleta_id=athlete.id, fecha=monday + timedelta(days=day),
            sueno_calidad=8, fatiga=7, dolor_muscular=6, estres=5, animo=4,
            horas_sueno=8, entreno_hoy=trained)
    measured, unmeasured, rest = record(0, True), record(1, True), record(2, False)
    unmeasured.tipo_entrenamiento_diario = "aerobico"
    measured.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
        tipo_duracion="no_especificada", duracion_min=30, rpe=5, carga_sesion=999))
    db.add_all([measured, unmeasured, rest]); db.commit()
    assert pd.carga_diaria(None) is None and pd.carga_diaria(unmeasured) is None
    result = pd.aggregate_week_reported(db, athlete.id, monday)
    assert result.dias_con_entreno == 2 and result.dias_reportados == 3
    assert result.cargas_diarias[monday.isoformat()] == 999
    assert result.cargas_diarias[(monday + timedelta(days=1)).isoformat()] is None
    assert result.cargas_diarias[(monday + timedelta(days=2)).isoformat()] == 0
    assert result.cargas_diarias[(monday + timedelta(days=3)).isoformat()] is None
    assert result.carga_semanal is None


def test_estadisticas_separan_sesiones_conservadas_en_descanso(client, db):
    athlete = crear_usuario(db, username="sesiones_descanso")
    teacher = crear_usuario(db, username="profesor_descanso", role="profesor")
    day = date(2026, 11, 23)
    def record(offset, trained, kind, load):
        p = ParteDiaria(atleta_id=athlete.id, fecha=day + timedelta(days=offset),
            sueno_calidad=8, fatiga=7, dolor_muscular=6, estres=5, animo=4,
            horas_sueno=8, entreno_hoy=trained)
        p.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
            tipo_duracion=kind, duracion_min=30, rpe=5, carga_sesion=load))
        return p
    trained = record(0, True, "no_especificada", 999)
    rest1 = record(1, False, "no_especificada", 777)
    rest2 = record(2, False, "trabajo_principal", 555)
    db.add_all([trained, rest1, rest2]); db.commit()
    before = [(s.id, s.carga_sesion, s.tipo_duracion) for s in db.query(SesionEntrenamiento).order_by(SesionEntrenamiento.id)]
    result = sd.resumen_reportes([trained, rest1, rest2], [athlete], day, day + timedelta(days=2))
    assert result["sesiones"]["cantidad"] == 1 and result["sesiones"]["por_tipo"]["no_especificada"]["carga"] == 999
    assert result["sesiones_descanso"]["cantidad"] == 2
    assert result["sesiones_descanso"]["por_tipo"]["no_especificada"]["carga"] == 777
    assert result["sesiones_descanso"]["por_tipo"]["trabajo_principal"]["carga"] == 555
    assert result["filas_atletas"][0]["sesiones_descanso"] == 2
    individual = sd.resumen_diario_atleta(db, athlete.id, desde=day, hasta=day + timedelta(days=2))
    assert individual["sesiones"]["cantidad"] == result["sesiones"]["cantidad"]
    for tipo in ("no_especificada", "trabajo_principal"):
        for campo in ("cantidad", "minutos", "carga"):
            assert individual["sesiones"]["por_tipo"][tipo][campo] == result["sesiones"]["por_tipo"][tipo][campo]
            assert individual["sesiones_descanso"]["por_tipo"][tipo][campo] == result["sesiones_descanso"]["por_tipo"][tipo][campo]
    entrar(client, teacher)
    page = client.get("/estadisticas", params={"desde": day.isoformat(), "hasta": (day + timedelta(days=2)).isoformat()})
    assert page.status_code == 200
    assert "sesiones históricas conservadas en partes marcados como descanso" in page.text
    assert "carga almacenada total 777" in page.text and "carga almacenada total 555" in page.text
    assert "carga almacenada total 999" in page.text
    ficha = client.get(f"/atletas/{athlete.id}", params={"desde": day.isoformat(), "hasta": (day + timedelta(days=2)).isoformat()})
    assert ficha.status_code == 200
    assert "sesiones históricas conservadas en partes marcados como descanso" in ficha.text
    assert "Descanso · Duración no especificada: 1 sesiones · 30 min guardados · carga almacenada total 777" in ficha.text
    assert "Descanso · Trabajo principal: 1 sesiones · 30 min guardados · carga almacenada total 555" in ficha.text
    assert "Duración no especificada: 1 sesiones · 30 min guardados · RPE promedio 5.0 · carga almacenada total 999" in ficha.text
    descanso = client.get(f"/atletas/{athlete.id}", params={"desde": (day + timedelta(days=1)).isoformat(), "hasta": (day + timedelta(days=2)).isoformat()})
    assert "No hay sesiones en partes de entrenamiento" in descanso.text
    assert "2 sesiones históricas conservadas en partes marcados como descanso" in descanso.text
    db.expire_all()
    assert [(s.id, s.carga_sesion, s.tipo_duracion) for s in db.query(SesionEntrenamiento).order_by(SesionEntrenamiento.id)] == before


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
