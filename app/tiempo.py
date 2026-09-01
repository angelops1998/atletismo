"""Hora local del club: Bolivia (America/La_Paz, UTC-4).

El servidor de producción corre en UTC, así que `date.today()` devuelve el día
equivocado a partir de las 20:00 hora local: un parte cargado el domingo a la
noche caía en la semana siguiente y quedaba fuera del control del profesor.
Todo el código que necesite "hoy" o "ahora" tiene que usar `hoy()` y `ahora()`.

Si el club no está en Bolivia, esta constante es lo único que hay que tocar:
la sesión de Postgres se abre con esta misma zona (ver database.py), así que las
columnas timestamptz ya vuelven en hora local sin convertir nada en los templates.
"""
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

NOMBRE_TZ = "America/La_Paz"
TZ = ZoneInfo(NOMBRE_TZ)


def ahora() -> datetime:
    """Fecha y hora actuales del club, con tzinfo."""
    return datetime.now(TZ)


def hoy() -> date:
    """El día de hoy en el club (no el del servidor)."""
    return ahora().date()


def lunes_de(dia: date) -> date:
    """El lunes de la semana a la que pertenece `dia`.

    Es la clave con la que se guarda el parte semanal. Toda la app identifica una
    semana por su lunes: así "esta semana" significa lo mismo para el atleta que
    carga el domingo a la noche y para el profesor que mira el lunes a la mañana.
    """
    return dia - timedelta(days=dia.weekday())


def lunes_actual() -> date:
    """El lunes de la semana en curso."""
    return lunes_de(hoy())
