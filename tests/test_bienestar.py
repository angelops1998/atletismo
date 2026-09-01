"""Cálculos sobre los partes semanales.

Nada de esto se guarda en la base, así que si un cálculo se corre de lugar no hay
ninguna columna que lo delate: la pantalla muestra un número plausible y
equivocado. De ahí que sea lo primero que conviene tener cubierto.
"""
from decimal import Decimal

import pytest

from app.services import bienestar
from conftest import crear_parte, crear_usuario, semana


class TestBienestarTotal:
    def test_suma_los_cinco_items(self, db):
        atleta = crear_usuario(db)
        parte = crear_parte(db, atleta.id, semana(), sueno_calidad=5, fatiga=4,
                            dolor_muscular=3, estres=2, animo=1)
        assert bienestar.bienestar_total(parte) == 15

    def test_el_maximo_es_25(self, db):
        atleta = crear_usuario(db)
        parte = crear_parte(db, atleta.id, semana(), sueno_calidad=5, fatiga=5,
                            dolor_muscular=5, estres=5, animo=5)
        assert bienestar.bienestar_total(parte) == bienestar.MAXIMO == 25

    def test_porcentaje(self, db):
        atleta = crear_usuario(db)
        parte = crear_parte(db, atleta.id, semana())      # 4 en los cinco = 20
        assert bienestar.bienestar_pct(parte) == 80


class TestSemaforo:
    """El color con el que se pinta la semana en el padrón. Es lo que decide a
    quién mira el profesor primero, así que los bordes importan."""

    def test_bien_cuando_esta_arriba_de_17(self, db):
        atleta = crear_usuario(db)
        assert bienestar.semaforo(crear_parte(db, atleta.id, semana())) == "bien"

    def test_atencion_en_la_franja_del_medio(self, db):
        atleta = crear_usuario(db)
        parte = crear_parte(db, atleta.id, semana(), sueno_calidad=3, fatiga=3,
                            dolor_muscular=3, estres=3, animo=3)   # 15
        assert bienestar.semaforo(parte) == "atencion"

    def test_mal_cuando_suma_12_o_menos(self, db):
        atleta = crear_usuario(db)
        parte = crear_parte(db, atleta.id, semana(), sueno_calidad=2, fatiga=2,
                            dolor_muscular=3, estres=3, animo=2)   # 12
        assert bienestar.semaforo(parte) == "mal"

    def test_un_uno_solo_alcanza_para_pintarlo_mal(self, db):
        """Aunque el total dé bien: un 1 en cualquier pregunta es una persona
        diciendo que algo está muy mal, y el promedio se lo come."""
        atleta = crear_usuario(db)
        parte = crear_parte(db, atleta.id, semana(), sueno_calidad=1, fatiga=5,
                            dolor_muscular=5, estres=5, animo=5)   # 21
        assert bienestar.bienestar_total(parte) == 21
        assert bienestar.semaforo(parte) == "mal"


class TestCarga:
    def test_carga_es_rpe_por_minutos(self, db):
        atleta = crear_usuario(db)
        parte = crear_parte(db, atleta.id, semana(), rpe=6, minutos_totales=300)
        assert bienestar.carga_ua(parte) == 1800

    @pytest.mark.parametrize("campos", [{"rpe": 6}, {"minutos_totales": 300}, {}])
    def test_sin_los_dos_datos_no_hay_carga(self, db, campos):
        atleta = crear_usuario(db)
        parte = crear_parte(db, atleta.id, semana(), **campos)
        assert bienestar.carga_ua(parte) is None


class TestPromedio:
    def test_ignora_los_none(self):
        assert bienestar.promedio([4, None, 6, None]) == 5

    def test_todo_none_da_none(self):
        assert bienestar.promedio([None, None]) is None
        assert bienestar.promedio([]) is None

    def test_acepta_decimales_de_la_base(self):
        assert bienestar.promedio([Decimal("7.5"), Decimal("8.5")]) == 8.0


class TestSerieIndividual:
    def test_devuelve_una_fila_por_semana_pedida(self, db):
        atleta = crear_usuario(db)
        serie = bienestar.serie_individual(db, atleta.id, 12)
        assert len(serie) == 12

    def test_las_semanas_sin_parte_quedan_en_none(self, db):
        """El hueco tiene que verse: una semana en la que no cargó nada es
        justamente lo que el profesor necesita mirar, no un dato interpolado."""
        atleta = crear_usuario(db)
        crear_parte(db, atleta.id, semana(0))
        crear_parte(db, atleta.id, semana(2))
        serie = bienestar.serie_individual(db, atleta.id, 4)
        assert [f["bienestar"] for f in serie] == [None, 20, None, 20]

    def test_va_de_la_mas_vieja_a_la_mas_nueva(self, db):
        atleta = crear_usuario(db)
        serie = bienestar.serie_individual(db, atleta.id, 5)
        assert [f["semana"] for f in serie] == [semana(4), semana(3), semana(2),
                                                semana(1), semana(0)]

    def test_no_mezcla_los_partes_de_otro_atleta(self, db):
        uno = crear_usuario(db, username="uno")
        otro = crear_usuario(db, username="otro")
        crear_parte(db, otro.id, semana(0), sueno_calidad=1, fatiga=1,
                    dolor_muscular=1, estres=1, animo=1)
        serie = bienestar.serie_individual(db, uno.id, 3)
        assert all(f["parte"] is None for f in serie)


class TestSerieGrupo:
    def test_el_porcentaje_cuenta_solo_a_los_activos(self, db):
        """Un atleta dado de baja no puede bajar el porcentaje de partes
        cargados: ya no se le pide nada."""
        activo = crear_usuario(db, username="activo")
        crear_usuario(db, username="baja", is_active=False)
        crear_parte(db, activo.id, semana(0))
        fila = bienestar.serie_grupo(db, 1)[0]
        assert fila["total"] == 1
        assert fila["cargados"] == 1
        assert fila["pct_cargados"] == 100

    def test_sin_atletas_no_divide_por_cero(self, db):
        assert bienestar.serie_grupo(db, 2)[0]["pct_cargados"] == 0
