"""El parte diario: lo que el atleta carga cada dia.

Fase 3: reemplaza el flujo semanal del /parte por el seguimiento diario,
delegando validacion, concurrencia y descarte en los servicios de Phase 2.
"""
from datetime import date, timedelta

import pytest

from app.models.parte import ParteSemanal
from app.models.parte_diaria import ParteDiaria
from app.services import parte_diaria as pd
from conftest import con_csrf, crear_parte, crearonusuario, entrar


def _session_str(items):
    return "\n".join(
        f"{s.get('id','')}|{s.get('orden',1)}|{s.get('tipo_entrenamiento','resistencia')}"
        f"|{s.get('duracion_min',45)}|{s.get('rpe',6)}|{s.get('comentarios_entrenamiento','')}"
        for s in items
    )


def completo(client, **campos):
    datos = {
        "csrf_token": con_csrf(client, "/parte"),
        "sueno_calidad": "7", "horas_sueno": "7.5", "fatiga": "4",
        "dolor_muscular": "3", "estres": "4", "animo": "8",
        "entreno_hoy": "1",
        "sessions": _session_str([{"orden": 1, "tipo_entrenamiento": "resistencia",
                                   "duracion_min": 45, "rpe": 6}]),
    }
    datos.update(campos)
    return datos


@pytest.fixture
def atleta(db):
    return crearonusuario(db, username="atleta1", full_name="Un Atleta")


class TestAcceso:
    def test_el_profesor_no_carga_partes(self, client, db):
        profe = crearonusuario(db, username="profe", role="profesor")
        entrar(client, profe)
        assert client.get("/parte").status_code == 403

    def test_sin_sesion_manda_al_login(self, client):
        r = client.get("/parte", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].startswith("/auth/login")

    def test_csrf_requerido(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client)
        del datos["csrf_token"]
        r = client.post("/parte", data=datos)
        assert r.status_code == 403

    def test_el_atleta_no_puede_escribirle_el_parte_a_otro(self, client, db, atleta):
        otro = crearonusuario(db, username="otro")
        entrar(client, atleta)
        client.post("/parte", data=completo(client, atleta_id=str(otro.id)),
                    follow_redirects=False)
        assert db.query(ParteDiaria).filter(ParteDiaria.atleta_id == atleta.id).count() == 1


class TestCreacionYActualizacion:
    def test_carga_el_parte_diario(self, client, db, atleta):
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client), follow_redirects=False)
        assert r.status_code == 302
        parte = db.query(ParteDiaria).one()
        assert parte.atleta_id == atleta.id
        assert parte.entreno_hoy is True
        assert parte.animo == 8
        assert len(parte.sesiones) == 1
        assert parte.sesiones[0].carga_sesion == 270

    def test_volver_a_entrar_actualiza_en_vez_de_duplicar(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        client.post("/parte", data=completo(client, animo="2"), follow_redirects=False)
        assert db.query(ParteDiaria).count() == 1
        assert db.query(ParteDiaria).one().animo == 2

    def test_sin_entreno_hoy_no_guarda_sesiones(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client, entreno_hoy="0", sessions="")
        r = client.post("/parte", data=datos, follow_redirects=False)
        assert r.status_code == 302
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is False
        assert len(parte.sesiones) == 0

    def test_entreno_hoy_sin_sesiones_es_422(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client, entreno_hoy="1", sessions="")
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        assert db.query(ParteDiaria).count() == 0

    def test_actualizacion_persiste_en_nueva_sesion(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        db.commit()
        db.expire_all()
        entrar(client, atleta)
        client.post("/parte", data=completo(client, animo="9"), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert parte.animo == 9