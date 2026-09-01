"""Marcas: los resultados de cada atleta en cada prueba."""
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_profesor
from ..models.user import User
from ..models.marca import Marca
from ..services import pruebas
from ..tiempo import hoy
from ..urls import ruta_interna

router = APIRouter(prefix="/marcas", tags=["marcas"])

# Topes de lo que se puede cargar. El de la marca es el de la columna
# (Numeric(8,3)): pasarse hace que Postgres corte con "numeric field overflow" y,
# sin nadie que lo atrape, eso termina en un 500 pelado en la cara del profesor.
# El del viento es físico y bastante más chico que la columna: arriba de 20 m/s no
# se corre, así que un 150 no es un dato, es un dedazo, y guardarlo callado
# arruina la lectura de la marca (una con más de +2.0 no es homologable).
VALOR_MAXIMO = Decimal("99999.999")
VIENTO_MAXIMO = Decimal("20")


def _valor(texto: str, clave: str) -> Decimal | None:
    """Acepta '12.34', '12,34' y también '4:32.10' para las pruebas largas.

    Nadie anota un 1500 en segundos: el profesor lo escribe en minutos como lo
    ve en el cronómetro, y se guarda en segundos porque es lo único que se puede
    promediar y graficar.
    """
    texto = (texto or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        if ":" in texto:
            minutos, segundos = texto.split(":", 1)
            return Decimal(minutos) * 60 + Decimal(segundos)
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return None


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db)):
    user = get_current_profesor(request, db)
    prueba = request.query_params.get("prueba") or ""

    consulta = (db.query(Marca, User).join(User, User.id == Marca.atleta_id))
    if pruebas.existe(prueba):
        consulta = consulta.filter(Marca.prueba == prueba)
    filas = consulta.order_by(Marca.fecha.desc(), Marca.id.desc()).limit(100).all()

    # Con una prueba elegida se arma el ranking del club: es la vista que el
    # profesor usa para armar la posta o decidir quién va a la competencia.
    #
    # Va con su propia consulta y SIN límite, a propósito. Antes se armaba sobre
    # `filas`, que trae solo las 100 más recientes para la tabla de arriba: pasadas
    # las 100 marcas de una prueba, el atleta cuyo mejor registro era de temporadas
    # anteriores desaparecía del ranking, y al que quedaba se le mostraba como
    # "mejor" lo mejor de lo reciente. Justo al revés de para qué sirve la pantalla.
    ranking = []
    if pruebas.existe(prueba):
        historial = (db.query(Marca, User)
                     .join(User, User.id == Marca.atleta_id)
                     .filter(Marca.prueba == prueba).all())
        mejores: dict[int, Marca] = {}
        nombres: dict[int, User] = {}
        for marca, atleta in historial:
            nombres[atleta.id] = atleta
            actual = mejores.get(atleta.id)
            if actual is None or pruebas.es_mejora(prueba, marca.valor, actual.valor):
                mejores[atleta.id] = marca
        ranking = sorted(
            ({"atleta": nombres[aid], "marca": m} for aid, m in mejores.items()),
            key=lambda r: float(r["marca"].valor),
            reverse=not pruebas.menor_es_mejor(prueba))

    return templates.TemplateResponse(request, "panel/marcas.html", {
        "user": user,
        "filas": filas,
        "ranking": ranking,
        "prueba": prueba,
        "pruebas": pruebas,
        "grupos": pruebas.grupos(),
        "atletas": db.query(User).filter(User.role == "atleta", User.is_active.is_(True))
                     .order_by(User.full_name, User.username).all(),
        "hoy": hoy(),
        "error": request.query_params.get("error"),
    })


@router.post("", response_class=HTMLResponse)
async def registrar(
    request: Request,
    atleta_id: int = Form(...),
    prueba: str = Form(""),
    fecha: str = Form(""),
    valor: str = Form(""),
    viento: str = Form(""),
    es_competencia: str = Form(""),
    competencia: str = Form(""),
    lugar: str = Form(""),
    nota: str = Form(""),
    volver: str = Form(""),
    db: Session = Depends(get_db),
):
    get_current_profesor(request, db)
    if not db.query(User).filter(User.id == atleta_id, User.role == "atleta").first():
        raise HTTPException(status_code=404, detail="No existe ese atleta.")
    if not pruebas.existe(prueba):
        return RedirectResponse(url="/marcas?error=prueba", status_code=302)

    numero = _valor(valor, prueba)
    if numero is None or numero <= 0 or numero > VALOR_MAXIMO:
        return RedirectResponse(url="/marcas?error=valor", status_code=302)

    try:
        cuando = date.fromisoformat(fecha) if fecha else hoy()
    except ValueError:
        cuando = hoy()

    aire = None
    if viento.strip():
        try:
            aire = Decimal(viento.strip().replace(",", "."))
        except InvalidOperation:
            return RedirectResponse(url="/marcas?error=viento", status_code=302)
        if abs(aire) > VIENTO_MAXIMO:
            return RedirectResponse(url="/marcas?error=viento", status_code=302)

    db.add(Marca(
        atleta_id=atleta_id, prueba=prueba, fecha=cuando, valor=numero,
        viento=aire, es_competencia=es_competencia == "si",
        competencia=competencia.strip()[:120] or None,
        lugar=lugar.strip()[:120] or None,
        nota=nota.strip()[:200] or None,
    ))
    db.commit()
    destino = ruta_interna(volver, "/marcas")
    return RedirectResponse(url=destino, status_code=302)


@router.post("/{marca_id}/borrar", response_class=HTMLResponse)
async def borrar(marca_id: int, request: Request, volver: str = Form(""),
                 db: Session = Depends(get_db)):
    get_current_profesor(request, db)
    marca = db.query(Marca).filter(Marca.id == marca_id).first()
    if not marca:
        raise HTTPException(status_code=404, detail="No existe esa marca.")
    db.delete(marca)
    db.commit()
    destino = ruta_interna(volver, "/marcas")
    return RedirectResponse(url=destino, status_code=302)
