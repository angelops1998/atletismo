"""Catálogo de pruebas de atletismo.

Vive en código y no en la base porque es una lista fija: las pruebas del
atletismo no las inventa cada club. Cada entrada define cómo se mide la prueba y,
sobre todo, hacia dónde es "mejor": en los 100 m bajar de 12.40 a 12.10 es una
mejora, en salto largo es un retroceso. Sin ese dato, cualquier gráfico de
evolución termina mostrando el progreso al revés.
"""
from decimal import Decimal

# Planillas de pruebas: la categoría por edad decide qué pruebas se compiten.
# Son tres porque el programa cambia con la edad: en U14 se corren 60 y 150 m
# con vallas a 60 y 190, en U16 aparecen los 80 y 300 m, las vallas a 295 y los
# 1500 con obstáculos, y de U18 en adelante rige el programa de Mayores.
MAYORES = "mayores"      # U18, U20 y Mayores
U16 = "u16"              # 14 y 15 años
U14 = "u14"              # 12 y 13 años
CATEGORIAS = [(U14, "U14 (12–13)"), (U16, "U16 (14–15)"), (MAYORES, "U18 y Mayores")]
_TODAS = frozenset({U14, U16, MAYORES})
_MAY = frozenset({MAYORES})
_U16 = frozenset({U16})
_U14 = frozenset({U14})
_U16_MAY = frozenset({U16, MAYORES})
_U14_U16 = frozenset({U14, U16})

# (clave, nombre, grupo, unidad, menor_es_mejor, decimales, planillas)
#
# Las tres listas son las planillas que mandó el club: la de Mayores, la de
# combos U14 (60 m, largo, 60 c/v, 150 m, 190 c/v, 600, 1200, 800, marcha 300 y
# 1600, alto, jabalina y disco) y la de U16 del reglamento técnico 2025 (80 m
# vallas niñas / 100 m vallas niños, 295 c/v, 1500 obstáculos, marcha 3000
# niñas / 5000 niños). Los relevos no están: acá se guardan marcas individuales.
PRUEBAS = [
    # --- Velocidad ---
    ("60m",         "60 m llanos",            "Velocidad",     "s",   True,  2, _U14),
    ("80m",         "80 m llanos",            "Velocidad",     "s",   True,  2, _U16),
    ("100m",        "100 m llanos",           "Velocidad",     "s",   True,  2, _MAY),
    ("150m",        "150 m llanos",           "Velocidad",     "s",   True,  2, _U14_U16),
    ("200m",        "200 m llanos",           "Velocidad",     "s",   True,  2, _MAY),
    ("300m",        "300 m llanos",           "Velocidad",     "s",   True,  2, _U16),
    ("400m",        "400 m llanos",           "Velocidad",     "s",   True,  2, _MAY),
    # --- Medio fondo ---
    ("600m",        "600 m",                  "Medio fondo",   "s",   True,  2, _U14_U16),
    ("800m",        "800 m",                  "Medio fondo",   "s",   True,  2, frozenset({U14, MAYORES})),
    ("1200m",       "1200 m",                 "Medio fondo",   "s",   True,  2, _U14),
    ("1500m",       "1500 m",                 "Medio fondo",   "s",   True,  2, _MAY),
    # --- Fondo ---
    ("2400m",       "2400 m",                 "Fondo",         "s",   True,  2, _U16),
    ("3000m",       "3000 m",                 "Fondo",         "s",   True,  2, _MAY),
    ("5000m",       "5000 m",                 "Fondo",         "s",   True,  2, _MAY),
    ("10000m",      "10.000 m",               "Fondo",         "s",   True,  2, _MAY),
    # --- Vallas y obstáculos ---
    ("60vallas",    "60 m con vallas",        "Vallas",        "s",   True,  2, _U14),
    ("80vallas",    "80 m con vallas",        "Vallas",        "s",   True,  2, _U16),
    ("100vallas",   "100 m con vallas",       "Vallas",        "s",   True,  2, _U16_MAY),
    ("110vallas",   "110 m con vallas",       "Vallas",        "s",   True,  2, _MAY),
    ("190vallas",   "190 m con vallas",       "Vallas",        "s",   True,  2, _U14),
    ("295vallas",   "295 m con vallas",       "Vallas",        "s",   True,  2, _U16),
    ("400vallas",   "400 m con vallas",       "Vallas",        "s",   True,  2, _MAY),
    ("1500obs",     "1500 m con obstáculos",  "Vallas",        "s",   True,  2, _U16),
    ("2000obs",     "2000 m con obstáculos",  "Vallas",        "s",   True,  2, _MAY),
    ("3000obs",     "3000 m con obstáculos",  "Vallas",        "s",   True,  2, _MAY),
    # --- Marcha ---
    ("300marcha",   "300 m marcha",           "Marcha",        "s",   True,  2, _U14),
    ("1600marcha",  "1600 m marcha",          "Marcha",        "s",   True,  2, _U14),
    ("3000marcha",  "3000 m marcha",          "Marcha",        "s",   True,  2, _U16),
    ("5000marcha",  "5000 m marcha",          "Marcha",        "s",   True,  2, _U16_MAY),
    ("10000marcha", "10.000 m marcha",        "Marcha",        "s",   True,  2, _MAY),
    ("21kmarcha",   "21 km marcha",           "Marcha",        "s",   True,  0, _MAY),
    # --- Saltos ---
    ("largo",       "Salto en largo",         "Saltos",        "m",   False, 2, _TODAS),
    ("alto",        "Salto en alto",          "Saltos",        "m",   False, 2, _TODAS),
    ("triple",      "Salto triple",           "Saltos",        "m",   False, 2, _U16_MAY),
    ("garrocha",    "Salto con garrocha",     "Saltos",        "m",   False, 2, _U16_MAY),
    # --- Lanzamientos ---
    ("bala",        "Lanzamiento de bala",    "Lanzamientos",  "m",   False, 2, _U16_MAY),
    ("disco",       "Lanzamiento de disco",   "Lanzamientos",  "m",   False, 2, _TODAS),
    ("jabalina",    "Lanzamiento de jabalina", "Lanzamientos", "m",   False, 2, _TODAS),
    ("martillo",    "Lanzamiento de martillo", "Lanzamientos", "m",   False, 2, _U16_MAY),
    # --- Pruebas combinadas (se cargan en puntos) ---
    ("hexatlon",    "Hexatlón",               "Combinadas",    "pts", False, 0, _U16),
    ("heptatlon",   "Heptatlón",              "Combinadas",    "pts", False, 0, _MAY),
    ("decatlon",    "Decatlón",               "Combinadas",    "pts", False, 0, _MAY),
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
    return p[6] if p else _TODAS


def planilla_de(atleta) -> str | None:
    """Qué planilla le corresponde a un atleta, para preseleccionarla al cargar
    una marca.

    Primero por la edad, que es lo que define la categoría de verdad: hasta 13
    años U14, 14 y 15 U16, de 16 en adelante Mayores. Si la ficha no tiene fecha
    de nacimiento se mira el texto de la categoría ("Menores", "Pequeños"…), y
    si tampoco hay nada, None: se muestran todas y el profesor elige.
    """
    edad = atleta.edad() if atleta is not None else None
    if edad is not None:
        if edad <= 13:
            return U14
        return U16 if edad <= 15 else MAYORES
    texto = ((atleta.categoria if atleta is not None else "") or "").strip().lower()
    if not texto:
        return None
    if texto.startswith(("men", "peq", "inf", "mini", "u14", "u12")):
        return U14
    if texto.startswith(("u16", "cad")):
        return U16
    return MAYORES


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
