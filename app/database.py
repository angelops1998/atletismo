from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import get_settings
from .tiempo import NOMBRE_TZ

settings = get_settings()

# Los tests corren sobre SQLite en memoria (ver tests/conftest.py) y su pool no
# entiende estas opciones: se aplican solo cuando la base es la de verdad.
_ES_POSTGRES = settings.database_url.startswith("postgresql")

_OPCIONES_POOL = {
    "pool_pre_ping": True,
    # El pooler de Supabase corta las conexiones que quedan ociosas, y en el plan
    # free de Render el servicio se duerme entre visita y visita: sin reciclar,
    # la primera consulta después de un rato falla con "server closed the
    # connection unexpectedly".
    "pool_recycle": 300,
    # Modesto a propósito: son 2 workers de gunicorn contra el pooler compartido
    # de Supabase, y un club de 30 personas no necesita más conexiones abiertas.
    "pool_size": 5,
    "max_overflow": 5,
} if _ES_POSTGRES else {}

engine = create_engine(settings.database_url, **_OPCIONES_POOL)


if _ES_POSTGRES:
    @event.listens_for(engine, "connect")
    def _zona_horaria_de_la_sesion(dbapi_connection, connection_record):
        """Abre cada conexión en la hora local del club.

        El servidor corre en UTC y sin esto las columnas timestamptz (enviado,
        creado…) vuelven adelantadas: un parte cargado el domingo a la noche se
        muestra con fecha del lunes. Fijándolo acá se arregla en toda la app de
        una vez, sin convertir en cada template.

        Va como sentencia después de conectar y no como parámetro de arranque
        (`options=-c timezone=…`, que es como estaba cuando la base vivía en el
        mismo VPS): a través del pooler de Supabase los parámetros de arranque no
        siempre llegan, y una sentencia sí.
        """
        autocommit_previo = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        try:
            with dbapi_connection.cursor() as cur:
                cur.execute("SELECT set_config('timezone', %s, false)", (NOMBRE_TZ,))
        finally:
            dbapi_connection.autocommit = autocommit_previo


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
