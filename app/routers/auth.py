from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import (authenticate_user, create_access_token, huella_password,
                    get_current_user_optional, set_auth_cookie)
from ..tiempo import ahora
from ..urls import ruta_interna

router = APIRouter(prefix="/auth", tags=["auth"])

# --- Freno de fuerza bruta ---
# No hay registro público ni recuperación por correo, así que la única puerta es
# este formulario, y el usuario del profesor es adivinable ("profe"). Sin ningún
# freno se le pueden tirar miles de contraseñas por minuto.
#
# El registro vive en memoria del proceso: con 30 personas no justifica una tabla
# ni Redis, y aunque gunicorn levante 2 workers y cada uno lleve su propia cuenta,
# el techo real sigue siendo un puñado de intentos por ventana en vez de infinito.
INTENTOS_MAX = 8
VENTANA = timedelta(minutes=15)
_MAX_CLAVES = 2000            # tope del diccionario, por si alguien rota usuarios

_fallos: dict[str, list] = {}


def _ip_del_cliente(request: Request) -> str:
    """La IP de quien hace el pedido, sin dejar que la elija él mismo.

    En Render la app está detrás de un proxy, así que `request.client.host` es
    siempre la misma IP (la del proxy) y el freno dejaría de distinguir entre
    personas. La IP real viaja en X-Forwarded-For, pero **Render no descarta el
    header que venga de afuera: le agrega la suya al final**. O sea que las
    entradas de la izquierda las puede escribir el atacante, y si se leyera la
    primera —que es lo que hace uvicorn con `--forwarded-allow-ips=*`— bastaría
    con rotar ese header para tener intentos infinitos.

    Por eso se lee la **última**, que es la que agregó el proxy: puede ser la del
    cliente o la de un proxy intermedio, pero nunca una inventada. En el peor
    caso queda constante y el freno cuenta por usuario, que es como se comportaba
    antes; en el mejor separa por persona.
    """
    reenviadas = request.headers.get("x-forwarded-for", "")
    if reenviadas:
        return reenviadas.rsplit(",", 1)[-1].strip()
    return request.client.host if request.client else "?"


def _clave(request: Request, identificador: str) -> str:
    """IP + usuario. Se cuenta por par y no solo por usuario a propósito: contando
    solo por usuario, cualquiera podría dejar al profesor afuera de su propio
    sistema tirándole contraseñas mal a propósito."""
    return f"{_ip_del_cliente(request)}|{identificador.strip().lower()}"


def _recientes(clave: str) -> list:
    corte = ahora() - VENTANA
    quedan = [t for t in _fallos.get(clave, []) if t > corte]
    if quedan:
        _fallos[clave] = quedan
    else:
        _fallos.pop(clave, None)
    return quedan


def _bloqueado(clave: str) -> bool:
    return len(_recientes(clave)) >= INTENTOS_MAX


def _anotar_fallo(clave: str) -> None:
    if len(_fallos) > _MAX_CLAVES:
        for otra in list(_fallos):
            _recientes(otra)
    _fallos.setdefault(clave, []).append(ahora())


def _destino(user) -> str:
    """Adónde va cada rol después de entrar."""
    return "/panel" if user.role == "profesor" else "/inicio"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url=_destino(user), status_code=302)
    return templates.TemplateResponse(request, "auth/login.html", {
        "next": request.query_params.get("next", ""),
    })


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    identificador: str = Form(""),
    password: str = Form(""),
    next: str = Form(""),
    db: Session = Depends(get_db),
):
    # Validación a mano para devolver el error en HTML y no un JSON de FastAPI:
    # el atleta que se equivoca la contraseña en el celular tiene que ver el
    # formulario de nuevo, no una pantalla de error de la API.
    password = password.strip()
    if not identificador.strip() or not password:
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": "Completá tu usuario y tu contraseña.",
            "next": next, "form": {"identificador": identificador},
        }, status_code=422)

    clave = _clave(request, identificador)
    if _bloqueado(clave):
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": ("Demasiados intentos fallidos. Esperá unos minutos y probá "
                      "de nuevo, o pedile la contraseña al profesor."),
            "next": next, "form": {"identificador": identificador},
        }, status_code=429)

    user = authenticate_user(db, identificador, password)
    if not user:
        _anotar_fallo(clave)
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": "Usuario o contraseña incorrectos.",
            "next": next, "form": {"identificador": identificador},
        }, status_code=401)
    if not user.is_active:
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": "Tu cuenta está desactivada. Hablá con el profesor.",
            "next": next,
        }, status_code=401)

    _fallos.pop(clave, None)
    token = create_access_token(data={"sub": user.username,
                                      "pv": huella_password(user.hashed_password)})
    # `next` solo se respeta si es una ruta interna: si no, un link armado desde
    # afuera podría usar el login para mandar a alguien a otro sitio.
    response = RedirectResponse(url=ruta_interna(next, _destino(user)), status_code=302)
    set_auth_cookie(response, token)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
