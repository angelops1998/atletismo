"""Catálogo de pruebas de atletismo.

Vive en código y no en la base porque es una lista fija: las pruebas del
atletismo no las inventa cada club. Cada entrada define cómo se mide la prueba y,
sobre todo, hacia dónde es "mejor": en los 100 m bajar de 12.40 a 12.10 es una
mejora, en salto largo es un retroceso. Sin ese dato, cualquier gráfico de
evolución termina mostrando el progreso al revés.
"""
from decimal import Decimal

# Categorías del club para las que se lleva el historial de marcas. Son dos
# planillas distintas porque las pruebas cambian: los Menores (10 a 13 años)
# corren 80 y 150 m, no 100 y 200, y con vallas y pesos más bajos.
MAYORES = "mayores"      # Juveniles y Mayores
MENORES = "menores"      # Menores (10 a 13) y Pequeños
CATEGORIAS = [(MAYORES, "Juveniles y Mayores"), (MENORES, "Menores")]
_AMBAS = frozenset({MAYORES, MENORES})
_MAY = frozenset({MAYORES})
_MEN = frozenset({MENORES})

# (clave, nombre, grupo, unidad, menor_es_mejor, decimales, categorías)
#
# La lista de Mayores es la planilla que mandó el club. La de Menores es
# PROVISORIA: quedó armada con el programa habitual de la categoría (U14) hasta
# que el club mande la suya; cambiarla es tocar solo esta tabla.
PRUEBAS = [
    # --- Velocidad ---
    ("60m",         "60 m llanos",            "Velocidad",     "s",   True,  2, _MEN),
    ("80m",         "80 m llanos",            "Velocidad",     "s",   True,  2, _MEN),
    ("100m",        "100 m llanos",           "Velocidad",     "s",   True,  2, _AMBAS),
    ("150m",        "150 m llanos",           "Velocidad",     "s",   True,  2, _MEN),
    ("200m",        "200 m llanos",           "Velocidad",     "s",   True,  2, _MAY),
    ("300m",        "300 m llanos",           "Velocidad",     "s",   True,  2, _MEN),
    ("400m",        "400 m llanos",           "Velocidad",     "s",   True,  2, _MAY),
    # --- Medio fondo ---
    ("600m",        "600 m",                  "Medio fondo",   "s",   True,  2, _MEN),
    ("800m",        "800 m",                  "Medio fondo",   "s",   True,  2, _MAY),
    ("1000m",       "1000 m",                 "Medio fondo",   "s",   True,  2, _MEN),
    ("1500m",       "1500 m",                 "Medio fondo",   "s",   True,  2, _MAY),
    # --- Fondo ---
    ("2000m",       "2000 m",                 "Fondo",         "s",   True,  2, _MEN),
    ("3000m",       "3000 m",                 "Fondo",         "s",   True,  2, _MAY),
    ("5000m",       "5000 m",                 "Fondo",         "s",   True,  2, _MAY),
    ("10000m",      "10.000 m",               "Fondo",         "s",   True,  2, _MAY),
    # --- Vallas y obstáculos ---
    ("60vallas",    "60 m con vallas",        "Vallas",        "s",   True,  2, _MEN),
    ("80vallas",    "80 m con vallas",        "Vallas",        "s",   True,  2, _MEN),
    ("100vallas",   "100 m con vallas",       "Vallas",        "s",   True,  2, _MAY),
    ("110vallas",   "110 m con vallas",       "Vallas",        "s",   True,  2, _MAY),
    ("400vallas",   "400 m con vallas",       "Vallas",        "s",   True,  2, _MAY),
    ("2000obs",     "2000 m con obstáculos",  "Vallas",        "s",   True,  2, _MAY),
    ("3000obs",     "3000 m con obstáculos",  "Vallas",        "s",   True,  2, _MAY),
    # --- Marcha ---
    ("2000marcha",  "2000 m marcha",          "Marcha",        "s",   True,  2, _MEN),
    ("3000marcha",  "3000 m marcha",          "Marcha",        "s",   True,  2, _MEN),
    ("5000marcha",  "5000 m marcha",          "Marcha",        "s",   True,  2, _MAY),
    ("10000marcha", "10.000 m marcha",        "Marcha",        "s",   True,  2, _MAY),
    ("21kmarcha",   "21 km marcha",           "Marcha",        "s",   True,  0, _MAY),
    # --- Saltos ---
    ("largo",       "Salto en largo",         "Saltos",        "m",   False, 2, _AMBAS),
    ("alto",        "Salto en alto",          "Saltos",        "m",   False, 2, _AMBAS),
    ("triple",      "Salto triple",           "Saltos",        "m",   False, 2, _AMBAS),
    ("garrocha",    "Salto con garrocha",     "Saltos",        "m",   False, 2, _AMBAS),
    # --- Lanzamientos ---
    ("bala",        "Lanzamiento de bala",    "Lanzamientos",  "m",   False, 2, _AMBAS),
    ("disco",       "Lanzamiento de disco",   "Lanzamientos",  "m",   False, 2, _AMBAS),
    ("jabalina",    "Lanzamiento de jabalina", "Lanzamientos", "m",   False, 2, _AMBAS),
    ("martillo",    "Lanzamiento de martillo", "Lanzamientos", "m",   False, 2, _AMBAS),
    # --- Pruebas combinadas (se cargan en puntos) ---
    ("heptatlon",   "Heptatlón",              "Combinadas",    "pts", False, 0, _MAY),
    ("decatlon",    "Decatlón",               "Combinadas",    "pts", False, 0, _MAY),
    ("pentatlon",   "Pentatlón",              "Combinadas",    "pts", False, 0, _MEN),
    ("hexatlon",    "Hexatlón",               "Combinadas",    "pts", False, 0, _MEN),
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


def categorias_de(clave: str) -> frozenset:
    p = _POR_CLAVE.get(clave)
    return p[6] if p else _AMBAS


def categoria_de(texto_categoria: str | None) -> str | None:
    """A qué planilla de pruebas corresponde la categoría escrita en la ficha.

    La categoría del padrón es texto libre ("Menores", "Juveniles", "Mayores",
    "Pequeños"…), así que se resuelve por nombre: lo que empieza con "men" o
    "peq" va a la planilla de Menores; el resto a la de Mayores. None si la
    ficha no tiene categoría, para no filtrar nada.
    """
    if not texto_categoria:
        return None
    t = texto_categoria.strip().lower()
    return MENORES if t.startswith(("men", "peq", "inf", "mini")) else MAYORES


def grupos(categoria: str | None = None) -> dict:
    """Las pruebas agrupadas por familia, para armar el <select> del formulario
    con <optgroup>: con cuarenta pruebas en una lista plana, en el celular hay
    que hacer scroll a ciegas.

    Con `categoria` devuelve solo las de esa planilla; sin ella, todas. Cada
    entrada es (clave, nombre, categorías) para que la plantilla pueda marcar a
    qué planilla pertenece cada opción y filtrarlas sin recargar.
    """
    salida = {}
    for clave, nom, grupo, _u, _m, _d, cats in PRUEBAS:
        if categoria and categoria not in cats:
            continue
        salida.setdefault(grupo, []).append((clave, nom, sorted(cats)))
    return salida


def formatear(clave: str, valor) -> str:
    """12.34 s · 5.87 m · 6.850 pts · y los tiempos largos como el cronómetro:
    4:32.10, y con horas en la marcha larga: 1:45:30.

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
        # Ancho de los segundos con el cero adelante: "05.30" o "05".
        ancho = decimales + 3 if decimales else 2
        minutos_totales = int(v // 60)
        segundos = v - (minutos_totales * 60)
        if minutos_totales >= 60:
            horas, minutos = divmod(minutos_totales, 60)
            return f"{horas}:{minutos:02d}:{segundos:0{ancho}.{decimales}f}"
        return f"{minutos_totales}:{segundos:0{ancho}.{decimales}f}"
    if u == "pts":
        return f"{int(v):,} pts".replace(",", ".")
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
