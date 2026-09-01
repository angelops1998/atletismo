"""El parte semanal: lo que carga el atleta.

Es el único formulario que usa gente que no es el profesor, una vez por semana y
desde el celular. Las dos reglas que lo definen —una fila por semana y una sola
semana hacia atrás— son las que hay que sostener.
"""
from datetime import timedelta

import pytest

from app.models.parte import ParteSemanal
from conftest import con_csrf, crear_parte, crear_usuario, entrar, semana


@pytest.fixture
def atleta(db):
    return crear_usuario(db, username="atleta1", full_name="Un Atleta")


def completo(client, **campos):
    datos = {"csrf_token": con_csrf(client, "/parte"),
             "sueno_calidad": "4", "fatiga": "4", "dolor_muscular": "4",
             "estres": "4", "animo": "4"}
    datos.update(campos)
    return datos


class TestUnParteporSemana:
    def test_carga_el_parte_de_la_semana(self, client, db, atleta):
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client), follow_redirects=False)
        assert r.status_code == 302
        parte = db.query(ParteSemanal).one()
        assert parte.semana == semana(0) and parte.atleta_id == atleta.id

    def test_volver_a_entrar_edita_en_vez_de_duplicar(self, client, db, atleta):
        """El que entra el jueves y el que entra el domingo escriben la misma
        fila. Sin esto, 'una vez por semana' deja de cumplirse a la primera vez
        que alguien vuelve a abrir el formulario."""
        entrar(client, atleta)
        client.post("/parte", data=completo(client), follow_redirects=False)
        client.post("/parte", data=completo(client, animo="2"), follow_redirects=False)
        assert db.query(ParteSemanal).count() == 1
        assert db.query(ParteSemanal).one().animo == 2

    def test_se_puede_completar_la_semana_pasada(self, client, db, atleta):
        """Para no perder el dato del que se olvidó el domingo."""
        entrar(client, atleta)
        anterior = semana(1)
        r = client.post("/parte", data=completo(client, semana=anterior.isoformat()),
                        follow_redirects=False)
        assert r.status_code == 302
        assert db.query(ParteSemanal).one().semana == anterior

    def test_mas_atras_esta_cerrado(self, client, db, atleta):
        """Más de una semana ya no es un recuerdo, es una invención, y datos
        inventados son peores que datos faltantes."""
        entrar(client, atleta)
        vieja = (semana(5)).isoformat()
        assert client.post("/parte", data=completo(client, semana=vieja)).status_code == 403
        assert db.query(ParteSemanal).count() == 0

    def test_una_semana_futura_cae_en_la_actual(self, client, db, atleta):
        entrar(client, atleta)
        futura = (semana(0) + timedelta(weeks=3)).isoformat()
        client.post("/parte", data=completo(client, semana=futura), follow_redirects=False)
        assert db.query(ParteSemanal).one().semana == semana(0)


class TestValidacion:
    def test_faltando_una_respuesta_no_guarda(self, client, db, atleta):
        entrar(client, atleta)
        datos = completo(client)
        del datos["animo"]
        r = client.post("/parte", data=datos)
        assert r.status_code == 422
        assert "Faltan responder" in r.text
        assert db.query(ParteSemanal).count() == 0

    @pytest.mark.parametrize("valor", ["0", "6", "-1", "abc"])
    def test_un_puntaje_fuera_de_la_escala_no_guarda(self, client, db, atleta, valor):
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client, animo=valor))
        assert r.status_code == 422
        assert db.query(ParteSemanal).count() == 0

    def test_la_molestia_pide_zona_y_dolor(self, client, db, atleta):
        """Una molestia sin zona ni intensidad no le sirve al profesor para nada:
        es la alerta que puede terminar en una lesión."""
        entrar(client, atleta)
        r = client.post("/parte", data=completo(client, molestias="si"))
        assert r.status_code == 422
        assert "cuánto te duele" in r.text
        assert "parte del cuerpo" in r.text

    def test_la_molestia_completa_se_guarda(self, client, db, atleta):
        entrar(client, atleta)
        client.post("/parte", data=completo(client, molestias="si",
                                            molestia_zona="gemelo derecho",
                                            molestia_dolor="7"),
                    follow_redirects=False)
        parte = db.query(ParteSemanal).one()
        assert parte.molestias is True and parte.molestia_dolor == 7

    def test_los_numeros_con_coma_del_celular_se_entienden(self, client, db, atleta):
        """El teclado del teléfono manda '7,5' y float() se rompe con eso."""
        entrar(client, atleta)
        client.post("/parte", data=completo(client, horas_sueno="7,5", peso_kg="62,4"),
                    follow_redirects=False)
        parte = db.query(ParteSemanal).one()
        assert float(parte.horas_sueno) == 7.5 and float(parte.peso_kg) == 62.4

    @pytest.mark.parametrize("campo,valor", [
        ("horas_sueno", "48"), ("peso_kg", "900"), ("rpe", "50"),
        ("minutos_totales", "999999"), ("hidratacion_litros", "80"),
    ])
    def test_los_valores_imposibles_se_descartan(self, client, db, atleta, campo, valor):
        """Se guarda el parte igual, sin ese dato: son campos opcionales, y
        perder el parte entero por un dedazo en el peso es peor."""
        entrar(client, atleta)
        client.post("/parte", data=completo(client, **{campo: valor}),
                    follow_redirects=False)
        assert getattr(db.query(ParteSemanal).one(), campo) is None


class TestQuienCarga:
    def test_el_profesor_no_carga_partes(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        entrar(client, profe)
        assert client.get("/parte").status_code == 403

    def test_el_atleta_no_puede_escribirle_el_parte_a_otro(self, client, db, atleta):
        """El formulario no tiene campo de atleta: el parte es siempre del que
        está en sesión. Este test lo fija para que siga siendo así."""
        otro = crear_usuario(db, username="otro")
        entrar(client, atleta)
        client.post("/parte", data=completo(client, atleta_id=str(otro.id)),
                    follow_redirects=False)
        assert db.query(ParteSemanal).one().atleta_id == atleta.id
