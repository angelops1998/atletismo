"""Andamiaje de los tests.

Dos reglas que valen para todo el suite:

* **Nunca se toca la base del club.** Las variables de entorno se fijan acá
  arriba, antes de importar nada de `app`, así los tests no dependen del `.env`
  de la máquina ni pueden escribir en la base de verdad por un descuido de
  configuración. La base de los tests es SQLite en memoria y se arma de cero en
  cada test.
* **Sin red y sin Postgres.** El suite tiene que correr en cualquier máquina con
  el repo clonado; si hiciera falta levantar servicios, se dejaría de correr.
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "clave-solo-para-los-tests-0123456789abcdef"
os.environ["HTTPS_ONLY"] = "false"

from datetime import date, timedelta  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.parte import ParteSemanal  # noqa: E402
from app.auth import hash_password, create_access_token, huella_password  # noqa: E402
from app.tiempo import lunes_actual  # noqa: E402


@pytest.fixture(autouse=True)
def _sin_intentos_previos():
    """El registro de logins fallidos vive en memoria del módulo. Si no se limpia,
    un test que agota los intentos deja bloqueado al siguiente y el suite pasa o
    falla según el orden en que corra."""
    from app.routers import auth as router_auth
    router_auth._fallos.clear()
    yield
    router_auth._fallos.clear()


@pytest.fixture
def db():
    """Una base vacía por test.

    StaticPool + una sola conexión: sin eso cada sesión de SQLite en memoria abre
    su propia base y las tablas creadas acá no se ven desde la app.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    sesion = Session()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()


@pytest.fixture
def contar_consultas(db):
    """Cuenta las consultas SQL que dispara un bloque de código.

        with contar_consultas() as n:
            client.get("/panel")
        assert n.total < 20
    """
    from contextlib import contextmanager
    from sqlalchemy import event

    motor = db.get_bind()

    class Cuenta:
        total = 0

    @contextmanager
    def medir():
        cuenta = Cuenta()

        def sumar(*a, **k):
            cuenta.total += 1

        event.listen(motor, "before_cursor_execute", sumar)
        try:
            yield cuenta
        finally:
            event.remove(motor, "before_cursor_execute", sumar)

    return medir


@pytest.fixture
def client(db):
    """Cliente HTTP contra la app real, con la base de test enchufada.

    `raise_server_exceptions=False` para poder comprobar que un error no previsto
    devuelve la pantalla de error de la app y no revienta el proceso.
    """
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# --- Ayudas para armar datos ---

def crear_usuario(db, username="atleta1", role="atleta", password="claveprueba1",
                  **campos) -> User:
    user = User(username=username, role=role, full_name=campos.pop("full_name", None),
                hashed_password=hash_password(password), **campos)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def crear_parte(db, atleta_id: int, semana: date, **campos) -> ParteSemanal:
    """Un parte con los cinco ítems en 4 salvo lo que se pise por nombre."""
    valores = {"sueno_calidad": 4, "fatiga": 4, "dolor_muscular": 4,
               "estres": 4, "animo": 4}
    valores.update(campos)
    parte = ParteSemanal(atleta_id=atleta_id, semana=semana, **valores)
    db.add(parte)
    db.commit()
    return parte


def semana(atras: int = 0) -> date:
    """El lunes de hace `atras` semanas."""
    return lunes_actual() - timedelta(weeks=atras)


def entrar(client, user: User) -> None:
    """Deja al cliente con la sesión de `user` abierta, sin pasar por el login."""
    client.cookies.set("access_token", create_access_token(
        {"sub": user.username, "pv": huella_password(user.hashed_password)}))


def con_csrf(client, url: str = "/auth/login") -> str:
    """Carga una pantalla para quedarse con la cookie CSRF y devuelve el token que
    va en el formulario, ya firmado."""
    respuesta = client.get(url)
    marca = 'name="csrf_token" value="'
    cuerpo = respuesta.text
    i = cuerpo.index(marca) + len(marca)
    return cuerpo[i:cuerpo.index('"', i)]


__all__ = ["crear_usuario", "crear_parte", "semana", "entrar", "con_csrf",
           "Decimal", "date", "timedelta"]
