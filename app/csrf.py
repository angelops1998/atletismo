import hmac
import hashlib
import secrets
from fastapi import Request, HTTPException
from .config import get_settings

_COOKIE = "csrf_token"

def _sign(token: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


def get_csrf_token(request: Request) -> str:
    token = request.cookies.get(_COOKIE)
    if not token:
        token = secrets.token_hex(32)
    return token


def set_csrf_cookie(response, token: str):
    # Sin max_age sería una cookie de sesión del navegador: al cerrarlo se pierde
    # y las pestañas restauradas quedan con un formulario firmado contra un token
    # que ya no existe -> 403 al enviarlo. Le damos la misma vida que la sesión
    # para que el par cookie/formulario sobreviva junto con el login.
    settings = get_settings()
    response.set_cookie(
        _COOKIE, token,
        httponly=False,
        samesite="strict",
        secure=settings.https_only,
        max_age=settings.access_token_expire_minutes * 60,
    )


def validate_csrf(request: Request, form_token: str):
    cookie_token = request.cookies.get(_COOKIE)
    if not cookie_token or not form_token:
        raise HTTPException(status_code=403, detail="Token CSRF inválido.")
    expected = _sign(cookie_token)
    if not hmac.compare_digest(expected, form_token):
        raise HTTPException(status_code=403, detail="Token CSRF inválido.")
