"""Tomar lista de un día de entrenamiento.

Va todo en un solo POST con un campo por atleta, así que lo que hay que sostener
es que solo entre a la tabla lo que la pantalla realmente mostró.
"""
from datetime import date

from app.models.asistencia import Asistencia
from conftest import con_csrf, crear_usuario, entrar


def tomar_lista(client, **campos):
    datos = {"csrf_token": con_csrf(client, "/asistencia"), "fecha": "2026-03-02"}
    datos.update(campos)
    return client.post("/asistencia", data=datos, follow_redirects=False)


class TestGuardarLaLista:
    def test_guarda_el_estado_de_cada_uno(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        uno = crear_usuario(db, username="uno")
        otro = crear_usuario(db, username="otro")
        entrar(client, profe)

        tomar_lista(client, **{f"estado_{uno.id}": "presente",
                               f"estado_{otro.id}": "ausente"})
        estados = {a.atleta_id: a.estado for a in db.query(Asistencia).all()}
        assert estados == {uno.id: "presente", otro.id: "ausente"}

    def test_volver_a_tomar_lista_corrige_en_vez_de_duplicar(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        atleta = crear_usuario(db, username="uno")
        entrar(client, profe)

        tomar_lista(client, **{f"estado_{atleta.id}": "ausente"})
        tomar_lista(client, **{f"estado_{atleta.id}": "presente"})
        assert db.query(Asistencia).one().estado == "presente"

    def test_sin_marcar_borra_la_fila(self, client, db):
        """Es distinto de 'ausente': un día en que el profesor no tomó lista no
        puede contar como falta de todos."""
        profe = crear_usuario(db, username="profe", role="profesor")
        atleta = crear_usuario(db, username="uno")
        entrar(client, profe)

        tomar_lista(client, **{f"estado_{atleta.id}": "presente"})
        assert db.query(Asistencia).count() == 1
        tomar_lista(client, **{f"estado_{atleta.id}": ""})
        assert db.query(Asistencia).count() == 0

    def test_un_estado_inventado_no_entra(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        atleta = crear_usuario(db, username="uno")
        entrar(client, profe)
        tomar_lista(client, **{f"estado_{atleta.id}": "lesionado"})
        assert db.query(Asistencia).count() == 0


class TestSoloElPadron:
    """El POST recibe un campo `estado_<id>` por atleta. Sin cotejarlo contra el
    padrón, lo que viniera en ese id entraba a la tabla tal cual: la clave foránea
    frena los ids inexistentes, pero no el del propio profesor ni el de alguien
    dado de baja, que no tienen por qué estar en una lista de entrenamiento.
    """

    def test_no_se_le_toma_lista_al_profesor(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        entrar(client, profe)
        tomar_lista(client, **{f"estado_{profe.id}": "presente"})
        assert db.query(Asistencia).count() == 0

    def test_no_se_le_toma_lista_a_un_atleta_dado_de_baja(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        baja = crear_usuario(db, username="exatleta", is_active=False)
        entrar(client, profe)
        tomar_lista(client, **{f"estado_{baja.id}": "presente"})
        assert db.query(Asistencia).count() == 0

    def test_un_id_inexistente_no_rompe_la_lista(self, client, db):
        """El resto de la lista se tiene que guardar igual: el profesor está en la
        pista y no puede perder los treinta estados por un campo raro."""
        profe = crear_usuario(db, username="profe", role="profesor")
        atleta = crear_usuario(db, username="uno")
        entrar(client, profe)

        r = tomar_lista(client, **{"estado_999999": "presente",
                                   "estado_abc": "presente",
                                   f"estado_{atleta.id}": "presente"})
        assert r.status_code == 302
        assert [a.atleta_id for a in db.query(Asistencia).all()] == [atleta.id]


class TestQuienTomaLista:
    def test_el_atleta_no_puede_tomar_lista(self, client, db):
        atleta = crear_usuario(db, username="uno")
        entrar(client, atleta)
        client.post("/asistencia", data={"csrf_token": "x",
                                         f"estado_{atleta.id}": "presente"})
        assert db.query(Asistencia).count() == 0


class TestPantalla:
    def test_una_fecha_ilegible_cae_en_hoy(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        entrar(client, profe)
        assert client.get("/asistencia?fecha=basura").status_code == 200

    def test_muestra_el_padron_entero(self, client, db):
        """Tomar lista es marcar quién falta, y para eso hay que ver a todos."""
        profe = crear_usuario(db, username="profe", role="profesor")
        crear_usuario(db, username="uno", full_name="Atleta Uno")
        crear_usuario(db, username="dos", full_name="Atleta Dos")
        entrar(client, profe)
        cuerpo = client.get("/asistencia").text
        assert "Atleta Uno" in cuerpo and "Atleta Dos" in cuerpo
