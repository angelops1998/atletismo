"""La página de promoción del club, que es lo único que se ve sin cuenta."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..templates_config import templates
from ..database import get_db
from ..auth import get_current_user_optional

router = APIRouter(tags=["publico"])


@router.get("/", response_class=HTMLResponse)
async def inicio(request: Request, db: Session = Depends(get_db)):
    """La landing para quien no tiene sesión; para el resto, su pantalla.

    La raíz hace las dos cosas porque es la dirección que la gente escribe y la
    que queda guardada en el celular: al atleta que ya entró una vez le tiene que
    abrir directamente su parte, no la página de promoción.
    """
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(
            url="/panel" if user.role == "profesor" else "/inicio", status_code=302)
    return templates.TemplateResponse(request, "publico/landing.html", {})


@router.get("/club", response_class=HTMLResponse)
async def landing(request: Request, db: Session = Depends(get_db)):
    """La misma landing, pero sin el redirect: el enlace "Ver la página del
    club" del menú usa esta ruta para que quien ya tiene sesión también pueda
    verla, en vez de rebotar de vuelta a su panel.

    Se le pasa el usuario (si lo hay) porque la sección "Entrenamos con datos"
    solo se muestra a quien tiene cuenta: el club no quiere exhibir el sistema
    de seguimiento a quien todavía no está inscripto."""
    return templates.TemplateResponse(request, "publico/landing.html", {
        "user": get_current_user_optional(request, db),
    })
