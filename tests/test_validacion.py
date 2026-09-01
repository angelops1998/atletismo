"""Lo que se carga a mano y llega a la base.

Todo lo de acá terminaba en un 500 pelado de Postgres: un número más grande que
la columna, un texto más largo que el varchar. Son los errores que comete
cualquiera desde el celular, así que tienen que devolver una pantalla que diga
qué corregir.
"""
from datetime import date

import pytest

from app.models.marca import Marca
from app.models.user import User
from app.tiempo import fecha_razonable
from conftest import con_csrf, crear_usuario, entrar


@pytest.fixture
def profe(db):
    return crear_usuario(db, username="profe", role="profesor")


@pytest.fixture
def atleta(db):
    return crear_usuario(db, username="atleta1", full_name="Un Atleta")


def cargar_marca(client, atleta, **campos):
    datos = {"csrf_token": con_csrf(client, "/marcas"), "atleta_id": atleta.id,
             "prueba": "100m", "fecha": "2026-08-01", "valor": "12.34"}
    datos.update(campos)
    return client.post("/marcas", data=datos, follow_redirects=False)


class TestRangosDeMarcas:
    @pytest.mark.parametrize("viento", ["150", "-150", "99.99", "abc"])
    def test_un_viento_imposible_se_rechaza(self, client, db, profe, atleta, viento):
        """La columna es Numeric(4,2) y arriba de 20 m/s no se corre: guardarlo
        callado arruina la lectura de la marca, y pasarse de la columna hacía
        cortar a Postgres con 'numeric field overflow'."""
        entrar(client, profe)
        r = cargar_marca(client, atleta, viento=viento)
        assert r.headers["location"] == "/marcas?error=viento"
        assert db.query(Marca).count() == 0

    def test_una_marca_mas_grande_que_la_columna_se_rechaza(self, client, db, profe, atleta):
        entrar(client, profe)
        r = cargar_marca(client, atleta, valor="999999999")
        assert r.headers["location"] == "/marcas?error=valor"
        assert db.query(Marca).count() == 0

    @pytest.mark.parametrize("valor", ["0", "-5", "abc", ""])
    def test_una_marca_que_no_es_un_numero_positivo_se_rechaza(self, client, db,
                                                               profe, atleta, valor):
        entrar(client, profe)
        assert cargar_marca(client, atleta, valor=valor).headers["location"] == \
            "/marcas?error=valor"
        assert db.query(Marca).count() == 0

    def test_los_datos_buenos_se_guardan(self, client, db, profe, atleta):
        entrar(client, profe)
        r = cargar_marca(client, atleta, valor="12.34", viento="1.8")
        assert r.headers["location"] == "/marcas"
        marca = db.query(Marca).one()
        assert float(marca.valor) == 12.34 and float(marca.viento) == 1.8

    def test_acepta_el_tiempo_escrito_como_el_cronometro(self, client, db, profe, atleta):
        entrar(client, profe)
        cargar_marca(client, atleta, prueba="1500m", valor="4:32.10")
        assert float(db.query(Marca).one().valor) == 272.10


class TestTextosLargos:
    def test_un_texto_mas_largo_que_la_columna_no_tumba_el_alta(self, client, db, profe):
        """Postgres no recorta: corta con error. Un teléfono pegado con saltos de
        línea tiraba abajo el alta entera."""
        entrar(client, profe)
        r = client.post("/atletas/nuevo", data={
            "csrf_token": con_csrf(client, "/atletas/nuevo"),
            "full_name": "N" * 400, "password": "provisoria1",
            "documento": "D" * 100, "telefono": "T" * 100,
            "categoria": "C" * 100, "contacto_emergencia": "E" * 400,
        }, follow_redirects=False)
        assert r.status_code == 302
        nuevo = db.query(User).filter(User.role == "atleta").one()
        assert len(nuevo.full_name) == 150
        assert len(nuevo.documento) == 20
        assert len(nuevo.telefono) == 30
        assert len(nuevo.categoria) == 40
        assert len(nuevo.contacto_emergencia) == 150

    def test_un_usuario_demasiado_largo_se_avisa_en_vez_de_recortarse(self, client, db, profe):
        """El usuario es con lo que la persona entra: guardarlo a medias es peor
        que rechazarlo."""
        entrar(client, profe)
        r = client.post("/atletas/nuevo", data={
            "csrf_token": con_csrf(client, "/atletas/nuevo"),
            "full_name": "Un Atleta", "username": "u" * 80, "password": "provisoria1",
        })
        assert r.status_code == 422
        assert db.query(User).filter(User.role == "atleta").count() == 0


class TestFechas:
    @pytest.mark.parametrize("fecha", [date(2026, 3, 1), date(1900, 1, 1)])
    def test_acepta_las_creibles(self, fecha):
        assert fecha_razonable(fecha) is True

    @pytest.mark.parametrize("fecha", [date(1899, 12, 31), date(2206, 5, 1), None])
    def test_rechaza_las_absurdas(self, fecha):
        assert fecha_razonable(fecha) is False

    def test_un_cobro_desde_absurdo_no_se_guarda(self, client, db, profe):
        """Puesto en el año 2, el estado de cuenta recorrería veinticuatro mil
        meses y el atleta aparecería debiendo una fortuna que nunca se le cobró."""
        entrar(client, profe)
        client.post("/atletas/nuevo", data={
            "csrf_token": con_csrf(client, "/atletas/nuevo"),
            "full_name": "Un Atleta", "password": "provisoria1",
            "cuota_mensual": "150", "cobro_desde": "0002-01-01",
        }, follow_redirects=False)
        nuevo = db.query(User).filter(User.role == "atleta").one()
        # Sin fecha válida cae al mes del alta, no al año 2.
        assert nuevo.cobro_desde.year >= 1900


class TestErrorNoPrevisto:
    def test_muestra_la_pantalla_de_la_app_y_no_el_error_pelado(self, client, monkeypatch):
        """Sin manejador, el atleta ve el 'Internal Server Error' de uvicorn, que
        no le dice qué hacer y parece que la app se rompió del todo.

        Se rompe algo propio del router y no el objeto `templates`, que es el
        mismo que usa el manejador de error para dibujar esta pantalla.
        """
        from app.routers import publico

        def explota(*a, **k):
            raise RuntimeError("algo inesperado")
        monkeypatch.setattr(publico, "get_current_user_optional", explota)

        r = client.get("/")
        assert r.status_code == 500
        assert "Algo falló" in r.text
        assert "Internal Server Error" not in r.text
