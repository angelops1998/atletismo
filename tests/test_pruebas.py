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
                                       "600m", "1500m", "10000m", "80vallas",
                                       "110vallas", "400vallas", "3000obs",
                                       "5000marcha", "21kmarcha"])
    def test_en_las_carreras_menos_es_mejor(self, clave):
        assert pruebas.menor_es_mejor(clave) is True

    @pytest.mark.parametrize("clave", ["largo", "triple", "alto", "garrocha",
                                       "bala", "disco", "jabalina", "martillo"])
    def test_en_saltos_y_lanzamientos_mas_es_mejor(self, clave):
        assert pruebas.menor_es_mejor(clave) is False

    @pytest.mark.parametrize("clave", ["heptatlon", "decatlon", "pentatlon", "hexatlon"])
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
    """Las pruebas de la planilla que mandó el club para Mayores tienen que
    estar todas, y las de Menores no pueden mezclarse con las de Mayores."""

    PLANILLA_MAYORES = ["100m", "200m", "400m", "800m", "1500m", "3000m", "5000m",
                        "10000m", "100vallas", "110vallas", "400vallas", "2000obs",
                        "3000obs", "5000marcha", "10000marcha", "21kmarcha",
                        "largo", "alto", "triple", "garrocha", "bala", "disco",
                        "jabalina", "martillo", "heptatlon", "decatlon"]

    def test_la_planilla_de_mayores_esta_completa(self):
        claves = {c for lista in pruebas.grupos(pruebas.MAYORES).values()
                  for c, _n, _cats in lista}
        assert set(self.PLANILLA_MAYORES) <= claves

    def test_menores_no_ve_las_pruebas_solo_de_mayores(self):
        claves = {c for lista in pruebas.grupos(pruebas.MENORES).values()
                  for c, _n, _cats in lista}
        assert "400vallas" not in claves and "decatlon" not in claves
        assert "80m" in claves and "largo" in claves

    def test_mayores_no_ve_las_pruebas_solo_de_menores(self):
        claves = {c for lista in pruebas.grupos(pruebas.MAYORES).values()
                  for c, _n, _cats in lista}
        assert "80m" not in claves and "600m" not in claves

    @pytest.mark.parametrize("texto,esperado", [
        ("Menores (10 a 13)", "menores"), ("Menores", "menores"),
        ("Pequeños (5 a 8)", "menores"), ("Juveniles", "mayores"),
        ("Mayores", "mayores"), ("Máster", "mayores"), ("", None), (None, None),
    ])
    def test_la_categoria_de_la_ficha_elige_la_planilla(self, texto, esperado):
        assert pruebas.categoria_de(texto) == esperado
