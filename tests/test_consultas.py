"""Cuántas consultas hace cada pantalla del profesor.

El panel, el padrón, la cobranza y las estadísticas muestran una fila por atleta.
Armadas de a una, cada fila iba a buscar sus propios datos y el costo de la
pantalla crecía con el club: con sesenta atletas, abrir el padrón eran 242
consultas. El profesor abre estas pantallas desde la pista, con el celular y a
veces con mala señal, así que no puede depender de cuánta gente haya.

Estos tests no miden tiempo —eso varía con la máquina— sino que el número de
consultas NO crezca con el padrón, que es la propiedad que se rompió antes.
"""
from datetime import timedelta
from decimal import Decimal

import pytest

from app.models.parte import ParteSemanal
from app.models.user import User
from app.auth import hash_password
from conftest import crear_parte, crear_usuario, entrar, semana

PANTALLAS = ["/panel", "/atletas", "/pagos", "/estadisticas"]


def poblar(db, cuantos: int, desde: int = 0) -> None:
    """`cuantos` atletas con cuota, deuda y cuatro meses de partes.

    Todo en un solo commit: con una fila por vez, armar el padrón de estos tests
    tardaba más que las cuatro pantallas que vienen a medir.
    """
    clave = hash_password("x")
    atletas = [User(username=f"a{i}", full_name=f"Atleta {i:03d}", role="atleta",
                    hashed_password=clave, cuota_mensual=Decimal(150),
                    cobro_desde=semana(0).replace(day=1))
               for i in range(desde, desde + cuantos)]
    db.add_all(atletas)
    db.flush()
    db.add_all([ParteSemanal(atleta_id=a.id, semana=semana(atras),
                             sueno_calidad=4, dolor_muscular=4,
                             estres=4, animo=4, rpe=6, minutos_totales=300,
                             horas_sueno=Decimal("7.5"), peso_kg=Decimal("62.0"))
                for a in atletas for atras in range(16)])
    db.commit()


@pytest.fixture
def profe(db):
    return crear_usuario(db, username="profe", role="profesor")


@pytest.mark.parametrize("ruta", PANTALLAS)
def test_el_costo_no_crece_con_el_padron(client, db, profe, contar_consultas, ruta):
    entrar(client, profe)

    poblar(db, 5)
    with contar_consultas() as pocos:
        assert client.get(ruta).status_code == 200

    poblar(db, 25, desde=5)             # 30 atletas en total
    with contar_consultas() as muchos:
        assert client.get(ruta).status_code == 200

    assert muchos.total == pocos.total, (
        f"{ruta} hizo {pocos.total} consultas con 5 atletas y {muchos.total} con 30: "
        "la pantalla volvió a consultar de a un atleta por vez")


@pytest.mark.parametrize("ruta", PANTALLAS)
def test_ninguna_pantalla_pasa_de_un_puñado_de_consultas(client, db, profe,
                                                          contar_consultas, ruta):
    """Un techo absoluto, además del crecimiento: sirve para notar si alguien
    agrega una consulta suelta en un bucle nuevo."""
    entrar(client, profe)
    poblar(db, 30)
    with contar_consultas() as cuenta:
        client.get(ruta)
    assert cuenta.total <= 20, f"{ruta} hizo {cuenta.total} consultas"


class TestLosLotesDevuelvenLoMismo:
    """Las versiones por lote tienen que dar exactamente lo que daban las de a una:
    son las que usan ahora todas las pantallas."""

    def test_series_de_coincide_con_serie_individual(self, db):
        from app.services import bienestar
        uno = crear_usuario(db, username="uno")
        otro = crear_usuario(db, username="otro")
        crear_parte(db, uno.id, semana(0), animo=2)
        crear_parte(db, uno.id, semana(3), animo=5)
        crear_parte(db, otro.id, semana(1), horas_sueno=Decimal("6.0"))

        lote = bienestar.series_de(db, [uno.id, otro.id], 8)
        for atleta in (uno, otro):
            individual = bienestar.serie_individual(db, atleta.id, 8)
            assert [f["semana"] for f in lote[atleta.id]] == [f["semana"] for f in individual]
            assert [f["bienestar"] for f in lote[atleta.id]] == [f["bienestar"] for f in individual]
            assert [f["sueno"] for f in lote[atleta.id]] == [f["sueno"] for f in individual]

    def test_el_atleta_sin_partes_igual_tiene_serie(self, db):
        from app.services import bienestar
        nuevo = crear_usuario(db, username="nuevo")
        serie = bienestar.series_de(db, [nuevo.id], 12)[nuevo.id]
        assert len(serie) == 12 and all(f["parte"] is None for f in serie)

    def test_sin_ids_no_consulta_nada(self, db, contar_consultas):
        from app.services import bienestar, cobranza
        with contar_consultas() as cuenta:
            assert bienestar.series_de(db, []) == {}
            assert cobranza.pagados_de(db, []) == {}
        assert cuenta.total == 0

    def test_estados_de_coincide_con_estado_cuenta(self, db):
        from datetime import date
        from app.models.pago import Pago
        from app.services import cobranza
        uno = crear_usuario(db, username="uno", cuota_mensual=Decimal(150),
                            cobro_desde=date(2026, 1, 1))
        otro = crear_usuario(db, username="otro", cuota_mensual=Decimal(200),
                             cobro_desde=date(2026, 2, 1))
        sin_cuota = crear_usuario(db, username="sincuota")
        db.add(Pago(atleta_id=uno.id, periodo=date(2026, 2, 1),
                    fecha_pago=date(2026, 2, 3), monto=Decimal(150)))
        db.commit()

        hasta = date(2026, 4, 15)
        lote = cobranza.estados_de(db, [uno, otro, sin_cuota], hasta)
        for atleta in (uno, otro, sin_cuota):
            assert lote[atleta.id] == cobranza.estado_cuenta(db, atleta, hasta)

    def test_las_alertas_del_club_no_cambian(self, db):
        """del_club pasa la serie y la cuenta ya resueltas a del_atleta; tiene que
        dar lo mismo que cuando cada alerta las buscaba por su cuenta."""
        from datetime import date
        from app.services import alertas
        dolorido = crear_usuario(db, username="dolorido", full_name="Dolorido",
                                 cuota_mensual=Decimal(150), cobro_desde=date(2026, 1, 1))
        crear_parte(db, dolorido.id, semana(0), molestias=True,
                    molestia_zona="rodilla", molestia_dolor=8)

        del_club = alertas.del_club(db)[0]["alertas"]
        suelto = alertas.del_atleta(db, dolorido)
        assert [a["tipo"] for a in del_club] == [a["tipo"] for a in suelto]
        assert [a["detalle"] for a in del_club] == [a["detalle"] for a in suelto]
