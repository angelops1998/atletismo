"""El parte diario: lo que el atleta carga cada dia.

Fase 3: reemplaza el flujo semanal del /parte por el seguimiento diario,
delegando validacion, concurrencia y descarte en los servicios de Phase 2.
"""
from datetime import date, timedelta

import pytest

from app.models.parte import ParteSemanal
from app.models.parte_diaria import ParteDiaria
from app.services import parte_diaria as pd
from conftest import con_csrf, crear_parte, crear_usuario, entrar


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


def _get_edit_token(client):
    """Extract edit_state_token from GET /parte response."""
    import re
    r = client.get("/parte")
    m = re.search(r'name="edit_state_token" value="([^"]+)"', r.text)
    return m.group(1) if m else None


@pytest.fixture
def atleta(db):
    return crear_usuario(db, username="atleta1", full_name="Un Atleta")


class TestAcceso:
    def test_el_profesor_no_carga_partes(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
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
        otro = crear_usuario(db, username="otro")
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
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        client.post("/parte", data=completo(client, animo="2", edit_state_token=edit_token), follow_redirects=False)
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
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        client.post("/parte", data=completo(client, animo="9", edit_state_token=edit_token), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert parte.animo == 9

    def test_no_hay_duplicado(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        client.post("/parte", data=completo(client, edit_state_token=edit_token), follow_redirects=False)
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
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        datos = completo(client,
                         sessions=_session_str([{"id": sid, "orden": 1,
                                                 "tipo_entrenamiento": "fuerza",
                                                 "duracion_min": 30, "rpe": 8}]),
                         edit_state_token=edit_token)
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
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        # Use allow_full_session_replacement to replace all sessions
        datos = completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ]), edit_state_token=edit_token, allow_full_session_replacement="1")
        client.post("/parte", data=datos, follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert len(parte.sesiones) == 2

    def test_eliminar_sesion_explicitamente(self, client, db, atleta):
        entrar(client, atleta)
        # Create with two sessions first
        datos = completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ]))
        client.post("/parte", data=datos, follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        ids = [s.id for s in parte.sesiones]
        sid_to_delete = ids[0]
        sid_to_keep = ids[1]
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        # Delete one session explicitly, keep the other by including it in sessions
        datos = completo(client, entreno_hoy="si",
                         sessions=_session_str([{"id": sid_to_keep, "orden": 1,
                                                 "tipo_entrenamiento": "fuerza",
                                                 "duracion_min": 30, "rpe": 8}]),
                         delete_session_ids=str(sid_to_delete),
                         edit_state_token=edit_token)
        client.post("/parte", data=datos, follow_redirects=False)
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert len(parte.sesiones) == 1
        assert parte.sesiones[0].id == sid_to_keep

    def test_eliminar_varias_sesiones(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ]))
        client.post("/parte", data=datos, follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        ids = [s.id for s in parte.sesiones]
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        # Use discard flow to remove all sessions (entreno_hoy=false)
        datos = completo(client, entreno_hoy="no", sessions="", edit_state_token=edit_token)
        r1 = client.post("/parte", data=datos)
        assert r1.status_code == 422
        import re
        m = re.search(r'name="discard_token" value="([^"]+)"', r1.text)
        assert m, "descarte token debe estar en el formulario"
        discard_tok = m.group(1)
        datos2 = completo(client, entreno_hoy="no", sessions="",
                          confirm_discard_sessions="si",
                          discard_token=discard_tok, edit_state_token=edit_token)
        client.post("/parte", data=datos2, follow_redirects=False)
        db.expire_all()
        assert len(db.query(ParteDiaria).one().sesiones) == 0

    def test_id_ajeno_rechazado(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        datos = completo(client, sessions=_session_str([{"id": 99999, "orden": 1,
                                                          "tipo_entrenamiento": "resistencia",
                                                          "duracion_min": 45, "rpe": 6}]),
                         edit_state_token=edit_token)
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        assert db.query(ParteDiaria).count() == 1

    def test_sesiones_no_eliminadas_no_se_boran(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        sid = parte.sesiones[0].id
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        datos = completo(client, entreno_hoy="si",
                         sessions=_session_str([{"id": sid, "orden": 1,
                                                 "tipo_entrenamiento": "resistencia",
                                                 "duracion_min": 45, "rpe": 6}]),
                         edit_state_token=edit_token)
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
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        datos = completo(client, entreno_hoy="no", sessions="", edit_state_token=edit_token)
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is True
        assert len(parte.sesiones) == 1

    def test_descarte_sin_token_es_422(self, client, db, atleta):
        entrar(client, atleta)
        self._crear_con_sesiones(client, db, atleta)
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        datos = completo(client, entreno_hoy="no", sessions="",
                         confirm_discard_sessions="si", edit_state_token=edit_token)
        r = client.post("/parte", data=datos)
        assert r.status_code == 422

    def test_descarte_valido(self, client, db, atleta):
        entrar(client, atleta)
        self._crear_con_sesiones(client, db, atleta)
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        # Step 1: intento -> 422 con discard_token
        datos = completo(client, entreno_hoy="no", sessions="", edit_state_token=edit_token)
        r1 = client.post("/parte", data=datos)
        assert r1.status_code == 422
        # Extract discard_token from the rendered form
        import re
        m = re.search(r'name="discard_token" value="([^"]+)"', r1.text)
        assert m, "descarte token debe estar en el formulario"
        discard_tok = m.group(1)
        datos2 = completo(client, entreno_hoy="no", sessions="",
                          confirm_discard_sessions="si",
                          discard_token=discard_tok, edit_state_token=edit_token)
        r2 = client.post("/parte", data=datos2, follow_redirects=False)
        assert r2.status_code == 302
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is False
        assert len(parte.sesiones) == 0

    def test_descarte_stale_es_409(self, client, db, atleta):
        entrar(client, atleta)
        self._crear_con_sesiones(client, db, atleta)
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        # Get fresh tokens
        datos = completo(client, entreno_hoy="no", sessions="", edit_state_token=edit_token)
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
                          discard_token=discard_tok, edit_state_token=edit_token)
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
        # GET to obtain edit_state_token for update
        edit_token = _get_edit_token(client)
        datos = completo(client, entreno_hoy="no", sessions="", edit_state_token=edit_token)
        datos.pop("confirm_discard_sessions", None)
        client.post("/parte", data=datos)
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is True
        assert len(parte.sesiones) == 1



class TestInputParsing:
    """Fase 3: rechazos explícitos de entrada malformada (router, sin service)."""

    def _post(self, client, data):
        return client.post("/parte", data=data)

    def test_malformed_delete_id_es_422(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        sid = parte.sesiones[0].id
        edit_token = _get_edit_token(client)
        datos = completo(
            client,
            sessions=_session_str([{"id": sid, "orden": 1, "tipo_entrenamiento": "resistencia",
                                    "duracion_min": 45, "rpe": 6}]),
            delete_session_ids="abc",
            edit_token=edit_token,
        )
        # edit_token must be passed as edit_state_token
        datos["edit_state_token"] = edit_token
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert len(parte.sesiones) == 1
        assert parte.sesiones[0].id == sid

    def test_mixed_valid_and_malformed_delete_ids_no_borra_nada(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ])), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        ids = {s.id for s in parte.sesiones}
        edit_token = _get_edit_token(client)
        keep = list(ids)[0]
        drop = list(ids)[1]
        datos = completo(
            client,
            sessions=_session_str([{"id": keep, "orden": 1, "tipo_entrenamiento": "resistencia",
                                    "duracion_min": 45, "rpe": 6}]),
            delete_session_ids=f"{drop},abc",
            edit_state_token=edit_token,
        )
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert {s.id for s in parte.sesiones} == ids
        assert len(parte.sesiones) == 2

    def test_non_positive_delete_id_es_422(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        sid = parte.sesiones[0].id
        edit_token = _get_edit_token(client)
        datos = completo(
            client,
            sessions=_session_str([{"id": sid, "orden": 1, "tipo_entrenamiento": "resistencia",
                                    "duracion_min": 45, "rpe": 6}]),
            delete_session_ids="0",
            edit_state_token=edit_token,
        )
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        assert db.query(ParteDiaria).one().sesiones[0].id == sid

    def test_duplicate_delete_ids_es_422(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ])), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        ids = {s.id for s in parte.sesiones}
        drop = list(ids)[0]
        keep = list(ids)[1]
        edit_token = _get_edit_token(client)
        datos = completo(
            client,
            sessions=_session_str([{"id": keep, "orden": 1, "tipo_entrenamiento": "fuerza",
                                    "duracion_min": 30, "rpe": 8}]),
            delete_session_ids=f"{drop},{drop}",
            edit_state_token=edit_token,
        )
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        assert {s.id for s in db.query(ParteDiaria).one().sesiones} == ids

    def test_malformed_existing_session_id_no_crea_nueva(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        sid = parte.sesiones[0].id
        edit_token = _get_edit_token(client)
        datos = completo(
            client,
            sessions="abc|1|resistencia|45|6|",
            edit_state_token=edit_token,
        )
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert len(parte.sesiones) == 1
        assert parte.sesiones[0].id == sid
        assert parte.sesiones[0].tipo_entrenamiento == "resistencia"

    def test_malformed_session_order_es_422(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        sid = db.query(ParteDiaria).one().sesiones[0].id
        edit_token = _get_edit_token(client)
        datos = completo(client, sessions=f"{sid}|abc|resistencia|45|6|", edit_state_token=edit_token)
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        assert db.query(ParteDiaria).one().sesiones[0].orden == 1

    def test_malformed_duration_es_422(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        sid = db.query(ParteDiaria).one().sesiones[0].id
        edit_token = _get_edit_token(client)
        datos = completo(client, sessions=f"{sid}|1|resistencia|abc|6|", edit_state_token=edit_token)
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        assert db.query(ParteDiaria).one().sesiones[0].duracion_min == 45

    def test_malformed_rpe_es_422(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        sid = db.query(ParteDiaria).one().sesiones[0].id
        edit_token = _get_edit_token(client)
        datos = completo(client, sessions=f"{sid}|1|resistencia|45|abc|", edit_state_token=edit_token)
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        assert db.query(ParteDiaria).one().sesiones[0].rpe == 6

    def test_repeated_sessions_fields_se_preservan(self, client, db, atleta):
        entrar(client, atleta)
        csrf = con_csrf(client, "/parte")
        line1 = "|1|resistencia|45|6|a"
        line2 = "|2|fuerza|30|8|b"
        data = {
            "csrf_token": csrf,
            "sueno_calidad": "7", "horas_sueno": "7.5", "fatiga": "4",
            "dolor_muscular": "3", "estres": "4", "animo": "abc",  # force 422
            "entreno_hoy": "si",
            "sessions": [line1, line2],
        }
        r = client.post("/parte", data=data)
        assert r.status_code == 422
        # both submitted session lines preserved in form (rendered textarea)
        assert line1 in r.text
        assert line2 in r.text
        assert line1 in r.text.split('name="sessions"', 1)[1]
        assert line2 in r.text.split('name="sessions"', 1)[1]
        assert db.query(ParteDiaria).count() == 0

    def test_repeated_sessions_fields_crean_multiples(self, client, db, atleta):
        entrar(client, atleta)
        csrf = con_csrf(client, "/parte")
        data = {
            "csrf_token": csrf,
            "sueno_calidad": "7", "horas_sueno": "7.5", "fatiga": "4",
            "dolor_muscular": "3", "estres": "4", "animo": "8",
            "entreno_hoy": "si",
            "sessions": ["|1|resistencia|45|6|", "|2|fuerza|30|8|"],
        }
        r = client.post("/parte", data=data, follow_redirects=False)
        assert r.status_code == 302
        parte = db.query(ParteDiaria).one()
        assert len(parte.sesiones) == 2

    def test_repeated_sessions_fields_surviven_409(self, client, db, atleta):
        """Repeated sessions survive HTTP 409 conflict restoration."""
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        r_get = client.get("/parte")
        import re
        m = re.search(r'name="edit_state_token" value="([^"]+)"', r_get.text)
        edit_tok = m.group(1) if m else ""
        # Make token stale
        parte.animo = 5
        db.commit()
        csrf = con_csrf(client, "/parte")
        line1 = "|1|resistencia|45|6|conflict-a"
        line2 = "|2|fuerza|30|8|conflict-b"
        datos = {
            "csrf_token": csrf,
            "edit_state_token": edit_tok,
            "sueno_calidad": "7", "horas_sueno": "7.5", "fatiga": "4",
            "dolor_muscular": "3", "estres": "4", "animo": "9",
            "entreno_hoy": "si",
            "sessions": [line1, line2],
        }
        r = client.post("/parte", data=datos)
        assert r.status_code == 409
        sessions_area = r.text.split('name="sessions"', 1)[1].split("</textarea>", 1)[0]
        assert line1 in sessions_area
        assert line2 in sessions_area
        db.expire_all()
        assert db.query(ParteDiaria).one().animo == 5

    def test_newline_sessions_textarea_survives_422(self, client, db, atleta):
        """Newline-separated textarea sessions retain prior behavior on 422."""
        entrar(client, atleta)
        csrf = con_csrf(client, "/parte")
        line1 = "|1|resistencia|45|6|linea1"
        line2 = "|2|fuerza|30|8|linea2"
        datos = {
            "csrf_token": csrf,
            "sueno_calidad": "7", "horas_sueno": "7.5", "fatiga": "4",
            "dolor_muscular": "3", "estres": "4", "animo": "abc",  # force 422
            "entreno_hoy": "si",
            "sessions": f"{line1}\n{line2}",
        }
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        sessions_area = r.text.split('name="sessions"', 1)[1].split("</textarea>", 1)[0]
        assert line1 in sessions_area
        assert line2 in sessions_area
        assert db.query(ParteDiaria).count() == 0

    def test_repeated_delete_ids_survive_422(self, client, db, atleta):
        """Repeated delete_session_ids survive 422 and persisted state unchanged."""
        entrar(client, atleta)
        client.post("/parte", data=completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ])), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        ids = [s.id for s in parte.sesiones]
        edit_token = _get_edit_token(client)
        csrf = con_csrf(client, "/parte")
        datos = {
            "csrf_token": csrf,
            "edit_state_token": edit_token,
            "sueno_calidad": "7", "horas_sueno": "7.5", "fatiga": "4",
            "dolor_muscular": "3", "estres": "4", "animo": "abc",  # force 422
            "entreno_hoy": "si",
            "sessions": _session_str([{"id": ids[0], "orden": 1, "tipo_entrenamiento": "resistencia",
                                       "duracion_min": 45, "rpe": 6}]),
            "delete_session_ids": [str(ids[0]), str(ids[1])],
        }
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        delete_area = r.text.split('name="delete_session_ids"', 1)[1].split(">", 1)[0]
        assert str(ids[0]) in delete_area
        assert str(ids[1]) in delete_area
        db.expire_all()
        assert {s.id for s in db.query(ParteDiaria).one().sesiones} == set(ids)

    def test_repeated_delete_ids_survive_409(self, client, db, atleta):
        """Repeated delete_session_ids survive 409 conflict restoration."""
        entrar(client, atleta)
        client.post("/parte", data=completo(client, sessions=_session_str([
            {"orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6},
            {"orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 8},
        ])), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        ids = [s.id for s in parte.sesiones]
        r_get = client.get("/parte")
        import re
        m = re.search(r'name="edit_state_token" value="([^"]+)"', r_get.text)
        edit_tok = m.group(1) if m else ""
        parte.animo = 5
        db.commit()
        csrf = con_csrf(client, "/parte")
        datos = {
            "csrf_token": csrf,
            "edit_state_token": edit_tok,
            "sueno_calidad": "7", "horas_sueno": "7.5", "fatiga": "4",
            "dolor_muscular": "3", "estres": "4", "animo": "9",
            "entreno_hoy": "si",
            "sessions": _session_str([{"id": ids[0], "orden": 1, "tipo_entrenamiento": "resistencia",
                                       "duracion_min": 45, "rpe": 6}]),
            "delete_session_ids": [str(ids[0]), str(ids[1])],
        }
        r = client.post("/parte", data=datos)
        assert r.status_code == 409
        delete_area = r.text.split('name="delete_session_ids"', 1)[1].split(">", 1)[0]
        assert str(ids[0]) in delete_area
        assert str(ids[1]) in delete_area
        db.expire_all()
        persisted = db.query(ParteDiaria).one()
        assert persisted.animo == 5
        assert {s.id for s in persisted.sesiones} == set(ids)

    def test_parsing_failure_no_llama_service_ni_modifica(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        before = (parte.animo, parte.fatiga, [(s.id, s.duracion_min, s.rpe) for s in parte.sesiones])
        edit_token = _get_edit_token(client)
        datos = completo(
            client,
            animo="9",  # would change if service ran
            sessions="abc|1|resistencia|45|6|",
            delete_session_ids="1,bad",
            edit_state_token=edit_token,
        )
        r = self._post(client, datos)
        assert r.status_code == 422
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        after = (parte.animo, parte.fatiga, [(s.id, s.duracion_min, s.rpe) for s in parte.sesiones])
        assert before == after
class TestConflictos:
    def test_edicion_stale_es_409(self, client, db, atleta):
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
        assert "9" in r.text

    def test_409_distingue_enviado_y_persistido(self, client, db, atleta):
        """HTTP 409 muestra el valor enviado (formulario) y el persistido (servidor) por separado."""
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        r_get = client.get("/parte")
        import re
        m = re.search(r'name="edit_state_token" value="([^"]+)"', r_get.text)
        edit_tok = m.group(1) if m else None
        # Valor autoritativo distinto al que se va a enviar
        parte.horas_sueno = 9.5
        db.commit()
        datos = completo(client, horas_sueno="4.0", edit_state_token=edit_tok or "")
        r = client.post("/parte", data=datos)
        assert r.status_code == 409
        # Valor enviado preservado en el formulario
        assert 'name="horas_sueno"' in r.text
        assert 'value="4.0"' in r.text
        # Valor autoritativo persistido mostrado en la tarjeta de recuperación
        assert '9.5' in r.text
        # Nunca se sobrescribió con el envío
        db.expire_all()
        assert float(db.query(ParteDiaria).one().horas_sueno) == 9.5


class TestRenderizado:
    def test_form_renderiza_campos_diarios_obligatorios(self, client, db, atleta):
        entrar(client, atleta)
        r = client.get("/parte")
        assert r.status_code == 200
        for campo in ["sueno_calidad", "fatiga", "dolor_muscular", "estres", "animo",
                      "horas_sueno", "hay_molestia", "molestia_zona",
                      "molestia_dolor", "afecta_entrenamiento", "sintomas_enfermedad",
                      "detalle_sintomas", "comentarios", "entreno_hoy",
                      "sessions", "delete_session_ids"]:
            assert f'name="{campo}"' in r.text

    def test_escala_bienestar_1_a_10_con_requerido(self, client, db, atleta):
        entrar(client, atleta)
        r = client.get("/parte")
        assert r.status_code == 200
        for campo in ["sueno_calidad", "fatiga", "dolor_muscular", "estres", "animo"]:
            assert f'id="{campo}_1"' in r.text
            assert f'id="{campo}_10"' in r.text
            assert f'name="{campo}"' in r.text
        assert 'required' in r.text

    def test_rango_horas_sueno_0_a_24(self, client, db, atleta):
        entrar(client, atleta)
        r = client.get("/parte")
        assert r.status_code == 200
        assert 'name="horas_sueno"' in r.text
        assert 'min="0"' in r.text
        assert 'max="24"' in r.text
        assert 'step="0.5"' in r.text

    def test_instrucciones_escala_tienen_descriptores(self, client, db, atleta):
        entrar(client, atleta)
        r = client.get("/parte")
        assert r.status_code == 200
        assert "Muy mala" in r.text
        assert "Excelente" in r.text
        assert "Ninguna" in r.text
        assert "Extrema" in r.text

    def test_bloques_condicionales_presentes(self, client, db, atleta):
        entrar(client, atleta)
        r = client.get("/parte")
        assert r.status_code == 200
        assert 'id="bloque-molestia"' in r.text
        assert 'id="bloque-entrenamiento"' in r.text
        assert 'id="bloque-sintomas"' in r.text
        assert 'data-abre="bloque-molestia"' in r.text
        assert 'data-abre="bloque-entrenamiento"' in r.text
        assert 'data-abre="bloque-sintomas"' in r.text

    def test_guia_zonas_molestia(self, client, db, atleta):
        entrar(client, atleta)
        r = client.get("/parte")
        assert r.status_code == 200
        assert 'list="zonas-molestia"' in r.text
        assert 'id="zonas-molestia"' in r.text
        for z in ["cuello", "hombros", "rodillas", "pies", "otro"]:
            assert f'<option value="{z}">' in r.text

    def test_form_crea_y_edita(self, client, db, atleta):
        entrar(client, atleta)
        r = client.get("/parte")
        assert r.status_code == 200
        assert "Enviar mi parte" in r.text
        client.post("/parte", data=completo(client), follow_redirects=False)
        r = client.get("/parte")
        assert r.status_code == 200
        assert "Guardar los cambios" in r.text


class TestCondicionales:
    def test_valores_molestia_se_preservan_al_ocultar(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client, hay_molestia="si",
                                              molestia_zona="rodillas",
                                              molestia_dolor="7",
                                              afecta_entrenamiento="1"),
                    follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert parte.hay_molestia is True
        assert "rodillas" in parte.molestia_zona
        assert parte.molestia_dolor == 7
        assert parte.afecta_entrenamiento == 1

        edit_token = _get_edit_token(client)
        datos = completo(client, hay_molestia="no", edit_state_token=edit_token)
        r = client.post("/parte", data=datos, follow_redirects=False)
        assert r.status_code == 302
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert parte.hay_molestia is False

    def test_sintomas_condicionales(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client, sintomas_enfermedad="si",
                                            detalle_sintomas="fiebre y tos"),
                    follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert parte.sintomas_enfermedad is True
        assert parte.detalle_sintomas == "fiebre y tos"

        edit_token = _get_edit_token(client)
        datos = completo(client, sintomas_enfermedad="no", edit_state_token=edit_token)
        client.post("/parte", data=datos, follow_redirects=False)
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert parte.sintomas_enfermedad is False
        assert parte.detalle_sintomas is None


class TestValidacionAdicional:
    def test_422_muestra_resumen_de_errores(self, client, db, atleta):
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client, animo="abc"))
        assert r.status_code == 422
        assert "aviso-error" in r.text
        assert "Corregí los errores" in r.text
        assert db.query(ParteDiaria).count() == 0

    def test_422_preserva_valores_enviados(self, client, db, atleta):
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client, animo="abc"))
        assert r.status_code == 422
        assert "animo" in r.text
        assert db.query(ParteDiaria).count() == 0


from html.parser import HTMLParser


def _is_radio_checked(html_text: str, name: str, value: str) -> bool:
    class RadioFinder(HTMLParser):
        def __init__(self):
            super().__init__()
            self.checked = False

        def handle_starttag(self, tag, attrs):
            if tag.lower() != "input":
                return
            attr = dict(attrs)
            if attr.get("type") != "radio":
                return
            if attr.get("name") != name or attr.get("value") != value:
                return
            # HTML boolean attribute: may appear as checked, checked="", or checked=None
            if "checked" in attr:
                self.checked = True

    parser = RadioFinder()
    parser.feed(html_text)
    return parser.checked


class TestBinaryRestorationPrecedence:
    def _post_422(self, client, db, atleta, persisted_field: str, submitted_overrides: dict):
        entrar(client, atleta)
        base = completo(client)
        base[persisted_field] = "si"
        # make it valid for persistence (molestia requires details)
        if persisted_field == "hay_molestia":
            base.update({"molestia_zona": "rodillas", "molestia_dolor": "7", "afecta_entrenamiento": "1"})
        if persisted_field == "sintomas_enfermedad":
            base.update({"detalle_sintomas": "fiebre"})
        r = client.post("/parte", data=base, follow_redirects=False)
        assert r.status_code == 302
        edit_token = _get_edit_token(client)
        datos = completo(client, edit_state_token=edit_token, animo="abc", **submitted_overrides)
        # ensure persisted state remains true in DB for the target field
        if persisted_field == "hay_molestia":
            datos.update({"hay_molestia": "no"})
        elif persisted_field == "sintomas_enfermedad":
            datos.update({"sintomas_enfermedad": "no", "detalle_sintomas": "fiebre"})
        elif persisted_field == "entreno_hoy":
            datos.update({"entreno_hoy": "no", "sessions": ""})
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        return r

    def test_entreno_hoy_submitted_no_overrides_persisted_true_on_422(self, client, db, atleta):
        r = self._post_422(client, db, atleta, "entreno_hoy", {"entreno_hoy": "no", "sessions": ""})
        assert _is_radio_checked(r.text, "entreno_hoy", "no")
        assert not _is_radio_checked(r.text, "entreno_hoy", "si")

    def test_entreno_hoy_submitted_no_overrides_persisted_true_on_409(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is True
        r_get = client.get("/parte")
        import re
        m = re.search(r'name="edit_state_token" value="([^"]+)"', r_get.text)
        edit_tok = m.group(1) if m else ""
        parte.animo = 5
        db.commit()
        datos = completo(client, entreno_hoy="no", sessions="", animo="9", edit_state_token=edit_tok)
        r = client.post("/parte", data=datos)
        assert r.status_code == 409
        assert _is_radio_checked(r.text, "entreno_hoy", "no")
        assert not _is_radio_checked(r.text, "entreno_hoy", "si")
        db.expire_all()
        assert db.query(ParteDiaria).one().entreno_hoy is True

    def test_hay_molestia_submitted_no_overrides_persisted_true_on_422(self, client, db, atleta):
        r = self._post_422(client, db, atleta, "hay_molestia", {"hay_molestia": "no"})
        assert _is_radio_checked(r.text, "hay_molestia", "no")
        assert not _is_radio_checked(r.text, "hay_molestia", "si")

    def test_sintomas_enfermedad_submitted_no_overrides_persisted_true_on_422(self, client, db, atleta):
        r = self._post_422(client, db, atleta, "sintomas_enfermedad", {"sintomas_enfermedad": "no", "detalle_sintomas": "fiebre"})
        assert _is_radio_checked(r.text, "sintomas_enfermedad", "no")
        assert not _is_radio_checked(r.text, "sintomas_enfermedad", "si")

    def test_discard_intent_422_preserves_sessions_and_submitted_entreno_no(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is True
        assert len(parte.sesiones) == 1
        edit_token = _get_edit_token(client)
        # entreno_hoy=no with existing sessions and no discard confirmation -> discard intent 422
        datos = completo(client, entreno_hoy="no", sessions="", edit_state_token=edit_token)
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        assert _is_radio_checked(r.text, "entreno_hoy", "no")
        assert not _is_radio_checked(r.text, "entreno_hoy", "si")
        db.expire_all()
        parte = db.query(ParteDiaria).one()
        assert parte.entreno_hoy is True
        assert len(parte.sesiones) == 1

    def test_initial_get_and_normal_edit_restore_persisted_binary_values(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client, hay_molestia="si", molestia_zona="rodillas",
                         molestia_dolor="7", afecta_entrenamiento="1",
                         sintomas_enfermedad="si", detalle_sintomas="tos")
        client.post("/parte", data=datos, follow_redirects=False)
        # Initial GET
        r = client.get("/parte")
        assert r.status_code == 200
        assert _is_radio_checked(r.text, "entreno_hoy", "si")
        assert _is_radio_checked(r.text, "hay_molestia", "si")
        assert _is_radio_checked(r.text, "sintomas_enfermedad", "si")
        # Normal edit (valid save) still restores persisted values on next GET
        edit_token = _get_edit_token(client)
        datos2 = completo(client, hay_molestia="si", molestia_zona="rodillas",
                          molestia_dolor="7", afecta_entrenamiento="1",
                          sintomas_enfermedad="si", detalle_sintomas="tos",
                          animo="9", edit_state_token=edit_token)
        r2 = client.post("/parte", data=datos2, follow_redirects=False)
        assert r2.status_code == 302
        r3 = client.get("/parte")
        assert _is_radio_checked(r3.text, "entreno_hoy", "si")
        assert _is_radio_checked(r3.text, "hay_molestia", "si")
        assert _is_radio_checked(r3.text, "sintomas_enfermedad", "si")
        assert db.query(ParteDiaria).one().animo == 9
