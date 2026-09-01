"""Estado de cuenta de los atletas.

La deuda no se guarda en ninguna columna: se calcula contando los meses desde
`users.cobro_desde` hasta el mes actual y restando los períodos con pago
registrado. Guardar un saldo obliga a recalcularlo en cada alta, baja o cambio de
cuota, y basta un olvido para que el profesor le reclame plata a alguien que ya
pagó. Con 30 atletas, calcularlo cada vez no cuesta nada.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.pago import Pago
from ..models.user import User
from ..tiempo import hoy


def formato_pesos(monto, con_signo: bool = True, decimales: bool = False) -> str:
    """Bs 200 — miles con punto y decimales con coma.

    Vive acá y no en el filtro de Jinja porque los montos también aparecen dentro
    de textos armados en Python (las alertas de deuda), y tener dos formatos
    distintos para la misma plata quedaba a la vista en la misma pantalla.
    """
    try:
        d = Decimal(str(monto or 0))
    except (InvalidOperation, ValueError, TypeError):
        d = Decimal(0)
    s = f"{d:,.2f}" if decimales else f"{d:,.0f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs {s}" if con_signo else s


def primer_dia(d: date) -> date:
    """El día 1 del mes de `d`. Es la forma canónica de guardar un período."""
    return d.replace(day=1)


def mes_siguiente(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def mes_anterior(d: date) -> date:
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def meses_entre(desde: date, hasta: date) -> list[date]:
    """Todos los períodos (día 1) entre dos fechas, ambos incluidos."""
    actual, fin, salida = primer_dia(desde), primer_dia(hasta), []
    while actual <= fin:
        salida.append(actual)
        actual = mes_siguiente(actual)
    return salida


def periodos_pagados(db: Session, atleta_id: int) -> set[date]:
    return {p.periodo for p in db.query(Pago.periodo)
            .filter(Pago.atleta_id == atleta_id).all()}


def meses_adeudados(db: Session, atleta: User, hasta: date | None = None) -> list[date]:
    """Los períodos que el atleta debe, del más viejo al más nuevo.

    El mes en curso cuenta como adeudado desde el día 1: el club cobra por mes
    adelantado, que es como trabaja el profesor.
    """
    if not atleta.cobro_desde or not atleta.cuota_mensual:
        return []
    esperados = meses_entre(atleta.cobro_desde, hasta or hoy())
    pagados = periodos_pagados(db, atleta.id)
    return [m for m in esperados if m not in pagados]


def estado_cuenta(db: Session, atleta: User, hasta: date | None = None) -> dict:
    """Resumen para pintar el chip de pago: al día, debe N meses, o sin cuota."""
    if not atleta.cuota_mensual or not atleta.cobro_desde:
        return {"estado": "sin_cuota", "meses": [], "cantidad": 0,
                "deuda": Decimal(0), "texto": "Sin cuota asignada"}
    meses = meses_adeudados(db, atleta, hasta)
    deuda = Decimal(atleta.cuota_mensual) * len(meses)
    if not meses:
        return {"estado": "al_dia", "meses": [], "cantidad": 0,
                "deuda": Decimal(0), "texto": "Al día"}
    plural = "es" if len(meses) != 1 else ""
    return {"estado": "debe", "meses": meses, "cantidad": len(meses),
            "deuda": deuda, "texto": f"Debe {len(meses)} mes{plural}"}


def resumen_club(db: Session, hasta: date | None = None) -> dict:
    """Lo que el profesor mira una vez por mes: cuánto entró y cuánto falta."""
    referencia = hasta or hoy()
    mes = primer_dia(referencia)
    atletas = (db.query(User)
               .filter(User.role == "atleta", User.is_active.is_(True))
               .all())

    cobrado_mes = (db.query(func.coalesce(func.sum(Pago.monto), 0))
                   .filter(Pago.periodo == mes).scalar())
    esperado_mes = sum((Decimal(a.cuota_mensual or 0) for a in atletas), Decimal(0))

    deudores, deuda_total = [], Decimal(0)
    for a in atletas:
        est = estado_cuenta(db, a, referencia)
        if est["estado"] == "debe":
            deudores.append({"atleta": a, **est})
            deuda_total += est["deuda"]
    # Primero el que más meses debe: es a quien hay que llamar hoy.
    deudores.sort(key=lambda d: d["cantidad"], reverse=True)

    return {
        "mes": mes,
        "cobrado_mes": Decimal(cobrado_mes or 0),
        "esperado_mes": esperado_mes,
        "pendiente_mes": max(esperado_mes - Decimal(cobrado_mes or 0), Decimal(0)),
        "deudores": deudores,
        "deuda_total": deuda_total,
        "al_dia": len(atletas) - len(deudores),
        "total_atletas": len(atletas),
    }


def historial_mensual(db: Session, meses: int = 12) -> list[dict]:
    """Cuánto se cobró por mes, para el gráfico de ingresos."""
    inicio = primer_dia(hoy())
    for _ in range(meses - 1):
        inicio = mes_anterior(inicio)
    filas = dict(db.query(Pago.periodo, func.coalesce(func.sum(Pago.monto), 0))
                 .filter(Pago.periodo >= inicio)
                 .group_by(Pago.periodo).all())
    return [{"mes": m, "total": Decimal(filas.get(m, 0))}
            for m in meses_entre(inicio, hoy())]
