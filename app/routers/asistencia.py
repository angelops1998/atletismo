"""Tomar lista de un día de entrenamiento."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_profesor
from ..models.user import User
from ..models.asistencia import Asistencia, ESTADOS
from ..tiempo import hoy

router = APIRouter(prefix="/asistencia", tags=["asistencia"])

DIAS_RESUMEN = 30


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, fecha: str | None = None,
                db: Session = Depends(get_db)):
    """La lista del día, con todos los atletas y su estado actual.

    Se muestra el padrón entero y no solo a los presentes: tomar lista es marcar
    quién falta, y para eso hay que ver a todos.
    """
    user = get_current_profesor(request, db)
    try:
        dia = date.fromisoformat(fecha) if fecha else hoy()
    except ValueError:
        dia = hoy()

    atletas = (db.query(User)
               .filter(User.role == "atleta", User.is_active.is_(True))
               .order_by(User.full_name, User.username).all())
    marcadas = {a.atleta_id: a for a in db.query(Asistencia)
                .filter(Asistencia.fecha == dia).all()}

    # Cuánto vino cada uno en el último mes: un atleta que baja la asistencia
    # normalmente está por dejar el club, y conviene llamarlo antes de que se vaya.
    desde = dia - timedelta(days=DIAS_RESUMEN)
    historial = (db.query(Asistencia)
                 .filter(Asistencia.fecha >= desde, Asistencia.fecha <= dia).all())
    conteo: dict[int, list[int]] = {}
    for a in historial:
        totales = conteo.setdefault(a.atleta_id, [0, 0])
        totales[1] += 1
        if a.estado == "presente":
            totales[0] += 1

    filas = []
    for a in atletas:
        presentes, tomadas = conteo.get(a.id, [0, 0])
        filas.append({
            "atleta": a,
            "estado": marcadas[a.id].estado if a.id in marcadas else None,
            "presentes": presentes,
            "tomadas": tomadas,
            "pct": round(presentes / tomadas * 100) if tomadas else None,
        })

    return templates.TemplateResponse(request, "panel/asistencia.html", {
        "user": user, "dia": dia, "filas": filas, "estados": ESTADOS,
        "anterior": dia - timedelta(days=1), "siguiente": dia + timedelta(days=1),
        "es_hoy": dia == hoy(),
        "tomadas_hoy": len(marcadas),
        "guardado": request.query_params.get("ok") == "1",
    })


@router.post("", response_class=HTMLResponse)
async def guardar(request: Request, db: Session = Depends(get_db)):
    """Guarda la lista entera de una vez.

    Va todo en un solo POST y no uno por atleta: el profesor toma lista en la
    pista, con el celular en la mano y a veces sin señal, y treinta requests
    sueltas dejarían la lista cargada a medias.
    """
    get_current_profesor(request, db)
    form = await request.form()
    try:
        dia = date.fromisoformat(str(form.get("fecha", "")))
    except ValueError:
        dia = hoy()

    existentes = {a.atleta_id: a for a in db.query(Asistencia)
                  .filter(Asistencia.fecha == dia).all()}

    # El mismo padrón que arma la pantalla del GET. Sin cotejar contra él, lo que
    # viniera en un campo "estado_<id>" entraba a la tabla tal cual: la clave
    # foránea frena los ids inexistentes, pero no el del propio profesor ni el de
    # un atleta dado de baja, que no tienen por qué estar en una lista.
    validos = {fila[0] for fila in db.query(User.id)
               .filter(User.role == "atleta", User.is_active.is_(True)).all()}

    for clave, valor in form.multi_items():
        if not clave.startswith("estado_"):
            continue
        try:
            atleta_id = int(clave.removeprefix("estado_"))
        except ValueError:
            continue
        if atleta_id not in validos:
            continue

        registro = existentes.get(atleta_id)
        if valor not in ESTADOS:
            # "Sin marcar" borra la fila: es distinto de "ausente". Un día que el
            # profesor no tomó lista no puede contar como faltas de todos.
            if registro:
                db.delete(registro)
            continue
        if registro:
            registro.estado = valor
        else:
            db.add(Asistencia(atleta_id=atleta_id, fecha=dia, estado=valor))

    db.commit()
    return RedirectResponse(url=f"/asistencia?fecha={dia.isoformat()}&ok=1", status_code=302)
