from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
import secrets
import re

from .routers import (publico, auth as auth_router, panel, parte, atletas, pagos,
                      asistencia, marcas, estadisticas, cuenta)
from .auth import (NotAuthenticatedException, DebeCambiarPassword,
                   refrescar_token, set_auth_cookie)
from .csrf import set_csrf_cookie, validate_csrf
from .config import get_settings

# El mismo entorno que usan los routers: las páginas de error extienden base.html,
# que necesita los globals de templates_config (static(), csrf_input…).
from .templates_config import templates as _templates

app = FastAPI(
    title=f"{get_settings().club_nombre} — Gestión de atletas",
    version="0.1.0",
)

# El login maneja su propio flujo: en el primer GET todavía no hay cookie contra
# la cual firmar el formulario.
_CSRF_EXENTA = {"/auth/login"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Si todavía no hay cookie, generarla ANTES de procesar la request e
        # inyectarla en el header "cookie" del scope: así el token que se firma en
        # los formularios renderizados coincide con la cookie que se le termina
        # mandando al navegador. Sin esto quedaban desincronizados y el primer
        # POST de una sesión nueva fallaba con 403.
        nueva_cookie = None
        if "csrf_token" not in request.cookies:
            nueva_cookie = secrets.token_hex(32)
            headers = MutableHeaders(scope=request.scope)
            existente = headers.get("cookie", "")
            headers["cookie"] = (existente + "; " if existente else "") + f"csrf_token={nueva_cookie}"

        content_type = request.headers.get("content-type", "")
        es_form = ("application/x-www-form-urlencoded" in content_type or
                   "multipart/form-data" in content_type)
        if request.method == "POST" and es_form and request.url.path not in _CSRF_EXENTA:
            body = await request.body()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            request._receive = receive

            form_token = ""
            if "application/x-www-form-urlencoded" in content_type:
                from urllib.parse import parse_qs
                parsed = parse_qs(body.decode("utf-8", errors="replace"))
                form_token = parsed.get("csrf_token", [""])[0]
            elif "multipart/form-data" in content_type:
                decoded = body.decode("utf-8", errors="replace")
                m = re.search(r'name="csrf_token"\r\n\r\n([^\r\n]+)', decoded)
                form_token = m.group(1) if m else ""

            try:
                validate_csrf(request, form_token)
            except HTTPException:
                return _templates.TemplateResponse(request, "403.html", {}, status_code=403)

        response = await call_next(request)
        if nueva_cookie is not None:
            set_csrf_cookie(response, nueva_cookie)
        return response


app.add_middleware(CSRFMiddleware)

# Rutas que manejan la cookie de sesión por su cuenta (no hay que pisarles nada)
_SESION_EXENTA = {"/auth/login", "/auth/logout"}


class SesionDeslizanteMiddleware(BaseHTTPMiddleware):
    """Corre el vencimiento de la sesión en cada visita.

    El atleta entra una vez por semana desde el celular: con un vencimiento fijo
    se le cortaría la sesión entre parte y parte, y el que tiene que volver a
    tipear la contraseña simplemente no carga el parte.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        token = request.cookies.get("access_token")
        if token and request.url.path not in _SESION_EXENTA:
            nuevo = refrescar_token(token)
            if nuevo:
                set_auth_cookie(response, nuevo)
        return response


app.add_middleware(SesionDeslizanteMiddleware)


@app.exception_handler(NotAuthenticatedException)
async def no_autenticado(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse(url=f"/auth/login?next={exc.next_url}", status_code=302)


@app.exception_handler(DebeCambiarPassword)
async def debe_cambiar_password(request: Request, exc: DebeCambiarPassword):
    return RedirectResponse(url="/cuenta?cambiar=1", status_code=302)


@app.exception_handler(404)
async def no_encontrado(request: Request, exc: HTTPException):
    return _templates.TemplateResponse(request, "404.html", {}, status_code=404)


@app.exception_handler(403)
async def prohibido(request: Request, exc: HTTPException):
    return _templates.TemplateResponse(
        request, "403.html", {"detalle": getattr(exc, "detail", None)}, status_code=403)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(publico.router)
app.include_router(auth_router.router)
app.include_router(panel.router)
app.include_router(parte.router)
app.include_router(atletas.router)
app.include_router(pagos.router)
app.include_router(asistencia.router)
app.include_router(marcas.router)
app.include_router(estadisticas.router)
app.include_router(cuenta.router)
