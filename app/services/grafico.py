"""Arma los puntos de los gráficos; el SVG lo dibuja el template.

No se usa ninguna librería de gráficos. La app se ve sobre todo en el celular del
atleta y del profesor: sumar 100 kB de JavaScript para dibujar cuatro líneas es
el tipo de cosa que hace que la página no abra con mala señal. Un <svg> generado
por Jinja pesa unos pocos bytes, se ve nítido en cualquier pantalla y se imprime
bien.

Todas las funciones devuelven coordenadas ya escaladas a un viewBox fijo, así el
template solo tiene que interpolar strings.
"""
from typing import Sequence, Optional

ANCHO = 600
ALTO = 180
MARGEN_X = 8
MARGEN_Y = 12


def _escala(valores: Sequence[Optional[float]]) -> tuple[float, float]:
    """Mínimo y máximo del eje Y, con un poco de aire arriba y abajo.

    Si todos los valores son iguales, se abre un rango artificial: sin esto la
    línea quedaría pegada al borde o se dividiría por cero.
    """
    limpios = [float(v) for v in valores if v is not None]
    if not limpios:
        return 0.0, 1.0
    minimo, maximo = min(limpios), max(limpios)
    if minimo == maximo:
        return minimo - 1, maximo + 1
    aire = (maximo - minimo) * 0.15
    return minimo - aire, maximo + aire


def linea(valores: Sequence[Optional[float]], *, ancho: int = ANCHO, alto: int = ALTO,
          minimo: float | None = None, maximo: float | None = None) -> dict:
    """Serie de puntos para un gráfico de líneas.

    Los None (semanas sin parte) NO se interpolan: cortan la línea en segmentos.
    Dibujar una recta sobre una semana sin datos haría creer que el atleta cargó
    algo, que es justo lo contrario de lo que hay que ver.
    """
    n = len(valores)
    if n == 0:
        return {"segmentos": [], "puntos": [], "min": 0, "max": 1,
                "ancho": ancho, "alto": alto}

    auto_min, auto_max = _escala(valores)
    y_min = auto_min if minimo is None else float(minimo)
    y_max = auto_max if maximo is None else float(maximo)
    if y_max == y_min:
        y_max = y_min + 1

    util_x = ancho - MARGEN_X * 2
    util_y = alto - MARGEN_Y * 2

    def x_de(i: int) -> float:
        return MARGEN_X + (util_x * i / (n - 1) if n > 1 else util_x / 2)

    def y_de(v: float) -> float:
        return MARGEN_Y + util_y * (1 - (float(v) - y_min) / (y_max - y_min))

    puntos, segmentos, actual = [], [], []
    for i, v in enumerate(valores):
        if v is None:
            if len(actual) > 1:
                segmentos.append(actual)
            actual = []
            puntos.append(None)
            continue
        p = {"x": round(x_de(i), 2), "y": round(y_de(v), 2), "valor": v, "i": i}
        puntos.append(p)
        actual.append(p)
    if len(actual) > 1:
        segmentos.append(actual)

    return {
        "segmentos": [" ".join(f"{p['x']},{p['y']}" for p in seg) for seg in segmentos],
        "puntos": puntos,
        "min": round(y_min, 2),
        "max": round(y_max, 2),
        "ancho": ancho,
        "alto": alto,
        # Una sola lectura no dibuja línea: el template pinta igual el punto para
        # que el atleta que recién arranca vea que su dato quedó registrado.
        "solo_puntos": not segmentos,
    }


def barras(valores: Sequence[Optional[float]], *, maximo: float | None = None,
           ancho: int = ANCHO, alto: int = ALTO) -> dict:
    """Barras verticales desde el piso del gráfico (carga semanal, ingresos)."""
    n = len(valores)
    if n == 0:
        return {"barras": [], "max": 1, "ancho": ancho, "alto": alto}

    limpios = [float(v) for v in valores if v is not None]
    tope = float(maximo) if maximo is not None else (max(limpios) * 1.15 if limpios else 1)
    if tope <= 0:
        tope = 1

    util_x = ancho - MARGEN_X * 2
    util_y = alto - MARGEN_Y * 2
    paso = util_x / n
    grosor = max(paso * 0.55, 3)

    salida = []
    for i, v in enumerate(valores):
        valor = 0 if v is None else float(v)
        altura = util_y * min(valor / tope, 1)
        salida.append({
            "x": round(MARGEN_X + paso * i + (paso - grosor) / 2, 2),
            "y": round(MARGEN_Y + util_y - altura, 2),
            "w": round(grosor, 2),
            "h": round(max(altura, 0), 2),
            "valor": v,
            "vacia": v is None,
            "i": i,
        })
    return {"barras": salida, "max": round(tope, 2), "ancho": ancho, "alto": alto,
            "piso": MARGEN_Y + util_y}


def dispersion(pares: Sequence[tuple[float, float]], *, ancho: int = ANCHO,
               alto: int = ALTO) -> dict:
    """Nube de puntos para cruzar dos variables (bienestar contra rendimiento).

    Es el gráfico que contesta la pregunta del profesor: "¿las semanas en que
    duermen bien rinden más?". Ve la relación aunque no haya una fórmula detrás.
    """
    if not pares:
        return {"puntos": [], "ancho": ancho, "alto": alto}
    xs = [p[0] for p in pares]
    ys = [p[1] for p in pares]
    x_min, x_max = _escala(xs)
    y_min, y_max = _escala(ys)
    util_x = ancho - MARGEN_X * 2
    util_y = alto - MARGEN_Y * 2

    puntos = [{
        "x": round(MARGEN_X + util_x * (x - x_min) / (x_max - x_min), 2),
        "y": round(MARGEN_Y + util_y * (1 - (y - y_min) / (y_max - y_min)), 2),
        "vx": x, "vy": y,
    } for x, y in pares]
    return {"puntos": puntos, "ancho": ancho, "alto": alto,
            "x_min": round(x_min, 2), "x_max": round(x_max, 2),
            "y_min": round(y_min, 2), "y_max": round(y_max, 2)}


def correlacion(pares: Sequence[tuple[float, float]]) -> float | None:
    """Coeficiente de Pearson, redondeado. None si hay menos de 4 pares.

    Con tres puntos cualquier par de variables "correlaciona": pedir un mínimo
    evita mostrarle al profesor una relación que es puro ruido.
    """
    if len(pares) < 4:
        return None
    n = len(pares)
    xs = [float(p[0]) for p in pares]
    ys = [float(p[1]) for p in pares]
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if not dx or not dy:
        return None
    return round(num / (dx * dy), 2)
