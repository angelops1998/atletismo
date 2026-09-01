"""Cálculos sobre los partes semanales.

Nada de esto se guarda en la base: son derivados de columnas que ya están, y una
columna calculada que se desincroniza miente peor que no tenerla. Con 30 atletas
y 52 semanas al año el volumen es mínimo, así que se calcula al vuelo.
"""
from datetime import date, timedelta
from typing import Iterable, Optional
from sqlalchemy.orm import Session

from ..models.parte import ParteSemanal
from ..models.user import User
from ..tiempo import lunes_de, lunes_actual

# Los cinco ítems del cuestionario, todos 1–5 y todos en el mismo sentido
# (5 = mejor). El orden es el que se muestra en el formulario.
ITEMS = [
    ("sueno_calidad",  "Sueño",          "¿Cómo dormiste esta semana?"),
    ("fatiga",         "Energía",        "¿Con cuánta energía te sentiste?"),
    ("dolor_muscular", "Dolor muscular", "¿Cómo estuvieron tus músculos?"),
    ("estres",         "Estrés",         "¿Qué tan tranquilo estuviste?"),
    ("animo",          "Ánimo",          "¿Cómo estuvo tu ánimo?"),
]

# Las etiquetas de cada valor, por ítem. Un "3" pelado no le dice nada al atleta
# que carga desde el celular; con la palabra al lado contesta lo que quiso decir.
ETIQUETAS = {
    "sueno_calidad":  ["Muy mal", "Mal", "Normal", "Bien", "Muy bien"],
    "fatiga":         ["Agotado", "Cansado", "Normal", "Con energía", "Muy bien"],
    "dolor_muscular": ["Muy dolorido", "Dolorido", "Algo cargado", "Casi sin dolor", "Sin dolor"],
    "estres":         ["Muy estresado", "Estresado", "Normal", "Tranquilo", "Muy tranquilo"],
    "animo":          ["Muy bajo", "Bajo", "Normal", "Bien", "Muy bien"],
}

MAXIMO = len(ITEMS) * 5   # 25


def bienestar_total(parte: ParteSemanal) -> int:
    """Suma de los cinco ítems: 5 (todo mal) a 25 (todo bien)."""
    return sum(getattr(parte, campo) or 0 for campo, _l, _p in ITEMS)


def bienestar_pct(parte: ParteSemanal) -> int:
    """El bienestar como porcentaje, para las barras y los semáforos."""
    return round(bienestar_total(parte) / MAXIMO * 100)


def carga_ua(parte: ParteSemanal) -> Optional[int]:
    """Carga de la semana en unidades arbitrarias: RPE × minutos (método sRPE).

    Es la forma estándar de poner en un solo número una semana de entrenamiento:
    300 minutos suaves y 150 minutos muy intensos pueden costarle lo mismo al
    cuerpo, y solo multiplicando el esfuerzo percibido por el tiempo se ven iguales.
    """
    if parte.rpe is None or parte.minutos_totales is None:
        return None
    return int(parte.rpe) * int(parte.minutos_totales)


def semaforo(parte: ParteSemanal) -> str:
    """'bien' | 'atencion' | 'mal' — el color con el que se pinta la semana."""
    total = bienestar_total(parte)
    if total <= 12 or any((getattr(parte, c) or 5) == 1 for c, _l, _p in ITEMS):
        return "mal"
    if total <= 17:
        return "atencion"
    return "bien"


def promedio(valores: Iterable) -> Optional[float]:
    """Promedio ignorando los None (los campos opcionales del parte)."""
    limpios = [float(v) for v in valores if v is not None]
    if not limpios:
        return None
    return round(sum(limpios) / len(limpios), 2)


def semanas_hasta_hoy(cantidad: int, desde: date | None = None) -> list[date]:
    """Los últimos `cantidad` lunes, del más viejo al más nuevo.

    Se arma la lista completa —incluidas las semanas sin ningún parte— para que
    los gráficos muestren los huecos: una semana en la que nadie cargó nada es
    justamente lo que el profesor tiene que ver.
    """
    fin = lunes_de(desde) if desde else lunes_actual()
    return [fin - timedelta(weeks=i) for i in range(cantidad - 1, -1, -1)]


def partes_de(db: Session, atleta_id: int, semanas: int = 12) -> list[ParteSemanal]:
    """Los partes del atleta en las últimas `semanas`, del más viejo al más nuevo."""
    desde = lunes_actual() - timedelta(weeks=semanas - 1)
    return (db.query(ParteSemanal)
            .filter(ParteSemanal.atleta_id == atleta_id, ParteSemanal.semana >= desde)
            .order_by(ParteSemanal.semana)
            .all())


def parte_de_semana(db: Session, atleta_id: int, semana: date) -> Optional[ParteSemanal]:
    return (db.query(ParteSemanal)
            .filter(ParteSemanal.atleta_id == atleta_id, ParteSemanal.semana == semana)
            .first())


def serie_individual(db: Session, atleta_id: int, semanas: int = 12) -> list[dict]:
    """Una fila por semana con los indicadores del atleta (None si no cargó)."""
    partes = {p.semana: p for p in partes_de(db, atleta_id, semanas)}
    filas = []
    for semana in semanas_hasta_hoy(semanas):
        p = partes.get(semana)
        filas.append({
            "semana": semana,
            "parte": p,
            "bienestar": bienestar_total(p) if p else None,
            "sueno": float(p.horas_sueno) if p and p.horas_sueno is not None else None,
            "carga": carga_ua(p) if p else None,
            "peso": float(p.peso_kg) if p and p.peso_kg is not None else None,
            "dolor": p.molestia_dolor if p and p.molestias else None,
        })
    return filas


def serie_grupo(db: Session, semanas: int = 12) -> list[dict]:
    """Los promedios del club por semana, más cuántos atletas cargaron el parte.

    El porcentaje de partes cargados es un indicador en sí mismo: si baja, todos
    los demás números de esa semana están hechos con la mitad del grupo y no se
    pueden comparar contra las semanas anteriores.
    """
    total_atletas = (db.query(User)
                     .filter(User.role == "atleta", User.is_active.is_(True))
                     .count())
    desde = lunes_actual() - timedelta(weeks=semanas - 1)
    partes = (db.query(ParteSemanal)
              .join(User, User.id == ParteSemanal.atleta_id)
              .filter(ParteSemanal.semana >= desde, User.is_active.is_(True))
              .all())

    por_semana: dict[date, list[ParteSemanal]] = {}
    for p in partes:
        por_semana.setdefault(p.semana, []).append(p)

    filas = []
    for semana in semanas_hasta_hoy(semanas):
        grupo = por_semana.get(semana, [])
        filas.append({
            "semana": semana,
            "cargados": len(grupo),
            "total": total_atletas,
            "pct_cargados": round(len(grupo) / total_atletas * 100) if total_atletas else 0,
            "bienestar": promedio([bienestar_total(p) for p in grupo]),
            "sueno": promedio([p.horas_sueno for p in grupo]),
            "carga": promedio([carga_ua(p) for p in grupo]),
            "alimentacion": promedio([p.alimentacion_calidad for p in grupo]),
            "hidratacion": promedio([p.hidratacion_litros for p in grupo]),
            "con_molestias": sum(1 for p in grupo if p.molestias),
        })
    return filas


def promedio_items_grupo(db: Session, semana: date) -> dict:
    """Promedio de cada ítem del cuestionario en una semana.

    Sirve para el gráfico de barras del panel: muestra de un vistazo si lo que
    está flojo en el club es el sueño, la alimentación o la cabeza.
    """
    partes = (db.query(ParteSemanal)
              .join(User, User.id == ParteSemanal.atleta_id)
              .filter(ParteSemanal.semana == semana, User.is_active.is_(True))
              .all())
    return {campo: promedio([getattr(p, campo) for p in partes])
            for campo, _l, _p in ITEMS}


def cruce_con_marcas(db: Session, semanas: int = 26) -> dict:
    """Cruza el bienestar de cada semana con el rendimiento de esa misma semana.

    Es la pregunta que el profesor quiere contestar con los datos: "¿los que
    duermen y comen bien rinden más?". Para poder juntar en un mismo gráfico a un
    velocista y a un lanzador, cada marca se convierte en un porcentaje del mejor
    registro personal del atleta en esa prueba: 100 significa que igualó su
    récord, 95 que quedó un 5% por debajo. Así se comparan atletas y pruebas que
    en unidades crudas no tienen nada que ver.
    """
    from ..models.marca import Marca
    from . import pruebas as cat

    desde = lunes_actual() - timedelta(weeks=semanas - 1)
    marcas = (db.query(Marca)
              .join(User, User.id == Marca.atleta_id)
              .filter(Marca.fecha >= desde, User.is_active.is_(True))
              .all())
    if not marcas:
        return {"bienestar": [], "sueno": [], "carga": [], "muestras": 0}

    # El récord personal se toma sobre TODO el historial del atleta, no solo
    # sobre el período mirado: si no, el mejor de las últimas semanas sería
    # siempre un 100 y el eje quedaría aplastado contra el techo.
    historial = (db.query(Marca.atleta_id, Marca.prueba, Marca.valor)
                 .join(User, User.id == Marca.atleta_id).all())
    mejores: dict[tuple[int, str], float] = {}
    for atleta_id, prueba, valor in historial:
        clave = (atleta_id, prueba)
        actual = mejores.get(clave)
        v = float(valor)
        if actual is None or (v < actual if cat.menor_es_mejor(prueba) else v > actual):
            mejores[clave] = v

    partes = {(p.atleta_id, p.semana): p for p in db.query(ParteSemanal)
              .filter(ParteSemanal.semana >= desde).all()}

    cruce_bienestar, cruce_sueno, cruce_carga = [], [], []
    for m in marcas:
        parte = partes.get((m.atleta_id, lunes_de(m.fecha)))
        if parte is None:
            continue
        mejor = mejores.get((m.atleta_id, m.prueba))
        if not mejor:
            continue
        valor = float(m.valor)
        rendimiento = (mejor / valor * 100 if cat.menor_es_mejor(m.prueba)
                       else valor / mejor * 100)
        rendimiento = round(rendimiento, 1)
        cruce_bienestar.append((bienestar_total(parte), rendimiento))
        if parte.horas_sueno is not None:
            cruce_sueno.append((float(parte.horas_sueno), rendimiento))
        carga = carga_ua(parte)
        if carga is not None:
            cruce_carga.append((carga, rendimiento))

    return {"bienestar": cruce_bienestar, "sueno": cruce_sueno,
            "carga": cruce_carga, "muestras": len(cruce_bienestar)}
