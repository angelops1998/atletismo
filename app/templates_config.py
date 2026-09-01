from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from pathlib import Path
import hmac
import hashlib

from .tiempo import ahora, hoy
from .config import get_settings

templates = Jinja2Templates(directory="app/templates")

_STATIC = Path(__file__).resolve().parent / "static"

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _static(ruta: str) -> str:
    """URL de un estático con la fecha del archivo pegada (/static/css/main.css?v=175…).

    En producción nginx manda los estáticos con caché larga: sin esto, un arreglo
    de CSS no se ve hasta que al usuario se le vence la caché o hace Ctrl+F5, y en
    el celular eso puede tardar días.
    """
    try:
        version = int((_STATIC / ruta).stat().st_mtime)
    except OSError:
        return f"/static/{ruta}"
    return f"/static/{ruta}?v={version}"


def _csrf_input(request) -> Markup:
    cookie_token = request.cookies.get("csrf_token", "")
    firmado = hmac.new(get_settings().secret_key.encode(),
                       cookie_token.encode(), hashlib.sha256).hexdigest()
    return Markup(f'<input type="hidden" name="csrf_token" value="{firmado}">')


def pesos_filter(value, con_signo: bool = True, decimales: bool = False) -> str:
    """Formatea un monto: $ 25.000. La implementación está en cobranza.py, para
    que los montos dentro de los textos armados en Python (las alertas de deuda)
    se vean exactamente igual que los de las tablas."""
    from .services.cobranza import formato_pesos
    return formato_pesos(value, con_signo, decimales)


def fecha_filter(value, con_anio: bool = True) -> str:
    """3 de marzo de 2026. Vacío si no hay fecha."""
    if not value:
        return "—"
    if con_anio:
        return f"{value.day} de {MESES[value.month]} de {value.year}"
    return f"{value.day} de {MESES[value.month]}"


def fecha_corta_filter(value) -> str:
    """03/03/26 — para las tablas, donde el nombre del mes no entra."""
    if not value:
        return "—"
    return value.strftime("%d/%m/%y")


def mes_filter(value) -> str:
    """Marzo 2026 — para los períodos de cuota."""
    if not value:
        return "—"
    return f"{MESES[value.month].capitalize()} {value.year}"


def semana_filter(value) -> str:
    """Semana del 3 de marzo — así la nombra el profesor cuando habla con el atleta."""
    if not value:
        return "—"
    return f"semana del {value.day} de {MESES[value.month]}"


def duracion_filter(minutos) -> str:
    """95 -> 1 h 35 min. Las cargas semanales llegan a varias horas y en minutos
    puros no se leen."""
    try:
        m = int(minutos or 0)
    except (TypeError, ValueError):
        return "—"
    if m < 60:
        return f"{m} min"
    horas, resto = divmod(m, 60)
    return f"{horas} h" if resto == 0 else f"{horas} h {resto} min"


templates.env.globals["csrf_input"] = _csrf_input
templates.env.globals["static"] = _static
templates.env.globals["now"] = ahora
templates.env.globals["hoy"] = hoy
templates.env.globals["club"] = get_settings()
templates.env.filters["pesos"] = pesos_filter
templates.env.filters["fecha"] = fecha_filter
templates.env.filters["fecha_corta"] = fecha_corta_filter
templates.env.filters["mes"] = mes_filter
templates.env.filters["semana"] = semana_filter
templates.env.filters["duracion"] = duracion_filter
