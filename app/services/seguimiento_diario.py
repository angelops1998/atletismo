"""Consultas y agregaciones para las pantallas docentes del parte diario."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from statistics import mean

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..models.parte_diaria import ParteDiaria
from ..models.sesion_entrenamiento import SesionEntrenamiento
from ..models.user import User

_CARGA = (
    selectinload(ParteDiaria.entrenamiento_principal),
    selectinload(ParteDiaria.sesiones),
)
INDICADORES = (
    ("sueno_calidad", "Calidad del sueño"),
    ("fatiga", "Fatiga"),
    ("dolor_muscular", "Dolor muscular"),
    ("estres", "Estrés"),
    ("animo", "Ánimo"),
)


def parsear_fecha_filtro(valor: str | None, nombre: str) -> date | None:
    if not valor:
        return None
    try:
        parsed = date.fromisoformat(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"La fecha «{nombre}» no es válida.") from exc
    if parsed.isoformat() != valor:
        raise ValueError(f"La fecha «{nombre}» debe usar AAAA-MM-DD.")
    return parsed


def reportes_de_fecha(db: Session, dia: date, atleta_ids: list[int] | None = None) -> list[ParteDiaria]:
    if atleta_ids is not None and not atleta_ids:
        return []
    query = (db.query(ParteDiaria)
             .join(User, User.id == ParteDiaria.atleta_id)
             .options(*_CARGA)
             .filter(ParteDiaria.fecha == dia))
    if atleta_ids is not None:
        query = query.filter(ParteDiaria.atleta_id.in_(atleta_ids))
    return query.order_by(ParteDiaria.atleta_id).all()


def ultimas_fechas(db: Session, atleta_ids: list[int]) -> dict[int, date]:
    if not atleta_ids:
        return {}
    return dict(db.query(ParteDiaria.atleta_id, func.max(ParteDiaria.fecha))
                .filter(ParteDiaria.atleta_id.in_(atleta_ids))
                .group_by(ParteDiaria.atleta_id).all())


def historial_atleta(
    db: Session, atleta_id: int, *, desde: date | None = None,
    hasta: date | None = None, pagina: int = 1, por_pagina: int = 20,
) -> tuple[list[ParteDiaria], int]:
    query = db.query(ParteDiaria).options(*_CARGA).filter(ParteDiaria.atleta_id == atleta_id)
    if desde:
        query = query.filter(ParteDiaria.fecha >= desde)
    if hasta:
        query = query.filter(ParteDiaria.fecha <= hasta)
    total = query.count()
    rows = (query.order_by(ParteDiaria.fecha.desc(), ParteDiaria.id.desc())
            .offset((pagina - 1) * por_pagina).limit(por_pagina).all())
    return rows, total


def reportes_del_periodo(
    db: Session, desde: date, hasta: date, atleta_ids: list[int] | None = None,
) -> list[ParteDiaria]:
    if atleta_ids is not None and not atleta_ids:
        return []
    query = (db.query(ParteDiaria)
             .join(User, User.id == ParteDiaria.atleta_id)
             .options(*_CARGA)
             .filter(ParteDiaria.fecha >= desde, ParteDiaria.fecha <= hasta,
                     User.role == "atleta", User.is_active.is_(True)))
    if atleta_ids is not None:
        query = query.filter(ParteDiaria.atleta_id.in_(atleta_ids))
    return query.order_by(ParteDiaria.fecha, ParteDiaria.atleta_id).all()


def _promedio(reportes: list[ParteDiaria], campo: str) -> float | None:
    valores = [float(getattr(r, campo)) for r in reportes if getattr(r, campo) is not None]
    return round(mean(valores), 1) if valores else None


def resumen_reportes(reportes: list[ParteDiaria], atletas: list[User], desde: date, hasta: date) -> dict:
    """Agrega solo observaciones existentes; no completa reportes faltantes con ceros."""
    por_atleta: dict[int, list[ParteDiaria]] = defaultdict(list)
    por_dia: dict[date, list[ParteDiaria]] = defaultdict(list)
    sesiones_por_atleta: dict[int, list[SesionEntrenamiento]] = defaultdict(list)
    for reporte in reportes:
        por_atleta[reporte.atleta_id].append(reporte)
        por_dia[reporte.fecha].append(reporte)

    zonas: Counter[str] = Counter()
    tipos: Counter[str] = Counter()
    sesiones: list[SesionEntrenamiento] = []
    for reporte in reportes:
        if reporte.hay_molestia:
            zonas.update(reporte.molestia_zona or [])
        if reporte.entreno_hoy and reporte.entrenamiento_principal:
            tipos[reporte.entrenamiento_principal.estructura_tipo] += 1
        sesiones.extend(reporte.sesiones or [])
        sesiones_por_atleta[reporte.atleta_id].extend(reporte.sesiones or [])

    dias = (hasta - desde).days + 1
    posibles = len(atletas) * dias
    promedios = {campo: _promedio(reportes, campo) for campo, _ in INDICADORES}
    promedios["horas_sueno"] = _promedio(reportes, "horas_sueno")
    distribuciones = {}
    for campo, _ in INDICADORES:
        conteo = Counter(getattr(r, campo) for r in reportes if getattr(r, campo) is not None)
        distribuciones[campo] = {valor: conteo.get(valor, 0) for valor in range(1, 11)}
    resumen_atletas = []
    for atleta in atletas:
        rows = por_atleta.get(atleta.id, [])
        sesiones_atleta = sesiones_por_atleta.get(atleta.id, [])
        resumen_atletas.append({
            "atleta": atleta,
            "reportes": len(rows),
            "promedios": {campo: _promedio(rows, campo) for campo, _ in INDICADORES},
            "horas_sueno": _promedio(rows, "horas_sueno"),
            "entreno": sum(1 for r in rows if r.entreno_hoy),
            "no_entreno": sum(1 for r in rows if not r.entreno_hoy),
            "molestias": sum(1 for r in rows if r.hay_molestia),
            "sintomas": sum(1 for r in rows if r.sintomas_enfermedad),
            "sesiones": len(sesiones_atleta),
            "minutos_sesion": sum(s.duracion_min for s in sesiones_atleta),
            "rpe_sesion": round(mean(s.rpe for s in sesiones_atleta), 1) if sesiones_atleta else None,
            "carga_sesion": sum(s.carga_sesion for s in sesiones_atleta),
        })
    resumen_atletas.sort(key=lambda fila: (fila["reportes"] == 0, fila["reportes"], fila["atleta"].nombre.lower()))

    tendencia = []
    for dia, rows in sorted(por_dia.items()):
        tendencia.append({
            "fecha": dia,
            "reportes": len(rows),
            **{campo: _promedio(rows, campo) for campo, _ in INDICADORES},
            "horas_sueno": _promedio(rows, "horas_sueno"),
            "molestias": sum(1 for r in rows if r.hay_molestia),
            "sintomas": sum(1 for r in rows if r.sintomas_enfermedad),
            "entreno": sum(1 for r in rows if r.entreno_hoy),
            "no_entreno": sum(1 for r in rows if not r.entreno_hoy),
        })

    return {
        "total_reportes": len(reportes),
        "atletas_con_reporte": len(por_atleta),
        "atletas_sin_reporte": max(0, len(atletas) - len(por_atleta)),
        "dias_periodo": dias,
        "atletas_activos": len(atletas),
        "atletas_dia_posibles": posibles,
        "cobertura_pct": round(100 * len(reportes) / posibles, 1) if posibles else None,
        "promedios": promedios,
        "distribuciones": distribuciones,
        "molestias": sum(1 for r in reportes if r.hay_molestia),
        "sintomas": sum(1 for r in reportes if r.sintomas_enfermedad),
        "entrenaron": sum(1 for r in reportes if r.entreno_hoy),
        "no_entrenaron": sum(1 for r in reportes if not r.entreno_hoy),
        "zonas": zonas.most_common(),
        "tipos": sorted(tipos.items()),
        "sesiones": {
            "cantidad": len(sesiones),
            "minutos": sum(s.duracion_min for s in sesiones),
            "duracion_promedio": round(mean(s.duracion_min for s in sesiones), 1) if sesiones else None,
            "rpe_promedio": round(mean(s.rpe for s in sesiones), 1) if sesiones else None,
            "carga": sum(s.carga_sesion for s in sesiones),
            "carga_promedio": round(mean(s.carga_sesion for s in sesiones), 1) if sesiones else None,
        },
        "tendencia": tendencia,
        "filas_atletas": resumen_atletas,
    }


def hora_mmss(segundos: int | None) -> str:
    if segundos is None:
        return "—"
    minutos, resto = divmod(int(segundos), 60)
    return f"{minutos:02d}:{resto:02d}"
