from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import (authenticate_user, create_access_token,
                    get_current_user_optional, set_auth_cookie)

router = APIRouter(prefix="/auth", tags=["auth"])


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

    user = authenticate_user(db, identificador, password)
    if not user:
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": "Usuario o contraseña incorrectos.",
            "next": next, "form": {"identificador": identificador},
        }, status_code=401)
    if not user.is_active:
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": "Tu cuenta está desactivada. Hablá con el profesor.",
            "next": next,
        }, status_code=401)

    token = create_access_token(data={"sub": user.username})
    # `next` solo se respeta si es una ruta interna: si no, un link armado desde
    # afuera podría usar el login para mandar a alguien a otro sitio.
    destino = next if next.startswith("/") and not next.startswith("//") else _destino(user)
    response = RedirectResponse(url=destino, status_code=302)
    set_auth_cookie(response, token)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
