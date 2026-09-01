"""Cobranza: quién debe, quién pagó y cuánto entró en el mes."""
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_profesor
from ..models.user import User
from ..models.pago import Pago, METODOS
from ..services import cobranza, grafico
from ..tiempo import hoy, fecha_razonable
from ..urls import ruta_interna

router = APIRouter(prefix="/pagos", tags=["pagos"])

# Tope de la columna monto (Numeric(12,2)): más que eso lo rechaza Postgres con
# "numeric field overflow", que sin capturar sale como un 500.
MONTO_MAXIMO = Decimal("9999999999.99")


def _fecha(valor: str) -> date | None:
    """La fecha del formulario, o None si está vacía o no es creíble (ver
    tiempo.fecha_razonable): un período con un año de cuatro cifras mal tipeadas
    deja al atleta debiendo meses que no existen."""
    try:
        d = date.fromisoformat(valor.strip()) if valor and valor.strip() else None
    except ValueError:
        return None
    return d if fecha_razonable(d) else None


@router.get("", response_class=HTMLResponse)
async def pagos(request: Request, db: Session = Depends(get_db)):
    user = get_current_profesor(request, db)
    resumen = cobranza.resumen_club(db)
    historial = cobranza.historial_mensual(db)

    ultimos = (db.query(Pago).order_by(Pago.creado.desc()).limit(20).all())
    nombres = {u.id: u for u in db.query(User).filter(User.role == "atleta").all()}

    # Para el formulario: los atletas activos con cuota, con lo que deben, así el
    # profesor elige a quién le está cobrando y el mes se completa solo.
    activos = (db.query(User).filter(User.role == "atleta", User.is_active.is_(True))
               .order_by(User.full_name, User.username).all())
    estados = cobranza.estados_de(db, activos)
    pendientes = []
    for a in activos:
        estado = estados[a.id]
        pendientes.append({"atleta": a, **estado,
                           "proximo": estado["meses"][0] if estado["meses"] else None})

    return templates.TemplateResponse(request, "panel/pagos.html", {
        "user": user,
        "resumen": resumen,
        "historial": historial,
        "grafico_ingresos": grafico.barras([float(h["total"]) for h in historial], alto=140),
        "ultimos": ultimos,
        "nombres": nombres,
        "pendientes": pendientes,
        "metodos": METODOS,
        "hoy": hoy(),
        "error": request.query_params.get("error"),
    })


@router.post("", response_class=HTMLResponse)
async def registrar(
    request: Request,
    atleta_id: int = Form(...),
    periodo: str = Form(""),
    fecha_pago: str = Form(""),
    monto: str = Form(""),
    metodo: str = Form("efectivo"),
    nota: str = Form(""),
    volver: str = Form(""),
    db: Session = Depends(get_db),
):
    get_current_profesor(request, db)
    atleta = db.query(User).filter(User.id == atleta_id, User.role == "atleta").first()
    if not atleta:
        raise HTTPException(status_code=404, detail="No existe ese atleta.")

    mes = _fecha(periodo)
    if not mes:
        return RedirectResponse(url="/pagos?error=periodo", status_code=302)
    mes = cobranza.primer_dia(mes)

    importe = cobranza.parsear_monto(monto)
    if importe is not None and importe > MONTO_MAXIMO:
        return RedirectResponse(url="/pagos?error=monto", status_code=302)
    if importe is None or importe <= 0:
        # Si no se escribe monto se toma la cuota del atleta: es lo normal, y
        # tener que tipearla en cada cobro es la mitad del trabajo de la pantalla.
        importe = Decimal(atleta.cuota_mensual or 0)
    if importe <= 0:
        return RedirectResponse(url="/pagos?error=monto", status_code=302)

    pago = Pago(
        atleta_id=atleta.id,
        periodo=mes,
        fecha_pago=_fecha(fecha_pago) or hoy(),
        monto=importe,
        metodo=metodo if metodo in METODOS else "efectivo",
        nota=nota.strip()[:200] or None,
    )
    try:
        db.add(pago)
        db.commit()
    except IntegrityError:
        # La restricción (atleta, período) evita cobrar dos veces el mismo mes,
        # que es el error clásico cuando el profesor carga los pagos de memoria.
        db.rollback()
        return RedirectResponse(url="/pagos?error=duplicado", status_code=302)

    destino = ruta_interna(volver, "/pagos")
    return RedirectResponse(url=destino, status_code=302)


@router.post("/{pago_id}/borrar", response_class=HTMLResponse)
async def borrar(pago_id: int, request: Request, volver: str = Form(""),
                 db: Session = Depends(get_db)):
    """Anula un pago mal cargado. Es la única forma de corregir un mes cobrado
    por error, porque la restricción de unicidad no deja pisarlo."""
    get_current_profesor(request, db)
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="No existe ese pago.")
    db.delete(pago)
    db.commit()
    destino = ruta_interna(volver, "/pagos")
    return RedirectResponse(url=destino, status_code=302)
