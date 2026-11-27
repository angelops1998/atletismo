"""Flujo HTTP completo de atleta a profesor, con datos aislados en memoria."""
from datetime import timedelta

from app.models import ParteDiaria, SesionEntrenamiento
from app.tiempo import hoy
from conftest import crear_usuario, entrar
from test_formulario_mclean import data, enabled, token


def test_flujo_atleta_profesor_con_historico_y_mclean(client, db, enabled):
    athlete = crear_usuario(db, username="integral_atleta")
    teacher = crear_usuario(db, username="integral_profesor", role="profesor")
    ayer = hoy() - timedelta(days=1)
    historico = ParteDiaria(atleta_id=athlete.id, fecha=ayer, sueno_calidad=10, fatiga=9,
        dolor_muscular=8, estres=7, animo=6, horas_sueno=8, entreno_hoy=True)
    historico.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="resistencia",
        tipo_duracion="no_especificada", duracion_min=40, rpe=5, carga_sesion=999))
    db.add(historico); db.commit()

    entrar(client, athlete)
    invalid = data(client, tipo_entrenamiento_diario="invalido", comentarios="borrador inválido")
    response = client.post("/parte", data=invalid, follow_redirects=False)
    assert response.status_code == 422 and "borrador inválido" in response.text
    assert db.query(ParteDiaria).count() == 1
    body = data(client)
    assert client.post("/parte", data=body, follow_redirects=False).status_code == 302
    actual = db.query(ParteDiaria).filter_by(fecha=hoy()).one()
    assert (actual.mclean_sueno, actual.mclean_fatiga, actual.mclean_dolor_muscular,
            actual.mclean_estres, actual.mclean_animo) == (4, 5, 3, 2, 1)
    assert actual.tipo_entrenamiento_diario == "aerobico" and not actual.sesiones
    body.update(edit_state_token=token(client), sesion_id=[str(s.id) for s in actual.sesiones],
                comentarios="borrador anterior")
    actual.comentarios = "cambio simultáneo"; db.commit()
    conflict = client.post("/parte", data=body, follow_redirects=False)
    assert conflict.status_code == 409 and "borrador anterior" in conflict.text
    db.refresh(actual)
    assert actual.comentarios == "cambio simultáneo" and not actual.sesiones

    entrar(client, teacher)
    ficha = client.get(f"/atletas/{athlete.id}")
    assert ficha.status_code == 200
    for texto in ("Sueño 10/10", "Fatiga 9/10", "Dolor muscular 8/10", "Estrés 7/10", "Ánimo 6/10",
                  "Sueño 4/5", "Fatiga 5/5", "Dolor muscular 3/5", "Estrés 2/5", "Ánimo 1/5",
                  "Suma 15/25", "Promedio 3.0/5", "carga almacenada 999"):
        assert texto in ficha.text
    stats = client.get("/estadisticas", params={"desde": ayer.isoformat(), "hasta": hoy().isoformat()})
    assert stats.status_code == 200
    assert "carga almacenada total 999" in stats.text
    assert "Tipos de entrenamiento diarios" in stats.text and "Aeróbico · 1" in stats.text
    db.expire_all()
    assert historico.sesiones[0].carga_sesion == 999
    assert (historico.sueno_calidad, historico.fatiga, historico.dolor_muscular,
            historico.estres, historico.animo) == (10, 9, 8, 7, 6)
