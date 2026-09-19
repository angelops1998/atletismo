"""Las estadísticas del club: tendencias del grupo y de cada atleta."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_profesor
from ..models.user import User
from ..services import bienestar, alertas, grafico
from ..tiempo import lunes_actual

router = APIRouter(prefix="/estadisticas", tags=["estadisticas"])

RANGOS = {"8": 8, "12": 12, "26": 26, "52": 52}
POR_DEFECTO = 12


def _interpretar(coef: float | None, positivo: str, negativo: str) -> str | None:
    """Traduce un coeficiente de correlación a una frase.

    Un "r = 0.42" no le sirve a nadie en la pista. Y por debajo de 0.3 se dice
    explícitamente que no se ve relación, en vez de dejar que el número sugiera
    una que no está.
    """
    if coef is None:
        return None
    fuerza = abs(coef)
    if fuerza < 0.3:
        return "Por ahora no se ve una relación clara. Hacen falta más semanas de datos."
    intensidad = "marcada" if fuerza >= 0.6 else "moderada"
    return f"Se ve una relación {intensidad}: {positivo if coef > 0 else negativo}"


@router.get("", response_class=HTMLResponse)
async def estadisticas(request: Request, db: Session = Depends(get_db)):
    user = get_current_profesor(request, db)
    rango = RANGOS.get(request.query_params.get("semanas", ""), POR_DEFECTO)

    serie = bienestar.serie_grupo(db, rango)
    atletas = (db.query(User)
               .filter(User.role == "atleta", User.is_active.is_(True))
               .order_by(User.full_name, User.username).all())

    # Una fila por atleta con su promedio, su última semana y hacia dónde va.
    # La tendencia se calcula contra su propio promedio previo, no contra el
    # grupo: lo que importa es si ESTE atleta viene mejorando o cayendo.
    series = bienestar.series_de(db, [a.id for a in atletas], rango)
    filas = []
    for a in atletas:
        individual = series[a.id]
        cargados = [f["bienestar"] for f in individual if f["bienestar"] is not None]
        ultimo = individual[-1]["bienestar"] if individual else None
        previos = [f["bienestar"] for f in individual[:-1] if f["bienestar"] is not None]
        base = sum(previos) / len(previos) if previos else None
        if ultimo is None or base is None:
            tendencia = None
        elif ultimo > base * 1.05:
            tendencia = "sube"
        elif ultimo < base * 0.95:
            tendencia = "baja"
        else:
            tendencia = "igual"
        filas.append({
            "atleta": a,
            "promedio": round(sum(cargados) / len(cargados), 1) if cargados else None,
            "ultimo": ultimo,
            "tendencia": tendencia,
            "cargados": len(cargados),
            "posibles": rango,
            "sueno": bienestar.promedio([f["sueno"] for f in individual]),
            "carga": bienestar.promedio([f["carga"] for f in individual]),
            "acwr": alertas.acwr(individual),
            "chispa": grafico.linea([f["bienestar"] for f in individual],
                                    minimo=bienestar.MINIMO, maximo=bienestar.MAXIMO, ancho=120, alto=34),
        })
    # Primero los que peor vienen: es a quienes hay que mirar.
    filas.sort(key=lambda f: (f["promedio"] is None, f["promedio"] or 0))

    cruce = bienestar.cruce_con_marcas(db, max(rango, 26))
    r_bienestar = grafico.correlacion(cruce["bienestar"])
    r_sueno = grafico.correlacion(cruce["sueno"])

    return templates.TemplateResponse(request, "panel/estadisticas.html", {
        "user": user,
        "rango": rango,
        "rangos": sorted(RANGOS.values()),
        "serie": serie,
        "items": bienestar.ITEMS,
        "maximo": bienestar.MAXIMO,
        "filas": filas,
        # Escala automática, como en el panel: es el promedio del grupo.
        "grafico_bienestar": grafico.linea([f["bienestar"] for f in serie]),
        "grafico_sueno": grafico.linea([f["sueno"] for f in serie], alto=140),
        "grafico_carga": grafico.barras([f["carga"] for f in serie], alto=140),
        "grafico_participacion": grafico.barras([f["pct_cargados"] for f in serie],
                                                maximo=100, alto=120),
        "grafico_molestias": grafico.barras([f["con_molestias"] for f in serie], alto=110),
        "cruce": cruce,
        "dispersion_bienestar": grafico.dispersion(cruce["bienestar"], alto=200),
        "dispersion_sueno": grafico.dispersion(cruce["sueno"], alto=200),
        "r_bienestar": r_bienestar,
        "r_sueno": r_sueno,
        "texto_bienestar": _interpretar(
            r_bienestar,
            "las semanas de mejor bienestar son las de mejores marcas.",
            "las semanas de mejor bienestar coinciden con marcas más flojas, que es raro: "
            "conviene revisar cómo se están cargando los datos."),
        "texto_sueno": _interpretar(
            r_sueno,
            "cuanto más duermen, mejor rinden.",
            "las semanas de más horas de sueño coinciden con marcas más flojas; "
            "puede ser que duerman más justo en las semanas de más carga."),
        "semana_actual": lunes_actual(),
    })
