"""Convierte los partes semanales en cosas que el profesor puede hacer hoy.

Este módulo es el "para qué" de todo el sistema: nadie va a leer 30 formularios
por semana. Cada regla mira un dato concreto y devuelve una frase accionable.

Dos criterios que valen para todas las reglas:

* La referencia de cada atleta es ÉL MISMO, no el promedio del club. Hay chicos
  que siempre puntúan 3 y otros que siempre puntúan 5; comparándolos contra el
  grupo, al primero se lo ve siempre en rojo y al segundo nunca, aunque haya
  empeorado. Lo que importa es el cambio contra sus propias semanas anteriores.
* Los umbrales están acá arriba, con nombre y comentados, para que se puedan
  ajustar después de usar el sistema unos meses sin salir a buscarlos por el código.
"""
from sqlalchemy.orm import Session

from ..models.user import User
from ..tiempo import lunes_actual
from . import bienestar, cobranza

# --- Umbrales ---
BIENESTAR_BAJO = 12          # sobre 25: por debajo de esto la semana fue mala
CAIDA_PCT = 20               # % de caída contra su propio promedio de 4 semanas
DOLOR_ALTO = 5               # sobre 10: de acá para arriba se revisa antes de entrenar
SUENO_MINIMO = 7.0           # horas por noche
SEMANAS_SUENO = 2            # cuántas seguidas por debajo del mínimo para avisar
ACWR_ALTO = 1.5              # salto de carga: riesgo de lesión
ACWR_BAJO = 0.8              # caída de carga: se está desentrenando
PESO_PCT = 3.0               # % de variación contra su promedio del último mes
SEMANAS_REFERENCIA = 4       # ventana con la que se compara cada semana

# Cada alerta tiene una prioridad, y el panel las ordena por ahí: primero lo que
# puede terminar en una lesión, después lo administrativo.
PRIORIDAD = {"alta": 0, "media": 1, "baja": 2}


def _alerta(tipo, nivel, titulo, detalle):
    return {"tipo": tipo, "nivel": nivel, "titulo": titulo, "detalle": detalle}


def acwr(serie: list[dict]) -> float | None:
    """Ratio carga aguda / carga crónica: la carga de la última semana dividida
    por el promedio de las 4 previas.

    Es el indicador más usado para anticipar lesiones por sobrecarga: no lastima
    entrenar mucho, lastima entrenar de golpe mucho más que lo que el cuerpo
    venía tolerando. Devuelve None si no hay historial suficiente.
    """
    if not serie or serie[-1]["carga"] is None:
        return None
    previas = [f["carga"] for f in serie[:-1][-SEMANAS_REFERENCIA:] if f["carga"] is not None]
    if len(previas) < 2:
        return None
    cronica = sum(previas) / len(previas)
    if not cronica:
        return None
    return round(serie[-1]["carga"] / cronica, 2)


def _sin_parte(atleta, ultima, semana_actual):
    if ultima is None or ultima["parte"] is None:
        return _alerta("sin_parte", "media", "No cargó el parte",
                       "Todavía no completó el parte de esta semana.")
    return None


def _bienestar(atleta, parte, serie):
    salida = []
    total = bienestar.bienestar_total(parte)
    if total <= BIENESTAR_BAJO:
        salida.append(_alerta("bienestar_bajo", "alta", "Bienestar bajo",
                              f"Puntuó {total} sobre {bienestar.MAXIMO} esta semana."))
    peores = [etiqueta for campo, etiqueta, _p in bienestar.ITEMS
              if (getattr(parte, campo) or 5) == 1]
    if peores:
        salida.append(_alerta("item_minimo", "alta", "Puntuó el mínimo",
                              f"Marcó 1 sobre 5 en: {', '.join(peores).lower()}."))

    # Caída contra su propio promedio de las semanas anteriores
    previas = [f["bienestar"] for f in serie[:-1][-SEMANAS_REFERENCIA:] if f["bienestar"]]
    if len(previas) >= 2:
        base = sum(previas) / len(previas)
        if base and total < base * (1 - CAIDA_PCT / 100):
            caida = round((base - total) / base * 100)
            salida.append(_alerta("caida_bienestar", "alta", "Cayó su bienestar",
                                  f"Bajó {caida}% respecto de sus últimas semanas "
                                  f"({total} contra {round(base)} de promedio)."))
    return salida


def _molestia(atleta, parte):
    if not parte.molestias:
        return None
    dolor = parte.molestia_dolor or 0
    zona = parte.molestia_zona or "sin especificar"
    nivel = "alta" if dolor >= DOLOR_ALTO else "media"
    return _alerta("molestia", nivel, "Reportó una molestia",
                   f"{zona} — dolor {dolor}/10.")


def _sueno(atleta, serie):
    ultimas = [f["sueno"] for f in serie[-SEMANAS_SUENO:] if f["sueno"] is not None]
    if len(ultimas) < SEMANAS_SUENO:
        return None
    if all(h < SUENO_MINIMO for h in ultimas):
        return _alerta("sueno_insuficiente", "media", "Duerme poco",
                       f"{SEMANAS_SUENO} semanas seguidas por debajo de "
                       f"{SUENO_MINIMO:g} h por noche (última: {ultimas[-1]:g} h).")
    return None


def _carga(atleta, serie):
    ratio = acwr(serie)
    if ratio is None:
        return None
    if ratio > ACWR_ALTO:
        return _alerta("salto_de_carga", "alta", "Subió mucho la carga",
                       f"Entrenó {ratio}× lo que venía haciendo. "
                       "Conviene aflojar antes de que aparezca una lesión.")
    if ratio < ACWR_BAJO:
        return _alerta("caida_de_carga", "baja", "Bajó la carga",
                       f"Entrenó {ratio}× lo habitual: viene entrenando menos.")
    return None


def _peso(atleta, serie):
    pesos = [f["peso"] for f in serie if f["peso"] is not None]
    if len(pesos) < 3:
        return None
    actual, previos = pesos[-1], pesos[-(SEMANAS_REFERENCIA + 1):-1]
    if not previos:
        return None
    base = sum(previos) / len(previos)
    if not base:
        return None
    variacion = (actual - base) / base * 100
    if abs(variacion) >= PESO_PCT:
        signo = "Subió" if variacion > 0 else "Bajó"
        return _alerta("cambio_de_peso", "media", f"{signo} de peso",
                       f"{abs(round(variacion, 1))}% en el último mes "
                       f"({actual:g} kg contra {round(base, 1):g} kg).")
    return None


def del_atleta(db: Session, atleta: User, serie: list[dict] | None = None,
               cuenta: dict | None = None) -> list[dict]:
    """Todas las alertas de un atleta, de la más urgente a la menos.

    `serie` y `cuenta` se pasan ya resueltos cuando se está calculando el padrón
    entero (ver del_club): así la pantalla no vuelve a la base una vez por atleta.
    """
    serie = serie if serie is not None else bienestar.serie_individual(db, atleta.id)
    semana = lunes_actual()
    ultima = serie[-1] if serie else None
    salida = []

    falta = _sin_parte(atleta, ultima, semana)
    if falta:
        salida.append(falta)

    parte = ultima["parte"] if ultima else None
    if parte is not None:
        salida += _bienestar(atleta, parte, serie)
        for regla in (_molestia(atleta, parte),):
            if regla:
                salida.append(regla)
    for regla in (_sueno(atleta, serie), _carga(atleta, serie), _peso(atleta, serie)):
        if regla:
            salida.append(regla)

    estado = cuenta if cuenta is not None else cobranza.estado_cuenta(db, atleta)
    if estado["estado"] == "debe":
        nivel = "media" if estado["cantidad"] >= 2 else "baja"
        salida.append(_alerta("pago_vencido", nivel, estado["texto"],
                              f"Adeuda {cobranza.formato_pesos(estado['deuda'])} en total."))

    salida.sort(key=lambda a: PRIORIDAD[a["nivel"]])
    return salida


def del_club(db: Session) -> list[dict]:
    """Las alertas de todos los atletas activos, agrupadas por persona.

    Es lo que se muestra en el panel: una tarjeta por atleta con problemas, las
    más urgentes arriba. Los atletas sin alertas no aparecen.
    """
    atletas = (db.query(User)
               .filter(User.role == "atleta", User.is_active.is_(True))
               .order_by(User.full_name, User.username)
               .all())
    # Todo lo que hace falta, en dos consultas en vez de dos por atleta.
    series = bienestar.series_de(db, [a.id for a in atletas])
    cuentas = cobranza.estados_de(db, atletas)
    salida = []
    for a in atletas:
        serie = series[a.id]
        alertas = del_atleta(db, a, serie, cuentas[a.id])
        if alertas:
            salida.append({
                "atleta": a,
                "alertas": alertas,
                "peor": min(PRIORIDAD[x["nivel"]] for x in alertas),
            })
    salida.sort(key=lambda f: (f["peor"], -len(f["alertas"])))
    return salida
