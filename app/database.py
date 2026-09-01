from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import get_settings
from .tiempo import NOMBRE_TZ

settings = get_settings()

# La sesión de Postgres trabaja en hora local del club: el servidor corre en UTC
# y sin esto las columnas timestamptz (enviado, creado…) vuelven adelantadas y un
# parte cargado el domingo a la noche se muestra con fecha del lunes. Fijándolo
# acá se arregla en toda la app de una vez, sin convertir en cada template.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"options": f"-c timezone={NOMBRE_TZ}"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
