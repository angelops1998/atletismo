"""El parte semanal: lo que el atleta carga una vez por semana desde el celular."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_user
from ..models.parte import ParteSemanal
from ..services import bienestar
from ..tiempo import lunes_actual, lunes_de

router = APIRouter(prefix="/parte", tags=["parte"])

# Cuántas semanas para atrás se puede completar un parte. Una: el que se olvidó
# el domingo lo carga el lunes siguiente. Más que eso ya no es un recuerdo, es
# una invención, y datos inventados son peores que datos faltantes.
SEMANAS_EDITABLES = 1


def _semana_pedida(valor: str | None) -> date:
    """La semana que se está cargando, validada contra la ventana permitida."""
    actual = lunes_actual()
    if not valor:
        return actual
    try:
        pedida = lunes_de(date.fromisoformat(valor))
    except ValueError:
        return actual
    if pedida > actual:
        return actual
    if pedida < actual - timedelta(weeks=SEMANAS_EDITABLES):
        raise HTTPException(status_code=403,
                            detail="Esa semana ya está cerrada. Avisale al profesor.")
    return pedida


def _entero(valor: str, minimo: int, maximo: int) -> int | None:
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return None
    return n if minimo <= n <= maximo else None


def _decimal(valor: str, minimo: float, maximo: float) -> Decimal | None:
    """Los números con coma se escriben con coma en el celular; el navegador
    manda '7,5' y float() se rompe, así que se normaliza acá."""
    if valor is None or not str(valor).strip():
        return None
    try:
        d = Decimal(str(valor).strip().replace(",", "."))
    except InvalidOperation:
        return None
    return d if Decimal(str(minimo)) <= d <= Decimal(str(maximo)) else None


@router.get("", response_class=HTMLResponse)
async def formulario(request: Request, semana: str | None = None,
                     db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "atleta":
        raise HTTPException(status_code=403,
                            detail="El parte semanal lo carga cada atleta.")

    objetivo = _semana_pedida(semana)
    parte = bienestar.parte_de_semana(db, user.id, objetivo)
    anterior = lunes_actual() - timedelta(weeks=1)

    return templates.TemplateResponse(request, "atleta/parte.html", {
        "user": user,
        "semana": objetivo,
        "parte": parte,
        "items": bienestar.ITEMS,
        "etiquetas": bienestar.ETIQUETAS,
        "rpe_escala": bienestar.RPE_ESCALA,
        "rpe_franjas": bienestar.RPE_FRANJAS,
        "es_semana_actual": objetivo == lunes_actual(),
        "parte_pendiente": bienestar.parte_de_semana(db, user.id, lunes_actual()) is None,
        # Si todavía no cargó la semana pasada, se le ofrece completarla: es la
        # forma de no perder el dato del que se olvidó el domingo.
        "falta_anterior": (objetivo == lunes_actual()
                           and bienestar.parte_de_semana(db, user.id, anterior) is None),
        "semana_anterior": anterior,
    })


@router.post("", response_class=HTMLResponse)
async def guardar(
    request: Request,
    semana: str = Form(""),
    sueno_calidad: str = Form(""),
    dolor_muscular: str = Form(""),
    estres: str = Form(""),
    animo: str = Form(""),
    horas_sueno: str = Form(""),
    comidas_dia: str = Form(""),
    alimentacion_calidad: str = Form(""),
    hidratacion_litros: str = Form(""),
    come_antes_entrenar: str = Form(""),
    suplementos: str = Form(""),
    peso_kg: str = Form(""),
    sesiones: str = Form(""),
    minutos_totales: str = Form(""),
    rpe: str = Form(""),
    molestias: str = Form(""),
    molestia_zona: str = Form(""),
    molestia_dolor: str = Form(""),
    comentarios: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user.role != "atleta":
        raise HTTPException(status_code=403,
                            detail="El parte semanal lo carga cada atleta.")

    objetivo = _semana_pedida(semana)
    valores = {campo: _entero(request_valor, 1, 5) for campo, request_valor in (
        ("sueno_calidad", sueno_calidad), ("dolor_muscular", dolor_muscular),
        ("estres", estres), ("animo", animo),
    )}

    errores = []
    faltantes = [etiqueta for campo, etiqueta, _p in bienestar.ITEMS
                 if valores[campo] is None]
    if faltantes:
        errores.append("Faltan responder: " + ", ".join(faltantes).lower() + ".")

    # El RPE reemplazó al ítem de energía, así que es obligatorio como lo era
    # aquel: salvo que el atleta diga que no entrenó (0 sesiones), en cuyo caso no
    # hay esfuerzo que calificar.
    cantidad_sesiones = _entero(sesiones, 0, 21)
    esfuerzo = _entero(rpe, 1, 10)
    if esfuerzo is None and cantidad_sesiones != 0:
        errores.append("Indicá del 1 al 10 qué tan duro te resultó entrenar (RPE).")

    tiene_molestias = molestias == "si"
    dolor = _entero(molestia_dolor, 0, 10)
    if tiene_molestias and dolor is None:
        errores.append("Indicá del 0 al 10 cuánto te duele.")
    if tiene_molestias and not molestia_zona.strip():
        errores.append("Indicá en qué parte del cuerpo tenés la molestia.")

    if errores:
        return templates.TemplateResponse(request, "atleta/parte.html", {
            "user": user, "semana": objetivo,
            "parte": bienestar.parte_de_semana(db, user.id, objetivo),
            "items": bienestar.ITEMS, "etiquetas": bienestar.ETIQUETAS,
            "rpe_escala": bienestar.RPE_ESCALA,
            "rpe_franjas": bienestar.RPE_FRANJAS,
            "es_semana_actual": objetivo == lunes_actual(),
            "parte_pendiente": True,
            "errores": errores,
            "form": await request.form(),
        }, status_code=422)

    # Si ya existe el parte de esa semana se edita, no se duplica: es lo que hace
    # que "una vez por semana" se cumpla aunque el atleta entre tres veces.
    parte = bienestar.parte_de_semana(db, user.id, objetivo)
    if parte is None:
        parte = ParteSemanal(atleta_id=user.id, semana=objetivo)
        db.add(parte)

    for campo, valor in valores.items():
        setattr(parte, campo, valor)
    parte.horas_sueno = _decimal(horas_sueno, 0, 24)
    parte.comidas_dia = _entero(comidas_dia, 0, 10)
    parte.alimentacion_calidad = _entero(alimentacion_calidad, 1, 5)
    parte.hidratacion_litros = _decimal(hidratacion_litros, 0, 15)
    parte.come_antes_entrenar = (come_antes_entrenar == "si") if come_antes_entrenar else None
    parte.suplementos = suplementos.strip()[:200] or None
    parte.peso_kg = _decimal(peso_kg, 20, 250)
    parte.sesiones = cantidad_sesiones
    parte.minutos_totales = _entero(minutos_totales, 0, 3000)
    parte.rpe = esfuerzo
    parte.molestias = tiene_molestias
    parte.molestia_zona = molestia_zona.strip()[:80] if tiene_molestias else None
    parte.molestia_dolor = dolor if tiene_molestias else None
    parte.comentarios = comentarios.strip() or None

    db.commit()
    return RedirectResponse(url="/inicio?parte=1", status_code=302)
