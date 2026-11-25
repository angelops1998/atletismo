"""Estadísticas actuales agregadas desde los partes diarios."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_profesor
from ..models.user import User
from ..services import grafico, seguimiento_diario
from ..tiempo import hoy

router = APIRouter(prefix="/estadisticas", tags=["estadisticas"])


@router.get("", response_class=HTMLResponse)
async def estadisticas(request: Request, db: Session = Depends(get_db)):
    user = get_current_profesor(request, db)
    hoy_local = hoy()
    try:
        desde = seguimiento_diario.parsear_fecha_filtro(
            request.query_params.get("desde"), "desde") or hoy_local - timedelta(days=29)
        hasta = seguimiento_diario.parsear_fecha_filtro(
            request.query_params.get("hasta"), "hasta") or hoy_local
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if desde > hasta:
        raise HTTPException(status_code=422, detail="La fecha inicial no puede ser posterior a la final.")

    atletas = (db.query(User)
               .filter(User.role == "atleta", User.is_active.is_(True))
               .order_by(User.full_name, User.username).all())
    reportes = seguimiento_diario.reportes_del_periodo(db, desde, hasta, [a.id for a in atletas])
    resumen = seguimiento_diario.resumen_reportes(reportes, atletas, desde, hasta)

    campos_grafico = {
        "sueno_calidad": "Calidad del sueño",
        "fatiga": "Fatiga",
        "dolor_muscular": "Dolor muscular",
        "estres": "Estrés",
        "animo": "Ánimo",
        "horas_sueno": "Horas de sueño",
        **{campo: etiqueta + " · McLean" for campo, etiqueta in seguimiento_diario.INDICADORES_MCLEAN},
        "mclean_suma": "Suma · McLean", "mclean_promedio": "Promedio · McLean",
    }
    tendencias = resumen["tendencia"]
    graficos = {
        campo: grafico.linea([dia[campo] for dia in tendencias], minimo=0 if campo == "horas_sueno" else (5 if campo == "mclean_suma" else 1),
                             maximo=24 if campo == "horas_sueno" else (25 if campo == "mclean_suma" else (5 if campo.startswith("mclean_") else 10)), ancho=500, alto=120)
        for campo in campos_grafico
    }
    return templates.TemplateResponse(request, "panel/estadisticas.html", {
        "user": user, "desde": desde, "hasta": hasta,
        "resumen": resumen, "indicadores": seguimiento_diario.INDICADORES,
        "indicadores_mclean": seguimiento_diario.INDICADORES_MCLEAN,
        "campos_grafico": campos_grafico, "graficos": graficos,
        "tendencias": tendencias,
    })
