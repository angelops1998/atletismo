"""Las dos pantallas de inicio: la del profesor y la del atleta."""
from datetime import timedelta
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_user, get_current_profesor
from ..models.user import User
from ..models.marca import Marca
from ..services import bienestar, cobranza, grafico, pruebas, seguimiento_diario
from ..tiempo import hoy, lunes_actual

router = APIRouter(tags=["panel"])

SEMANAS_PANEL = 12


@router.get("/panel", response_class=HTMLResponse)
async def panel(request: Request, db: Session = Depends(get_db)):
    """Lo primero que ve el profesor: qué pasó esta semana y a quién hay que ver.

    El orden de la pantalla es deliberado: primero las alertas (lo que hay que
    hacer hoy), después los números del grupo. Si arranca con los gráficos, el
    profesor se queda mirando tendencias y no ve que hay un atleta con dolor 8/10.
    """
    user = get_current_profesor(request, db)
    try:
        fecha = seguimiento_diario.parsear_fecha_filtro(
            request.query_params.get("fecha"), "fecha") or hoy()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    atletas = (db.query(User)
               .filter(User.role == "atleta", User.is_active.is_(True))
               .order_by(User.full_name, User.username).all())
    reportes = seguimiento_diario.reportes_de_fecha(db, fecha, [a.id for a in atletas])
    por_atleta = {r.atleta_id: r for r in reportes}
    sin_cargar = [a for a in atletas if a.id not in por_atleta]
    con_alerta = [r for r in reportes if r.hay_molestia or r.sintomas_enfermedad]
    finanzas = cobranza.resumen_club(db)

    return templates.TemplateResponse(request, "panel/panel.html", {
        "user": user,
        "fecha": fecha,
        "total_atletas": len(atletas),
        "reportes": reportes,
        "atletas_por_id": {a.id: a for a in atletas},
        "cargados": len(reportes),
        "sin_cargar": sin_cargar,
        "con_alerta": con_alerta,
        "con_molestias": sum(1 for r in reportes if r.hay_molestia),
        "con_sintomas": sum(1 for r in reportes if r.sintomas_enfermedad),
        "entrenaron": sum(1 for r in reportes if r.entreno_hoy),
        "no_entrenaron": sum(1 for r in reportes if not r.entreno_hoy),
        "finanzas": finanzas,
    })


@router.get("/inicio", response_class=HTMLResponse)
async def inicio(request: Request, db: Session = Depends(get_db)):
    """La pantalla del atleta: sobre todo, el botón para cargar el parte.

    Todo lo demás (su evolución, sus marcas, su cuota) va abajo. Lo único que
    tiene que poder hacer sin pensar, con una mano y desde el vestuario, es
    cargar el parte de la semana.
    """
    user = get_current_user(request, db)
    if user.role == "profesor":
        return await panel(request, db)

    semana = lunes_actual()
    anterior = semana - timedelta(weeks=1)
    parte = bienestar.parte_de_semana(db, user.id, semana)
    serie = bienestar.serie_individual(db, user.id, SEMANAS_PANEL)
    estado = cobranza.estado_cuenta(db, user)

    ultimas_marcas = (db.query(Marca)
                      .filter(Marca.atleta_id == user.id)
                      .order_by(Marca.fecha.desc(), Marca.id.desc())
                      .limit(5).all())

    return templates.TemplateResponse(request, "atleta/inicio.html", {
        "user": user,
        "semana": semana,
        "parte": parte,
        "bienestar_total": bienestar.bienestar_total(parte) if parte else None,
        "maximo": bienestar.MAXIMO,
        "serie": serie,
        "grafico_bienestar": grafico.linea([f["bienestar"] for f in serie],
                                           minimo=bienestar.MINIMO, maximo=bienestar.MAXIMO, alto=140),
        "falta_anterior": bienestar.parte_de_semana(db, user.id, anterior) is None,
        "semana_anterior": anterior,
        "estado_cuenta": estado,
        "marcas": ultimas_marcas,
        "pruebas": pruebas,
        "parte_pendiente": parte is None,
        "guardado": request.query_params.get("parte") == "1",
        "password_cambiada": request.query_params.get("password") == "1",
    })


@router.get("/mis-datos", response_class=HTMLResponse)
async def mis_datos(request: Request, db: Session = Depends(get_db)):
    """La evolución del atleta, con sus propios datos.

    Es la contrapartida de pedirle un parte por semana: si el atleta no ve nunca
    para qué sirve lo que carga, deja de cargarlo a las pocas semanas.
    """
    from ..models.asistencia import Asistencia

    user = get_current_user(request, db)
    if user.role != "atleta":
        return RedirectResponse(url="/estadisticas", status_code=302)

    semanas = 16
    serie = bienestar.serie_individual(db, user.id, semanas)
    cargados = [f["bienestar"] for f in serie if f["bienestar"] is not None]

    marcas = (db.query(Marca).filter(Marca.atleta_id == user.id)
              .order_by(Marca.fecha).all())
    por_prueba: dict[str, list] = {}
    for m in marcas:
        por_prueba.setdefault(m.prueba, []).append(m)
    resumen_pruebas = [{
        "clave": clave,
        "nombre": pruebas.nombre(clave),
        "mejor": pruebas.mejor(clave, [m.valor for m in lista]),
        "marcas": lista,
        "grafico": grafico.linea([float(m.valor) for m in lista], alto=130),
    } for clave, lista in por_prueba.items()]

    asistencias = db.query(Asistencia).filter(Asistencia.atleta_id == user.id).all()

    return templates.TemplateResponse(request, "atleta/mis_datos.html", {
        "user": user,
        "serie": serie,
        "parte_pendiente": serie[-1]["parte"] is None if serie else True,
        "cargados": len(cargados),
        "promedio_bienestar": round(sum(cargados) / len(cargados), 1) if cargados else None,
        "promedio_sueno": bienestar.promedio([f["sueno"] for f in serie]),
        "presentes": sum(1 for a in asistencias if a.estado == "presente"),
        "tomadas": len(asistencias),
        "maximo": bienestar.MAXIMO,
        "grafico_bienestar": grafico.linea([f["bienestar"] for f in serie],
                                           minimo=bienestar.MINIMO, maximo=bienestar.MAXIMO, alto=150),
        "grafico_sueno": grafico.linea([f["sueno"] for f in serie], alto=130),
        "grafico_carga": grafico.barras([f["carga"] for f in serie], alto=130),
        "resumen_pruebas": resumen_pruebas,
        "pruebas": pruebas,
    })
