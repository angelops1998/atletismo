"""El ranking del club.

Es la pantalla con la que el profesor arma la posta y decide quién va a la
competencia, así que un ranking incompleto no se nota: se ve una lista razonable
a la que le falta gente.
"""
from datetime import date, timedelta
from decimal import Decimal

from app.models.marca import Marca
from conftest import con_csrf, crear_usuario, entrar


def solo_el_ranking(cuerpo: str) -> str:
    """El bloque del ranking, sin la tabla de últimas marcas que va abajo.

    Sin recortar, cada marca de la tabla cuenta como una aparición del atleta y
    las comprobaciones de orden y de cantidad pasan por casualidad.
    """
    desde = cuerpo.index("Ranking del club")
    return cuerpo[desde:cuerpo.index("Últimas marcas cargadas", desde)]


def marca(db, atleta_id, prueba, valor, cuando):
    db.add(Marca(atleta_id=atleta_id, prueba=prueba, fecha=cuando,
                 valor=Decimal(str(valor))))
    db.commit()


class TestRanking:
    def test_toma_el_mejor_registro_aunque_sea_viejo(self, client, db):
        """La regresión que arregló esta pantalla: el ranking se armaba sobre las
        100 marcas más recientes, las mismas que se listan arriba. Pasadas las 100
        marcas de una prueba, el atleta cuyo récord era de temporadas anteriores
        desaparecía del ranking entero.
        """
        profe = crear_usuario(db, username="profe", role="profesor")
        veterana = crear_usuario(db, username="veterana", full_name="Veterana")
        novato = crear_usuario(db, username="novato", full_name="Novato")

        marca(db, veterana.id, "100m", "10.50", date(2020, 5, 1))
        for i in range(105):
            marca(db, novato.id, "100m", 12 + i / 100, date(2026, 8, 1) - timedelta(days=i))

        entrar(client, profe)
        ranking = solo_el_ranking(client.get("/marcas?prueba=100m").text)
        assert "Veterana" in ranking, "el mejor del club quedaba afuera del ranking"
        assert ranking.index("Veterana") < ranking.index("Novato")

    def test_en_carrera_ordena_de_menor_a_mayor(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        rapida = crear_usuario(db, username="rapida", full_name="Rapida")
        lenta = crear_usuario(db, username="lenta", full_name="Lenta")
        marca(db, rapida.id, "100m", "11.20", date(2026, 3, 1))
        marca(db, lenta.id, "100m", "13.80", date(2026, 3, 1))

        entrar(client, profe)
        ranking = solo_el_ranking(client.get("/marcas?prueba=100m").text)
        assert ranking.index("Rapida") < ranking.index("Lenta")

    def test_en_salto_ordena_de_mayor_a_menor(self, client, db):
        """El sentido lo define la prueba: en largo, el número grande es el bueno."""
        profe = crear_usuario(db, username="profe", role="profesor")
        lejos = crear_usuario(db, username="lejos", full_name="Lejos")
        cerca = crear_usuario(db, username="cerca", full_name="Cerca")
        marca(db, lejos.id, "largo", "6.40", date(2026, 3, 1))
        marca(db, cerca.id, "largo", "4.90", date(2026, 3, 1))

        entrar(client, profe)
        ranking = solo_el_ranking(client.get("/marcas?prueba=largo").text)
        assert ranking.index("Lejos") < ranking.index("Cerca")

    def test_cada_atleta_aparece_una_sola_vez(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        atleta = crear_usuario(db, username="unica", full_name="Unica")
        for valor in ("12.90", "12.40", "12.10"):
            marca(db, atleta.id, "100m", valor, date(2026, 3, 1))

        entrar(client, profe)
        ranking = solo_el_ranking(client.get("/marcas?prueba=100m").text)
        assert ranking.count("Unica") == 1
        assert "12.10" in ranking and "12.90" not in ranking


class TestBorrar:
    def test_el_profesor_puede_anular_una_marca_mal_cargada(self, client, db):
        profe = crear_usuario(db, username="profe", role="profesor")
        atleta = crear_usuario(db, username="atleta1")
        marca(db, atleta.id, "100m", "12.34", date(2026, 3, 1))
        creada = db.query(Marca).one()

        entrar(client, profe)
        r = client.post(f"/marcas/{creada.id}/borrar",
                        data={"csrf_token": con_csrf(client, "/marcas")},
                        follow_redirects=False)
        assert r.status_code == 302
        assert db.query(Marca).count() == 0

    def test_el_atleta_no_puede_borrar_marcas(self, client, db):
        atleta = crear_usuario(db, username="atleta1")
        marca(db, atleta.id, "100m", "12.34", date(2026, 3, 1))
        creada = db.query(Marca).one()

        entrar(client, atleta)
        client.post(f"/marcas/{creada.id}/borrar", data={"csrf_token": "x"})
        assert db.query(Marca).count() == 1
