"""Padrón de atletas: alta, ficha y edición. Todo esto es solo del profesor."""
from datetime import date
from decimal import Decimal, InvalidOperation
import secrets
import unicodedata

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_profesor, hash_password
from ..models.user import User
from ..models.marca import Marca
from ..models.pago import Pago
from ..models.asistencia import Asistencia
from ..services import bienestar, alertas, cobranza, grafico, pruebas
from ..tiempo import hoy, lunes_actual

router = APIRouter(prefix="/atletas", tags=["atletas"])

SEMANAS_FICHA = 16


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _usuario_sugerido(db: Session, nombre: str) -> str:
    """Un usuario corto a partir del nombre: 'Juan Pérez' -> 'jperez'.

    Los atletas entran una vez por semana desde el celular: un usuario que se
    pueda dictar por teléfono y escribir sin errores baja mucho los logins
    fallidos. Si ya existe, se le agrega un número.
    """
    partes = [p for p in _sin_acentos(nombre.lower()).split() if p.isalpha()]
    if not partes:
        base = "atleta"
    elif len(partes) == 1:
        base = partes[0]
    else:
        base = partes[0][0] + partes[-1]
    base = base[:20] or "atleta"
    candidato, n = base, 1
    while db.query(User).filter(User.username == candidato).first():
        n += 1
        candidato = f"{base}{n}"
    return candidato


def _password_provisoria() -> str:
    """Una contraseña que se pueda dictar: sin caracteres que se confundan.

    El profesor se la pasa en mano al atleta y la app lo obliga a cambiarla al
    entrar (users.debe_cambiar_password), así que solo tiene que sobrevivir un
    viaje en papel, no ser eterna.
    """
    alfabeto = "abcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(10))


def _fecha(valor: str) -> date | None:
    try:
        return date.fromisoformat(valor.strip()) if valor and valor.strip() else None
    except ValueError:
        return None


def _monto(valor: str) -> Decimal:
    if not valor or not str(valor).strip():
        return Decimal(0)
    try:
        return Decimal(str(valor).strip().replace(".", "").replace(",", "."))
    except InvalidOperation:
        return Decimal(0)


def _obtener(db: Session, atleta_id: int) -> User:
    atleta = db.query(User).filter(User.id == atleta_id, User.role == "atleta").first()
    if not atleta:
        raise HTTPException(status_code=404, detail="No existe ese atleta.")
    return atleta


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db)):
    """El padrón con un semáforo por atleta: parte, alertas y pago.

    Es la pantalla que el profesor abre para saber a quién llamar, así que cada
    fila tiene que contestar eso sin entrar a la ficha.
    """
    user = get_current_profesor(request, db)
    ver_bajas = request.query_params.get("bajas") == "1"
    busqueda = (request.query_params.get("q") or "").strip()

    consulta = db.query(User).filter(User.role == "atleta")
    if not ver_bajas:
        consulta = consulta.filter(User.is_active.is_(True))
    if busqueda:
        patron = f"%{busqueda.lower()}%"
        consulta = consulta.filter(
            func.lower(func.coalesce(User.full_name, User.username)).like(patron))
    atletas = consulta.order_by(User.full_name, User.username).all()

    semana = lunes_actual()
    filas = []
    for a in atletas:
        parte = bienestar.parte_de_semana(db, a.id, semana)
        sus_alertas = alertas.del_atleta(db, a)
        filas.append({
            "atleta": a,
            "parte": parte,
            "semaforo": bienestar.semaforo(parte) if parte else None,
            "bienestar": bienestar.bienestar_total(parte) if parte else None,
            "cuenta": cobranza.estado_cuenta(db, a),
            "alertas": [x for x in sus_alertas if x["nivel"] == "alta"],
        })

    return templates.TemplateResponse(request, "panel/atletas.html", {
        "user": user, "filas": filas, "semana": semana,
        "ver_bajas": ver_bajas, "busqueda": busqueda,
        "maximo": bienestar.MAXIMO,
    })


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo(request: Request, db: Session = Depends(get_db)):
    user = get_current_profesor(request, db)
    return templates.TemplateResponse(request, "panel/atleta_form.html", {
        "user": user, "atleta": None, "pruebas": pruebas,
        "hoy": hoy(), "password_sugerida": _password_provisoria(),
    })


@router.post("/nuevo", response_class=HTMLResponse)
async def crear(
    request: Request,
    full_name: str = Form(""),
    username: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    fecha_nacimiento: str = Form(""),
    documento: str = Form(""),
    telefono: str = Form(""),
    categoria: str = Form(""),
    prueba_principal: str = Form(""),
    fecha_alta: str = Form(""),
    contacto_emergencia: str = Form(""),
    observaciones_medicas: str = Form(""),
    cuota_mensual: str = Form(""),
    cobro_desde: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_profesor(request, db)
    errores = []

    if not full_name.strip():
        errores.append("El nombre y apellido son obligatorios.")
    password = password.strip()
    if len(password) < 6:
        errores.append("La contraseña provisoria tiene que tener al menos 6 caracteres.")

    usuario = (username.strip().lower() or
               (_usuario_sugerido(db, full_name) if full_name.strip() else ""))
    if usuario and db.query(User).filter(User.username == usuario).first():
        errores.append(f"El usuario «{usuario}» ya está en uso.")

    alta = _fecha(fecha_alta) or hoy()
    if errores:
        return templates.TemplateResponse(request, "panel/atleta_form.html", {
            "user": user, "atleta": None, "pruebas": pruebas, "hoy": hoy(),
            "errores": errores, "form": await request.form(),
            "password_sugerida": password or _password_provisoria(),
        }, status_code=422)

    atleta = User(
        username=usuario,
        email=email.strip().lower() or None,
        hashed_password=hash_password(password),
        full_name=full_name.strip(),
        role="atleta",
        debe_cambiar_password=True,
        fecha_nacimiento=_fecha(fecha_nacimiento),
        documento=documento.strip() or None,
        telefono=telefono.strip() or None,
        categoria=categoria.strip() or None,
        prueba_principal=prueba_principal.strip() or None,
        fecha_alta=alta,
        contacto_emergencia=contacto_emergencia.strip() or None,
        observaciones_medicas=observaciones_medicas.strip() or None,
        cuota_mensual=_monto(cuota_mensual),
        # Por defecto se le empieza a cobrar el mes en que se dio de alta: si no,
        # aparecería debiendo meses en los que todavía no era del club.
        cobro_desde=_fecha(cobro_desde) or cobranza.primer_dia(alta),
    )
    try:
        db.add(atleta)
        db.commit()
        db.refresh(atleta)
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(request, "panel/atleta_form.html", {
            "user": user, "atleta": None, "pruebas": pruebas, "hoy": hoy(),
            "errores": ["Ese usuario o ese email ya están en uso."],
            "form": await request.form(), "password_sugerida": password,
        }, status_code=422)

    # La contraseña se muestra una sola vez, en la ficha: después queda hasheada
    # y ni el profesor ni nadie puede volver a verla.
    return RedirectResponse(url=f"/atletas/{atleta.id}?alta={password}", status_code=302)


@router.get("/{atleta_id}", response_class=HTMLResponse)
async def ficha(atleta_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_profesor(request, db)
    atleta = _obtener(db, atleta_id)

    serie = bienestar.serie_individual(db, atleta.id, SEMANAS_FICHA)
    marcas = (db.query(Marca).filter(Marca.atleta_id == atleta.id)
              .order_by(Marca.fecha.desc(), Marca.id.desc()).all())

    # Las marcas agrupadas por prueba, con la mejor de cada una: es como el
    # profesor las lee ("¿cómo viene en 100?"), no como una lista cronológica.
    por_prueba = {}
    for m in marcas:
        por_prueba.setdefault(m.prueba, []).append(m)
    resumen_pruebas = []
    for clave, lista_marcas in por_prueba.items():
        valores = [m.valor for m in lista_marcas]
        cronologico = sorted(lista_marcas, key=lambda m: m.fecha)
        resumen_pruebas.append({
            "clave": clave,
            "nombre": pruebas.nombre(clave),
            "mejor": pruebas.mejor(clave, valores),
            "ultima": cronologico[-1],
            "cantidad": len(lista_marcas),
            "marcas": cronologico,
            "grafico": grafico.linea([float(m.valor) for m in cronologico], alto=130),
            "progreso": pruebas.progreso_pct(
                clave, cronologico[-1].valor, cronologico[0].valor) if len(cronologico) > 1 else None,
        })
    resumen_pruebas.sort(key=lambda r: r["ultima"].fecha, reverse=True)

    asistencias = (db.query(Asistencia).filter(Asistencia.atleta_id == atleta.id)
                   .order_by(Asistencia.fecha.desc()).limit(30).all())
    presentes = sum(1 for a in asistencias if a.estado == "presente")

    pagos = (db.query(Pago).filter(Pago.atleta_id == atleta.id)
             .order_by(Pago.periodo.desc()).all())

    return templates.TemplateResponse(request, "panel/atleta_ficha.html", {
        "user": user, "atleta": atleta, "serie": serie, "items": bienestar.ITEMS,
        "alertas": alertas.del_atleta(db, atleta, serie),
        "acwr": alertas.acwr(serie),
        "grafico_bienestar": grafico.linea([f["bienestar"] for f in serie],
                                           minimo=5, maximo=25, alto=150),
        "grafico_carga": grafico.barras([f["carga"] for f in serie], alto=130),
        "grafico_sueno": grafico.linea([f["sueno"] for f in serie], alto=130),
        "grafico_peso": grafico.linea([f["peso"] for f in serie], alto=130),
        "tiene_peso": any(f["peso"] is not None for f in serie),
        "resumen_pruebas": resumen_pruebas,
        "pruebas": pruebas,
        "asistencias": asistencias,
        "presentes": presentes,
        "cuenta": cobranza.estado_cuenta(db, atleta),
        "pagos": pagos,
        "maximo": bienestar.MAXIMO,
        # Solo viene con valor justo después del alta, para poder dictársela.
        "password_nueva": request.query_params.get("alta"),
    })


@router.get("/{atleta_id}/editar", response_class=HTMLResponse)
async def editar(atleta_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_profesor(request, db)
    atleta = _obtener(db, atleta_id)
    return templates.TemplateResponse(request, "panel/atleta_form.html", {
        "user": user, "atleta": atleta, "pruebas": pruebas, "hoy": hoy(),
    })


@router.post("/{atleta_id}/editar", response_class=HTMLResponse)
async def guardar_edicion(
    atleta_id: int,
    request: Request,
    full_name: str = Form(""),
    email: str = Form(""),
    fecha_nacimiento: str = Form(""),
    documento: str = Form(""),
    telefono: str = Form(""),
    categoria: str = Form(""),
    prueba_principal: str = Form(""),
    fecha_alta: str = Form(""),
    contacto_emergencia: str = Form(""),
    observaciones_medicas: str = Form(""),
    cuota_mensual: str = Form(""),
    cobro_desde: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_profesor(request, db)
    atleta = _obtener(db, atleta_id)

    if not full_name.strip():
        return templates.TemplateResponse(request, "panel/atleta_form.html", {
            "user": user, "atleta": atleta, "pruebas": pruebas, "hoy": hoy(),
            "errores": ["El nombre y apellido son obligatorios."],
        }, status_code=422)

    atleta.full_name = full_name.strip()
    atleta.email = email.strip().lower() or None
    atleta.fecha_nacimiento = _fecha(fecha_nacimiento)
    atleta.documento = documento.strip() or None
    atleta.telefono = telefono.strip() or None
    atleta.categoria = categoria.strip() or None
    atleta.prueba_principal = prueba_principal.strip() or None
    atleta.fecha_alta = _fecha(fecha_alta) or atleta.fecha_alta
    atleta.contacto_emergencia = contacto_emergencia.strip() or None
    atleta.observaciones_medicas = observaciones_medicas.strip() or None
    atleta.cuota_mensual = _monto(cuota_mensual)
    atleta.cobro_desde = _fecha(cobro_desde) or atleta.cobro_desde
    db.commit()
    return RedirectResponse(url=f"/atletas/{atleta.id}", status_code=302)


@router.post("/{atleta_id}/password", response_class=HTMLResponse)
async def resetear_password(atleta_id: int, request: Request,
                            db: Session = Depends(get_db)):
    """Genera una contraseña provisoria nueva para el atleta que se la olvidó.

    Es la operación más frecuente de soporte del club, y no hay mail configurado:
    el profesor la genera acá y se la dice. Queda obligado a cambiarla al entrar.
    """
    get_current_profesor(request, db)
    atleta = _obtener(db, atleta_id)
    nueva = _password_provisoria()
    atleta.hashed_password = hash_password(nueva)
    atleta.debe_cambiar_password = True
    db.commit()
    return RedirectResponse(url=f"/atletas/{atleta.id}?alta={nueva}", status_code=302)


@router.post("/{atleta_id}/estado", response_class=HTMLResponse)
async def cambiar_estado(atleta_id: int, request: Request,
                         db: Session = Depends(get_db)):
    """Da de baja o reactiva a un atleta.

    Nunca se borra: sus partes, marcas y pagos son el historial del club, y
    borrar a alguien que vuelve el año siguiente es perder todo su seguimiento.
    Un atleta inactivo no cuenta para las estadísticas ni para la cobranza.
    """
    get_current_profesor(request, db)
    atleta = _obtener(db, atleta_id)
    atleta.is_active = not atleta.is_active
    db.commit()
    return RedirectResponse(url=f"/atletas/{atleta.id}", status_code=302)
