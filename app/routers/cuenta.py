from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_user_libre, hash_password, verify_password
from ..services import bienestar
from ..tiempo import lunes_actual

router = APIRouter(prefix="/cuenta", tags=["cuenta"])

MINIMO = 8


def _parte_pendiente(db: Session, user) -> bool:
    """Si al atleta le falta el parte de esta semana, para el globo del menú."""
    if user.role != "atleta":
        return False
    return bienestar.parte_de_semana(db, user.id, lunes_actual()) is None


@router.get("", response_class=HTMLResponse)
async def cuenta(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_libre(request, db)
    return templates.TemplateResponse(request, "cuenta.html", {
        "user": user,
        "parte_pendiente": _parte_pendiente(db, user),
        # Cuando llega redirigido porque todavía tiene la contraseña provisoria,
        # la pantalla se lo explica en vez de mostrarle un formulario suelto.
        "obligatorio": user.debe_cambiar_password,
    })


@router.post("", response_class=HTMLResponse)
async def cambiar_password(
    request: Request,
    actual: str = Form(""),
    nueva: str = Form(""),
    repetir: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user_libre(request, db)
    errores = []

    if not verify_password(actual, user.hashed_password):
        errores.append("La contraseña actual no es correcta.")
    if len(nueva) < MINIMO:
        errores.append(f"La contraseña nueva tiene que tener al menos {MINIMO} caracteres.")
    if nueva != repetir:
        errores.append("Las dos contraseñas nuevas no coinciden.")
    if nueva and nueva == actual:
        errores.append("La contraseña nueva tiene que ser distinta de la actual.")

    if errores:
        return templates.TemplateResponse(request, "cuenta.html", {
            "user": user, "errores": errores, "obligatorio": user.debe_cambiar_password,
            "parte_pendiente": _parte_pendiente(db, user),
        }, status_code=422)

    user.hashed_password = hash_password(nueva)
    user.debe_cambiar_password = False
    db.commit()
    destino = "/panel" if user.role == "profesor" else "/inicio"
    return RedirectResponse(url=f"{destino}?password=1", status_code=302)
