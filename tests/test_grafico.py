"""Geometría de los gráficos SVG.

Se dibujan en el servidor, sin librería. Lo que importa acá no es el píxel exacto
sino que no mientan: que una semana sin parte se vea como un hueco y no como una
línea recta, y que ningún caso borde termine en una división por cero que deje la
pantalla del profesor en blanco.
"""
from app.services import grafico


class TestLinea:
    def test_los_huecos_cortan_la_linea(self):
        """Dibujar una recta sobre una semana sin datos haría creer que el atleta
        cargó algo, que es justo lo contrario de lo que hay que ver."""
        salida = grafico.linea([10, 12, None, 15, 14])
        assert len(salida["segmentos"]) == 2
        assert salida["puntos"][2] is None

    def test_una_serie_entera_dibuja_un_solo_segmento(self):
        assert len(grafico.linea([10, 12, 15])["segmentos"]) == 1

    def test_una_sola_lectura_se_marca_como_punto_suelto(self):
        """El atleta que recién arranca tiene que ver que su dato quedó
        registrado, aunque todavía no haya línea que dibujar."""
        salida = grafico.linea([None, None, 18])
        assert salida["solo_puntos"] is True
        assert salida["segmentos"] == []
        assert salida["puntos"][2] is not None

    def test_serie_vacia_no_rompe(self):
        salida = grafico.linea([])
        assert salida["segmentos"] == [] and salida["puntos"] == []

    def test_todo_none_no_rompe(self):
        assert grafico.linea([None, None])["segmentos"] == []

    def test_valores_iguales_no_dividen_por_cero(self):
        salida = grafico.linea([20, 20, 20])
        assert salida["min"] < salida["max"]
        assert all(p is not None for p in salida["puntos"])

    def test_la_escala_fija_se_respeta(self):
        salida = grafico.linea([10, 20], minimo=5, maximo=25)
        assert (salida["min"], salida["max"]) == (5, 25)

    def test_el_valor_mas_alto_queda_mas_arriba(self):
        """En SVG el eje Y crece hacia abajo: si esto se invierte, todos los
        gráficos de evolución muestran el progreso al revés."""
        puntos = grafico.linea([10, 20])["puntos"]
        assert puntos[1]["y"] < puntos[0]["y"]

    def test_los_puntos_caen_dentro_del_lienzo(self):
        salida = grafico.linea([5, 25, 15], minimo=5, maximo=25, alto=150)
        assert all(0 <= p["y"] <= 150 for p in salida["puntos"] if p)


class TestBarras:
    def test_una_barra_por_valor(self):
        assert len(grafico.barras([1, 2, 3])["barras"]) == 3

    def test_las_semanas_sin_dato_quedan_marcadas(self):
        barras = grafico.barras([100, None, 50])["barras"]
        assert barras[1]["vacia"] is True and barras[1]["h"] == 0

    def test_ninguna_barra_se_pasa_del_lienzo(self):
        """`maximo` es el tope del eje, no la altura: un valor que lo supera se
        recorta a la barra llena en vez de dibujarse fuera del gráfico."""
        alto = 140
        util = alto - grafico.MARGEN_Y * 2
        barras = grafico.barras([50, 300], maximo=100, alto=alto)["barras"]
        assert all(0 <= b["h"] <= util for b in barras)
        assert barras[1]["h"] == util          # el 300 llega al tope, no más
        assert barras[0]["h"] == util / 2      # el 50 es la mitad del eje

    def test_todo_cero_no_divide_por_cero(self):
        salida = grafico.barras([0, 0, 0])
        assert salida["max"] > 0

    def test_serie_vacia(self):
        assert grafico.barras([])["barras"] == []


class TestCorrelacion:
    def test_relacion_directa_perfecta(self):
        assert grafico.correlacion([(1, 2), (2, 4), (3, 6), (4, 8)]) == 1.0

    def test_relacion_inversa_perfecta(self):
        assert grafico.correlacion([(1, 8), (2, 6), (3, 4), (4, 2)]) == -1.0

    def test_con_menos_de_cuatro_pares_no_se_informa(self):
        """Con tres puntos cualquier par de variables 'correlaciona': mostrarlo
        sería inventarle al profesor una relación que es puro ruido."""
        assert grafico.correlacion([(1, 2), (2, 4), (3, 6)]) is None

    def test_una_variable_constante_no_correlaciona(self):
        assert grafico.correlacion([(5, 1), (5, 2), (5, 3), (5, 4)]) is None


class TestDispersion:
    def test_sin_pares_no_rompe(self):
        assert grafico.dispersion([])["puntos"] == []

    def test_un_solo_par_no_divide_por_cero(self):
        salida = grafico.dispersion([(10, 100)])
        assert len(salida["puntos"]) == 1
