"""El parte diario: lo que el atleta carga cada dia.

Fase 3: reemplaza el flujo semanal del /parte por el seguimiento diario,
delegando validacion, concurrencia y descarte en los servicios de Phase 2.
"""
from datetime import date, timedelta

import pytest

from app.models.parte import ParteSemanal
from app.models.parte_diaria import ParteDiaria
from app.services import parte_diaria as pd
from conftest import con_csrf, crear_parte, crearadius, entrar


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
        "entreno_hoy": "si",
        "sessions": _session_str([{"orden": 1, "tipo_entrenamiento": "resistencia",
                                   "duracion_min": 45, "rpe": 6}]),
    }
    datos.update(campos)
    return datos


@pytest.fixture
def atleta(db):
    return crearadius(db, username="atleta1", full_name="Un Atleta")


class TestAcceso:
    def test_el_profesor_no_carga_partes(self, client, db):
        profe = crearadius(db, username="profe", role="profesor")
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
        otro = crearadius(db, username="otro")
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
        assert parte.fatiga == 4
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
        datos = completo(client, entreno_hoy="no", sessions="")
        r = client.post("/parte", data=datos, follow_redirects=False)
        assert r.status_code == 302
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is False
        assert len(parte.sesiones) == 0

    def test_entreno_hoy_sin_sesiones_es_422(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client, entreno_hoy="si", sessions="")
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

    def test_no_hay_duplicado(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        client.post("/parte", data=completo(client), follow_redirects=False)
        assert db.query(ParteDiaria).count() == 1

class TestValidacion:
    def test_faltando_una_respuesta_no_guarda(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client)
        del datos["animo"]
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        assert db.query(ParteDiaria).count() == 0

    @pytest.mark.parametrize("valor", ["0", "11", "-1", "abc"])
    def test_puntaje_fuera_de_la_escala_no_guarda(self, client, db, atleta, valor):
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client, animo=valor))
        assert r.status_code == 422
        assert db.query(ParteDiaria).count() == 0

    def test_molestia_pide_zona_y_dolor(self, client, db, atleta):
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client, hay_molestia="si"))
        assert r.status_code == 422
        assert "molestia" in r.text.lower()

    def test_molestia_completa_se_guarda(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client, hay_molestia="si",
                                            molestia_zona="rodillas",
                                            molestia_dolor="7",
                                            afecta_entrenamiento="1"),
                    follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert parte.hay_molestia is True
        assert parte.molestia_dolor == 7
        assert parte.afecta_entrenamiento == 1

    def test_los_numeros_con_coma_se_entienden(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client, horas_sueno="7,5"),
                    follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert float(parte.horas_sueno) == 7.5

    def test_valores_imposibles_se_descartan(self, client, db, atleta):
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client, horas_sueno="48"))
        assert r.status_code == 422
        assert db.query(ParteDiaria).count() == 0

    def test_valores_preservados_en_422(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client, animo="abc")
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        assert "animo" in r.text
        assert db.query(ParteDiaria).count() == 0

class TestSesiones:
    def test_crear_y_actualizar_sesion(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        sid = parte.sesiones[0].id
        datos = completo(client,
                         sessions=_session_str([{"id": sid, "orden": 1,
                                                 "tipo_entrenamiento": "fuerza",
                                                 "duracion_min": 30, "rpe": 8}]))
        client.post("/parte", data=datos, follow_redirects=False)
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert len(parte.sesiones) == 1
        assert parte.sesiones[0].id == sid
        assert parte.sesiones[0].tipo_entrenamiento == "fuerza"
        assert parte.sesiones[0].carga_sesion == 240

    def test_nueva_sesion_sin_id(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        datos = completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ]))
        client.post("/parte", data=datos, follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert len(parte.sesiones) == 2

    def test_eliminar_sesion_explicitamente(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        sid = parte.sesiones[0].id
        datos = completo(client, entreno_hoy="si",
                         sessions="",
                         delete_session_ids=str(sid))
        client.post("/parte", data=datos, follow_redirects=False)
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert len(parte.sesiones) == 0

    def test_eliminar_varias_sesiones(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ]))
        client.post("/parte", data=datos, follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        ids = [s.id for s in parte.sesiones]
        datos = completo(client, entreno_hoy="si", sessions="",
                         delete_session_ids=",".join(str(i) for i in ids))
        client.post("/parte", data=datos, follow_redirects=False)
        db.expire_all()
        assert len(db.query(ParteDiaria).one().sesiones) == 0

    def test_id_ajeno_rechazado(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        datos = completo(client, sessions=_session_str([{"id": 99999, "orden": 1,
                                                          "tipo_entrenamiento": "resistencia",
                                                          "duracion_min": 45, "rpe": 6}]))
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        assert db.query(ParteDiaria).count() == 1

    def test_sesiones_no_eliminadas_no_se_boran(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        sid = parte.sesiones[0].id
        datos = completo(client, entreno_hoy="si",
                         sessions=_session_str([{"id": sid, "orden": 1,
                                                 "tipo_entrenamiento": "resistencia",
                                                 "duracion_min": 45, "rpe": 6}]))
        client.post("/parte", data=datos, follow_redirects=False)
        db.expire_all()
        assert len(db.query(ParteDiaria).one().sesiones) == 1

class TestDescarte:
    def _crear_con_sesiones(self, client, db, atleta):
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        return parte

    def test_descarte_sin_confirmacion_es_422(self, client, db, atleta):
        entrar(client, atleta)
        self._crear_con_sesiones(client, db, atleta)
        datos = completo(client, entreno_hoy="no", sessions="")
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is True
        assert len(parte.sesiones) == 1

    def test_descarte_sin_token_es_422(self, client, db, atleta):
        entrar(client, atleta)
        self._crear_con_sesiones(client, db, atleta)
        datos = completo(client, entreno_hoy="no", sessions="",
                         confirm_discard_sessions="si")
        r = client.post("/parte", data=datos)
        assert r.status_code == 422

    def test_descarte_valido(self, client, db, atleta):
        entrar(client, atleta)
        self._crear_con_sesiones(client, db, atleta)
        # Step 1: intento -> 422 con discard_token
        datos = completo(client, entreno_hoy="no", sessions="")
        r1 = client.post("/parte", data=datos)
        assert r1.status_code == 422
        # Extract discard_token from the rendered form
        import re
        m = re.search(r'name="discard_token" value="([^"]+)"', r1.text)
        assert m, "descarte token debe estar en el formulario"
        discard_tok = m.group(1)
        datos2 = completo(client, entreno_hoy="no", sessions="",
                          confirm_discard_sessions="si",
                          discard_token=discard_tok)
        r2 = client.post("/parte", data=datos2, follow_redirects=False)
        assert r2.status_code == 302
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is False
        assert len(parte.sesiones) == 0

    def test_descarte_stale_es_409(self, client, db, atleta):
        entrar(client, atleta)
        self._crear_con_sesiones(client, db, atleta)
        # Get fresh tokens
        datos = completo(client, entreno_hoy="no", sessions="")
        r1 = client.post("/parte", data=datos)
        import re
        m = re.search(r'name="discard_token" value="([^"]+)"', r1.text)
        discard_tok = m.group(1)
        # Mutate sessions directly (simulating concurrent change)
        parte = db.query(ParteDiaria).one()
        from app.models.sesion_entrenamiento import SesionEntrenamiento
        db.add(SesionEntrenamiento(parte_diaria_id=parte.id, orden=2,
                                   tipo_entrenamiento="fuerza",
                                   duracion_min=30, rpe=8, carga_sesion=240))
        db.commit()
        datos2 = completo(client, entreno_hoy="no", sessions="",
                          confirm_discard_sessions="si",
                          discard_token=discard_tok)
        r2 = client.post("/parte", data=datos2)
        assert r2.status_code == 409
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is True
        assert len(parte.sesiones) == 2

    def test_descarte_no_es_silencioso(self, client, db, atleta):
        """Un booleano solo no debe borrar sesiones."""
        entrar(client, atleta)
        self._crear_con_sesiones(client, db, atleta)
        datos = completo(client, entreno_hoy="no", sessions="")
        datos.pop("confirm_discard_sessions", None)
        client.post("/parte", data=datos)
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is True
        assert len(parte.sesiones) == 1

class TestConflictos:
    def test_edicion_stale_es_409(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        # Capture edit token from GET
        r_get = client.get("/parte")
        import re
        m = re.search(r'name="edit_state_token" value="([^"]+)"', r_get.text)
        edit_tok = m.group(1) if m else None
        # Mutate directly (simulating concurrent change)
        parte.animo = 5
        db.commit()
        datos = completo(client, animo="9", edit_state_token=edit_tok or "")
        r = client.post("/parte", data=datos)
        assert r.status_code == 409
        db.expire_all()
        assert db.query(ParteDiaria).one().animo == 5

    def test_409_preserva_lo_submitido(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        r_get = client.get("/parte")
        import re
        m = re.search(r'name="edit_state_token" value="([^"]+)"', r_get.text)
        edit_tok = m.group(1) if m else None
        parte.animo = 5
        db.commit()
        datos = completo(client, animo="9", edit_state_token=edit_tok or "")
        r = client.post("/parte", data=datos)
        assert r.status_code == 409
        # The submitted value must still be visible (not silently replaced)
        assert "9" in r.text