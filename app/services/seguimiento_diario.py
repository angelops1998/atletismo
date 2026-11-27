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


INDICADORES_MCLEAN = (
    ("mclean_sueno", "Calidad del sueño"), ("mclean_fatiga", "Fatiga"),
    ("mclean_dolor_muscular", "Dolor muscular"), ("mclean_estres", "Estrés"),
    ("mclean_animo", "Ánimo"),
)
TIPOS_DURACION = ("no_especificada", "trabajo_principal")


def resumen_sesiones(sesiones):
    """Agrega cada semántica por separado, usando siempre la carga guardada."""
    grupos = {}
    for tipo in TIPOS_DURACION:
        items = [s for s in sesiones if s.tipo_duracion == tipo]
        n = len(items)
        grupos[tipo] = {
            "cantidad": n, "minutos": sum(s.duracion_min for s in items),
            "duracion_promedio": round(mean(s.duracion_min for s in items), 1) if n else None,
            "rpe_promedio": round(mean(s.rpe for s in items), 1) if n else None,
            "carga": sum(s.carga_sesion for s in items),
            "carga_promedio": round(mean(s.carga_sesion for s in items), 1) if n else None,
        }
    return grupos


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


def resumen_diario_atleta(
    db: Session, atleta_id: int, *, desde: date | None = None,
    hasta: date | None = None,
) -> dict:
    """Resumen y serie cronológica desde partes diarios del rango elegido.

    La consulta principal devuelve solo columnas escalares. Las sesiones se
    agregan aparte por fecha, evitando cargar el historial ORM completo para
    calcular tarjetas y gráficas. Cada sesión cuenta una vez; minutos y carga
    son sumas de los campos ya guardados en ``SesionEntrenamiento``.
    """
    campos = [campo for campo, _ in INDICADORES] + [campo for campo, _ in INDICADORES_MCLEAN] + ["mclean_suma", "mclean_promedio", "horas_sueno"]
    query = db.query(
        ParteDiaria.fecha.label("fecha"),
        ParteDiaria.version_cuestionario.label("version_cuestionario"),
        *[getattr(ParteDiaria, campo).label(campo) for campo, _ in INDICADORES_MCLEAN],
        ParteDiaria.sueno_calidad.label("sueno_calidad"),
        ParteDiaria.fatiga.label("fatiga"),
        ParteDiaria.dolor_muscular.label("dolor_muscular"),
        ParteDiaria.estres.label("estres"),
        ParteDiaria.animo.label("animo"),
        ParteDiaria.horas_sueno.label("horas_sueno"),
        ParteDiaria.entreno_hoy.label("entreno_hoy"),
        ParteDiaria.hay_molestia.label("hay_molestia"),
        ParteDiaria.sintomas_enfermedad.label("sintomas_enfermedad"),
    ).filter(ParteDiaria.atleta_id == atleta_id)
    if desde:
        query = query.filter(ParteDiaria.fecha >= desde)
    if hasta:
        query = query.filter(ParteDiaria.fecha <= hasta)
    observaciones = [dict(row._mapping) for row in query.order_by(ParteDiaria.fecha).all()]
    for reporte in observaciones:
        valores = [reporte[campo] for campo, _ in INDICADORES_MCLEAN]
        suma = sum(valores) if reporte["version_cuestionario"] == "mclean_1_5" and all(v is not None for v in valores) else None
        reporte["mclean_suma"] = suma
        reporte["mclean_promedio"] = suma / 5 if suma is not None else None

    sesiones_query = (db.query(
        ParteDiaria.fecha.label("fecha"),
        ParteDiaria.entreno_hoy.label("entreno_hoy"),
        SesionEntrenamiento.tipo_duracion.label("tipo_duracion"),
        func.count(SesionEntrenamiento.id).label("cantidad"),
        func.sum(SesionEntrenamiento.duracion_min).label("minutos"),
        func.sum(SesionEntrenamiento.rpe).label("suma_rpe"),
        func.sum(SesionEntrenamiento.carga_sesion).label("carga"),
    ).join(SesionEntrenamiento, SesionEntrenamiento.parte_diaria_id == ParteDiaria.id)
        .filter(ParteDiaria.atleta_id == atleta_id))
    if desde:
        sesiones_query = sesiones_query.filter(ParteDiaria.fecha >= desde)
    if hasta:
        sesiones_query = sesiones_query.filter(ParteDiaria.fecha <= hasta)
    agrupadas = sesiones_query.group_by(ParteDiaria.fecha, ParteDiaria.entreno_hoy, SesionEntrenamiento.tipo_duracion).all()
    sesiones_por_fecha = defaultdict(dict)
    for row in agrupadas:
        sesiones_por_fecha[row.fecha][row.tipo_duracion] = {
            "cantidad": int(row.cantidad or 0), "minutos": int(row.minutos or 0),
            "suma_rpe": int(row.suma_rpe or 0), "carga": int(row.carga or 0),
        }
    for reporte in observaciones:
        reporte["sesiones"] = sesiones_por_fecha.get(reporte["fecha"], {})

    def promedio(campo: str) -> float | None:
        valores = [float(reporte[campo]) for reporte in observaciones if reporte[campo] is not None]
        return round(mean(valores), 1) if valores else None

    def resumen_por_estado(entreno_hoy):
        por_tipo = {}
        for tipo in TIPOS_DURACION:
            rows = [r for r in agrupadas if r.tipo_duracion == tipo and r.entreno_hoy == entreno_hoy]
            n = sum(int(r.cantidad or 0) for r in rows)
            por_tipo[tipo] = {
                "cantidad": n, "minutos": sum(int(r.minutos or 0) for r in rows),
                "rpe_promedio": round(sum(int(r.suma_rpe or 0) for r in rows) / n, 1) if n else None,
                "carga": sum(int(r.carga or 0) for r in rows),
            }
        return {"cantidad": sum(v["cantidad"] for v in por_tipo.values()), "por_tipo": por_tipo}
    fechas = [r["fecha"] for r in observaciones]
    series = {}
    for campo in campos:
        valores = []
        fecha_anterior = None
        for reporte in observaciones:
            fecha = reporte["fecha"]
            if fecha_anterior is not None and (fecha - fecha_anterior).days > 1:
                valores.append(None)
            valor = reporte[campo]
            valores.append(float(valor) if valor is not None else None)
            fecha_anterior = fecha
        series[campo] = valores

    return {
        "reportes": len(observaciones),
        "primera_fecha": fechas[0] if fechas else None,
        "ultima_fecha": fechas[-1] if fechas else None,
        "promedios": {campo: promedio(campo) for campo in campos},
        "molestias": sum(1 for r in observaciones if r["hay_molestia"]),
        "sintomas": sum(1 for r in observaciones if r["sintomas_enfermedad"]),
        "entrenaron": sum(1 for r in observaciones if r["entreno_hoy"]),
        "no_entrenaron": sum(1 for r in observaciones if not r["entreno_hoy"]),
        "sesiones": resumen_por_estado(True),
        "sesiones_descanso": resumen_por_estado(False),
        "observaciones": observaciones,
        "series": series,
    }


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


def _promedios_totales_mclean(reportes: list[ParteDiaria]) -> tuple[float | None, float | None]:
    totales = [sum(getattr(r, campo) for campo, _ in INDICADORES_MCLEAN)
               for r in reportes if r.version_cuestionario == "mclean_1_5"]
    return (round(mean(totales), 1), round(mean(totales) / 5, 1)) if totales else (None, None)


def resumen_reportes(reportes: list[ParteDiaria], atletas: list[User], desde: date, hasta: date) -> dict:
    """Agrega solo observaciones existentes; no completa reportes faltantes con ceros."""
    por_atleta: dict[int, list[ParteDiaria]] = defaultdict(list)
    por_dia: dict[date, list[ParteDiaria]] = defaultdict(list)
    sesiones_por_atleta: dict[int, list[SesionEntrenamiento]] = defaultdict(list)
    sesiones_descanso_por_atleta: dict[int, list[SesionEntrenamiento]] = defaultdict(list)
    for reporte in reportes:
        por_atleta[reporte.atleta_id].append(reporte)
        por_dia[reporte.fecha].append(reporte)

    zonas: Counter[str] = Counter()
    tipos: Counter[str] = Counter()
    sesiones: list[SesionEntrenamiento] = []
    sesiones_descanso: list[SesionEntrenamiento] = []
    for reporte in reportes:
        if reporte.hay_molestia:
            zonas.update(reporte.molestia_zona or [])
        if reporte.entreno_hoy and reporte.entrenamiento_principal:
            tipos[reporte.entrenamiento_principal.estructura_tipo] += 1
        if reporte.entreno_hoy:
            sesiones.extend(reporte.sesiones or [])
            sesiones_por_atleta[reporte.atleta_id].extend(reporte.sesiones or [])
        else:
            sesiones_descanso.extend(reporte.sesiones or [])
            sesiones_descanso_por_atleta[reporte.atleta_id].extend(reporte.sesiones or [])

    dias = (hasta - desde).days + 1
    posibles = len(atletas) * dias
    promedios = {campo: _promedio(reportes, campo) for campo, _ in INDICADORES}
    promedios["horas_sueno"] = _promedio(reportes, "horas_sueno")
    promedios_mclean = {campo: _promedio(reportes, campo) for campo, _ in INDICADORES_MCLEAN}
    mclean_reportes = [r for r in reportes if r.version_cuestionario == "mclean_1_5"]
    promedios_mclean["suma"], promedios_mclean["promedio"] = _promedios_totales_mclean(reportes)
    distribuciones_mclean = {campo: {v: sum(1 for r in mclean_reportes if getattr(r, campo) == v)
                                    for v in range(1, 6)} for campo, _ in INDICADORES_MCLEAN}
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
            "promedios_mclean": {campo: _promedio(rows, campo) for campo, _ in INDICADORES_MCLEAN},
            "mclean_suma": _promedios_totales_mclean(rows)[0],
            "mclean_promedio": _promedios_totales_mclean(rows)[1],
            "sesiones_por_tipo": resumen_sesiones(sesiones_atleta),
            "horas_sueno": _promedio(rows, "horas_sueno"),
            "entreno": sum(1 for r in rows if r.entreno_hoy),
            "no_entreno": sum(1 for r in rows if not r.entreno_hoy),
            "molestias": sum(1 for r in rows if r.hay_molestia),
            "sintomas": sum(1 for r in rows if r.sintomas_enfermedad),
            "sesiones": len(sesiones_atleta),
            "sesiones_descanso": len(sesiones_descanso_por_atleta.get(atleta.id, [])),
        })
    resumen_atletas.sort(key=lambda fila: (fila["reportes"] == 0, fila["reportes"], fila["atleta"].nombre.lower()))

    tendencia = []
    for dia, rows in sorted(por_dia.items()):
        tendencia.append({
            "fecha": dia,
            "reportes": len(rows),
            **{campo: _promedio(rows, campo) for campo, _ in INDICADORES},
            **{campo: _promedio(rows, campo) for campo, _ in INDICADORES_MCLEAN},
            "mclean_suma": _promedios_totales_mclean(rows)[0],
            "mclean_promedio": _promedios_totales_mclean(rows)[1],
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
        "promedios_mclean": promedios_mclean,
        "distribuciones_mclean": distribuciones_mclean,
        "distribuciones": distribuciones,
        "molestias": sum(1 for r in reportes if r.hay_molestia),
        "sintomas": sum(1 for r in reportes if r.sintomas_enfermedad),
        "entrenaron": sum(1 for r in reportes if r.entreno_hoy),
        "no_entrenaron": sum(1 for r in reportes if not r.entreno_hoy),
        "zonas": zonas.most_common(),
        "tipos": sorted(tipos.items()),
        "tipos_diarios": Counter(r.tipo_entrenamiento_diario for r in reportes if r.tipo_entrenamiento_diario),
        "sesiones": {"cantidad": len(sesiones), "por_tipo": resumen_sesiones(sesiones),
                     "tipos_realizados": Counter(s.tipo_entrenamiento for s in sesiones)},
        "sesiones_descanso": {"cantidad": len(sesiones_descanso), "por_tipo": resumen_sesiones(sesiones_descanso)},
        "tendencia": tendencia,
        "filas_atletas": resumen_atletas,
    }


def hora_mmss(segundos: int | None) -> str:
    if segundos is None:
        return "—"
    minutos, resto = divmod(int(segundos), 60)
    return f"{minutos:02d}:{resto:02d}"
