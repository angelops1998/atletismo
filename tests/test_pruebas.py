"""Catálogo de pruebas.

Lo que hay que proteger acá es el sentido de cada prueba: en los 100 m bajar es
mejorar, en salto largo es empeorar. Si eso se invierte, todos los gráficos de
evolución y todos los rankings muestran el progreso al revés, y se ve bien.
"""
from decimal import Decimal

import pytest

from app.services import pruebas


class TestSentidoDeLaPrueba:
    @pytest.mark.parametrize("clave", ["60m", "80m", "100m", "150m", "300m", "400m",
                                       "600m", "1200m", "1500m", "2400m", "10000m",
                                       "60vallas", "190vallas", "295vallas",
                                       "110vallas", "400vallas", "1500obs", "3000obs",
                                       "300marcha", "5000marcha", "21kmarcha"])
    def test_en_las_carreras_menos_es_mejor(self, clave):
        assert pruebas.menor_es_mejor(clave) is True

    @pytest.mark.parametrize("clave", ["largo", "triple", "alto", "garrocha",
                                       "bala", "disco", "jabalina", "martillo"])
    def test_en_saltos_y_lanzamientos_mas_es_mejor(self, clave):
        assert pruebas.menor_es_mejor(clave) is False

    @pytest.mark.parametrize("clave", ["heptatlon", "decatlon", "hexatlon"])
    def test_en_las_combinadas_mas_puntos_es_mejor(self, clave):
        assert pruebas.menor_es_mejor(clave) is False
        assert pruebas.unidad(clave) == "pts"

    def test_mejor_marca_en_carrera_es_la_mas_baja(self):
        assert pruebas.mejor("100m", [Decimal("12.40"), Decimal("12.10"),
                                      Decimal("12.90")]) == Decimal("12.10")

    def test_mejor_marca_en_salto_es_la_mas_alta(self):
        assert pruebas.mejor("largo", [Decimal("5.20"), Decimal("5.87"),
                                       Decimal("5.40")]) == Decimal("5.87")

    def test_mejor_ignora_los_none(self):
        assert pruebas.mejor("100m", [None, Decimal("12.1"), None]) == Decimal("12.1")

    def test_mejor_sin_marcas(self):
        assert pruebas.mejor("100m", []) is None
        assert pruebas.mejor("100m", [None]) is None

    def test_es_mejora_respeta_el_sentido(self):
        assert pruebas.es_mejora("100m", Decimal("12.1"), Decimal("12.4")) is True
        assert pruebas.es_mejora("largo", Decimal("5.2"), Decimal("5.8")) is False
        assert pruebas.es_mejora("largo", Decimal("5.9"), Decimal("5.8")) is True

    def test_es_mejora_sin_con_que_comparar(self):
        assert pruebas.es_mejora("100m", Decimal("12.1"), None) is None


class TestFormato:
    def test_segundos_cortos(self):
        assert pruebas.formatear("100m", Decimal("12.34")) == "12.34 s"

    def test_a_partir_del_minuto_se_muestra_como_el_cronometro(self):
        """Nadie dice que corrió los 1500 en 272.10 segundos."""
        assert pruebas.formatear("1500m", Decimal("272.10")) == "4:32.10"

    def test_rellena_el_cero_de_los_segundos(self):
        assert pruebas.formatear("1500m", Decimal("245.30")) == "4:05.30"

    def test_metros(self):
        assert pruebas.formatear("largo", Decimal("5.87")) == "5.87 m"

    def test_la_marcha_larga_se_muestra_con_horas(self):
        assert pruebas.formatear("21kmarcha", Decimal("6330")) == "1:45:30"
        assert pruebas.formatear("21kmarcha", Decimal("3605")) == "1:00:05"

    def test_la_marcha_corta_sigue_en_minutos(self):
        assert pruebas.formatear("5000marcha", Decimal("1385.40")) == "23:05.40"

    def test_los_puntos_de_las_combinadas(self):
        assert pruebas.formatear("decatlon", Decimal("6850")) == "6.850 pts"

    def test_sin_valor(self):
        assert pruebas.formatear("100m", None) == "—"


class TestCatalogo:
    def test_existe(self):
        assert pruebas.existe("100m") is True
        assert pruebas.existe("natacion") is False
        assert pruebas.existe("") is False

    def test_una_clave_desconocida_no_rompe(self):
        """Si alguna vez queda una marca con una prueba que se sacó del catálogo,
        la ficha del atleta tiene que abrir igual."""
        assert pruebas.nombre("vieja") == "vieja"
        assert pruebas.unidad("vieja") == ""
        assert pruebas.formatear("vieja", Decimal("10")) == "10.00"

    def test_los_grupos_cubren_todo_el_catalogo(self):
        cuantas = sum(len(v) for v in pruebas.grupos().values())
        assert cuantas == len(pruebas.PRUEBAS)

    def test_las_claves_no_se_repiten(self):
        claves = [p[0] for p in pruebas.PRUEBAS]
        assert len(claves) == len(set(claves))

    def test_toda_prueba_tiene_al_menos_una_categoria(self):
        assert all(p[6] for p in pruebas.PRUEBAS)


class TestPlanillasPorCategoria:
    """Las tres planillas que mandó el club tienen que estar completas y no
    mezclarse: un U14 no corre 100 m con vallas ni un Mayor 190 m con vallas."""

    PLANILLA_MAYORES = ["100m", "200m", "400m", "800m", "1500m", "3000m", "5000m",
                        "10000m", "100vallas", "110vallas", "400vallas", "2000obs",
                        "3000obs", "5000marcha", "10000marcha", "21kmarcha",
                        "largo", "alto", "triple", "garrocha", "bala", "disco",
                        "jabalina", "martillo", "heptatlon", "decatlon"]
    # Los combos U14: velocidad, vallas, resistencia, marcha, saltos y lanzamientos.
    PLANILLA_U14 = ["60m", "largo", "60vallas", "150m", "190vallas", "600m", "1200m",
                    "800m", "300marcha", "1600marcha", "alto", "jabalina", "disco"]
    # Reglamento técnico 2025, niñas y niños juntos.
    PLANILLA_U16 = ["80m", "150m", "300m", "600m", "2400m", "80vallas", "100vallas",
                    "295vallas", "1500obs", "3000marcha", "5000marcha", "largo",
                    "triple", "alto", "garrocha", "bala", "jabalina", "disco",
                    "martillo", "hexatlon"]

    @staticmethod
    def claves(categoria):
        return {c for lista in pruebas.grupos(categoria).values() for c, _n, _cats in lista}

    def test_la_planilla_de_mayores_esta_completa(self):
        assert set(self.PLANILLA_MAYORES) == self.claves(pruebas.MAYORES)

    def test_la_planilla_u14_esta_completa(self):
        assert set(self.PLANILLA_U14) == self.claves(pruebas.U14)

    def test_la_planilla_u16_esta_completa(self):
        assert set(self.PLANILLA_U16) == self.claves(pruebas.U16)

    def test_toda_prueba_del_catalogo_esta_en_alguna_planilla(self):
        todas = self.claves(pruebas.U14) | self.claves(pruebas.U16) | self.claves(pruebas.MAYORES)
        assert todas == {p[0] for p in pruebas.PRUEBAS}


class TestPlanillaDelAtleta:
    """Al elegir un atleta, el formulario de marcas preselecciona su planilla."""

    class Ficha:
        def __init__(self, edad=None, categoria=None):
            self._edad, self.categoria = edad, categoria

        def edad(self):
            return self._edad

    @pytest.mark.parametrize("edad,esperado", [
        (11, "u14"), (13, "u14"), (14, "u16"), (15, "u16"), (16, "mayores"), (34, "mayores"),
    ])
    def test_la_edad_manda(self, edad, esperado):
        assert pruebas.planilla_de(self.Ficha(edad=edad, categoria="Mayores")) == esperado

    @pytest.mark.parametrize("texto,esperado", [
        ("Menores (10 a 13)", "u14"), ("Pequeños (5 a 8)", "u14"), ("U16", "u16"),
        ("Juveniles", "mayores"), ("Mayores", "mayores"), ("", None), (None, None),
    ])
    def test_sin_fecha_de_nacimiento_se_mira_la_categoria(self, texto, esperado):
        assert pruebas.planilla_de(self.Ficha(categoria=texto)) == esperado

    def test_sin_atleta_no_filtra(self):
        assert pruebas.planilla_de(None) is None
