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
    # La app se renderiza entera en el servidor: no hay ninguna API que consumir
    # desde afuera, y /docs abierto le publica el mapa completo de rutas a
    # cualquiera que pase por la dirección, sin necesidad de tener cuenta.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# El login maneja su propio flujo: en el primer GET todavía no hay cookie contra
# la cual firmar el formulario.
_CSRF_EXENTA = {"/auth/login"}

# Todo lo que puede cambiar algo tiene que traer el token. No alcanza con mirar
# los POST con cuerpo de formulario: cualquier método que escriba entra acá.
_METODOS_INSEGUROS = {"POST", "PUT", "PATCH", "DELETE"}


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

        # La validación se decide por el MÉTODO, no por el content-type. Cuando
        # dependía del content-type, mandar el mismo POST con "application/json"
        # salteaba el control entero y llegaba al handler: los endpoints cuyos
        # campos de formulario tienen todos valor por defecto (borrar un pago,
        # resetear una contraseña, dar de baja a un atleta) se ejecutaban igual.
        content_type = request.headers.get("content-type", "")
        if request.method in _METODOS_INSEGUROS and request.url.path not in _CSRF_EXENTA:
            body = await request.body()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            request._receive = receive

            # Si el cuerpo no es un formulario no hay de dónde sacar el token, y
            # queda en "" -> 403. Es lo correcto: la app no recibe otra cosa.
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


# Todo lo que la app carga es propio, tipografías incluidas (ver
# static/css/fuentes.css), así que no hay ningún origen externo en la política.
# Los estilos sí necesitan 'unsafe-inline': hay style="…" repartidos por las
# plantillas, y una inyección de estilo no es comparable a una de script (que acá
# queda bloqueada). 'form-action' es la segunda red contra los redirects a otro
# sitio: aunque a alguien se le escape un destino sin validar, el formulario no
# sale de la app.
_CSP = ("default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' data:; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'")

_CABECERAS = {
    "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    # same-origin: los links a WhatsApp y a worldathletics.org salen sin decirle a
    # esos sitios desde qué pantalla del club se los abrió.
    "Referrer-Policy": "same-origin",
}


class CabecerasSeguridadMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for nombre, valor in _CABECERAS.items():
            response.headers.setdefault(nombre, valor)
        return response


app.add_middleware(CabecerasSeguridadMiddleware)


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


@app.exception_handler(Exception)
async def error_interno(request: Request, exc: Exception):
    """Cualquier error no previsto, con la cara de la app.

    Sin esto el atleta que llega a un caso raro ve el "Internal Server Error"
    pelado de uvicorn, que no le dice qué hacer y parece que la app se rompió del
    todo. Starlette vuelve a levantar la excepción después de mandar esta
    respuesta, así que el traceback sigue apareciendo entero en el log del
    servicio: esto cambia lo que ve la persona, no lo que se registra.
    """
    return _templates.TemplateResponse(request, "500.html", {}, status_code=500)


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
