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
