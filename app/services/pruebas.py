"""Catálogo de pruebas de atletismo.

Vive en código y no en la base porque es una lista fija: las pruebas del
atletismo no las inventa cada club. Cada entrada define cómo se mide la prueba y,
sobre todo, hacia dónde es "mejor": en los 100 m bajar de 12.40 a 12.10 es una
mejora, en salto largo es un retroceso. Sin ese dato, cualquier gráfico de
evolución termina mostrando el progreso al revés.
"""
from decimal import Decimal

# (clave, nombre, grupo, unidad, menor_es_mejor, decimales)
PRUEBAS = [
    ("60m",        "60 m llanos",        "Velocidad",     "s",  True,  2),
    ("100m",       "100 m llanos",       "Velocidad",     "s",  True,  2),
    ("200m",       "200 m llanos",       "Velocidad",     "s",  True,  2),
    ("400m",       "400 m llanos",       "Velocidad",     "s",  True,  2),
    ("800m",       "800 m",              "Medio fondo",   "s",  True,  2),
    ("1500m",      "1500 m",             "Medio fondo",   "s",  True,  2),
    ("3000m",      "3000 m",             "Fondo",         "s",  True,  2),
    ("5000m",      "5000 m",             "Fondo",         "s",  True,  2),
    ("10000m",     "10.000 m",           "Fondo",         "s",  True,  2),
    ("110vallas",  "110 m con vallas",   "Vallas",        "s",  True,  2),
    ("400vallas",  "400 m con vallas",   "Vallas",        "s",  True,  2),
    ("largo",      "Salto en largo",     "Saltos",        "m",  False, 2),
    ("triple",     "Salto triple",       "Saltos",        "m",  False, 2),
    ("alto",       "Salto en alto",      "Saltos",        "m",  False, 2),
    ("garrocha",   "Salto con garrocha", "Saltos",        "m",  False, 2),
    ("bala",       "Lanzamiento de bala", "Lanzamientos", "m",  False, 2),
    ("disco",      "Lanzamiento de disco", "Lanzamientos", "m", False, 2),
    ("jabalina",   "Lanzamiento de jabalina", "Lanzamientos", "m", False, 2),
    ("martillo",   "Lanzamiento de martillo", "Lanzamientos", "m", False, 2),
]

_POR_CLAVE = {p[0]: p for p in PRUEBAS}


def existe(clave: str) -> bool:
    return clave in _POR_CLAVE


def nombre(clave: str) -> str:
    p = _POR_CLAVE.get(clave)
    return p[1] if p else clave


def unidad(clave: str) -> str:
    p = _POR_CLAVE.get(clave)
    return p[3] if p else ""


def menor_es_mejor(clave: str) -> bool:
    p = _POR_CLAVE.get(clave)
    return p[4] if p else True


def grupos() -> dict:
    """Las pruebas agrupadas por familia, para armar el <select> del formulario
    con <optgroup>: con 19 pruebas en una lista plana, en el celular hay que
    hacer scroll a ciegas."""
    salida = {}
    for clave, nom, grupo, _u, _m, _d in PRUEBAS:
        salida.setdefault(grupo, []).append((clave, nom))
    return salida


def formatear(clave: str, valor) -> str:
    """12.34 s · 5.87 m · y los tiempos largos en minutos: 4:32.10.

    Nadie dice que corrió los 1500 en "272.10 segundos": se guarda en segundos
    porque es lo único que se puede promediar y graficar, pero se muestra como lo
    lee el profesor.
    """
    if valor is None:
        return "—"
    p = _POR_CLAVE.get(clave)
    decimales = p[5] if p else 2
    u = p[3] if p else ""
    v = Decimal(str(valor))
    if u == "s" and v >= 60:
        minutos = int(v // 60)
        segundos = v - (minutos * 60)
        return f"{minutos}:{segundos:0{decimales + 3}.{decimales}f}"
    return f"{v:.{decimales}f} {u}".strip()


def mejor(clave: str, valores: list):
    """La mejor marca de la lista, según el sentido de la prueba."""
    limpios = [v for v in valores if v is not None]
    if not limpios:
        return None
    return min(limpios) if menor_es_mejor(clave) else max(limpios)


def es_mejora(clave: str, nuevo, anterior) -> bool | None:
    """Si `nuevo` es mejor que `anterior`. None si no hay con qué comparar."""
    if nuevo is None or anterior is None:
        return None
    if menor_es_mejor(clave):
        return nuevo < anterior
    return nuevo > anterior


def progreso_pct(clave: str, nuevo, anterior) -> float | None:
    """Cuánto mejoró en porcentaje (positivo = mejoró), en el sentido correcto."""
    if nuevo is None or anterior is None or not anterior:
        return None
    n, a = float(nuevo), float(anterior)
    if not a:
        return None
    delta = (a - n) / a * 100 if menor_es_mejor(clave) else (n - a) / a * 100
    return round(delta, 2)
